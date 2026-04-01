import logging
from database.db import get_session
from database.models import Utility, LandType, WasteManagement
from services.audit_service import log_action

logger = logging.getLogger(__name__)


# ── Utilities ─────────────────────────────────────────────────

def get_utility_records(barangay_id: int) -> list[dict]:
    session = get_session()
    try:
        records = (
            session.query(Utility)
            .filter_by(barangay_id=barangay_id)
            .order_by(Utility.year.desc())
            .all()
        )
        return [
            {
                "id": r.id, "year": r.year,
                "water_source": r.water_source, "water_coverage_pct": r.water_coverage_pct,
                "power_provider": r.power_provider, "power_coverage_pct": r.power_coverage_pct,
                "internet_coverage_pct": r.internet_coverage_pct,
            }
            for r in records
        ]
    finally:
        session.close()


def save_utility_record(barangay_id: int, year: int, data: dict,
                        user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        existing = session.query(Utility).filter_by(barangay_id=barangay_id, year=year).first()
        if existing:
            old_values = {c.key: getattr(existing, c.key) for c in Utility.__table__.columns
                         if c.key not in ("id", "barangay_id", "year", "created_at", "updated_at")}
            for key, value in data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            session.commit()
            log_action(user_id, "UPDATE", "utilities", existing.id,
                       old_values=old_values, new_values=data)
            return True, "Utility record updated."
        else:
            record = Utility(barangay_id=barangay_id, year=year, **data)
            session.add(record)
            session.commit()
            log_action(user_id, "CREATE", "utilities", record.id,
                       new_values={"barangay_id": barangay_id, "year": year, **data})
            return True, "Utility record created."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


# ── Land Types ────────────────────────────────────────────────

def get_land_types(barangay_id: int) -> list[dict]:
    session = get_session()
    try:
        records = session.query(LandType).filter_by(barangay_id=barangay_id).all()
        return [
            {"id": r.id, "type": r.type, "area_sqkm": r.area_sqkm, "percentage": r.percentage}
            for r in records
        ]
    finally:
        session.close()


def save_land_type(barangay_id: int, data: dict, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        land_id = data.pop("id", None)
        if land_id:
            record = session.get(LandType, land_id)
            if not record:
                return False, "Land type not found."
            old_values = {"type": record.type, "area_sqkm": record.area_sqkm, "percentage": record.percentage}
            for key, value in data.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            session.commit()
            log_action(user_id, "UPDATE", "land_types", record.id,
                       old_values=old_values, new_values=data)
            return True, "Land type updated."
        else:
            record = LandType(barangay_id=barangay_id, **data)
            session.add(record)
            session.commit()
            log_action(user_id, "CREATE", "land_types", record.id,
                       new_values={"barangay_id": barangay_id, **data})
            return True, "Land type created."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


# ── Waste Management ──────────────────────────────────────────

def get_waste_records(barangay_id: int) -> list[dict]:
    session = get_session()
    try:
        records = (
            session.query(WasteManagement)
            .filter_by(barangay_id=barangay_id)
            .order_by(WasteManagement.year.desc())
            .all()
        )
        return [
            {
                "id": r.id, "year": r.year,
                "collection_frequency": r.collection_frequency,
                "disposal_method": r.disposal_method,
                "coverage_pct": r.coverage_pct,
            }
            for r in records
        ]
    finally:
        session.close()


def save_waste_record(barangay_id: int, year: int, data: dict,
                      user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        existing = session.query(WasteManagement).filter_by(barangay_id=barangay_id, year=year).first()
        if existing:
            old_values = {c.key: getattr(existing, c.key) for c in WasteManagement.__table__.columns
                         if c.key not in ("id", "barangay_id", "year", "created_at", "updated_at")}
            for key, value in data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            session.commit()
            log_action(user_id, "UPDATE", "waste_management", existing.id,
                       old_values=old_values, new_values=data)
            return True, "Waste management record updated."
        else:
            record = WasteManagement(barangay_id=barangay_id, year=year, **data)
            session.add(record)
            session.commit()
            log_action(user_id, "CREATE", "waste_management", record.id,
                       new_values={"barangay_id": barangay_id, "year": year, **data})
            return True, "Waste management record created."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()
