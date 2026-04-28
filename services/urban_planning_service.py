import json
import logging
import numpy as np
from datetime import datetime, date
from database.db import get_session
from database.models import (
    UrbanDevelopmentProjection, DevelopmentScenario,
    Barangay, PopulationRecord, Utility, DisasterRiskProfile
)
from services.audit_service import log_action

logger = logging.getLogger(__name__)


# ── Housing Projections ─────────────────────────────────

def project_housing(barangay_id: int, years_ahead: int = 10) -> dict:
    session = get_session()
    try:
        # Get historical population data
        records = session.query(PopulationRecord).filter_by(
            barangay_id=barangay_id
        ).order_by(PopulationRecord.year).all()
        
        if not records or len(records) < 2:
            return {"error": "Insufficient historical data"}
        
        years = [r.year for r in records]
        populations = [r.total_population for r in records]
        
        # Simple linear extrapolation with carrying capacity
        avg_increase = (populations[-1] - populations[0]) / len(years)
        carrying_capacity = populations[-1] * 3  # Assume 3x current as max
        
        projected = {}
        current_pop = populations[-1]
        base_year = years[-1]
        
        for i in range(1, years_ahead + 1):
            target_year = base_year + i
            # Logistic growth
            growth = avg_increase * (1 - current_pop / carrying_capacity)
            current_pop = current_pop + growth
            # Assume 4 persons per household
            projected[target_year] = round(current_pop / 4)
            
        return {
            "barangay_id": barangay_id,
            "projection_type": "housing",
            "years_ahead": years_ahead,
            "projected_values": projected,
            "methodology": "logistic_growth",
        }
    finally:
        session.close()


def project_infrastructure(barangay_id: int, years_ahead: int = 10) -> dict:
    session = get_session()
    try:
        # Get recent utility data
        utility = session.query(Utility).filter_by(
            barangay_id=barangay_id
        ).order_by(Utility.year.desc()).first()
        
        if not utility:
            return {"error": "No utility data"}
        
        base_year = utility.year
        base_water = utility.water_coverage_pct or 0
        base_power = utility.power_coverage_pct or 0
        base_internet = utility.internet_coverage_pct or 0
        
        projected = {}
        for i in range(1, years_ahead + 1):
            target_year = base_year + i
            # Linear improvement (2% per year toward 100%)
            water = min(100, base_water + i * 2)
            power = min(100, base_power + i * 2)
            internet = min(100, base_internet + i * 1.5)
            projected[target_year] = {
                "water_coverage": water,
                "power_coverage": power,
                "internet_coverage": internet,
            }
            
        return {
            "barangay_id": barangay_id,
            "projection_type": "infrastructure",
            "years_ahead": years_ahead,
            "projected_values": projected,
            "methodology": "linear_improvement",
        }
    finally:
        session.close()


def project_disaster_resilience(barangay_id: int, years_ahead: int = 10) -> dict:
    session = get_session()
    try:
        risk = session.query(DisasterRiskProfile).filter_by(
            barangay_id=barangay_id
        ).order_by(DisasterRiskProfile.year.desc()).first()
        
        if not risk:
            return {"error": "No disaster risk data"}
        
        # Base risk score (0-100)
        base_risk = 0
        if risk.flood_prone:
            base_risk += 30
        if risk.landslide_prone:
            base_risk += 30
        risk_scores = {"low": 20, "medium": 50, "high": 80}
        base_risk = base_risk + risk_scores.get(risk.fire_risk_level or "low", 20)
        
        base_year = risk.year
        projected = {}
        
        # Risk decreases with mitigation (3% per year)
        for i in range(1, years_ahead + 1):
            target_year = base_year + i
            resilience = min(100, 100 - base_risk + i * 3)
            projected[target_year] = resilience
            
        return {
            "barangay_id": barangay_id,
            "projection_type": "disaster_resilience",
            "years_ahead": years_ahead,
            "projected_values": projected,
            "methodology": "mitigation_improvement",
        }
    finally:
        session.close()


# ── Save Projections ──────────────────────────────────────

def save_projection(barangay_id: int, data: dict, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        projection = UrbanDevelopmentProjection(
            barangay_id=barangay_id,
            projection_type=data.get("projection_type"),
            baseline_year=data.get("baseline_year"),
            target_horizon=data.get("target_horizon"),
            baseline_value=data.get("baseline_value"),
            projected_values=json.dumps(data.get("projected_values", {})),
            confidence_intervals=json.dumps(data.get("confidence_intervals", {})),
            assumptions=data.get("assumptions"),
            methodology=data.get("methodology"),
        )
        session.add(projection)
        session.commit()
        
        log_action(user_id, "CREATE", "urban_development_projections", projection.id,
                  new_values={"barangay_id": barangay_id, "type": projection.projection_type})
                  
        return True, f"Projection {projection.id} saved"
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def get_projections(barangay_id: int | None = None, projection_type: str | None = None) -> list[dict]:
    session = get_session()
    try:
        query = session.query(UrbanDevelopmentProjection)
        
        if barangay_id:
            query = query.filter_by(barangay_id=barangay_id)
        if projection_type:
            query = query.filter_by(projection_type=projection_type)
            
        projections = query.order_by(UrbanDevelopmentProjection.baseline_year.desc()).all()
        
        return [
            {
                "id": p.id,
                "barangay_id": p.barangay_id,
                "barangay_name": p.barangay.name if p.barangay else "",
                "projection_type": p.projection_type,
                "baseline_year": p.baseline_year,
                "target_horizon": p.target_horizon,
                "baseline_value": p.baseline_value,
                "projected_values": json.loads(p.projected_values),
                "assumptions": p.assumptions,
                "methodology": p.methodology,
            }
            for p in projections
        ]
    finally:
        session.close()


# ── Development Scenarios ───────────────────────────────────

def save_scenario(data: dict, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        scenario_id = data.pop("id", None)
        
        if scenario_id:
            scenario = session.get(DevelopmentScenario, scenario_id)
            for key, value in data.items():
                if hasattr(scenario, key):
                    setattr(scenario, key, value)
        else:
            scenario = DevelopmentScenario(
                name=data.get("name"),
                description=data.get("description"),
                scenario_type=data.get("scenario_type"),
                parameters=json.dumps(data.get("parameters", {})),
                created_by=user_id,
            )
            session.add(scenario)
            
        session.commit()
        
        log_action(user_id, "CREATE" if not scenario_id else "UPDATE",
                  "development_scenarios", scenario.id if scenario.id else 0,
                  new_values={"name": scenario.name})
                  
        return True, "Scenario saved"
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def get_scenarios(scenario_type: str | None = None) -> list[dict]:
    session = get_session()
    try:
        query = session.query(DevelopmentScenario)
        
        if scenario_type:
            query = query.filter_by(scenario_type=scenario_type)
            
        scenarios = query.order_by(DevelopmentScenario.created_at.desc()).all()
        
        return [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "scenario_type": s.scenario_type,
                "parameters": json.loads(s.parameters),
                "created_by": s.created_by,
                "created_by_name": s.creator.username if s.creator else "",
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in scenarios
        ]
    finally:
        session.close()


def delete_scenario(scenario_id: int, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        scenario = session.get(DevelopmentScenario, scenario_id)
        if not scenario:
            return False, "Scenario not found"
            
        session.delete(scenario)
        session.commit()
        
        log_action(user_id, "DELETE", "development_scenarios", scenario_id)
        return True, "Scenario deleted"
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()