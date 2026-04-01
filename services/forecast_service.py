import logging
import numpy as np
from database.db import get_session
from database.models import (
    Barangay, PopulationRecord, Utility, GovernmentFacility
)

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
