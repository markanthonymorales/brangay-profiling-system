import logging
from database.db import get_session
from database.models import FoodSource, GovernmentFacility, ReligiousDemographic
from services.audit_service import log_action
from services.history_service import record_field_changes

logger = logging.getLogger(__name__)


# ── Food Sources ──────────────────────────────────────────────

def get_food_sources(barangay_id: int) -> list[dict]:
    session = get_session()
    try:
        records = session.query(FoodSource).filter_by(barangay_id=barangay_id).all()
        return [{"id": r.id, "type": r.type, "description": r.description} for r in records]
    finally:
        session.close()


def save_food_source(barangay_id: int, data: dict, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        source_id = data.pop("id", None)
        if source_id:
            record = session.get(FoodSource, source_id)
            if not record:
                return False, "Food source not found."
            old_data = {c.key: getattr(record, c.key) for c in record.__table__.columns}
            old_values = {"type": record.type, "description": record.description}
            for key, value in data.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            new_data = {c.key: getattr(record, c.key) for c in record.__table__.columns}
            record_field_changes("food_sources", record.id, old_data, new_data, user_id)
            session.commit()
            log_action(user_id, "UPDATE", "food_sources", record.id,
                       old_values=old_values, new_values=data)
            return True, "Food source updated."
        else:
            record = FoodSource(barangay_id=barangay_id, **data)
            session.add(record)
            session.commit()
            log_action(user_id, "CREATE", "food_sources", record.id,
                       new_values={"barangay_id": barangay_id, **data})
            return True, "Food source created."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def delete_food_source(source_id: int, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        record = session.get(FoodSource, source_id)
        if not record:
            return False, "Food source not found."
        old_values = {"type": record.type, "description": record.description}
        session.delete(record)
        session.commit()
        log_action(user_id, "DELETE", "food_sources", source_id, old_values=old_values)
        return True, "Food source deleted."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


# ── Government Facilities ─────────────────────────────────────

def get_government_facilities(barangay_id: int) -> list[dict]:
    session = get_session()
    try:
        records = session.query(GovernmentFacility).filter_by(barangay_id=barangay_id).all()
        return [
            {"id": r.id, "agency_name": r.agency_name, "facility_type": r.facility_type, "address": r.address}
            for r in records
        ]
    finally:
        session.close()


def save_government_facility(barangay_id: int, data: dict, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        facility_id = data.pop("id", None)
        if facility_id:
            record = session.get(GovernmentFacility, facility_id)
            if not record:
                return False, "Facility not found."
            old_data = {c.key: getattr(record, c.key) for c in record.__table__.columns}
            old_values = {"agency_name": record.agency_name, "facility_type": record.facility_type}
            for key, value in data.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            new_data = {c.key: getattr(record, c.key) for c in record.__table__.columns}
            record_field_changes("government_facilities", record.id, old_data, new_data, user_id)
            session.commit()
            log_action(user_id, "UPDATE", "government_facilities", record.id,
                       old_values=old_values, new_values=data)
            return True, "Facility updated."
        else:
            record = GovernmentFacility(barangay_id=barangay_id, **data)
            session.add(record)
            session.commit()
            log_action(user_id, "CREATE", "government_facilities", record.id,
                       new_values={"barangay_id": barangay_id, **data})
            return True, "Facility created."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def delete_government_facility(facility_id: int, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        record = session.get(GovernmentFacility, facility_id)
        if not record:
            return False, "Facility not found."
        old_values = {"agency_name": record.agency_name, "facility_type": record.facility_type}
        session.delete(record)
        session.commit()
        log_action(user_id, "DELETE", "government_facilities", facility_id, old_values=old_values)
        return True, "Facility deleted."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


# ── Religious Demographics ────────────────────────────────────

def get_religious_demographics(barangay_id: int, year: int | None = None) -> list[dict]:
    session = get_session()
    try:
        query = session.query(ReligiousDemographic).filter_by(barangay_id=barangay_id)
        if year:
            query = query.filter_by(year=year)
        records = query.order_by(ReligiousDemographic.year.desc(), ReligiousDemographic.count.desc()).all()
        return [
            {"id": r.id, "year": r.year, "religion": r.religion, "count": r.count, "percentage": r.percentage}
            for r in records
        ]
    finally:
        session.close()


def save_religious_demographic(barangay_id: int, data: dict, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        demo_id = data.pop("id", None)
        if demo_id:
            record = session.get(ReligiousDemographic, demo_id)
            if not record:
                return False, "Record not found."
            old_data = {c.key: getattr(record, c.key) for c in record.__table__.columns}
            old_values = {"religion": record.religion, "count": record.count, "percentage": record.percentage}
            for key, value in data.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            new_data = {c.key: getattr(record, c.key) for c in record.__table__.columns}
            record_field_changes("religious_demographics", record.id, old_data, new_data, user_id)
            session.commit()
            log_action(user_id, "UPDATE", "religious_demographics", record.id,
                       old_values=old_values, new_values=data)
            return True, "Record updated."
        else:
            record = ReligiousDemographic(barangay_id=barangay_id, **data)
            session.add(record)
            session.commit()
            log_action(user_id, "CREATE", "religious_demographics", record.id,
                       new_values={"barangay_id": barangay_id, **data})
            return True, "Record created."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()
