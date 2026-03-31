import logging
from sqlalchemy import func
from database.db import get_session
from database.models import (
    Barangay, District, PopulationRecord, ResidentCategory,
    IncomeData, Business, Utility, LandType, WasteManagement,
    FoodSource, GovernmentFacility, ReligiousDemographic,
    User, AuditLog
)

logger = logging.getLogger(__name__)


# ── Dashboard Stats (Phase 1) ────────────────────────────────

def get_dashboard_stats() -> dict:
    session = get_session()
    try:
        total_barangays = session.query(Barangay).count()
        total_districts = session.query(District).count()
        active_users = session.query(User).filter_by(is_active=True).count()

        latest_pop = (
            session.query(func.sum(PopulationRecord.total_population))
            .filter(
                PopulationRecord.year == session.query(func.max(PopulationRecord.year)).scalar_subquery()
            )
            .scalar()
        )

        latest_households = (
            session.query(func.sum(PopulationRecord.household_count))
            .filter(
                PopulationRecord.year == session.query(func.max(PopulationRecord.year)).scalar_subquery()
            )
            .scalar()
        )

        return {
            "total_barangays": total_barangays,
            "total_districts": total_districts,
            "total_population": latest_pop or 0,
            "total_households": latest_households or 0,
            "active_users": active_users,
        }
    finally:
        session.close()


def get_district_overview() -> list[dict]:
    session = get_session()
    try:
        districts = session.query(District).order_by(District.name).all()
        result = []
        for d in districts:
            brgy_count = session.query(Barangay).filter_by(district_id=d.id).count()
            brgy_ids = [b.id for b in session.query(Barangay.id).filter_by(district_id=d.id).all()]

            pop = 0
            if brgy_ids:
                pop = (
                    session.query(func.sum(PopulationRecord.total_population))
                    .filter(PopulationRecord.barangay_id.in_(brgy_ids))
                    .filter(
                        PopulationRecord.year == session.query(func.max(PopulationRecord.year)).scalar_subquery()
                    )
                    .scalar()
                ) or 0

            result.append({
                "id": d.id,
                "name": d.name,
                "barangay_count": brgy_count,
                "total_population": pop,
            })
        return result
    finally:
        session.close()


# ── Phase 2: Report Queries ──────────────────────────────────

def _get_latest_year(session) -> int | None:
    return session.query(func.max(PopulationRecord.year)).scalar()


def _get_latest_record(session, model, barangay_id: int):
    return (
        session.query(model)
        .filter_by(barangay_id=barangay_id)
        .order_by(model.year.desc())
        .first()
    )


def get_barangay_full_profile(barangay_id: int) -> dict | None:
    session = get_session()
    try:
        brgy = session.query(Barangay).get(barangay_id)
        if not brgy:
            return None

        # Basic info
        profile = {
            "barangay": {
                "name": brgy.name,
                "district_name": brgy.district.name,
                "classification": brgy.classification or "N/A",
                "latitude": brgy.latitude,
                "longitude": brgy.longitude,
                "area_sqkm": brgy.area_sqkm,
            },
        }

        # Population records
        pop_records = (
            session.query(PopulationRecord)
            .filter_by(barangay_id=barangay_id)
            .order_by(PopulationRecord.year.desc())
            .all()
        )
        profile["population"] = [
            {
                "year": r.year, "total_population": r.total_population,
                "male_count": r.male_count, "female_count": r.female_count,
                "registered_voters": r.registered_voters,
                "non_registered_residents": r.non_registered_residents,
                "foreign_residents": r.foreign_residents,
                "household_count": r.household_count,
            }
            for r in pop_records
        ]

        # Resident categories
        res_records = (
            session.query(ResidentCategory)
            .filter_by(barangay_id=barangay_id)
            .order_by(ResidentCategory.year.desc())
            .all()
        )
        profile["resident_categories"] = [
            {
                "year": r.year, "renters_count": r.renters_count,
                "homeowners_count": r.homeowners_count,
                "squatters_count": r.squatters_count,
                "informal_settlers_count": r.informal_settlers_count,
            }
            for r in res_records
        ]

        # Income
        income_records = (
            session.query(IncomeData)
            .filter_by(barangay_id=barangay_id)
            .order_by(IncomeData.year.desc())
            .all()
        )
        profile["income"] = [
            {
                "year": r.year,
                "average_household_income": r.average_household_income,
                "below_poverty_count": r.below_poverty_count,
                "low_income_count": r.low_income_count,
                "middle_income_count": r.middle_income_count,
                "high_income_count": r.high_income_count,
            }
            for r in income_records
        ]

        # Businesses
        businesses = (
            session.query(Business)
            .filter_by(barangay_id=barangay_id)
            .order_by(Business.name)
            .all()
        )
        profile["businesses"] = [
            {
                "name": b.name, "type": b.type,
                "is_active": b.is_active,
                "registered_date": b.registered_date.strftime("%Y-%m-%d") if b.registered_date else "",
            }
            for b in businesses
        ]

        # Utilities
        util_records = (
            session.query(Utility)
            .filter_by(barangay_id=barangay_id)
            .order_by(Utility.year.desc())
            .all()
        )
        profile["utilities"] = [
            {
                "year": r.year, "water_source": r.water_source,
                "water_coverage_pct": r.water_coverage_pct,
                "power_provider": r.power_provider,
                "power_coverage_pct": r.power_coverage_pct,
                "internet_coverage_pct": r.internet_coverage_pct,
            }
            for r in util_records
        ]

        # Land types
        land_records = session.query(LandType).filter_by(barangay_id=barangay_id).all()
        profile["land_types"] = [
            {"type": r.type, "area_sqkm": r.area_sqkm, "percentage": r.percentage}
            for r in land_records
        ]

        # Waste management
        waste_records = (
            session.query(WasteManagement)
            .filter_by(barangay_id=barangay_id)
            .order_by(WasteManagement.year.desc())
            .all()
        )
        profile["waste_management"] = [
            {
                "year": r.year, "collection_frequency": r.collection_frequency,
                "disposal_method": r.disposal_method, "coverage_pct": r.coverage_pct,
            }
            for r in waste_records
        ]

        # Food sources
        food_records = session.query(FoodSource).filter_by(barangay_id=barangay_id).all()
        profile["food_sources"] = [
            {"type": r.type, "description": r.description}
            for r in food_records
        ]

        # Government facilities
        facility_records = session.query(GovernmentFacility).filter_by(barangay_id=barangay_id).all()
        profile["government_facilities"] = [
            {"agency_name": r.agency_name, "facility_type": r.facility_type, "address": r.address}
            for r in facility_records
        ]

        # Religious demographics
        rel_records = (
            session.query(ReligiousDemographic)
            .filter_by(barangay_id=barangay_id)
            .order_by(ReligiousDemographic.year.desc(), ReligiousDemographic.count.desc())
            .all()
        )
        profile["religious_demographics"] = [
            {"year": r.year, "religion": r.religion, "count": r.count, "percentage": r.percentage}
            for r in rel_records
        ]

        return profile
    finally:
        session.close()


def get_district_report(district_id: int) -> dict | None:
    session = get_session()
    try:
        district = session.query(District).get(district_id)
        if not district:
            return None

        barangays = session.query(Barangay).filter_by(district_id=district_id).order_by(Barangay.name).all()
        brgy_ids = [b.id for b in barangays]

        latest_year = _get_latest_year(session)

        # Population aggregates
        pop_query = session.query(
            func.sum(PopulationRecord.total_population),
            func.sum(PopulationRecord.male_count),
            func.sum(PopulationRecord.female_count),
            func.sum(PopulationRecord.household_count),
            func.sum(PopulationRecord.registered_voters),
        ).filter(PopulationRecord.barangay_id.in_(brgy_ids))

        if latest_year:
            pop_query = pop_query.filter(PopulationRecord.year == latest_year)

        pop_row = pop_query.first()

        # Income aggregates
        income_query = session.query(
            func.avg(IncomeData.average_household_income),
            func.sum(IncomeData.below_poverty_count),
        ).filter(IncomeData.barangay_id.in_(brgy_ids))

        if latest_year:
            income_query = income_query.filter(IncomeData.year == latest_year)

        income_row = income_query.first()

        # Utility averages
        util_query = session.query(
            func.avg(Utility.water_coverage_pct),
            func.avg(Utility.power_coverage_pct),
            func.avg(Utility.internet_coverage_pct),
        ).filter(Utility.barangay_id.in_(brgy_ids))

        if latest_year:
            util_query = util_query.filter(Utility.year == latest_year)

        util_row = util_query.first()

        # Business counts
        active_biz = session.query(Business).filter(
            Business.barangay_id.in_(brgy_ids), Business.is_active == True
        ).count()
        inactive_biz = session.query(Business).filter(
            Business.barangay_id.in_(brgy_ids), Business.is_active == False
        ).count()

        # Barangay list with population
        barangay_list = []
        for b in barangays:
            pop = None
            if latest_year:
                pr = session.query(PopulationRecord).filter_by(
                    barangay_id=b.id, year=latest_year
                ).first()
                if pr:
                    pop = pr.total_population
            barangay_list.append({
                "name": b.name,
                "population": pop,
                "classification": b.classification or "N/A",
            })

        return {
            "district": {"name": district.name, "barangay_count": len(barangays)},
            "population": {
                "total_population": pop_row[0] or 0 if pop_row else 0,
                "total_male": pop_row[1] or 0 if pop_row else 0,
                "total_female": pop_row[2] or 0 if pop_row else 0,
                "total_households": pop_row[3] or 0 if pop_row else 0,
                "total_voters": pop_row[4] or 0 if pop_row else 0,
            },
            "income": {
                "average_household_income": round(income_row[0], 2) if income_row and income_row[0] else 0,
                "total_below_poverty": income_row[1] or 0 if income_row else 0,
            },
            "utilities": {
                "avg_water_coverage": round(util_row[0], 1) if util_row and util_row[0] else 0,
                "avg_power_coverage": round(util_row[1], 1) if util_row and util_row[1] else 0,
                "avg_internet_coverage": round(util_row[2], 1) if util_row and util_row[2] else 0,
            },
            "businesses": {"total_active": active_biz, "total_inactive": inactive_biz},
            "barangay_list": barangay_list,
        }
    finally:
        session.close()


def get_citywide_report() -> dict:
    session = get_session()
    try:
        total_barangays = session.query(Barangay).count()
        total_districts = session.query(District).count()
        latest_year = _get_latest_year(session)

        all_brgy_ids = [b.id for b in session.query(Barangay.id).all()]

        # Population
        pop_query = session.query(
            func.sum(PopulationRecord.total_population),
            func.sum(PopulationRecord.male_count),
            func.sum(PopulationRecord.female_count),
            func.sum(PopulationRecord.household_count),
            func.sum(PopulationRecord.registered_voters),
        )
        if latest_year:
            pop_query = pop_query.filter(PopulationRecord.year == latest_year)
        pop_row = pop_query.first()

        # Income
        income_query = session.query(
            func.avg(IncomeData.average_household_income),
            func.sum(IncomeData.below_poverty_count),
        )
        if latest_year:
            income_query = income_query.filter(IncomeData.year == latest_year)
        income_row = income_query.first()

        # Utilities
        util_query = session.query(
            func.avg(Utility.water_coverage_pct),
            func.avg(Utility.power_coverage_pct),
            func.avg(Utility.internet_coverage_pct),
        )
        if latest_year:
            util_query = util_query.filter(Utility.year == latest_year)
        util_row = util_query.first()

        # Businesses
        active_biz = session.query(Business).filter_by(is_active=True).count()
        inactive_biz = session.query(Business).filter_by(is_active=False).count()

        # Per-district breakdown
        districts = session.query(District).order_by(District.name).all()
        district_reports = []
        for d in districts:
            dr = get_district_report(d.id)
            if dr:
                district_reports.append(dr)

        return {
            "city": {"total_barangays": total_barangays, "total_districts": total_districts},
            "population": {
                "total_population": pop_row[0] or 0 if pop_row else 0,
                "total_male": pop_row[1] or 0 if pop_row else 0,
                "total_female": pop_row[2] or 0 if pop_row else 0,
                "total_households": pop_row[3] or 0 if pop_row else 0,
                "total_voters": pop_row[4] or 0 if pop_row else 0,
            },
            "income": {
                "average_household_income": round(income_row[0], 2) if income_row and income_row[0] else 0,
                "total_below_poverty": income_row[1] or 0 if income_row else 0,
            },
            "utilities": {
                "avg_water_coverage": round(util_row[0], 1) if util_row and util_row[0] else 0,
                "avg_power_coverage": round(util_row[1], 1) if util_row and util_row[1] else 0,
                "avg_internet_coverage": round(util_row[2], 1) if util_row and util_row[2] else 0,
            },
            "businesses": {"total_active": active_biz, "total_inactive": inactive_biz},
            "districts": district_reports,
        }
    finally:
        session.close()


def get_comparative_report(barangay_ids: list[int]) -> dict:
    session = get_session()
    try:
        latest_year = _get_latest_year(session)
        barangays_data = []

        for bid in barangay_ids:
            brgy = session.query(Barangay).get(bid)
            if not brgy:
                continue

            row = {"name": brgy.name, "district_name": brgy.district.name}

            # Population
            pop = None
            if latest_year:
                pop = session.query(PopulationRecord).filter_by(
                    barangay_id=bid, year=latest_year
                ).first()
            row["population"] = pop.total_population if pop else None
            row["household_count"] = pop.household_count if pop else None

            # Income
            inc = None
            if latest_year:
                inc = session.query(IncomeData).filter_by(
                    barangay_id=bid, year=latest_year
                ).first()
            row["avg_income"] = inc.average_household_income if inc else None

            # Utilities
            util = None
            if latest_year:
                util = session.query(Utility).filter_by(
                    barangay_id=bid, year=latest_year
                ).first()
            row["water_coverage"] = util.water_coverage_pct if util else None
            row["power_coverage"] = util.power_coverage_pct if util else None
            row["internet_coverage"] = util.internet_coverage_pct if util else None

            # Business count
            biz_count = session.query(Business).filter_by(
                barangay_id=bid, is_active=True
            ).count()
            row["business_count"] = biz_count

            barangays_data.append(row)

        return {"barangays": barangays_data}
    finally:
        session.close()
