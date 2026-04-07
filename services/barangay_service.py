import logging
from functools import lru_cache
from sqlalchemy import func
from database.db import get_session
from database.models import Barangay, District, PopulationRecord

logger = logging.getLogger(__name__)

# Module-level caches for static geography data (3 districts, 182 barangays).
# These never change at runtime so we cache after first DB hit.
_districts_cache: list[dict] | None = None
_barangays_by_district_cache: dict[int, list[dict]] = {}


def get_all_barangays() -> list[dict]:
    session = get_session()
    try:
        barangays = (
            session.query(Barangay)
            .join(District)
            .order_by(District.name, Barangay.name)
            .all()
        )
        result = []
        for b in barangays:
            latest_pop = (
                session.query(PopulationRecord)
                .filter_by(barangay_id=b.id)
                .order_by(PopulationRecord.year.desc())
                .first()
            )
            result.append({
                "id": b.id,
                "name": b.name,
                "district_id": b.district_id,
                "district_name": b.district.name,
                "classification": b.classification or "N/A",
                "population": latest_pop.total_population if latest_pop else None,
                "updated_at": b.updated_at.strftime("%Y-%m-%d") if b.updated_at else "",
            })
        return result
    finally:
        session.close()


def get_barangay_by_id(barangay_id: int) -> dict | None:
    session = get_session()
    try:
        b = session.get(Barangay, barangay_id)
        if b is None:
            return None
        return {
            "id": b.id,
            "name": b.name,
            "district_id": b.district_id,
            "district_name": b.district.name,
            "latitude": b.latitude,
            "longitude": b.longitude,
            "area_sqkm": b.area_sqkm,
            "classification": b.classification,
        }
    finally:
        session.close()


def get_barangays_by_district(district_id: int) -> list[dict]:
    if district_id in _barangays_by_district_cache:
        return _barangays_by_district_cache[district_id]
    session = get_session()
    try:
        barangays = (
            session.query(Barangay)
            .filter_by(district_id=district_id)
            .order_by(Barangay.name)
            .all()
        )
        result = [{"id": b.id, "name": b.name} for b in barangays]
        _barangays_by_district_cache[district_id] = result
        return result
    finally:
        session.close()


def search_barangays(search_term: str, district_id: int | None = None,
                     classification: str | None = None) -> list[dict]:
    session = get_session()
    try:
        query = session.query(Barangay).join(District)

        if search_term:
            query = query.filter(Barangay.name.ilike(f"%{search_term}%"))
        if district_id is not None:
            query = query.filter(Barangay.district_id == district_id)
        if classification is not None:
            query = query.filter(Barangay.classification == classification)

        barangays = query.order_by(District.name, Barangay.name).all()
        result = []
        for b in barangays:
            latest_pop = (
                session.query(PopulationRecord)
                .filter_by(barangay_id=b.id)
                .order_by(PopulationRecord.year.desc())
                .first()
            )
            result.append({
                "id": b.id,
                "name": b.name,
                "district_id": b.district_id,
                "district_name": b.district.name,
                "classification": b.classification or "N/A",
                "population": latest_pop.total_population if latest_pop else None,
                "updated_at": b.updated_at.strftime("%Y-%m-%d") if b.updated_at else "",
            })
        return result
    finally:
        session.close()


def get_all_districts() -> list[dict]:
    global _districts_cache
    if _districts_cache is not None:
        return _districts_cache
    session = get_session()
    try:
        districts = session.query(District).order_by(District.name).all()
        _districts_cache = [{"id": d.id, "name": d.name} for d in districts]
        return _districts_cache
    finally:
        session.close()


def get_district_summary() -> list[dict]:
    session = get_session()
    try:
        districts = session.query(District).order_by(District.name).all()
        summaries = []
        for d in districts:
            brgy_count = session.query(Barangay).filter_by(district_id=d.id).count()
            summaries.append({
                "id": d.id,
                "name": d.name,
                "barangay_count": brgy_count,
            })
        return summaries
    finally:
        session.close()
