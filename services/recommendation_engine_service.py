import json
import logging
from datetime import datetime, date
from database.db import get_session
from database.models import (
    PolicyRecommendation, RecommendationTemplate, ResourceInventory,
    Barangay, District, User,
    PopulationRecord, CrimeIncident, HealthStatistics, DisasterRiskProfile,
    IncomeData, Utility
)
from services.audit_service import log_action

logger = logging.getLogger(__name__)

DOMAINS = ["crime", "health", "disaster", "infrastructure", "economic"]
PRIORITIES = ["critical", "high", "medium", "low"]


# ── Recommendation Generation ─────────────────────────────────

def generate_recommendations(barangay_id: int, year: int, domain: str, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        # Get active templates for domain
        templates = session.query(RecommendationTemplate).filter_by(
            domain=domain, is_active=True
        ).all()

        if not templates:
            return False, f"No active templates for domain: {domain}"

        # Analyze barangay data
        data_snapshot = _analyze_barangay_data(session, barangay_id, year, domain)
        
        generated = 0
        for template in templates:
            # Evaluate conditions
            if _evaluate_conditions(template.condition_rules, data_snapshot):
                # Calculate urgency/impact scores
                urgency = _calculate_urgency(data_snapshot, domain)
                impact = _calculate_impact(data_snapshot, domain)
                
                # Create recommendation
                rec = PolicyRecommendation(
                    barangay_id=barangay_id,
                    year=year,
                    domain=domain,
                    priority=template.default_priority or _score_to_priority(urgency, impact),
                    urgency_score=urgency,
                    impact_score=impact,
                    recommendation_text=template.recommendation_text,
                    suggested_actions=template.suggested_actions,
                    status="pending"
                )
                session.add(rec)
                generated += 1

        session.commit()
        
        # Audit log
        log_action(user_id, "CREATE", "policy_recommendations", None,
                  new_values={"barangay_id": barangay_id, "domain": domain, "count": generated})
        
        return True, f"Generated {generated} recommendations for {domain}"
    except Exception as e:
        session.rollback()
        logger.error(f"Recommendation generation failed: {e}")
        return False, str(e)
    finally:
        session.close()


def _analyze_barangay_data(session, barangay_id: int, year: int, domain: str) -> dict:
    snapshot = {"barangay_id": barangay_id, "year": year, "domain": domain}
    
    if domain == "crime":
        # Crime analysis
        incidents = session.query(CrimeIncident).filter_by(barangay_id=barangay_id).all()
        recent = [i for i in incidents if i.date_occurred and 
                 (date.today() - i.date_occurred).days <= 365]
        snapshot["incident_count"] = len(recent)
        snapshot["recent_severity"] = max([0] + [{"critical": 4, "high": 3, "medium": 2, "low": 1}.get(i.severity, 0) for i in recent])
        
    elif domain == "health":
        # Health analysis
        health = session.query(HealthStatistics).filter_by(
            barangay_id=barangay_id, year=year
        ).first()
        if health:
            total_cases = (health.dengue_cases or 0) + (health.covid_cases or 0) + \
                       (health.tuberculosis_cases or 0) + (health.pneumonia_cases or 0)
            snapshot["disease_cases"] = total_cases
            snapshot["malnutrition_rate"] = health.malnutrition_rate or 0
            snapshot["vaccination_coverage"] = health.vaccination_coverage_pct or 0
            
    elif domain == "disaster":
        # Disaster risk analysis
        risk = session.query(DisasterRiskProfile).filter_by(
            barangay_id=barangay_id, year=year
        ).first()
        if risk:
            risk_count = sum([risk.flood_prone, risk.landslide_prone])
            snapshot["risk_factors"] = risk_count
            snapshot["fire_risk"] = risk.fire_risk_level
            
    elif domain == "infrastructure":
        # Utility analysis
        utilities = session.query(Utility).filter_by(
            barangay_id=barangay_id, year=year
        ).first()
        if utilities:
            snapshot["water_coverage"] = utilities.water_coverage or 0
            snapshot["power_coverage"] = utilities.power_coverage or 0
            snapshot["internet_coverage"] = utilities.internet_coverage or 0
            
    elif domain == "economic":
        # Economic analysis
        income = session.query(IncomeData).filter_by(
            barangay_id=barangay_id, year=year
        ).first()
        if income:
            snapshot["avg_income"] = income.average_household_income or 0
            snapshot["poverty_rate"] = income.poverty_rate or 0
            
    return snapshot


def _evaluate_conditions(condition_rules: str, data: dict) -> bool:
    try:
        rules = json.loads(condition_rules)
        
        for field, operator, value in rules:
            if field not in data:
                continue
            data_value = data[field]
            
            if operator == "gt" and not data_value > value:
                return False
            elif operator == "lt" and not data_value < value:
                return False
            elif operator == "gte" and not data_value >= value:
                return False
            elif operator == "lte" and not data_value <= value:
                return False
            elif operator == "eq" and not data_value == value:
                return False
                
        return True
    except Exception as e:
        logger.warning(f"Condition evaluation failed: {e}")
        return False


def _calculate_urgency(data: dict, domain: str) -> float:
    if domain == "crime":
        return min(100, (data.get("incident_count", 0) * 10) + 
                    (data.get("recent_severity", 0) * 15))
    elif domain == "health":
        return min(100, (data.get("disease_cases", 0) / 10) + 
                    (100 - data.get("vaccination_coverage", 50)))
    elif domain == "disaster":
        return min(100, data.get("risk_factors", 0) * 35)
    elif domain == "infrastructure":
        gaps = (100 - data.get("water_coverage", 0)) + \
              (100 - data.get("power_coverage", 0)) + \
              (100 - data.get("internet_coverage", 0))
        return gaps / 3
    elif domain == "economic":
        return data.get("poverty_rate", 0) + (100 - min(100, data.get("avg_income", 0) / 1000))
    return 50


def _calculate_impact(data: dict, domain: str) -> float:
    if domain == "crime":
        return min(100, data.get("recent_severity", 0) * 25 + 30)
    elif domain == "health":
        return min(100, data.get("malnutrition_rate", 0) * 2 + 
                    (data.get("disease_cases", 0) / 5))
    elif domain == "disaster":
        return data.get("risk_factors", 0) * 40 + 20
    elif domain == "infrastructure":
        return 100 - ((data.get("water_coverage", 0) + data.get("power_coverage", 0)) / 2)
    elif domain == "economic":
        return data.get("poverty_rate", 0) * 2
    return 50


def _score_to_priority(urgency: float, impact: float) -> str:
    combined = (urgency + impact) / 2
    if combined >= 75:
        return "critical"
    elif combined >= 50:
        return "high"
    elif combined >= 25:
        return "medium"
    return "low"


# ── Batch Generation ───────────────────────────────────────────

def generate_all_recommendations(year: int, district_id: int | None = None) -> tuple[bool, str]:
    session = get_session()
    try:
        # Get barangays
        query = session.query(Barangay)
        if district_id:
            query = query.filter_by(district_id=district_id)
        barangays = query.all()

        total_generated = 0
        for brgy in barangays:
            for domain in DOMAINS:
                success, msg = generate_recommendations(brgy.id, year, domain, user_id=1)
                if success:
                    total_generated += int(msg.split()[0])
                    
        return True, f"Generated {total_generated} recommendations"
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


# ── Recommendation CRUD ─────────────────────────────────────

def get_recommendations(barangay_id: int | None = None, domain: str | None = None,
                    status: str | None = None) -> list[dict]:
    session = get_session()
    try:
        query = session.query(PolicyRecommendation)
        
        if barangay_id:
            query = query.filter_by(barangay_id=barangay_id)
        if domain:
            query = query.filter_by(domain=domain)
        if status:
            query = query.filter_by(status=status)
            
        recs = query.order_by(PolicyRecommendation.urgency_score.desc()).all()
        
        return [
            {
                "id": r.id,
                "barangay_id": r.barangay_id,
                "barangay_name": r.barangay.name if r.barangay else "",
                "year": r.year,
                "domain": r.domain,
                "priority": r.priority,
                "urgency_score": r.urgency_score,
                "impact_score": r.impact_score,
                "recommendation_text": r.recommendation_text,
                "suggested_actions": r.suggested_actions,
                "status": r.status,
                "approved_by": r.approved_by,
                "implemented_at": r.implemented_at.isoformat() if r.implemented_at else None,
            }
            for r in recs
        ]
    finally:
        session.close()


def update_recommendation_status(rec_id: int, new_status: str, user_id: int,
                           approved_by: int | None = None) -> tuple[bool, str]:
    session = get_session()
    try:
        rec = session.get(PolicyRecommendation, rec_id)
        if not rec:
            return False, "Recommendation not found"
            
        old_status = rec.status
        rec.status = new_status
        
        if new_status == "approved" and approved_by:
            rec.approved_by = approved_by
            rec.approved_at = datetime.utcnow()
        elif new_status == "implemented":
            rec.implemented_at = datetime.utcnow()
            
        session.commit()
        
        log_action(user_id, "UPDATE", "policy_recommendations", rec_id,
                  old_values={"status": old_status},
                  new_values={"status": new_status})
                  
        return True, f"Recommendation {new_status}"
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


# ── Recommendation Templates ─────────────────────────────────

def save_template(data: dict, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        template_id = data.pop("id", None)
        
        if template_id:
            template = session.get(RecommendationTemplate, template_id)
            for key, value in data.items():
                if hasattr(template, key):
                    setattr(template, key, value)
        else:
            template = RecommendationTemplate(**data)
            session.add(template)
            
        session.commit()
        
        log_action(user_id, "CREATE" if not template_id else "UPDATE",
                  "recommendation_templates", template.id if template.id else 0,
                  new_values=data)
                  
        return True, "Template saved"
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def get_templates(domain: str | None = None) -> list[dict]:
    session = get_session()
    try:
        query = session.query(RecommendationTemplate)
        if domain:
            query = query.filter_by(domain=domain)
            
        templates = query.all()
        
        return [
            {
                "id": t.id,
                "domain": t.domain,
                "category": t.category,
                "condition_rules": t.condition_rules,
                "recommendation_text": t.recommendation_text,
                "default_priority": t.default_priority,
                "is_active": t.is_active,
            }
            for t in templates
        ]
    finally:
        session.close()