import logging
from sqlalchemy import func
from database.db import get_session
from database.models import (
    Barangay, District, PopulationRecord, IncomeData,
    Business, Utility
)

logger = logging.getLogger(__name__)


def _get_latest_year(session) -> int | None:
    return session.query(func.max(PopulationRecord.year)).scalar()


def get_population_by_district() -> list[dict]:
    session = get_session()
    try:
        latest_year = _get_latest_year(session)
        if not latest_year:
            return []

        districts = session.query(District).order_by(District.name).all()
        result = []
        for d in districts:
            brgy_ids = [b.id for b in session.query(Barangay.id).filter_by(district_id=d.id).all()]
            if not brgy_ids:
                result.append({"district_name": d.name, "total_population": 0})
                continue

            pop = (
                session.query(func.sum(PopulationRecord.total_population))
                .filter(PopulationRecord.barangay_id.in_(brgy_ids))
                .filter(PopulationRecord.year == latest_year)
                .scalar()
            ) or 0

            result.append({"district_name": d.name, "total_population": pop})
        return result
    finally:
        session.close()


def get_population_trend(barangay_id: int | None = None,
                         district_id: int | None = None) -> list[dict]:
    session = get_session()
    try:
        if barangay_id:
            records = (
                session.query(PopulationRecord)
                .filter_by(barangay_id=barangay_id)
                .order_by(PopulationRecord.year)
                .all()
            )
            return [
                {
                    "year": r.year,
                    "total_population": r.total_population or 0,
                    "male_count": r.male_count or 0,
                    "female_count": r.female_count or 0,
                }
                for r in records
            ]

        if district_id:
            brgy_ids = [b.id for b in session.query(Barangay.id).filter_by(district_id=district_id).all()]
        else:
            brgy_ids = [b.id for b in session.query(Barangay.id).all()]

        if not brgy_ids:
            return []

        years = (
            session.query(PopulationRecord.year)
            .filter(PopulationRecord.barangay_id.in_(brgy_ids))
            .distinct()
            .order_by(PopulationRecord.year)
            .all()
        )

        result = []
        for (year,) in years:
            row = session.query(
                func.sum(PopulationRecord.total_population),
                func.sum(PopulationRecord.male_count),
                func.sum(PopulationRecord.female_count),
            ).filter(
                PopulationRecord.barangay_id.in_(brgy_ids),
                PopulationRecord.year == year,
            ).first()

            result.append({
                "year": year,
                "total_population": row[0] or 0,
                "male_count": row[1] or 0,
                "female_count": row[2] or 0,
            })
        return result
    finally:
        session.close()


def get_district_comparison() -> list[dict]:
    session = get_session()
    try:
        latest_year = _get_latest_year(session)
        districts = session.query(District).order_by(District.name).all()
        result = []

        for d in districts:
            brgy_ids = [b.id for b in session.query(Barangay.id).filter_by(district_id=d.id).all()]
            row = {"district_name": d.name}

            if not brgy_ids:
                row.update({
                    "total_population": 0, "avg_income": 0,
                    "avg_water_coverage": 0, "avg_power_coverage": 0,
                    "avg_internet_coverage": 0, "active_businesses": 0,
                })
                result.append(row)
                continue

            # Population
            pop_query = session.query(func.sum(PopulationRecord.total_population)).filter(
                PopulationRecord.barangay_id.in_(brgy_ids)
            )
            if latest_year:
                pop_query = pop_query.filter(PopulationRecord.year == latest_year)
            row["total_population"] = pop_query.scalar() or 0

            # Income
            inc_query = session.query(func.avg(IncomeData.average_household_income)).filter(
                IncomeData.barangay_id.in_(brgy_ids)
            )
            if latest_year:
                inc_query = inc_query.filter(IncomeData.year == latest_year)
            avg_inc = inc_query.scalar()
            row["avg_income"] = round(avg_inc, 2) if avg_inc else 0

            # Utilities
            util_query = session.query(
                func.avg(Utility.water_coverage_pct),
                func.avg(Utility.power_coverage_pct),
                func.avg(Utility.internet_coverage_pct),
            ).filter(Utility.barangay_id.in_(brgy_ids))
            if latest_year:
                util_query = util_query.filter(Utility.year == latest_year)
            util_row = util_query.first()
            row["avg_water_coverage"] = round(util_row[0], 1) if util_row and util_row[0] else 0
            row["avg_power_coverage"] = round(util_row[1], 1) if util_row and util_row[1] else 0
            row["avg_internet_coverage"] = round(util_row[2], 1) if util_row and util_row[2] else 0

            # Businesses
            row["active_businesses"] = session.query(Business).filter(
                Business.barangay_id.in_(brgy_ids), Business.is_active == True
            ).count()

            result.append(row)
        return result
    finally:
        session.close()


def get_income_distribution(barangay_id: int) -> dict | None:
    session = get_session()
    try:
        brgy = session.query(Barangay).get(barangay_id)
        if not brgy:
            return None

        record = (
            session.query(IncomeData)
            .filter_by(barangay_id=barangay_id)
            .order_by(IncomeData.year.desc())
            .first()
        )
        if not record:
            return None

        return {
            "barangay_name": brgy.name,
            "year": record.year,
            "below_poverty": record.below_poverty_count or 0,
            "low_income": record.low_income_count or 0,
            "middle_income": record.middle_income_count or 0,
            "high_income": record.high_income_count or 0,
        }
    finally:
        session.close()


def get_utility_coverage_by_district() -> list[dict]:
    session = get_session()
    try:
        latest_year = _get_latest_year(session)
        districts = session.query(District).order_by(District.name).all()
        result = []

        for d in districts:
            brgy_ids = [b.id for b in session.query(Barangay.id).filter_by(district_id=d.id).all()]
            row = {"district_name": d.name}

            if not brgy_ids:
                row.update({"water_coverage": 0, "power_coverage": 0, "internet_coverage": 0})
                result.append(row)
                continue

            util_query = session.query(
                func.avg(Utility.water_coverage_pct),
                func.avg(Utility.power_coverage_pct),
                func.avg(Utility.internet_coverage_pct),
            ).filter(Utility.barangay_id.in_(brgy_ids))
            if latest_year:
                util_query = util_query.filter(Utility.year == latest_year)
            util_row = util_query.first()

            row["water_coverage"] = round(util_row[0], 1) if util_row and util_row[0] else 0
            row["power_coverage"] = round(util_row[1], 1) if util_row and util_row[1] else 0
            row["internet_coverage"] = round(util_row[2], 1) if util_row and util_row[2] else 0
            result.append(row)
        return result
    finally:
        session.close()
