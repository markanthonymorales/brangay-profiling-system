import logging
import numpy as np
from database.db import get_session
from database.models import (
    Barangay, PopulationRecord, Utility, GovernmentFacility,
    CrimeIncident, TrafficIncident, LandType, FoodSource, Business,
)
from sqlalchemy import func, extract

logger = logging.getLogger(__name__)


def forecast_metric(data_points: list[tuple[int, float]],
                    years_ahead: int = 3) -> dict:
    """Generic forecaster using numpy polyfit.

    Args:
        data_points: list of (year, value) tuples
        years_ahead: how many years to project

    Returns:
        dict with "historical", "forecast", "trend"
    """
    if not data_points or len(data_points) < 2:
        return {
            "historical": data_points or [],
            "forecast": [],
            "trend": "stable",
        }

    # Sort by year
    data_points = sorted(data_points, key=lambda x: x[0])
    years = np.array([d[0] for d in data_points], dtype=float)
    values = np.array([d[1] for d in data_points], dtype=float)

    # Use linear fit (degree 1) for robustness
    try:
        coeffs = np.polyfit(years, values, 1)
        poly = np.poly1d(coeffs)
    except Exception as e:
        logger.warning(f"Polyfit failed: {e}")
        return {
            "historical": data_points,
            "forecast": [],
            "trend": "stable",
        }

    # Generate forecast points
    last_year = int(years[-1])
    forecast_years = list(range(last_year + 1, last_year + 1 + years_ahead))
    forecast_points = []
    for fy in forecast_years:
        predicted = max(0, float(poly(fy)))  # no negative values
        forecast_points.append((fy, round(predicted, 2)))

    # Determine trend
    slope = coeffs[0]
    if abs(slope) < 0.01 * np.mean(values):
        trend = "stable"
    elif slope > 0:
        trend = "increasing"
    else:
        trend = "decreasing"

    return {
        "historical": data_points,
        "forecast": forecast_points,
        "trend": trend,
    }


def forecast_population(barangay_id: int) -> dict:
    """Population growth projection for a barangay."""
    session = get_session()
    try:
        records = (
            session.query(PopulationRecord)
            .filter_by(barangay_id=barangay_id)
            .order_by(PopulationRecord.year)
            .all()
        )

        data_points = []
        for r in records:
            if r.total_population is not None:
                try:
                    data_points.append((r.year, float(r.total_population)))
                except (ValueError, TypeError):
                    pass

        return forecast_metric(data_points, years_ahead=3)
    finally:
        session.close()


def forecast_utility_demand(barangay_id: int) -> dict:
    """Utility coverage trend for a barangay (average of water, power, internet)."""
    session = get_session()
    try:
        records = (
            session.query(Utility)
            .filter_by(barangay_id=barangay_id)
            .order_by(Utility.year)
            .all()
        )

        data_points = []
        for r in records:
            coverages = [
                v for v in [r.water_coverage_pct, r.power_coverage_pct, r.internet_coverage_pct]
                if v is not None
            ]
            if coverages:
                avg_coverage = sum(coverages) / len(coverages)
                data_points.append((r.year, round(avg_coverage, 2)))

        return forecast_metric(data_points, years_ahead=3)
    finally:
        session.close()


def forecast_infrastructure_needs(barangay_id: int) -> dict:
    """Forecast infrastructure needs based on population growth.

    Uses population growth to project schools/healthcare facility needs.
    Returns population-based demand index.
    """
    session = get_session()
    try:
        # Get population data
        pop_records = (
            session.query(PopulationRecord)
            .filter_by(barangay_id=barangay_id)
            .order_by(PopulationRecord.year)
            .all()
        )

        # Get current facility count
        facility_count = (
            session.query(GovernmentFacility)
            .filter_by(barangay_id=barangay_id)
            .count()
        )

        if not pop_records:
            return {
                "historical": [],
                "forecast": [],
                "trend": "stable",
                "facility_count": facility_count,
            }

        # Calculate demand index: population / (facility_count * 5000)
        # where 5000 is assumed capacity per facility
        capacity_per_facility = max(facility_count, 1) * 5000

        data_points = []
        for r in pop_records:
            if r.total_population is not None:
                demand_index = round((r.total_population / capacity_per_facility) * 100, 2)
                data_points.append((r.year, demand_index))

        result = forecast_metric(data_points, years_ahead=3)
        result["facility_count"] = facility_count
        return result
    finally:
        session.close()


def forecast_food_supply(barangay_id: int) -> dict:
    """Food supply projection based on population growth and agricultural land."""
    session = get_session()
    try:
        # Get population data for demand projection
        pop_records = (
            session.query(PopulationRecord)
            .filter_by(barangay_id=barangay_id)
            .order_by(PopulationRecord.year)
            .all()
        )

        if not pop_records:
            return {"historical": [], "forecast": [], "trend": "stable",
                    "demand_gap": "balanced", "notes": "No population data available."}

        # Population-based food demand index
        # Higher population + lower agricultural land = higher demand pressure
        agri_land = (
            session.query(LandType)
            .filter(LandType.barangay_id == barangay_id, LandType.type.ilike("%agri%"))
            .first()
        )
        agri_pct = agri_land.percentage if agri_land and agri_land.percentage else 0

        food_source_count = (
            session.query(func.count(FoodSource.id))
            .filter_by(barangay_id=barangay_id)
            .scalar()
        ) or 0

        # Food demand index: population / (agri_factor * food_source_factor)
        # Higher = more demand pressure
        agri_factor = max(agri_pct, 1) / 10  # normalize: 10% agri = factor 1
        source_factor = max(food_source_count, 1)

        data_points = []
        for r in pop_records:
            if r.total_population is not None:
                demand_index = round(r.total_population / (agri_factor * source_factor), 2)
                data_points.append((r.year, demand_index))

        result = forecast_metric(data_points, years_ahead=3)

        # Determine gap
        if agri_pct < 5 and pop_records[-1].total_population and pop_records[-1].total_population > 10000:
            result["demand_gap"] = "deficit"
            result["notes"] = (
                f"Low agricultural land ({agri_pct:.1f}%) with large population. "
                f"Food supply sources: {food_source_count}. Consider food security programs."
            )
        elif agri_pct >= 20:
            result["demand_gap"] = "surplus"
            result["notes"] = f"Good agricultural base ({agri_pct:.1f}%). {food_source_count} food sources registered."
        else:
            result["demand_gap"] = "balanced"
            result["notes"] = f"Agricultural land: {agri_pct:.1f}%, Food sources: {food_source_count}."

        return result
    finally:
        session.close()


def forecast_transportation(barangay_id: int) -> dict:
    """Transportation demand projection based on traffic incidents and population."""
    session = get_session()
    try:
        pop_records = (
            session.query(PopulationRecord)
            .filter_by(barangay_id=barangay_id)
            .order_by(PopulationRecord.year)
            .all()
        )

        if not pop_records:
            return {"historical": [], "forecast": [], "trend": "stable",
                    "congestion_level": "low", "recommended_infrastructure": []}

        # Build congestion index per year: (traffic_incidents / population) * 10000
        data_points = []
        for r in pop_records:
            if r.total_population and r.total_population > 0:
                traffic_count = (
                    session.query(func.count(TrafficIncident.id))
                    .filter(
                        TrafficIncident.barangay_id == barangay_id,
                        extract("year", TrafficIncident.date_occurred) == r.year,
                    )
                    .scalar()
                ) or 0
                index = round((traffic_count / r.total_population) * 10000, 2)
                data_points.append((r.year, index))

        result = forecast_metric(data_points, years_ahead=3)

        # Determine congestion level from latest value
        latest_index = data_points[-1][1] if data_points else 0
        if latest_index > 20:
            result["congestion_level"] = "critical"
        elif latest_index > 10:
            result["congestion_level"] = "high"
        elif latest_index > 5:
            result["congestion_level"] = "moderate"
        else:
            result["congestion_level"] = "low"

        # Recommendations
        recs = []
        if result["congestion_level"] in ("high", "critical"):
            recs.append("Traffic management review and road widening")
            recs.append("Public transportation route optimization")
        if result["congestion_level"] in ("moderate", "high", "critical"):
            recs.append("Traffic signal improvements at key intersections")
            recs.append("Pedestrian and cycling infrastructure")
        result["recommended_infrastructure"] = recs

        return result
    finally:
        session.close()


def forecast_public_safety(barangay_id: int) -> dict:
    """Public safety projection based on crime trends and population."""
    session = get_session()
    try:
        pop_records = (
            session.query(PopulationRecord)
            .filter_by(barangay_id=barangay_id)
            .order_by(PopulationRecord.year)
            .all()
        )

        if not pop_records:
            return {"historical": [], "forecast": [], "trend": "stable",
                    "safety_level": "safe", "police_ratio": "N/A", "facility_gap": 0}

        # Crime rate per year: (incidents / population) * 10000
        data_points = []
        for r in pop_records:
            if r.total_population and r.total_population > 0:
                crime_count = (
                    session.query(func.count(CrimeIncident.id))
                    .filter(
                        CrimeIncident.barangay_id == barangay_id,
                        extract("year", CrimeIncident.date_occurred) == r.year,
                    )
                    .scalar()
                ) or 0
                rate = round((crime_count / r.total_population) * 10000, 2)
                data_points.append((r.year, rate))

        result = forecast_metric(data_points, years_ahead=3)

        # Safety level from latest crime rate
        latest_rate = data_points[-1][1] if data_points else 0
        if latest_rate > 100:
            result["safety_level"] = "critical"
        elif latest_rate > 50:
            result["safety_level"] = "at_risk"
        elif latest_rate > 20:
            result["safety_level"] = "moderate"
        else:
            result["safety_level"] = "safe"

        # Police ratio: recommended 1:500
        latest_pop = pop_records[-1].total_population or 0
        police_stations = (
            session.query(func.count(GovernmentFacility.id))
            .filter(
                GovernmentFacility.barangay_id == barangay_id,
                GovernmentFacility.facility_type.ilike("%police%"),
            )
            .scalar()
        ) or 0

        if latest_pop > 0:
            recommended_officers = latest_pop // 500
            result["police_ratio"] = f"{police_stations} stations (recommended officers: {recommended_officers})"
        else:
            result["police_ratio"] = "N/A"

        # Facility gap
        recommended_facilities = max(1, latest_pop // 10000)
        all_facilities = (
            session.query(func.count(GovernmentFacility.id))
            .filter_by(barangay_id=barangay_id)
            .scalar()
        ) or 0
        result["facility_gap"] = max(0, recommended_facilities - all_facilities)

        return result
    finally:
        session.close()


def get_all_barangays_for_forecast() -> list[dict]:
    """Get list of barangays for forecast scope selector."""
    session = get_session()
    try:
        barangays = (
            session.query(Barangay)
            .order_by(Barangay.name)
            .all()
        )
        return [{"id": b.id, "name": b.name} for b in barangays]
    finally:
        session.close()
