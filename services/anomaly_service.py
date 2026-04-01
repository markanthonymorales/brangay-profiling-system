import logging
import numpy as np
from database.db import get_session
from database.models import (
    Barangay, PopulationRecord, IncomeData, Utility, CrimeIncident,
)
from services.notification_service import create_notification
from services.schedule_service import get_schedule
from sqlalchemy import func, extract

logger = logging.getLogger(__name__)

ANOMALY_THRESHOLD = 2.0  # standard deviations


def detect_all_anomalies(notify_user_id: int | None = None) -> list[dict]:
    """Run all anomaly detection checks. Optionally create notifications."""
    anomalies = []

    # Check missing submissions for active schedule
    schedule = get_schedule()
    if schedule:
        anomalies.extend(detect_missing_submissions(schedule["year"]))

    # Statistical anomalies
    anomalies.extend(detect_statistical_anomalies())

    # Optionally notify
    if notify_user_id and anomalies:
        trigger_anomaly_notifications(anomalies, [notify_user_id])

    return anomalies


def detect_missing_submissions(year: int) -> list[dict]:
    """Detect barangays with no data for a given year."""
    session = get_session()
    try:
        barangays = session.query(Barangay).all()
        anomalies = []

        checks = [
            ("population_records", PopulationRecord, "year"),
            ("income_data", IncomeData, "year"),
            ("utilities", Utility, "year"),
        ]

        for table_name, model, filter_type in checks:
            for brgy in barangays:
                if filter_type == "year":
                    exists = session.query(model).filter_by(
                        barangay_id=brgy.id, year=year
                    ).first()
                else:
                    exists = (
                        session.query(model)
                        .filter(
                            model.barangay_id == brgy.id,
                            extract("year", model.date_occurred) == year,
                        )
                        .first()
                    )

                if not exists:
                    anomalies.append({
                        "type": "missing",
                        "severity": "warning",
                        "barangay_id": brgy.id,
                        "barangay_name": brgy.name,
                        "table_name": table_name,
                        "field_name": "",
                        "message": f"No {table_name.replace('_', ' ')} data for {brgy.name} in {year}",
                        "current_value": None,
                        "historical_mean": None,
                        "std_dev": None,
                    })

        return anomalies
    finally:
        session.close()


def detect_statistical_anomalies() -> list[dict]:
    """Detect values that deviate >2 std devs from historical mean."""
    session = get_session()
    try:
        barangays = session.query(Barangay).all()
        anomalies = []

        for brgy in barangays:
            # Population
            pop_records = (
                session.query(PopulationRecord)
                .filter_by(barangay_id=brgy.id)
                .order_by(PopulationRecord.year)
                .all()
            )
            values = [(r.year, float(r.total_population)) for r in pop_records
                       if r.total_population is not None]
            anomaly = _check_metric_anomaly(values, brgy.id, brgy.name,
                                            "population_records", "total_population")
            if anomaly:
                anomalies.append(anomaly)

            # Income
            income_records = (
                session.query(IncomeData)
                .filter_by(barangay_id=brgy.id)
                .order_by(IncomeData.year)
                .all()
            )
            values = [(r.year, float(r.average_household_income)) for r in income_records
                       if r.average_household_income is not None]
            anomaly = _check_metric_anomaly(values, brgy.id, brgy.name,
                                            "income_data", "average_household_income")
            if anomaly:
                anomalies.append(anomaly)

            # Utility coverages
            util_records = (
                session.query(Utility)
                .filter_by(barangay_id=brgy.id)
                .order_by(Utility.year)
                .all()
            )
            for field in ["water_coverage_pct", "power_coverage_pct", "internet_coverage_pct"]:
                values = [(r.year, float(getattr(r, field))) for r in util_records
                           if getattr(r, field) is not None]
                anomaly = _check_metric_anomaly(values, brgy.id, brgy.name,
                                                "utilities", field)
                if anomaly:
                    anomalies.append(anomaly)

            # Crime count by year
            crime_years = (
                session.query(
                    extract("year", CrimeIncident.date_occurred).label("yr"),
                    func.count(CrimeIncident.id).label("cnt"),
                )
                .filter(CrimeIncident.barangay_id == brgy.id)
                .group_by("yr")
                .order_by("yr")
                .all()
            )
            values = [(int(r.yr), float(r.cnt)) for r in crime_years]
            anomaly = _check_metric_anomaly(values, brgy.id, brgy.name,
                                            "crime_incidents", "yearly_count")
            if anomaly:
                anomalies.append(anomaly)

        return anomalies
    finally:
        session.close()


def _check_metric_anomaly(
    values: list[tuple[int, float]],
    barangay_id: int,
    barangay_name: str,
    table_name: str,
    field_name: str,
) -> dict | None:
    """Check if the latest value is anomalous (>2 std devs from historical mean).
    Requires at least 3 data points.
    """
    if len(values) < 3:
        return None

    historical = [v[1] for v in values[:-1]]
    latest_year, latest_value = values[-1]

    mean = float(np.mean(historical))
    std = float(np.std(historical))

    if std < 0.001:  # effectively constant
        return None

    z_score = abs(latest_value - mean) / std
    if z_score > ANOMALY_THRESHOLD:
        direction = "spike" if latest_value > mean else "drop"
        return {
            "type": direction,
            "severity": "error" if z_score > 3.0 else "warning",
            "barangay_id": barangay_id,
            "barangay_name": barangay_name,
            "table_name": table_name,
            "field_name": field_name,
            "message": (
                f"Unusual {direction} in {field_name.replace('_', ' ')} for {barangay_name} "
                f"(year {latest_year}): {latest_value:,.1f} vs historical mean {mean:,.1f}"
            ),
            "current_value": latest_value,
            "historical_mean": round(mean, 2),
            "std_dev": round(std, 2),
        }
    return None


def trigger_anomaly_notifications(anomalies: list[dict], admin_user_ids: list[int]) -> int:
    """Create notification entries for detected anomalies."""
    count = 0
    for anomaly in anomalies:
        for uid in admin_user_ids:
            success, _ = create_notification(
                user_id=uid,
                type="anomaly_detection",
                title=f"Data Anomaly: {anomaly['barangay_name']}",
                message=anomaly["message"],
                severity=anomaly["severity"],
            )
            if success:
                count += 1
    return count
