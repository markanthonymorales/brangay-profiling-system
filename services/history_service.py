import logging
from datetime import datetime
from database.db import get_session
from database.models import (
    RecordHistory, User,
    PopulationRecord, IncomeData, Utility, WasteManagement,
    CrimeIncident, TrafficIncident, FoodSource, GovernmentFacility,
    ReligiousDemographic, Business, LandType, ResidentCategory,
    HealthStatistics, SocialWelfareData, DisasterRiskProfile,
    DisasterIncident, EmergencyResource, EducationStatistics,
    BusinessPermit, DepartmentDataSync, CrossDepartmentAlert,
)

logger = logging.getLogger(__name__)

SKIP_FIELDS = {"id", "created_at", "updated_at"}

TABLE_MODEL_MAP = {
    "population_records": PopulationRecord,
    "income_data": IncomeData,
    "utilities": Utility,
    "waste_management": WasteManagement,
    "crime_incidents": CrimeIncident,
    "traffic_incidents": TrafficIncident,
    "food_sources": FoodSource,
    "government_facilities": GovernmentFacility,
    "religious_demographics": ReligiousDemographic,
    "businesses": Business,
    "land_types": LandType,
    "resident_categories": ResidentCategory,
    "health_statistics": HealthStatistics,
    "social_welfare_data": SocialWelfareData,
    "disaster_risk_profiles": DisasterRiskProfile,
    "disaster_incidents": DisasterIncident,
    "emergency_resources": EmergencyResource,
    "education_statistics": EducationStatistics,
    "business_permits": BusinessPermit,
    "department_data_sync": DepartmentDataSync,
    "cross_department_alerts": CrossDepartmentAlert,
}


def record_field_changes(table_name: str, record_id: int,
                         old_data: dict, new_data: dict,
                         user_id: int) -> int:
    session = get_session()
    try:
        count = 0
        for key, new_val in new_data.items():
            if key in SKIP_FIELDS:
                continue
            old_val = old_data.get(key)
            old_str = str(old_val) if old_val is not None else None
            new_str = str(new_val) if new_val is not None else None
            if old_str != new_str:
                entry = RecordHistory(
                    table_name=table_name,
                    record_id=record_id,
                    field_name=key,
                    old_value=old_str,
                    new_value=new_str,
                    changed_by=user_id,
                    changed_at=datetime.utcnow(),
                )
                session.add(entry)
                count += 1
        if count > 0:
            session.commit()
            logger.info(f"Recorded {count} field changes for {table_name}#{record_id}")
        return count
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to record field changes: {e}")
        return 0
    finally:
        session.close()


def get_record_history(table_name: str, record_id: int) -> list[dict]:
    session = get_session()
    try:
        entries = (
            session.query(RecordHistory)
            .filter_by(table_name=table_name, record_id=record_id)
            .order_by(RecordHistory.changed_at.desc())
            .all()
        )
        results = []
        for e in entries:
            user = session.get(User, e.changed_by)
            results.append({
                "field_name": e.field_name,
                "old_value": e.old_value,
                "new_value": e.new_value,
                "changed_by_name": user.full_name if user else "Unknown",
                "changed_at": e.changed_at.strftime("%Y-%m-%d %H:%M") if e.changed_at else "",
            })
        return results
    finally:
        session.close()


def get_barangay_history(barangay_id: int, limit: int = 50) -> list[dict]:
    session = get_session()
    try:
        all_entries = (
            session.query(RecordHistory)
            .order_by(RecordHistory.changed_at.desc())
            .limit(limit * 5)
            .all()
        )
        results = []
        for e in all_entries:
            if len(results) >= limit:
                break
            model_cls = TABLE_MODEL_MAP.get(e.table_name)
            if not model_cls:
                continue
            record = session.get(model_cls, e.record_id)
            if record and hasattr(record, "barangay_id") and record.barangay_id == barangay_id:
                user = session.get(User, e.changed_by)
                results.append({
                    "table_name": e.table_name,
                    "record_id": e.record_id,
                    "field_name": e.field_name,
                    "old_value": e.old_value,
                    "new_value": e.new_value,
                    "changed_by_name": user.full_name if user else "Unknown",
                    "changed_at": e.changed_at.strftime("%Y-%m-%d %H:%M") if e.changed_at else "",
                })
        return results
    finally:
        session.close()
