import logging
from sqlalchemy import func
from database.db import get_session
from database.models import HealthStatistics, Barangay, District
from services.audit_service import log_action
from services.history_service import record_field_changes

logger = logging.getLogger(__name__)

DISEASE_TYPES = ["dengue", "tuberculosis", "covid", "diarrhea", "pneumonia", "hypertension", "diabetes", "other"]


def save_health_statistics(barangay_id: int, year: int, data: dict,
                           user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        existing = (
            session.query(HealthStatistics)
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
            record_field_changes("health_statistics", existing.id, old_data, new_data, user_id)
            session.commit()
            log_action(user_id, "UPDATE", "health_statistics", existing.id,
                       old_values=old_values, new_values=data)
            from services.cross_department_service import on_department_data_saved
            on_department_data_saved("health", barangay_id, year, user_id)
            return True, "Health statistics updated."
        else:
            record = HealthStatistics(barangay_id=barangay_id, year=year, **data)
            session.add(record)
            session.commit()
            log_action(user_id, "CREATE", "health_statistics", record.id,
                       new_values={"barangay_id": barangay_id, "year": year, **data})
            from services.cross_department_service import on_department_data_saved
            on_department_data_saved("health", barangay_id, year, user_id)
            return True, "Health statistics created."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def get_health_statistics(barangay_id: int) -> list[dict]:
    session = get_session()
    try:
        records = (
            session.query(HealthStatistics)
            .filter_by(barangay_id=barangay_id)
            .order_by(HealthStatistics.year.desc())
            .all()
        )
        return [
            {
                "id": r.id, "barangay_id": r.barangay_id, "year": r.year,
                "dengue_cases": r.dengue_cases, "tuberculosis_cases": r.tuberculosis_cases,
                "covid_cases": r.covid_cases, "diarrhea_cases": r.diarrhea_cases,
                "pneumonia_cases": r.pneumonia_cases, "hypertension_cases": r.hypertension_cases,
                "diabetes_cases": r.diabetes_cases, "other_disease_cases": r.other_disease_cases,
                "vaccination_coverage_pct": r.vaccination_coverage_pct,
                "hospital_count": r.hospital_count, "clinic_count": r.clinic_count,
                "health_worker_count": r.health_worker_count,
                "maternal_mortality": r.maternal_mortality, "infant_mortality": r.infant_mortality,
                "malnutrition_rate": r.malnutrition_rate,
            }
            for r in records
        ]
    finally:
        session.close()


def _get_brgy_ids(session, barangay_id=None, district_id=None) -> list[int] | None:
    if barangay_id:
        return [barangay_id]
    if district_id:
        return [b.id for b in session.query(Barangay.id).filter_by(district_id=district_id).all()]
    return None


def get_health_stats_by_year(year: int, district_id: int | None = None) -> list[dict]:
    session = get_session()
    try:
        query = session.query(HealthStatistics).join(Barangay).filter(HealthStatistics.year == year)
        if district_id:
            query = query.filter(Barangay.district_id == district_id)
        records = query.all()
        return [
            {
                "barangay_id": r.barangay_id, "barangay_name": r.barangay.name,
                "dengue_cases": r.dengue_cases or 0, "tuberculosis_cases": r.tuberculosis_cases or 0,
                "covid_cases": r.covid_cases or 0, "vaccination_coverage_pct": r.vaccination_coverage_pct or 0,
                "malnutrition_rate": r.malnutrition_rate or 0,
                "maternal_mortality": r.maternal_mortality or 0, "infant_mortality": r.infant_mortality or 0,
            }
            for r in records
        ]
    finally:
        session.close()


def get_disease_trend(barangay_id: int | None = None, district_id: int | None = None) -> list[dict]:
    session = get_session()
    try:
        brgy_ids = _get_brgy_ids(session, barangay_id, district_id)
        query = session.query(
            HealthStatistics.year,
            func.sum(HealthStatistics.dengue_cases).label("dengue"),
            func.sum(HealthStatistics.tuberculosis_cases).label("tb"),
            func.sum(HealthStatistics.covid_cases).label("covid"),
            func.sum(HealthStatistics.diarrhea_cases).label("diarrhea"),
            func.sum(HealthStatistics.pneumonia_cases).label("pneumonia"),
        )
        if brgy_ids:
            query = query.filter(HealthStatistics.barangay_id.in_(brgy_ids))
        rows = query.group_by(HealthStatistics.year).order_by(HealthStatistics.year).all()
        return [
            {"year": r[0], "dengue": r[1] or 0, "tb": r[2] or 0, "covid": r[3] or 0,
             "diarrhea": r[4] or 0, "pneumonia": r[5] or 0}
            for r in rows
        ]
    finally:
        session.close()


def get_health_summary(barangay_id: int | None = None, district_id: int | None = None,
                       year: int | None = None) -> dict:
    session = get_session()
    try:
        brgy_ids = _get_brgy_ids(session, barangay_id, district_id)
        query = session.query(HealthStatistics)
        if brgy_ids:
            query = query.filter(HealthStatistics.barangay_id.in_(brgy_ids))
        if year:
            query = query.filter(HealthStatistics.year == year)
        records = query.all()
        if not records:
            return {"total_disease_cases": 0, "avg_vaccination": 0, "avg_malnutrition": 0,
                    "total_hospitals": 0, "total_clinics": 0}

        total_diseases = sum(
            (r.dengue_cases or 0) + (r.tuberculosis_cases or 0) + (r.covid_cases or 0) +
            (r.diarrhea_cases or 0) + (r.pneumonia_cases or 0) + (r.hypertension_cases or 0) +
            (r.diabetes_cases or 0) + (r.other_disease_cases or 0)
            for r in records
        )
        vax = [r.vaccination_coverage_pct for r in records if r.vaccination_coverage_pct is not None]
        mal = [r.malnutrition_rate for r in records if r.malnutrition_rate is not None]
        return {
            "total_disease_cases": total_diseases,
            "avg_vaccination": round(sum(vax) / len(vax), 1) if vax else 0,
            "avg_malnutrition": round(sum(mal) / len(mal), 1) if mal else 0,
            "total_hospitals": sum(r.hospital_count or 0 for r in records),
            "total_clinics": sum(r.clinic_count or 0 for r in records),
        }
    finally:
        session.close()
