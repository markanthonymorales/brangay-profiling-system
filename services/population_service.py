import logging
from database.db import get_session
from database.models import PopulationRecord, AgeDemographic
from services.audit_service import log_action

logger = logging.getLogger(__name__)

AGE_GROUPS = [
    "0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34",
    "35-39", "40-44", "45-49", "50-54", "55-59", "60-64",
    "65-69", "70-74", "75-79", "80+"
]


def get_population_records(barangay_id: int) -> list[dict]:
    session = get_session()
    try:
        records = (
            session.query(PopulationRecord)
            .filter_by(barangay_id=barangay_id)
            .order_by(PopulationRecord.year.desc())
            .all()
        )
        return [
            {
                "id": r.id,
                "year": r.year,
                "total_population": r.total_population,
                "male_count": r.male_count,
                "female_count": r.female_count,
                "registered_voters": r.registered_voters,
                "non_registered_residents": r.non_registered_residents,
                "foreign_residents": r.foreign_residents,
                "household_count": r.household_count,
            }
            for r in records
        ]
    finally:
        session.close()


def save_population_record(barangay_id: int, year: int, data: dict,
                           user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        existing = (
            session.query(PopulationRecord)
            .filter_by(barangay_id=barangay_id, year=year)
            .first()
        )

        if existing:
            old_values = {
                "total_population": existing.total_population,
                "male_count": existing.male_count,
                "female_count": existing.female_count,
                "registered_voters": existing.registered_voters,
                "non_registered_residents": existing.non_registered_residents,
                "foreign_residents": existing.foreign_residents,
                "household_count": existing.household_count,
            }
            for key, value in data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            session.commit()

            log_action(user_id, "UPDATE", "population_records", existing.id,
                       old_values=old_values, new_values=data)
            return True, "Population record updated."
        else:
            record = PopulationRecord(barangay_id=barangay_id, year=year, **data)
            session.add(record)
            session.commit()

            log_action(user_id, "CREATE", "population_records", record.id,
                       new_values={"barangay_id": barangay_id, "year": year, **data})
            return True, "Population record created."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def get_age_demographics(population_record_id: int) -> list[dict]:
    session = get_session()
    try:
        records = (
            session.query(AgeDemographic)
            .filter_by(population_record_id=population_record_id)
            .all()
        )
        return [
            {
                "id": r.id,
                "age_group": r.age_group,
                "male_count": r.male_count,
                "female_count": r.female_count,
            }
            for r in records
        ]
    finally:
        session.close()


def save_age_demographics(population_record_id: int, demographics: list[dict],
                          user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        session.query(AgeDemographic).filter_by(
            population_record_id=population_record_id
        ).delete()

        for d in demographics:
            record = AgeDemographic(
                population_record_id=population_record_id,
                age_group=d["age_group"],
                male_count=d.get("male_count"),
                female_count=d.get("female_count"),
            )
            session.add(record)

        session.commit()

        log_action(user_id, "UPDATE", "age_demographics", population_record_id,
                   new_values={"count": len(demographics)})
        return True, "Age demographics saved."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()
