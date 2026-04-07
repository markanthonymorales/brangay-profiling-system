import logging
from datetime import date, datetime, timedelta
from sqlalchemy import func
from database.db import get_session
from database.models import (
    DisasterRiskProfile, DisasterIncident, EmergencyResource, Barangay, District
)
from services.audit_service import log_action
from services.history_service import record_field_changes

logger = logging.getLogger(__name__)

DISASTER_TYPES = ["flood", "fire", "earthquake", "typhoon", "landslide", "storm_surge"]
RISK_LEVELS = ["low", "medium", "high"]
DISASTER_SEVERITY = ["low", "medium", "high", "critical"]
DISASTER_STATUSES = ["reported", "responding", "resolved", "recovery"]
RESOURCE_TYPES = ["food", "water", "medicine", "shelter", "equipment"]
RESOURCE_UNITS = ["packs", "liters", "boxes", "units", "persons", "kg"]


# ── Disaster Risk Profile CRUD ───────────────────────────────

def save_disaster_risk_profile(barangay_id: int, year: int, data: dict,
                               user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        existing = (
            session.query(DisasterRiskProfile)
            .filter_by(barangay_id=barangay_id, year=year)
            .first()
        )

        if existing:
            old_data = {c.key: getattr(existing, c.key) for c in existing.__table__.columns}
            old_values = {k: v for k, v in old_data.items() if k not in ("id", "created_at", "updated_at")}
            for key, value in data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            new_data = {c.key: getattr(existing, c.key) for c in existing.__table__.columns}
            record_field_changes("disaster_risk_profiles", existing.id, old_data, new_data, user_id)
            session.commit()
            log_action(user_id, "UPDATE", "disaster_risk_profiles", existing.id,
                       old_values=old_values, new_values=data)
            return True, "Disaster risk profile updated."
        else:
            record = DisasterRiskProfile(barangay_id=barangay_id, year=year, **data)
            session.add(record)
            session.commit()
            log_action(user_id, "CREATE", "disaster_risk_profiles", record.id,
                       new_values={"barangay_id": barangay_id, "year": year, **data})
            return True, "Disaster risk profile created."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def get_disaster_risk_profiles(barangay_id: int) -> list[dict]:
    session = get_session()
    try:
        records = (
            session.query(DisasterRiskProfile)
            .filter_by(barangay_id=barangay_id)
            .order_by(DisasterRiskProfile.year.desc())
            .all()
        )
        return [
            {
                "id": r.id, "barangay_id": r.barangay_id, "year": r.year,
                "flood_prone": r.flood_prone, "landslide_prone": r.landslide_prone,
                "fire_risk_level": r.fire_risk_level or "", "earthquake_risk": r.earthquake_risk or "",
                "storm_surge_risk": r.storm_surge_risk or "",
                "evacuation_center_count": r.evacuation_center_count,
                "evacuation_capacity": r.evacuation_capacity,
            }
            for r in records
        ]
    finally:
        session.close()


# ── Disaster Incident CRUD ───────────────────────────────────

def save_disaster_incident(barangay_id: int, data: dict, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        incident_id = data.pop("id", None)
        if incident_id:
            record = session.get(DisasterIncident, incident_id)
            if not record:
                return False, "Disaster incident not found."
            old_data = {c.key: getattr(record, c.key) for c in record.__table__.columns}
            old_values = {
                "disaster_type": record.disaster_type, "severity": record.severity,
                "status": record.status, "date_occurred": str(record.date_occurred),
            }
            for key, value in data.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            new_data = {c.key: getattr(record, c.key) for c in record.__table__.columns}
            record_field_changes("disaster_incidents", record.id, old_data, new_data, user_id)
            session.commit()
            log_action(user_id, "UPDATE", "disaster_incidents", record.id,
                       old_values=old_values, new_values=data)
            return True, "Disaster incident updated."
        else:
            record = DisasterIncident(barangay_id=barangay_id, **data)
            session.add(record)
            session.commit()
            log_action(user_id, "CREATE", "disaster_incidents", record.id,
                       new_values={"barangay_id": barangay_id, **{k: str(v) for k, v in data.items()}})
            return True, "Disaster incident recorded."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def delete_disaster_incident(incident_id: int, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        record = session.get(DisasterIncident, incident_id)
        if not record:
            return False, "Disaster incident not found."
        old_values = {"disaster_type": record.disaster_type, "barangay_id": record.barangay_id}
        session.delete(record)
        session.commit()
        log_action(user_id, "DELETE", "disaster_incidents", incident_id, old_values=old_values)
        return True, "Disaster incident deleted."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def get_disaster_incidents(barangay_id: int | None = None, disaster_type: str | None = None,
                           severity: str | None = None, status: str | None = None,
                           limit: int = 200) -> list[dict]:
    session = get_session()
    try:
        query = session.query(DisasterIncident).join(Barangay)
        if barangay_id:
            query = query.filter(DisasterIncident.barangay_id == barangay_id)
        if disaster_type:
            query = query.filter(DisasterIncident.disaster_type == disaster_type)
        if severity:
            query = query.filter(DisasterIncident.severity == severity)
        if status:
            query = query.filter(DisasterIncident.status == status)

        records = query.order_by(DisasterIncident.date_occurred.desc()).limit(limit).all()
        return [
            {
                "id": r.id, "barangay_id": r.barangay_id,
                "barangay_name": r.barangay.name,
                "district_name": r.barangay.district.name if r.barangay.district else "",
                "disaster_type": r.disaster_type, "severity": r.severity,
                "date_occurred": r.date_occurred.strftime("%Y-%m-%d") if r.date_occurred else "",
                "affected_families": r.affected_families or 0,
                "casualties": r.casualties or 0,
                "damages_estimated": r.damages_estimated or 0,
                "status": r.status, "response_team": r.response_team or "",
                "description": r.description or "",
            }
            for r in records
        ]
    finally:
        session.close()


# ── Emergency Resource CRUD ──────────────────────────────────

def save_emergency_resource(barangay_id: int, data: dict, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        resource_id = data.pop("id", None)
        if resource_id:
            record = session.get(EmergencyResource, resource_id)
            if not record:
                return False, "Emergency resource not found."
            old_data = {c.key: getattr(record, c.key) for c in record.__table__.columns}
            old_values = {"resource_type": record.resource_type, "name": record.name}
            for key, value in data.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            new_data = {c.key: getattr(record, c.key) for c in record.__table__.columns}
            record_field_changes("emergency_resources", record.id, old_data, new_data, user_id)
            session.commit()
            log_action(user_id, "UPDATE", "emergency_resources", record.id,
                       old_values=old_values, new_values=data)
            return True, "Emergency resource updated."
        else:
            record = EmergencyResource(barangay_id=barangay_id, **data)
            session.add(record)
            session.commit()
            log_action(user_id, "CREATE", "emergency_resources", record.id,
                       new_values={"barangay_id": barangay_id, **{k: str(v) for k, v in data.items()}})
            return True, "Emergency resource recorded."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def delete_emergency_resource(resource_id: int, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        record = session.get(EmergencyResource, resource_id)
        if not record:
            return False, "Emergency resource not found."
        old_values = {"resource_type": record.resource_type, "name": record.name}
        session.delete(record)
        session.commit()
        log_action(user_id, "DELETE", "emergency_resources", resource_id, old_values=old_values)
        return True, "Emergency resource deleted."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def get_emergency_resources(barangay_id: int | None = None, resource_type: str | None = None,
                            limit: int = 200) -> list[dict]:
    session = get_session()
    try:
        query = session.query(EmergencyResource).join(Barangay)
        if barangay_id:
            query = query.filter(EmergencyResource.barangay_id == barangay_id)
        if resource_type:
            query = query.filter(EmergencyResource.resource_type == resource_type)

        records = query.order_by(EmergencyResource.created_at.desc()).limit(limit).all()
        return [
            {
                "id": r.id, "barangay_id": r.barangay_id,
                "barangay_name": r.barangay.name,
                "resource_type": r.resource_type, "name": r.name,
                "quantity": r.quantity, "unit": r.unit or "",
                "location_description": r.location_description or "",
                "last_restocked": r.last_restocked.strftime("%Y-%m-%d") if r.last_restocked else "",
                "expiry_date": r.expiry_date.strftime("%Y-%m-%d") if r.expiry_date else "",
            }
            for r in records
        ]
    finally:
        session.close()


# ── Analytics Queries ────────────────────────────────────────

def _get_brgy_ids(session, barangay_id=None, district_id=None) -> list[int] | None:
    if barangay_id:
        return [barangay_id]
    if district_id:
        return [b.id for b in session.query(Barangay.id).filter_by(district_id=district_id).all()]
    return None


def get_disaster_stats(barangay_id: int | None = None, district_id: int | None = None) -> dict:
    session = get_session()
    try:
        brgy_ids = _get_brgy_ids(session, barangay_id, district_id)

        query = session.query(DisasterIncident.disaster_type, func.count(DisasterIncident.id))
        if brgy_ids:
            query = query.filter(DisasterIncident.barangay_id.in_(brgy_ids))
        by_type = dict(query.group_by(DisasterIncident.disaster_type).all())

        query = session.query(DisasterIncident.severity, func.count(DisasterIncident.id))
        if brgy_ids:
            query = query.filter(DisasterIncident.barangay_id.in_(brgy_ids))
        by_severity = dict(query.group_by(DisasterIncident.severity).all())

        query = session.query(func.count(DisasterIncident.id))
        if brgy_ids:
            query = query.filter(DisasterIncident.barangay_id.in_(brgy_ids))
        total = query.scalar() or 0

        query = session.query(func.sum(DisasterIncident.affected_families))
        if brgy_ids:
            query = query.filter(DisasterIncident.barangay_id.in_(brgy_ids))
        total_affected = query.scalar() or 0

        return {"total": total, "by_type": by_type, "by_severity": by_severity,
                "total_affected_families": total_affected}
    finally:
        session.close()


def get_disaster_trend(barangay_id: int | None = None, district_id: int | None = None) -> list[dict]:
    session = get_session()
    try:
        from sqlalchemy import extract
        brgy_ids = _get_brgy_ids(session, barangay_id, district_id)
        query = session.query(
            extract("year", DisasterIncident.date_occurred).label("yr"),
            extract("month", DisasterIncident.date_occurred).label("mo"),
            func.count(DisasterIncident.id),
        )
        if brgy_ids:
            query = query.filter(DisasterIncident.barangay_id.in_(brgy_ids))
        rows = query.group_by("yr", "mo").order_by("yr", "mo").all()
        return [{"year": int(r[0]), "month": int(r[1]), "count": r[2]} for r in rows]
    finally:
        session.close()


def get_high_risk_barangays_disaster(limit: int = 20) -> list[dict]:
    session = get_session()
    try:
        cutoff = date.today() - timedelta(days=365)
        query = (
            session.query(
                Barangay.id, Barangay.name,
                func.count(DisasterIncident.id).label("incident_count"),
            )
            .join(DisasterIncident, Barangay.id == DisasterIncident.barangay_id)
            .filter(DisasterIncident.date_occurred >= cutoff)
            .group_by(Barangay.id, Barangay.name)
            .order_by(func.count(DisasterIncident.id).desc())
            .limit(limit)
        )
        rows = query.all()
        result = []
        for brgy_id, brgy_name, count in rows:
            brgy = session.get(Barangay, brgy_id)
            district_name = brgy.district.name if brgy and brgy.district else ""
            common_type_row = (
                session.query(DisasterIncident.disaster_type, func.count(DisasterIncident.id))
                .filter(DisasterIncident.barangay_id == brgy_id, DisasterIncident.date_occurred >= cutoff)
                .group_by(DisasterIncident.disaster_type)
                .order_by(func.count(DisasterIncident.id).desc())
                .first()
            )
            common_type = common_type_row[0] if common_type_row else "N/A"
            result.append({
                "rank": len(result) + 1, "barangay_name": brgy_name,
                "district_name": district_name, "incident_count": count,
                "common_type": common_type,
            })
        return result
    finally:
        session.close()


def get_expiring_resources(days_ahead: int = 30) -> list[dict]:
    session = get_session()
    try:
        cutoff = date.today() + timedelta(days=days_ahead)
        records = (
            session.query(EmergencyResource)
            .join(Barangay)
            .filter(EmergencyResource.expiry_date != None, EmergencyResource.expiry_date <= cutoff)
            .order_by(EmergencyResource.expiry_date)
            .all()
        )
        today = date.today()
        return [
            {
                "id": r.id, "barangay_name": r.barangay.name,
                "resource_type": r.resource_type, "name": r.name,
                "quantity": r.quantity, "unit": r.unit or "",
                "expiry_date": r.expiry_date.strftime("%Y-%m-%d") if r.expiry_date else "",
                "is_expired": r.expiry_date < today if r.expiry_date else False,
            }
            for r in records
        ]
    finally:
        session.close()
