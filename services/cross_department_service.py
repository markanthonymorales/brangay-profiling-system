import logging
from datetime import datetime, timedelta, date
from database.db import get_session
from database.models import (
    DepartmentDataSync, CrossDepartmentAlert, HealthStatistics,
    SocialWelfareData, IncomeData, EducationStatistics, DisasterRiskProfile,
    PopulationRecord, DisasterIncident, BusinessPermit, EmergencyResource,
    Barangay, User,
)
from services.audit_service import log_action

logger = logging.getLogger(__name__)

DEPARTMENT_NAMES = ["health", "social_welfare", "disaster", "education", "business_permits"]

THRESHOLDS = {
    "disease_poverty_correlation": {
        "description": "High disease cases in high-poverty barangay",
        "severity": "warning",
    },
    "disaster_health_impact": {
        "description": "Active disaster + high disease/malnutrition",
        "severity": "critical",
    },
    "education_poverty_gap": {
        "description": "High dropout rate in high-poverty area",
        "severity": "warning",
    },
    "resource_shortage": {
        "description": "High-risk barangay with low emergency resources",
        "severity": "critical",
    },
    "business_disaster_impact": {
        "description": "Active disaster in area with many active permits",
        "severity": "warning",
    },
}


def on_department_data_saved(department_name: str, barangay_id: int, year: int, user_id: int):
    try:
        update_sync_status(department_name, barangay_id, user_id)
        triggered = check_cross_department_thresholds(barangay_id, year)
        for alert_data in triggered:
            _create_alert_if_new(barangay_id, alert_data, user_id)
    except Exception as e:
        logger.error(f"Cross-department hook error: {e}")


def update_sync_status(department_name: str, barangay_id: int, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        existing = (
            session.query(DepartmentDataSync)
            .filter_by(department_name=department_name, barangay_id=barangay_id)
            .first()
        )
        if existing:
            existing.last_synced = datetime.utcnow()
            existing.sync_status = "synced"
            existing.synced_by = user_id
        else:
            record = DepartmentDataSync(
                department_name=department_name,
                barangay_id=barangay_id,
                last_synced=datetime.utcnow(),
                sync_status="synced",
                synced_by=user_id,
            )
            session.add(record)
        session.commit()
        return True, "Sync status updated."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def check_cross_department_thresholds(barangay_id: int, year: int) -> list[dict]:
    session = get_session()
    try:
        health = session.query(HealthStatistics).filter_by(barangay_id=barangay_id, year=year).first()
        income = session.query(IncomeData).filter_by(barangay_id=barangay_id, year=year).first()
        education = session.query(EducationStatistics).filter_by(barangay_id=barangay_id, year=year).first()
        risk = session.query(DisasterRiskProfile).filter_by(barangay_id=barangay_id, year=year).first()
        population = session.query(PopulationRecord).filter_by(barangay_id=barangay_id, year=year).first()

        active_disasters = (
            session.query(DisasterIncident)
            .filter(
                DisasterIncident.barangay_id == barangay_id,
                DisasterIncident.status.in_(["reported", "responding"]),
            ).count()
        )
        active_permits = (
            session.query(BusinessPermit)
            .filter(BusinessPermit.barangay_id == barangay_id, BusinessPermit.status == "active")
            .count()
        )
        resource_count = session.query(EmergencyResource).filter_by(barangay_id=barangay_id).count()

        barangay = session.get(Barangay, barangay_id)
        brgy_name = barangay.name if barangay else f"Barangay #{barangay_id}"

        triggered = []

        # Calculate poverty percentage
        poverty_pct = 0
        if income and population and population.household_count and population.household_count > 0:
            poverty_pct = (income.below_poverty_count or 0) / population.household_count * 100

        # 1. Disease + Poverty
        dengue = (health.dengue_cases or 0) if health else 0
        if dengue >= 10 and poverty_pct >= 20:
            triggered.append({
                "alert_type": "disease_poverty_correlation",
                "severity": "warning",
                "title": f"Disease-Poverty Alert: {brgy_name}",
                "message": f"High dengue cases ({dengue}) in high-poverty area ({poverty_pct:.0f}% poverty rate).",
                "source_tables": '["health_statistics", "income_data"]',
            })

        # 2. Disaster + Health
        malnutrition = (health.malnutrition_rate or 0) if health else 0
        if active_disasters >= 1 and malnutrition >= 15:
            triggered.append({
                "alert_type": "disaster_health_impact",
                "severity": "critical",
                "title": f"Disaster-Health Crisis: {brgy_name}",
                "message": f"Active disaster ({active_disasters}) with high malnutrition ({malnutrition:.1f}%).",
                "source_tables": '["disaster_incidents", "health_statistics"]',
            })

        # 3. Education + Poverty
        dropout = (education.dropout_rate or 0) if education else 0
        if dropout >= 10 and poverty_pct >= 15:
            triggered.append({
                "alert_type": "education_poverty_gap",
                "severity": "warning",
                "title": f"Education-Poverty Gap: {brgy_name}",
                "message": f"High dropout rate ({dropout:.1f}%) in high-poverty area ({poverty_pct:.0f}%).",
                "source_tables": '["education_statistics", "income_data"]',
            })

        # 4. Resource shortage
        risk_flags = 0
        if risk:
            risk_flags += int(risk.flood_prone)
            risk_flags += int(risk.landslide_prone)
            risk_flags += int(risk.fire_risk_level == "high") if risk.fire_risk_level else 0
            risk_flags += int(risk.earthquake_risk == "high") if risk.earthquake_risk else 0
            risk_flags += int(risk.storm_surge_risk == "high") if risk.storm_surge_risk else 0
        if risk_flags >= 2 and resource_count < 3:
            triggered.append({
                "alert_type": "resource_shortage",
                "severity": "critical",
                "title": f"Resource Shortage Alert: {brgy_name}",
                "message": f"High-risk barangay ({risk_flags} risk flags) with only {resource_count} emergency resources.",
                "source_tables": '["disaster_risk_profiles", "emergency_resources"]',
            })

        # 5. Business + Disaster
        if active_disasters >= 1 and active_permits >= 20:
            triggered.append({
                "alert_type": "business_disaster_impact",
                "severity": "warning",
                "title": f"Business-Disaster Impact: {brgy_name}",
                "message": f"Active disaster affecting area with {active_permits} active business permits.",
                "source_tables": '["disaster_incidents", "business_permits"]',
            })

        return triggered
    finally:
        session.close()


def _create_alert_if_new(barangay_id: int, alert_data: dict, user_id: int):
    session = get_session()
    try:
        existing = (
            session.query(CrossDepartmentAlert)
            .filter_by(
                barangay_id=barangay_id,
                alert_type=alert_data["alert_type"],
                is_resolved=False,
            )
            .first()
        )
        if existing:
            return

        alert = CrossDepartmentAlert(
            barangay_id=barangay_id,
            alert_type=alert_data["alert_type"],
            severity=alert_data["severity"],
            title=alert_data["title"],
            message=alert_data.get("message"),
            source_tables=alert_data.get("source_tables"),
        )
        session.add(alert)
        session.commit()

        # Notify admin and city_official users
        from services.notification_service import create_notification
        admin_users = session.query(User).filter(
            User.role.in_(["admin", "city_official"]),
            User.is_active == True,
        ).all()
        for user in admin_users:
            create_notification(
                user_id=user.id,
                type="cross_department_alert",
                title=alert_data["title"],
                message=alert_data.get("message", ""),
                severity=alert_data["severity"],
            )
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to create cross-department alert: {e}")
    finally:
        session.close()


def resolve_alert(alert_id: int, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        alert = session.get(CrossDepartmentAlert, alert_id)
        if not alert:
            return False, "Alert not found."
        alert.is_resolved = True
        alert.resolved_by = user_id
        alert.resolved_at = datetime.utcnow()
        session.commit()
        log_action(user_id, "UPDATE", "cross_department_alerts", alert_id,
                   old_values={"is_resolved": False}, new_values={"is_resolved": True})
        return True, "Alert resolved."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def get_cross_department_alerts(barangay_id: int | None = None, alert_type: str | None = None,
                                unresolved_only: bool = False, limit: int = 100) -> list[dict]:
    session = get_session()
    try:
        query = session.query(CrossDepartmentAlert).join(Barangay)
        if barangay_id:
            query = query.filter(CrossDepartmentAlert.barangay_id == barangay_id)
        if alert_type:
            query = query.filter(CrossDepartmentAlert.alert_type == alert_type)
        if unresolved_only:
            query = query.filter(CrossDepartmentAlert.is_resolved == False)

        records = query.order_by(CrossDepartmentAlert.created_at.desc()).limit(limit).all()
        return [
            {
                "id": r.id, "barangay_id": r.barangay_id,
                "barangay_name": r.barangay.name,
                "alert_type": r.alert_type, "severity": r.severity,
                "title": r.title, "message": r.message or "",
                "is_resolved": r.is_resolved,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
            }
            for r in records
        ]
    finally:
        session.close()


def get_sync_status(barangay_id: int | None = None, department_name: str | None = None) -> list[dict]:
    session = get_session()
    try:
        query = session.query(DepartmentDataSync)
        if barangay_id:
            query = query.filter(DepartmentDataSync.barangay_id == barangay_id)
        if department_name:
            query = query.filter(DepartmentDataSync.department_name == department_name)
        records = query.all()
        return [
            {
                "id": r.id, "department_name": r.department_name,
                "barangay_id": r.barangay_id,
                "last_synced": r.last_synced.strftime("%Y-%m-%d %H:%M") if r.last_synced else "",
                "sync_status": r.sync_status,
            }
            for r in records
        ]
    finally:
        session.close()


def get_cross_department_kpis(year: int | None = None) -> dict:
    session = get_session()
    try:
        # Active alerts
        active_alerts = session.query(CrossDepartmentAlert).filter_by(is_resolved=False).count()
        critical_alerts = session.query(CrossDepartmentAlert).filter_by(
            is_resolved=False, severity="critical"
        ).count()

        # Sync freshness
        today = datetime.utcnow()
        stale_cutoff = today - timedelta(days=30)
        synced_today = session.query(DepartmentDataSync).filter(
            DepartmentDataSync.last_synced >= today.replace(hour=0, minute=0, second=0)
        ).count()
        stale_count = session.query(DepartmentDataSync).filter(
            DepartmentDataSync.last_synced < stale_cutoff
        ).count()

        return {
            "active_alerts": active_alerts,
            "critical_alerts": critical_alerts,
            "synced_today": synced_today,
            "stale_data_warnings": stale_count,
        }
    finally:
        session.close()
