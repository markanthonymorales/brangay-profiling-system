import logging
from datetime import date, datetime, timedelta
from sqlalchemy import func, extract
import numpy as np
from database.db import get_session
from database.models import CrimeIncident, TrafficIncident, Barangay, District
from services.audit_service import log_action

logger = logging.getLogger(__name__)

CRIME_TYPES = ["theft", "assault", "robbery", "drugs", "homicide", "vandalism", "fraud", "domestic_violence", "other"]
TRAFFIC_TYPES = ["accident", "congestion", "road_hazard", "pedestrian", "hit_and_run", "other"]
SEVERITY_LEVELS = ["low", "medium", "high", "critical"]
INCIDENT_STATUSES = ["reported", "under_investigation", "resolved"]


# ── Crime Incident CRUD ───────────────────────────────────────

def save_crime_incident(barangay_id: int, data: dict, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        incident_id = data.pop("id", None)
        if incident_id:
            record = session.query(CrimeIncident).get(incident_id)
            if not record:
                return False, "Incident not found."
            old_values = {
                "crime_type": record.crime_type, "severity": record.severity,
                "status": record.status, "date_occurred": str(record.date_occurred),
            }
            for key, value in data.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            session.commit()
            log_action(user_id, "UPDATE", "crime_incidents", record.id,
                       old_values=old_values, new_values=data)
            return True, "Crime incident updated."
        else:
            record = CrimeIncident(barangay_id=barangay_id, **data)
            session.add(record)
            session.commit()
            log_action(user_id, "CREATE", "crime_incidents", record.id,
                       new_values={"barangay_id": barangay_id, **{k: str(v) for k, v in data.items()}})
            return True, "Crime incident recorded."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def delete_crime_incident(incident_id: int, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        record = session.query(CrimeIncident).get(incident_id)
        if not record:
            return False, "Incident not found."
        old_values = {"crime_type": record.crime_type, "barangay_id": record.barangay_id}
        session.delete(record)
        session.commit()
        log_action(user_id, "DELETE", "crime_incidents", incident_id, old_values=old_values)
        return True, "Crime incident deleted."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def get_crime_incidents(barangay_id: int | None = None, crime_type: str | None = None,
                        severity: str | None = None, status: str | None = None,
                        limit: int = 200) -> list[dict]:
    session = get_session()
    try:
        query = session.query(CrimeIncident).join(Barangay)
        if barangay_id:
            query = query.filter(CrimeIncident.barangay_id == barangay_id)
        if crime_type:
            query = query.filter(CrimeIncident.crime_type == crime_type)
        if severity:
            query = query.filter(CrimeIncident.severity == severity)
        if status:
            query = query.filter(CrimeIncident.status == status)

        records = query.order_by(CrimeIncident.date_occurred.desc()).limit(limit).all()
        return [
            {
                "id": r.id, "barangay_id": r.barangay_id,
                "barangay_name": r.barangay.name,
                "crime_type": r.crime_type, "severity": r.severity,
                "date_occurred": r.date_occurred.strftime("%Y-%m-%d") if r.date_occurred else "",
                "status": r.status, "description": r.description or "",
            }
            for r in records
        ]
    finally:
        session.close()


# ── Traffic Incident CRUD ─────────────────────────────────────

def save_traffic_incident(barangay_id: int, data: dict, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        incident_id = data.pop("id", None)
        if incident_id:
            record = session.query(TrafficIncident).get(incident_id)
            if not record:
                return False, "Incident not found."
            old_values = {
                "incident_type": record.incident_type, "severity": record.severity,
                "status": record.status, "date_occurred": str(record.date_occurred),
            }
            for key, value in data.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            session.commit()
            log_action(user_id, "UPDATE", "traffic_incidents", record.id,
                       old_values=old_values, new_values=data)
            return True, "Traffic incident updated."
        else:
            record = TrafficIncident(barangay_id=barangay_id, **data)
            session.add(record)
            session.commit()
            log_action(user_id, "CREATE", "traffic_incidents", record.id,
                       new_values={"barangay_id": barangay_id, **{k: str(v) for k, v in data.items()}})
            return True, "Traffic incident recorded."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def delete_traffic_incident(incident_id: int, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        record = session.query(TrafficIncident).get(incident_id)
        if not record:
            return False, "Incident not found."
        old_values = {"incident_type": record.incident_type, "barangay_id": record.barangay_id}
        session.delete(record)
        session.commit()
        log_action(user_id, "DELETE", "traffic_incidents", incident_id, old_values=old_values)
        return True, "Traffic incident deleted."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def get_traffic_incidents(barangay_id: int | None = None, incident_type: str | None = None,
                          severity: str | None = None, status: str | None = None,
                          limit: int = 200) -> list[dict]:
    session = get_session()
    try:
        query = session.query(TrafficIncident).join(Barangay)
        if barangay_id:
            query = query.filter(TrafficIncident.barangay_id == barangay_id)
        if incident_type:
            query = query.filter(TrafficIncident.incident_type == incident_type)
        if severity:
            query = query.filter(TrafficIncident.severity == severity)
        if status:
            query = query.filter(TrafficIncident.status == status)

        records = query.order_by(TrafficIncident.date_occurred.desc()).limit(limit).all()
        return [
            {
                "id": r.id, "barangay_id": r.barangay_id,
                "barangay_name": r.barangay.name,
                "incident_type": r.incident_type, "severity": r.severity,
                "date_occurred": r.date_occurred.strftime("%Y-%m-%d") if r.date_occurred else "",
                "status": r.status, "description": r.description or "",
            }
            for r in records
        ]
    finally:
        session.close()


# ── Analytics Queries ─────────────────────────────────────────

def _get_brgy_ids(session, barangay_id=None, district_id=None) -> list[int] | None:
    """Returns list of barangay IDs to filter on, or None for no filter."""
    if barangay_id:
        return [barangay_id]
    if district_id:
        return [b.id for b in session.query(Barangay.id).filter_by(district_id=district_id).all()]
    return None


def get_crime_stats(barangay_id: int | None = None, district_id: int | None = None) -> dict:
    session = get_session()
    try:
        brgy_ids = _get_brgy_ids(session, barangay_id, district_id)

        query = session.query(CrimeIncident.crime_type, func.count(CrimeIncident.id))
        if brgy_ids:
            query = query.filter(CrimeIncident.barangay_id.in_(brgy_ids))
        by_type = dict(query.group_by(CrimeIncident.crime_type).all())

        query = session.query(CrimeIncident.severity, func.count(CrimeIncident.id))
        if brgy_ids:
            query = query.filter(CrimeIncident.barangay_id.in_(brgy_ids))
        by_severity = dict(query.group_by(CrimeIncident.severity).all())

        query = session.query(func.count(CrimeIncident.id))
        if brgy_ids:
            query = query.filter(CrimeIncident.barangay_id.in_(brgy_ids))
        total = query.scalar() or 0

        return {"total": total, "by_type": by_type, "by_severity": by_severity}
    finally:
        session.close()


def get_traffic_stats(barangay_id: int | None = None, district_id: int | None = None) -> dict:
    session = get_session()
    try:
        brgy_ids = _get_brgy_ids(session, barangay_id, district_id)

        query = session.query(TrafficIncident.incident_type, func.count(TrafficIncident.id))
        if brgy_ids:
            query = query.filter(TrafficIncident.barangay_id.in_(brgy_ids))
        by_type = dict(query.group_by(TrafficIncident.incident_type).all())

        query = session.query(TrafficIncident.severity, func.count(TrafficIncident.id))
        if brgy_ids:
            query = query.filter(TrafficIncident.barangay_id.in_(brgy_ids))
        by_severity = dict(query.group_by(TrafficIncident.severity).all())

        query = session.query(func.count(TrafficIncident.id))
        if brgy_ids:
            query = query.filter(TrafficIncident.barangay_id.in_(brgy_ids))
        total = query.scalar() or 0

        return {"total": total, "by_type": by_type, "by_severity": by_severity}
    finally:
        session.close()


def get_crime_trend(barangay_id: int | None = None, district_id: int | None = None) -> list[dict]:
    session = get_session()
    try:
        brgy_ids = _get_brgy_ids(session, barangay_id, district_id)

        query = session.query(
            extract("year", CrimeIncident.date_occurred).label("yr"),
            extract("month", CrimeIncident.date_occurred).label("mo"),
            func.count(CrimeIncident.id),
        )
        if brgy_ids:
            query = query.filter(CrimeIncident.barangay_id.in_(brgy_ids))

        rows = query.group_by("yr", "mo").order_by("yr", "mo").all()
        return [{"year": int(r[0]), "month": int(r[1]), "count": r[2]} for r in rows]
    finally:
        session.close()


def get_traffic_trend(barangay_id: int | None = None, district_id: int | None = None) -> list[dict]:
    session = get_session()
    try:
        brgy_ids = _get_brgy_ids(session, barangay_id, district_id)

        query = session.query(
            extract("year", TrafficIncident.date_occurred).label("yr"),
            extract("month", TrafficIncident.date_occurred).label("mo"),
            func.count(TrafficIncident.id),
        )
        if brgy_ids:
            query = query.filter(TrafficIncident.barangay_id.in_(brgy_ids))

        rows = query.group_by("yr", "mo").order_by("yr", "mo").all()
        return [{"year": int(r[0]), "month": int(r[1]), "count": r[2]} for r in rows]
    finally:
        session.close()


def get_high_risk_barangays(risk_type: str = "crime", limit: int = 20) -> list[dict]:
    session = get_session()
    try:
        cutoff = date.today() - timedelta(days=365)

        if risk_type == "crime":
            model = CrimeIncident
            type_col = CrimeIncident.crime_type
            date_col = CrimeIncident.date_occurred
        else:
            model = TrafficIncident
            type_col = TrafficIncident.incident_type
            date_col = TrafficIncident.date_occurred

        # Count incidents per barangay in last 12 months
        query = (
            session.query(
                Barangay.id,
                Barangay.name,
                func.count(model.id).label("incident_count"),
            )
            .join(model, Barangay.id == model.barangay_id)
            .filter(date_col >= cutoff)
            .group_by(Barangay.id, Barangay.name)
            .order_by(func.count(model.id).desc())
            .limit(limit)
        )

        rows = query.all()
        result = []
        for brgy_id, brgy_name, count in rows:
            brgy = session.query(Barangay).get(brgy_id)
            district_name = brgy.district.name if brgy else ""

            # Most common type
            common_type_row = (
                session.query(type_col, func.count(model.id))
                .filter(model.barangay_id == brgy_id, date_col >= cutoff)
                .group_by(type_col)
                .order_by(func.count(model.id).desc())
                .first()
            )
            common_type = common_type_row[0] if common_type_row else "N/A"

            # Dominant severity
            sev_row = (
                session.query(model.severity, func.count(model.id))
                .filter(model.barangay_id == brgy_id, date_col >= cutoff)
                .group_by(model.severity)
                .order_by(func.count(model.id).desc())
                .first()
            )
            dominant_severity = sev_row[0] if sev_row else "N/A"

            result.append({
                "rank": len(result) + 1,
                "barangay_name": brgy_name,
                "district_name": district_name,
                "incident_count": count,
                "common_type": common_type,
                "dominant_severity": dominant_severity,
            })
        return result
    finally:
        session.close()


def get_crime_forecast(barangay_id: int | None = None, district_id: int | None = None,
                       months_ahead: int = 6) -> dict:
    trend_data = get_crime_trend(barangay_id=barangay_id, district_id=district_id)

    if len(trend_data) < 3:
        return {"historical": trend_data, "forecast": [], "trend": "insufficient_data"}

    # Convert to sequential indices for regression
    x = np.arange(len(trend_data), dtype=float)
    y = np.array([d["count"] for d in trend_data], dtype=float)

    # Linear regression
    coeffs = np.polyfit(x, y, 1)
    slope = coeffs[0]

    # Determine trend
    if slope > 0.5:
        trend = "increasing"
    elif slope < -0.5:
        trend = "decreasing"
    else:
        trend = "stable"

    # Project forward
    last_entry = trend_data[-1]
    last_year = last_entry["year"]
    last_month = last_entry["month"]

    forecast = []
    for i in range(1, months_ahead + 1):
        future_x = len(trend_data) - 1 + i
        projected = max(0, round(np.polyval(coeffs, future_x)))

        # Calculate future month/year
        total_months = last_year * 12 + last_month + i
        f_year = (total_months - 1) // 12
        f_month = (total_months - 1) % 12 + 1

        forecast.append({"year": f_year, "month": f_month, "count": projected})

    return {"historical": trend_data, "forecast": forecast, "trend": trend}
