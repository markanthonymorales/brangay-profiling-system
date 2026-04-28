import json
import logging
from datetime import datetime, date
from database.db import get_session
from database.models import DecisionRecord, User
from services.audit_service import log_action

logger = logging.getLogger(__name__)

VALID_STATUSES = ["pending", "approved", "implemented", "cancelled"]


# ── Decision CRUD ──────────────────────────────────────────

def record_decision(data: dict, user_id: int) -> tuple[bool, str]:
    decision_type = data.get("decision_type")
    context = data.get("context")
    options_considered = data.get("options_considered")
    chosen_option = data.get("chosen_option")
    rationale = data.get("rationale")
    
    if not decision_type:
        return (False, "decision_type is required")
    if not context:
        return (False, "context is required")
    
    session = get_session()
    try:
        # Validate user exists
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            return (False, f"User {user_id} not found")
        
        # Ensure context is JSON string
        if isinstance(context, dict):
            context = json.dumps(context)
        if options_considered and isinstance(options_considered, list):
            options_considered = json.dumps(options_considered)
        if chosen_option and isinstance(chosen_option, dict):
            chosen_option = json.dumps(chosen_option)
        
        record = DecisionRecord(
            decision_type=decision_type,
            context=context,
            options_considered=options_considered,
            chosen_option=chosen_option,
            rationale=rationale,
            decided_by=user_id,
            status="pending",
        )
        session.add(record)
        session.commit()
        
        log_action(user_id, "CREATE", "decision_records", record.id, None, {"decision_type": decision_type})
        
        return (True, f"Decision recorded: {record.id}")
    except Exception as e:
        session.rollback()
        logger.error(f"record_decision failed: {e}")
        return (False, str(e))
    finally:
        session.close()


def request_approval(decision_id: int, requester_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        record = session.query(DecisionRecord).filter(DecisionRecord.id == decision_id).first()
        if not record:
            return (False, f"Decision {decision_id} not found")
        
        if record.status != "pending":
            return (False, f"Decision status is already {record.status}")
        
        # Requesting approval keeps it pending but marks for review
        record.status = "pending"
        session.commit()
        
        log_action(requester_id, "UPDATE", "decision_records", decision_id, 
                 None, {"status": "pending", "approval_requested": True})
        
        return (True, f"Approval requested for decision {decision_id}")
    except Exception as e:
        session.rollback()
        logger.error(f"request_approval failed: {e}")
        return (False, str(e))
    finally:
        session.close()


# ── Approval Workflow ────────────────────────────────────

def approve_decision(decision_id: int, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        record = session.query(DecisionRecord).filter(DecisionRecord.id == decision_id).first()
        if not record:
            return (False, f"Decision {decision_id} not found")
        
        if record.status != "pending":
            return (False, f"Cannot approve: status is {record.status}")
        
        # Approve the decision
        record.approved_by = user_id
        record.approved_at = datetime.utcnow()
        record.status = "approved"
        session.commit()
        
        log_action(user_id, "UPDATE", "decision_records", decision_id,
                 {"status": "pending"}, {"status": "approved"})
        
        return (True, f"Decision {decision_id} approved")
    except Exception as e:
        session.rollback()
        logger.error(f"approve_decision failed: {e}")
        return (False, str(e))
    finally:
        session.close()


def reject_decision(decision_id: int, user_id: int, reason: str) -> tuple[bool, str]:
    if not reason:
        return (False, "Rejection reason is required")
    
    session = get_session()
    try:
        record = session.query(DecisionRecord).filter(DecisionRecord.id == decision_id).first()
        if not record:
            return (False, f"Decision {decision_id} not found")
        
        if record.status not in ["pending"]:
            return (False, f"Cannot reject: status is {record.status}")
        
        # Reject the decision
        record.approved_by = user_id
        record.approved_at = datetime.utcnow()
        record.rationale = f"REJECTED: {reason}"
        record.status = "cancelled"
        session.commit()
        
        log_action(user_id, "UPDATE", "decision_records", decision_id,
                 {"status": "pending"}, {"status": "cancelled"})
        
        return (True, f"Decision {decision_id} rejected")
    except Exception as e:
        session.rollback()
        logger.error(f"reject_decision failed: {e}")
        return (False, str(e))
    finally:
        session.close()


def implement_decision(decision_id: int, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        record = session.query(DecisionRecord).filter(DecisionRecord.id == decision_id).first()
        if not record:
            return (False, f"Decision {decision_id} not found")
        
        if record.status != "approved":
            return (False, f"Cannot implement: status is {record.status}")
        
        record.status = "implemented"
        session.commit()
        
        log_action(user_id, "UPDATE", "decision_records", decision_id,
                 {"status": "approved"}, {"status": "implemented"})
        
        return (True, f"Decision {decision_id} marked as implemented")
    except Exception as e:
        session.rollback()
        logger.error(f"implement_decision failed: {e}")
        return (False, str(e))
    finally:
        session.close()


# ── Get Functions ────────────────────────────────────────

def get_decisions(status: str | None = None, decision_type: str | None = None,
                decided_by: int | None = None, approved_by: int | None = None,
                limit: int = 100, offset: int = 0) -> list[dict]:
    session = get_session()
    try:
        query = session.query(DecisionRecord).order_by(DecisionRecord.created_at.desc())
        
        if status:
            query = query.filter(DecisionRecord.status == status)
        if decision_type:
            query = query.filter(DecisionRecord.decision_type == decision_type)
        if decided_by:
            query = query.filter(DecisionRecord.decided_by == decided_by)
        if approved_by:
            query = query.filter(DecisionRecord.approved_by == approved_by)
        
        results = query.offset(offset).limit(limit).all()
        
        decisions = []
        for r in results:
            decisions.append({
                "id": r.id,
                "decision_type": r.decision_type,
                "context": json.loads(r.context) if r.context else None,
                "options_considered": json.loads(r.options_considered) if r.options_considered else None,
                "chosen_option": json.loads(r.chosen_option) if r.chosen_option else None,
                "rationale": r.rationale,
                "decided_by": r.decided_by,
                "decider_name": r.decider.username if r.decider else None,
                "approved_by": r.approved_by,
                "approver_name": r.approver.username if r.approver else None,
                "approved_at": r.approved_at.strftime("%Y-%m-%d %H:%M:%S") if r.approved_at else None,
                "status": r.status,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": r.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            })
        return decisions
    finally:
        session.close()


def get_decision(id: int) -> dict | None:
    session = get_session()
    try:
        record = session.query(DecisionRecord).filter(DecisionRecord.id == id).first()
        if not record:
            return None
        
        return {
            "id": record.id,
            "decision_type": record.decision_type,
            "context": json.loads(record.context) if record.context else None,
            "options_considered": json.loads(record.options_considered) if record.options_considered else None,
            "chosen_option": json.loads(record.chosen_option) if record.chosen_option else None,
            "rationale": record.rationale,
            "decided_by": record.decided_by,
            "decider_name": record.decider.username if record.decider else None,
            "approved_by": record.approved_by,
            "approver_name": record.approver.username if record.approver else None,
            "approved_at": record.approved_at.strftime("%Y-%m-%d %H:%M:%S") if record.approved_at else None,
            "status": record.status,
            "created_at": record.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": record.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
    finally:
        session.close()


def get_decision_summary() -> dict:
    session = get_session()
    try:
        # Count by status
        status_counts = {}
        for status in VALID_STATUSES:
            count = session.query(DecisionRecord).filter(
                DecisionRecord.status == status
            ).count()
            status_counts[status] = count
        
        # Count by decision type
        from sqlalchemy import func
        type_counts_raw = session.query(
            DecisionRecord.decision_type,
            func.count(DecisionRecord.id)
        ).group_by(DecisionRecord.decision_type).all()
        type_counts = {dt: cnt for dt, cnt in type_counts_raw}
        
        # Total
        total = session.query(DecisionRecord).count()
        
        # Pending approval count
        pending = status_counts.get("pending", 0)
        
        return {
            "total": total,
            "by_status": status_counts,
            "by_type": type_counts,
            "pending_approval": pending,
        }
    finally:
        session.close()