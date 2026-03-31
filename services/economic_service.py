import logging
from database.db import get_session
from database.models import IncomeData, Business
from services.audit_service import log_action

logger = logging.getLogger(__name__)


def get_income_records(barangay_id: int) -> list[dict]:
    session = get_session()
    try:
        records = (
            session.query(IncomeData)
            .filter_by(barangay_id=barangay_id)
            .order_by(IncomeData.year.desc())
            .all()
        )
        return [
            {
                "id": r.id,
                "year": r.year,
                "average_household_income": r.average_household_income,
                "below_poverty_count": r.below_poverty_count,
                "low_income_count": r.low_income_count,
                "middle_income_count": r.middle_income_count,
                "high_income_count": r.high_income_count,
            }
            for r in records
        ]
    finally:
        session.close()


def save_income_record(barangay_id: int, year: int, data: dict,
                       user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        existing = (
            session.query(IncomeData)
            .filter_by(barangay_id=barangay_id, year=year)
            .first()
        )
        if existing:
            old_values = {c.key: getattr(existing, c.key) for c in IncomeData.__table__.columns
                         if c.key not in ("id", "barangay_id", "year", "created_at", "updated_at")}
            for key, value in data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            session.commit()
            log_action(user_id, "UPDATE", "income_data", existing.id,
                       old_values=old_values, new_values=data)
            return True, "Income record updated."
        else:
            record = IncomeData(barangay_id=barangay_id, year=year, **data)
            session.add(record)
            session.commit()
            log_action(user_id, "CREATE", "income_data", record.id,
                       new_values={"barangay_id": barangay_id, "year": year, **data})
            return True, "Income record created."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def get_businesses(barangay_id: int) -> list[dict]:
    session = get_session()
    try:
        businesses = (
            session.query(Business)
            .filter_by(barangay_id=barangay_id)
            .order_by(Business.name)
            .all()
        )
        return [
            {
                "id": b.id,
                "name": b.name,
                "type": b.type,
                "is_active": b.is_active,
                "registered_date": b.registered_date.strftime("%Y-%m-%d") if b.registered_date else "",
            }
            for b in businesses
        ]
    finally:
        session.close()


def save_business(barangay_id: int, data: dict, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        business_id = data.pop("id", None)
        if business_id:
            business = session.query(Business).get(business_id)
            if business is None:
                return False, "Business not found."
            old_values = {"name": business.name, "type": business.type, "is_active": business.is_active}
            for key, value in data.items():
                if hasattr(business, key):
                    setattr(business, key, value)
            session.commit()
            log_action(user_id, "UPDATE", "businesses", business.id,
                       old_values=old_values, new_values=data)
            return True, "Business updated."
        else:
            business = Business(barangay_id=barangay_id, **data)
            session.add(business)
            session.commit()
            log_action(user_id, "CREATE", "businesses", business.id,
                       new_values={"barangay_id": barangay_id, **data})
            return True, "Business created."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def delete_business(business_id: int, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        business = session.query(Business).get(business_id)
        if business is None:
            return False, "Business not found."
        old_values = {"name": business.name, "type": business.type}
        session.delete(business)
        session.commit()
        log_action(user_id, "DELETE", "businesses", business_id, old_values=old_values)
        return True, "Business deleted."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()
