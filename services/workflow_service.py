import logging
import uuid
from datetime import datetime
from database.db import get_session
from database.models import ResponseWorkflow, WorkflowAssignment, Department, User
from services.audit_service import log_action

logger = logging.getLogger(__name__)

# Incident type to required departments mapping
INCIDENT_DEPARTMENT_MAP = {
    "crime": ["PNP", "Barangay Police"],
    "disaster": ["CDRRMC", "Office of Civil Defense"],
    "fire": ["BFP", "Water District"],
    "health": ["CHO", "Social Welfare"],
    "traffic": ["Traffic Office", "Public Works"],
    "infrastructure": ["Public Works", "Engineering"],
}


# ── Workflow CRUD ────────────────────────────────────────

def create_workflow(data: dict, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        workflow = ResponseWorkflow(
            title=data.get("title"),
            incident_type=data.get("incident_type"),
            incident_id=data.get("incident_id"),
            severity=data.get("severity", "medium"),
            status="initiated",
            initiated_by=user_id,
            initiated_at=datetime.utcnow(),
            description=data.get("description"),
        )
        session.add(workflow)
        session.flush()
        
        # Auto-assign departments if configured
        incident_type = data.get("incident_type")
        if incident_type in INCIDENT_DEPARTMENT_MAP:
            for dept_name in INCIDENT_DEPARTMENT_MAP[incident_type]:
                dept = session.query(Department).filter_by(name=dept_name).first()
                if dept:
                    assignment = WorkflowAssignment(
                        workflow_id=workflow.id,
                        department_id=dept.id,
                        assigned_by=user_id,
                        assigned_at=datetime.utcnow(),
                        status="assigned"
                    )
                    session.add(assignment)
                    
        session.commit()
        
        log_action(user_id, "CREATE", "response_workflows", workflow.id,
                  new_values={"title": workflow.title, "severity": workflow.severity})
                  
        return True, f"Workflow {workflow.id} created"
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def update_workflow_status(workflow_id: int, new_status: str, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        workflow = session.get(ResponseWorkflow, workflow_id)
        if not workflow:
            return False, "Workflow not found"
            
        old_status = workflow.status
        workflow.status = new_status
        
        if new_status == "completed":
            workflow.completed_at = datetime.utcnow()
            
        session.commit()
        
        log_action(user_id, "UPDATE", "response_workflows", workflow_id,
                  old_values={"status": old_status},
                  new_values={"status": new_status})
                  
        return True, f"Workflow status updated to {new_status}"
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def get_workflows(status: str | None = None, incident_type: str | None = None) -> list[dict]:
    session = get_session()
    try:
        query = session.query(ResponseWorkflow)
        
        if status:
            query = query.filter_by(status=status)
        if incident_type:
            query = query.filter_by(incident_type=incident_type)
            
        workflows = query.order_by(ResponseWorkflow.initiated_at.desc()).all()
        
        result = []
        for w in workflows:
            assignments = session.query(WorkflowAssignment).filter_by(workflow_id=w.id).all()
            result.append({
                "id": w.id,
                "title": w.title,
                "incident_type": w.incident_type,
                "severity": w.severity,
                "status": w.status,
                "initiated_by": w.initiated_by,
                "initiator_name": w.initiator.username if w.initiator else "",
                "initiated_at": w.initiated_at.isoformat() if w.initiated_at else None,
                "completed_at": w.completed_at.isoformat() if w.completed_at else None,
                "assignments": [
                    {
                        "department_id": a.department_id,
                        "department_name": a.department.name if a.department else "",
                        "status": a.status,
                        "completed_at": a.completed_at.isoformat() if a.completed_at else None,
                    }
                    for a in assignments
                ],
            })
            
        return result
    finally:
        session.close()


# ── Assignment Management ─────────────────────────────────

def assign_department(workflow_id: int, department_id: int, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        # Check if already assigned
        existing = session.query(WorkflowAssignment).filter_by(
            workflow_id=workflow_id, department_id=department_id
        ).first()
        
        if existing:
            return False, "Department already assigned"
            
        assignment = WorkflowAssignment(
            workflow_id=workflow_id,
            department_id=department_id,
            assigned_by=user_id,
            assigned_at=datetime.utcnow(),
            status="assigned"
        )
        session.add(assignment)
        session.commit()
        
        log_action(user_id, "CREATE", "workflow_assignments", assignment.id,
                  new_values={"workflow_id": workflow_id, "department_id": department_id})
                  
        return True, "Department assigned"
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def update_assignment_status(assignment_id: int, new_status: str, user_id: int,
                        notes: str | None = None) -> tuple[bool, str]:
    session = get_session()
    try:
        assignment = session.get(WorkflowAssignment, assignment_id)
        if not assignment:
            return False, "Assignment not found"
            
        old_status = assignment.status
        assignment.status = new_status
        
        if new_status == "completed":
            assignment.completed_at = datetime.utcnow()
            
        if notes:
            assignment.response_notes = notes
            
        session.commit()
        
        log_action(user_id, "UPDATE", "workflow_assignments", assignment_id,
                  old_values={"status": old_status},
                  new_values={"status": new_status})
                  
        return True, f"Assignment {new_status}"
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def get_workflow_summary() -> dict:
    session = get_session()
    try:
        from sqlalchemy import func
        
        total = session.query(ResponseWorkflow).count()
        pending = session.query(ResponseWorkflow).filter_by(status="initiated").count()
        active = session.query(ResponseWorkflow).filter_by(status="responding").count()
        completed = session.query(ResponseWorkflow).filter_by(status="completed").count()
        
        by_type = dict(session.query(
            ResponseWorkflow.incident_type,
            func.count(ResponseWorkflow.id)
        ).group_by(ResponseWorkflow.incident_type).all())
        
        return {
            "total": total,
            "pending": pending,
            "active": active,
            "completed": completed,
            "by_type": by_type,
        }
    finally:
        session.close()