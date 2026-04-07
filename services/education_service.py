import logging
from sqlalchemy import func
from database.db import get_session
from database.models import EducationStatistics, Barangay
from services.audit_service import log_action
from services.history_service import record_field_changes

logger = logging.getLogger(__name__)


def save_education_statistics(barangay_id: int, year: int, data: dict,
                              user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        existing = (
            session.query(EducationStatistics)
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
            record_field_changes("education_statistics", existing.id, old_data, new_data, user_id)
            session.commit()
            log_action(user_id, "UPDATE", "education_statistics", existing.id,
                       old_values=old_values, new_values=data)
            return True, "Education statistics updated."
        else:
            record = EducationStatistics(barangay_id=barangay_id, year=year, **data)
            session.add(record)
            session.commit()
            log_action(user_id, "CREATE", "education_statistics", record.id,
                       new_values={"barangay_id": barangay_id, "year": year, **data})
            return True, "Education statistics created."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def get_education_statistics(barangay_id: int) -> list[dict]:
    session = get_session()
    try:
        records = (
            session.query(EducationStatistics)
            .filter_by(barangay_id=barangay_id)
            .order_by(EducationStatistics.year.desc())
            .all()
        )
        return [
            {
                "id": r.id, "barangay_id": r.barangay_id, "year": r.year,
                "total_enrollees": r.total_enrollees,
                "elementary_count": r.elementary_count,
                "highschool_count": r.highschool_count,
                "college_count": r.college_count,
                "out_of_school_youth": r.out_of_school_youth,
                "literacy_rate": r.literacy_rate,
                "school_count": r.school_count,
                "teacher_count": r.teacher_count,
                "classroom_count": r.classroom_count,
                "dropout_rate": r.dropout_rate,
            }
            for r in records
        ]
    finally:
        session.close()


def get_education_stats_by_year(year: int, district_id: int | None = None) -> list[dict]:
    session = get_session()
    try:
        query = session.query(EducationStatistics).join(Barangay).filter(EducationStatistics.year == year)
        if district_id:
            query = query.filter(Barangay.district_id == district_id)
        records = query.all()
        return [
            {
                "barangay_id": r.barangay_id, "barangay_name": r.barangay.name,
                "total_enrollees": r.total_enrollees or 0,
                "literacy_rate": r.literacy_rate or 0,
                "dropout_rate": r.dropout_rate or 0,
                "out_of_school_youth": r.out_of_school_youth or 0,
                "school_count": r.school_count or 0,
            }
            for r in records
        ]
    finally:
        session.close()


def get_education_summary(barangay_id: int | None = None, district_id: int | None = None,
                          year: int | None = None) -> dict:
    session = get_session()
    try:
        query = session.query(EducationStatistics)
        if barangay_id:
            query = query.filter(EducationStatistics.barangay_id == barangay_id)
        elif district_id:
            brgy_ids = [b.id for b in session.query(Barangay.id).filter_by(district_id=district_id).all()]
            query = query.filter(EducationStatistics.barangay_id.in_(brgy_ids))
        if year:
            query = query.filter(EducationStatistics.year == year)
        records = query.all()
        if not records:
            return {"total_enrollees": 0, "avg_literacy": 0, "avg_dropout": 0,
                    "total_schools": 0, "total_osy": 0}
        lit = [r.literacy_rate for r in records if r.literacy_rate is not None]
        drop = [r.dropout_rate for r in records if r.dropout_rate is not None]
        return {
            "total_enrollees": sum(r.total_enrollees or 0 for r in records),
            "avg_literacy": round(sum(lit) / len(lit), 1) if lit else 0,
            "avg_dropout": round(sum(drop) / len(drop), 1) if drop else 0,
            "total_schools": sum(r.school_count or 0 for r in records),
            "total_osy": sum(r.out_of_school_youth or 0 for r in records),
        }
    finally:
        session.close()


def get_education_trend(barangay_id: int | None = None, district_id: int | None = None) -> list[dict]:
    session = get_session()
    try:
        query = session.query(EducationStatistics)
        if barangay_id:
            query = query.filter(EducationStatistics.barangay_id == barangay_id)
        elif district_id:
            brgy_ids = [b.id for b in session.query(Barangay.id).filter_by(district_id=district_id).all()]
            query = query.filter(EducationStatistics.barangay_id.in_(brgy_ids))

        from sqlalchemy import func as f
        rows = (
            session.query(
                EducationStatistics.year,
                f.sum(EducationStatistics.total_enrollees).label("enrollees"),
                f.avg(EducationStatistics.literacy_rate).label("avg_literacy"),
                f.avg(EducationStatistics.dropout_rate).label("avg_dropout"),
                f.sum(EducationStatistics.out_of_school_youth).label("osy"),
            )
        )
        if barangay_id:
            rows = rows.filter(EducationStatistics.barangay_id == barangay_id)
        elif district_id:
            brgy_ids = [b.id for b in session.query(Barangay.id).filter_by(district_id=district_id).all()]
            rows = rows.filter(EducationStatistics.barangay_id.in_(brgy_ids))

        results = rows.group_by(EducationStatistics.year).order_by(EducationStatistics.year).all()
        return [
            {"year": r[0], "enrollees": r[1] or 0, "avg_literacy": round(r[2] or 0, 1),
             "avg_dropout": round(r[3] or 0, 1), "osy": r[4] or 0}
            for r in results
        ]
    finally:
        session.close()
