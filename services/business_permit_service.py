import logging
from datetime import date, timedelta
from sqlalchemy import func
from database.db import get_session
from database.models import BusinessPermit, Barangay
from services.audit_service import log_action
from services.history_service import record_field_changes

logger = logging.getLogger(__name__)

PERMIT_STATUSES = ["active", "expired", "revoked", "pending"]
BUSINESS_TYPES = ["retail", "food", "services", "manufacturing", "agriculture",
                  "construction", "transportation", "finance", "real_estate", "other"]


def save_business_permit(barangay_id: int, data: dict, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        permit_id = data.pop("id", None)
        if permit_id:
            record = session.get(BusinessPermit, permit_id)
            if not record:
                return False, "Business permit not found."
            old_data = {c.key: getattr(record, c.key) for c in record.__table__.columns}
            old_values = {
                "business_name": record.business_name, "status": record.status,
                "permit_number": record.permit_number,
            }
            for key, value in data.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            new_data = {c.key: getattr(record, c.key) for c in record.__table__.columns}
            record_field_changes("business_permits", record.id, old_data, new_data, user_id)
            session.commit()
            log_action(user_id, "UPDATE", "business_permits", record.id,
                       old_values=old_values, new_values=data)
            from services.cross_department_service import on_department_data_saved
            on_department_data_saved("business_permits", barangay_id, date.today().year, user_id)
            return True, "Business permit updated."
        else:
            record = BusinessPermit(barangay_id=barangay_id, **data)
            session.add(record)
            session.commit()
            log_action(user_id, "CREATE", "business_permits", record.id,
                       new_values={"barangay_id": barangay_id, **{k: str(v) for k, v in data.items()}})
            from services.cross_department_service import on_department_data_saved
            on_department_data_saved("business_permits", barangay_id, date.today().year, user_id)
            return True, "Business permit recorded."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def delete_business_permit(permit_id: int, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        record = session.get(BusinessPermit, permit_id)
        if not record:
            return False, "Business permit not found."
        old_values = {"business_name": record.business_name, "barangay_id": record.barangay_id}
        session.delete(record)
        session.commit()
        log_action(user_id, "DELETE", "business_permits", permit_id, old_values=old_values)
        return True, "Business permit deleted."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def get_business_permits(barangay_id: int | None = None, business_type: str | None = None,
                         status: str | None = None, limit: int = 200) -> list[dict]:
    session = get_session()
    try:
        query = session.query(BusinessPermit).join(Barangay)
        if barangay_id:
            query = query.filter(BusinessPermit.barangay_id == barangay_id)
        if business_type:
            query = query.filter(BusinessPermit.business_type == business_type)
        if status:
            query = query.filter(BusinessPermit.status == status)

        records = query.order_by(BusinessPermit.date_issued.desc()).limit(limit).all()
        return [
            {
                "id": r.id, "barangay_id": r.barangay_id,
                "barangay_name": r.barangay.name,
                "business_name": r.business_name, "owner_name": r.owner_name,
                "business_type": r.business_type or "",
                "permit_number": r.permit_number or "",
                "date_issued": r.date_issued.strftime("%Y-%m-%d") if r.date_issued else "",
                "date_expiry": r.date_expiry.strftime("%Y-%m-%d") if r.date_expiry else "",
                "status": r.status,
                "annual_revenue": r.annual_revenue or 0,
                "employee_count": r.employee_count or 0,
                "address": r.address or "",
            }
            for r in records
        ]
    finally:
        session.close()


def get_permit_stats(barangay_id: int | None = None, district_id: int | None = None) -> dict:
    session = get_session()
    try:
        query = session.query(BusinessPermit)
        if barangay_id:
            query = query.filter(BusinessPermit.barangay_id == barangay_id)
        elif district_id:
            brgy_ids = [b.id for b in session.query(Barangay.id).filter_by(district_id=district_id).all()]
            query = query.filter(BusinessPermit.barangay_id.in_(brgy_ids))

        by_type = dict(
            query.with_entities(BusinessPermit.business_type, func.count(BusinessPermit.id))
            .group_by(BusinessPermit.business_type).all()
        )
        by_status = dict(
            query.with_entities(BusinessPermit.status, func.count(BusinessPermit.id))
            .group_by(BusinessPermit.status).all()
        )
        total = query.count()
        total_revenue = query.with_entities(func.sum(BusinessPermit.annual_revenue)).scalar() or 0
        total_employees = query.with_entities(func.sum(BusinessPermit.employee_count)).scalar() or 0

        return {
            "total": total, "by_type": by_type, "by_status": by_status,
            "total_revenue": total_revenue, "total_employees": total_employees,
        }
    finally:
        session.close()


def get_expiring_permits(days_ahead: int = 30) -> list[dict]:
    session = get_session()
    try:
        cutoff = date.today() + timedelta(days=days_ahead)
        records = (
            session.query(BusinessPermit)
            .join(Barangay)
            .filter(
                BusinessPermit.date_expiry != None,
                BusinessPermit.date_expiry <= cutoff,
                BusinessPermit.status == "active",
            )
            .order_by(BusinessPermit.date_expiry)
            .all()
        )
        today = date.today()
        return [
            {
                "id": r.id, "barangay_name": r.barangay.name,
                "business_name": r.business_name, "owner_name": r.owner_name,
                "permit_number": r.permit_number or "",
                "date_expiry": r.date_expiry.strftime("%Y-%m-%d") if r.date_expiry else "",
                "is_expired": r.date_expiry < today if r.date_expiry else False,
            }
            for r in records
        ]
    finally:
        session.close()
