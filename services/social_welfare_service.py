import logging
from sqlalchemy import func
from database.db import get_session
from database.models import SocialWelfareData, Barangay
from services.audit_service import log_action
from services.history_service import record_field_changes

logger = logging.getLogger(__name__)


def save_social_welfare_data(barangay_id: int, year: int, data: dict,
                             user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        existing = (
            session.query(SocialWelfareData)
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
            record_field_changes("social_welfare_data", existing.id, old_data, new_data, user_id)
            session.commit()
            log_action(user_id, "UPDATE", "social_welfare_data", existing.id,
                       old_values=old_values, new_values=data)
            return True, "Social welfare data updated."
        else:
            record = SocialWelfareData(barangay_id=barangay_id, year=year, **data)
            session.add(record)
            session.commit()
            log_action(user_id, "CREATE", "social_welfare_data", record.id,
                       new_values={"barangay_id": barangay_id, "year": year, **data})
            return True, "Social welfare data created."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def get_social_welfare_data(barangay_id: int) -> list[dict]:
    session = get_session()
    try:
        records = (
            session.query(SocialWelfareData)
            .filter_by(barangay_id=barangay_id)
            .order_by(SocialWelfareData.year.desc())
            .all()
        )
        return [
            {
                "id": r.id, "barangay_id": r.barangay_id, "year": r.year,
                "fourps_beneficiaries": r.fourps_beneficiaries,
                "senior_citizen_count": r.senior_citizen_count,
                "pwd_count": r.pwd_count,
                "solo_parent_count": r.solo_parent_count,
                "indigent_families": r.indigent_families,
                "nutrition_program_beneficiaries": r.nutrition_program_beneficiaries,
            }
            for r in records
        ]
    finally:
        session.close()


def get_welfare_stats_by_year(year: int, district_id: int | None = None) -> list[dict]:
    session = get_session()
    try:
        query = session.query(SocialWelfareData).join(Barangay).filter(SocialWelfareData.year == year)
        if district_id:
            query = query.filter(Barangay.district_id == district_id)
        records = query.all()
        return [
            {
                "barangay_id": r.barangay_id, "barangay_name": r.barangay.name,
                "fourps_beneficiaries": r.fourps_beneficiaries or 0,
                "senior_citizen_count": r.senior_citizen_count or 0,
                "pwd_count": r.pwd_count or 0,
                "solo_parent_count": r.solo_parent_count or 0,
                "indigent_families": r.indigent_families or 0,
            }
            for r in records
        ]
    finally:
        session.close()


def get_welfare_summary(barangay_id: int | None = None, district_id: int | None = None,
                        year: int | None = None) -> dict:
    session = get_session()
    try:
        query = session.query(SocialWelfareData)
        if barangay_id:
            query = query.filter(SocialWelfareData.barangay_id == barangay_id)
        elif district_id:
            brgy_ids = [b.id for b in session.query(Barangay.id).filter_by(district_id=district_id).all()]
            query = query.filter(SocialWelfareData.barangay_id.in_(brgy_ids))
        if year:
            query = query.filter(SocialWelfareData.year == year)
        records = query.all()
        return {
            "total_fourps": sum(r.fourps_beneficiaries or 0 for r in records),
            "total_seniors": sum(r.senior_citizen_count or 0 for r in records),
            "total_pwd": sum(r.pwd_count or 0 for r in records),
            "total_solo_parents": sum(r.solo_parent_count or 0 for r in records),
            "total_indigent": sum(r.indigent_families or 0 for r in records),
        }
    finally:
        session.close()
