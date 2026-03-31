import logging
from database.db import get_session
from database.models import ResidentCategory
from services.audit_service import log_action

logger = logging.getLogger(__name__)


def get_resident_categories(barangay_id: int) -> list[dict]:
    session = get_session()
    try:
        records = (
            session.query(ResidentCategory)
            .filter_by(barangay_id=barangay_id)
            .order_by(ResidentCategory.year.desc())
            .all()
        )
        return [
            {
                "id": r.id,
                "year": r.year,
                "renters_count": r.renters_count,
                "homeowners_count": r.homeowners_count,
                "squatters_count": r.squatters_count,
                "informal_settlers_count": r.informal_settlers_count,
            }
            for r in records
        ]
    finally:
        session.close()


def save_resident_category(barangay_id: int, year: int, data: dict,
                           user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        existing = (
            session.query(ResidentCategory)
            .filter_by(barangay_id=barangay_id, year=year)
            .first()
        )

        if existing:
            old_values = {
                "renters_count": existing.renters_count,
                "homeowners_count": existing.homeowners_count,
                "squatters_count": existing.squatters_count,
                "informal_settlers_count": existing.informal_settlers_count,
            }
            for key, value in data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            session.commit()
            log_action(user_id, "UPDATE", "resident_categories", existing.id,
                       old_values=old_values, new_values=data)
            return True, "Resident category data updated."
        else:
            record = ResidentCategory(barangay_id=barangay_id, year=year, **data)
            session.add(record)
            session.commit()
            log_action(user_id, "CREATE", "resident_categories", record.id,
                       new_values={"barangay_id": barangay_id, "year": year, **data})
            return True, "Resident category data created."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()
