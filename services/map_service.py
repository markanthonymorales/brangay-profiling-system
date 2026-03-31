import logging
from datetime import date, timedelta
from sqlalchemy import func
from database.db import get_session
from database.models import (
    Barangay, District, PopulationRecord, CrimeIncident,
    TrafficIncident, IncomeData, Utility
)

logger = logging.getLogger(__name__)


def get_map_markers() -> list[dict]:
    session = get_session()
    try:
        barangays = (
            session.query(Barangay)
            .filter(Barangay.latitude.isnot(None), Barangay.longitude.isnot(None))
            .join(District)
            .order_by(District.name, Barangay.name)
            .all()
        )

        cutoff = date.today() - timedelta(days=365)

        result = []
        for b in barangays:
            # Latest population
            pop_rec = (
                session.query(PopulationRecord)
                .filter_by(barangay_id=b.id)
                .order_by(PopulationRecord.year.desc())
                .first()
            )

            # Crime count (last 12 months)
            crime_count = (
                session.query(func.count(CrimeIncident.id))
                .filter(CrimeIncident.barangay_id == b.id, CrimeIncident.date_occurred >= cutoff)
                .scalar()
            ) or 0

            result.append({
                "id": b.id,
                "name": b.name,
                "district_name": b.district.name,
                "district_id": b.district_id,
                "lat": b.latitude,
                "lon": b.longitude,
                "population": pop_rec.total_population if pop_rec else None,
                "crime_count": crime_count,
                "classification": b.classification or "N/A",
            })
        return result
    finally:
        session.close()


def get_barangay_map_info(barangay_id: int) -> dict | None:
    session = get_session()
    try:
        b = session.query(Barangay).get(barangay_id)
        if not b:
            return None

        cutoff = date.today() - timedelta(days=365)

        # Population
        pop = (
            session.query(PopulationRecord)
            .filter_by(barangay_id=barangay_id)
            .order_by(PopulationRecord.year.desc())
            .first()
        )

        # Crime count
        crime_count = (
            session.query(func.count(CrimeIncident.id))
            .filter(CrimeIncident.barangay_id == barangay_id, CrimeIncident.date_occurred >= cutoff)
            .scalar()
        ) or 0

        # Top crime type
        top_crime = (
            session.query(CrimeIncident.crime_type, func.count(CrimeIncident.id))
            .filter(CrimeIncident.barangay_id == barangay_id, CrimeIncident.date_occurred >= cutoff)
            .group_by(CrimeIncident.crime_type)
            .order_by(func.count(CrimeIncident.id).desc())
            .first()
        )

        # Traffic count
        traffic_count = (
            session.query(func.count(TrafficIncident.id))
            .filter(TrafficIncident.barangay_id == barangay_id, TrafficIncident.date_occurred >= cutoff)
            .scalar()
        ) or 0

        # Income
        income = (
            session.query(IncomeData)
            .filter_by(barangay_id=barangay_id)
            .order_by(IncomeData.year.desc())
            .first()
        )

        # Utilities
        util = (
            session.query(Utility)
            .filter_by(barangay_id=barangay_id)
            .order_by(Utility.year.desc())
            .first()
        )

        return {
            "name": b.name,
            "district_name": b.district.name,
            "classification": b.classification or "N/A",
            "population": pop.total_population if pop else None,
            "households": pop.household_count if pop else None,
            "crime_count_12m": crime_count,
            "traffic_count_12m": traffic_count,
            "top_crime_type": top_crime[0] if top_crime else None,
            "avg_income": income.average_household_income if income else None,
            "water_coverage": util.water_coverage_pct if util else None,
            "power_coverage": util.power_coverage_pct if util else None,
        }
    finally:
        session.close()
