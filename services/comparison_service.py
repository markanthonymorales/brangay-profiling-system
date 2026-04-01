import logging
from database.db import get_session
from database.models import (
    Barangay, District, PopulationRecord, IncomeData, Utility,
    CrimeIncident, WasteManagement,
)
from sqlalchemy import func, extract

logger = logging.getLogger(__name__)

# Supported metrics and which table/column they query
METRIC_CONFIG = {
    "population": {"model": PopulationRecord, "column": "total_population"},
    "income": {"model": IncomeData, "column": "average_household_income"},
    "water_coverage": {"model": Utility, "column": "water_coverage_pct"},
    "power_coverage": {"model": Utility, "column": "power_coverage_pct"},
    "internet_coverage": {"model": Utility, "column": "internet_coverage_pct"},
    "crime_count": {"model": CrimeIncident, "aggregate": True},
    "waste_collection_rate": {"model": WasteManagement, "column": "coverage_pct"},
}

ALL_METRICS = list(METRIC_CONFIG.keys())


def _get_metric_value(session, metric_key: str, barangay_id: int, year: int):
    """Fetch a single metric value for a barangay in a given year."""
    cfg = METRIC_CONFIG.get(metric_key)
    if not cfg:
        return None

    if cfg.get("aggregate"):
        # Crime count: count incidents in that year
        count = (
            session.query(func.count(CrimeIncident.id))
            .filter(
                CrimeIncident.barangay_id == barangay_id,
                extract("year", CrimeIncident.date_occurred) == year,
            )
            .scalar()
        ) or 0
        return count

    model = cfg["model"]
    col_name = cfg["column"]
    record = (
        session.query(model)
        .filter_by(barangay_id=barangay_id, year=year)
        .first()
    )
    if record:
        val = getattr(record, col_name, None)
        return round(float(val), 2) if val is not None else None
    return None


def compare_barangays(barangay_ids: list[int], metrics: list[str],
                      years: list[int]) -> dict:
    """Compare 2-4 barangays across selected metrics and years."""
    if len(barangay_ids) < 2 or len(barangay_ids) > 4:
        return {"error": "Select 2-4 barangays", "barangays": []}

    session = get_session()
    try:
        result = {"barangays": []}
        for bid in barangay_ids:
            brgy = session.get(Barangay, bid)
            if not brgy:
                continue
            brgy_data = {
                "id": brgy.id,
                "name": brgy.name,
                "district_name": brgy.district.name,
                "metrics": {},
            }
            for metric in metrics:
                brgy_data["metrics"][metric] = {}
                for year in sorted(years):
                    brgy_data["metrics"][metric][year] = _get_metric_value(
                        session, metric, bid, year
                    )
            result["barangays"].append(brgy_data)
        return result
    finally:
        session.close()


def compare_districts(metrics: list[str], years: list[int]) -> dict:
    """Compare all 3 districts on aggregated metrics."""
    session = get_session()
    try:
        districts = session.query(District).order_by(District.id).all()
        result = {"districts": []}

        for dist in districts:
            brgy_ids = [b.id for b in dist.barangays]
            dist_data = {
                "id": dist.id,
                "name": dist.name,
                "metrics": {},
            }
            for metric in metrics:
                dist_data["metrics"][metric] = {}
                for year in sorted(years):
                    values = []
                    for bid in brgy_ids:
                        val = _get_metric_value(session, metric, bid, year)
                        if val is not None:
                            values.append(val)
                    # Sum for population/crime, average for percentages/income
                    if values:
                        if metric in ("population", "crime_count"):
                            dist_data["metrics"][metric][year] = round(sum(values), 2)
                        else:
                            dist_data["metrics"][metric][year] = round(
                                sum(values) / len(values), 2
                            )
                    else:
                        dist_data["metrics"][metric][year] = None
            result["districts"].append(dist_data)
        return result
    finally:
        session.close()


def year_over_year(barangay_id: int, years: list[int]) -> dict:
    """All metrics for one barangay across years with growth percentages."""
    session = get_session()
    try:
        brgy = session.get(Barangay, barangay_id)
        if not brgy:
            return {"error": "Barangay not found"}

        sorted_years = sorted(years)
        result = {
            "barangay_name": brgy.name,
            "district_name": brgy.district.name,
            "metrics": {},
        }

        for metric in ALL_METRICS:
            metric_data = {"values": {}, "growth_pct": {}, "trend": "stable"}
            prev_val = None
            for year in sorted_years:
                val = _get_metric_value(session, metric, barangay_id, year)
                metric_data["values"][year] = val
                if prev_val is not None and val is not None and prev_val != 0:
                    pct = round(((val - prev_val) / prev_val) * 100, 1)
                    metric_data["growth_pct"][year] = pct
                prev_val = val

            # Determine trend from first to last non-None value
            vals = [v for v in metric_data["values"].values() if v is not None]
            if len(vals) >= 2:
                change = vals[-1] - vals[0]
                mean = sum(vals) / len(vals)
                if mean != 0 and abs(change / mean) > 0.05:
                    metric_data["trend"] = "increasing" if change > 0 else "decreasing"

            result["metrics"][metric] = metric_data
        return result
    finally:
        session.close()


def get_available_years() -> list[int]:
    """Return all years that have data across any table."""
    session = get_session()
    try:
        years = set()
        for record in session.query(PopulationRecord.year).distinct():
            years.add(record[0])
        for record in session.query(IncomeData.year).distinct():
            years.add(record[0])
        for record in session.query(Utility.year).distinct():
            years.add(record[0])
        return sorted(years)
    finally:
        session.close()
