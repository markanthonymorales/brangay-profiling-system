import logging
import random
import string
from datetime import datetime
from database.db import get_session
from database.models import CitizenSubmission, SubmissionRoutingRule, Department
from services.audit_service import log_action

logger = logging.getLogger(__name__)

# Valid submission statuses
VALID_STATUSES = ["submitted", "acknowledged", "routed", "resolved", "rejected"]

# Valid submission types
VALID_TYPES = ["incident", "concern", "feedback"]

# Category keywords for auto-categorization
CATEGORY_KEYWORDS = {
    "infrastructure": ["road", "bridge", "street", "light", "drainage", "sidewalk", "pothole"],
    "public_safety": ["crime", "theft", "robbery", "assault", "suspicious", "illegal"],
    "health": ["hospital", "clinic", "disease", "sanitation", "garbage", "waste"],
    "disaster": ["flood", "fire", "earthquake", "typhoon", "evacuation"],
    "traffic": ["road", "accident", "signal", "sign", "parking", "congestion"],
    "noise": ["noise", "loud", "party", "music", "construction"],
    "business": ["business", "permit", "license", "illegal", "operation"],
    "environment": ["pollution", "tree", "park", "animal", "noise"],
}


def _generate_tracking_code() -> str:
    chars = string.ascii_uppercase + string.digits
    return "CS-" + "".join(random.choices(chars, k=8))


# ── Submission Functions ─────────────────────────────────

def create_submission(data: dict) -> tuple[bool, str]:
    session = get_session()
    try:
        # Validate submission_type
        submission_type = data.get("submission_type")
        if submission_type not in VALID_TYPES:
            return False, f"Invalid submission_type. Must be one of: {VALID_TYPES}"
        
        # Auto-categorize if not provided
        category = data.get("category")
        if not category and data.get("description"):
            category = auto_categorize(data["description"])
        
        if not category:
            return False, "Category is required"
        
        # Generate unique tracking code
        tracking_code = _generate_tracking_code()
        max_attempts = 10
        attempts = 0
        while attempts < max_attempts:
            existing = session.query(CitizenSubmission).filter_by(
                tracking_code=tracking_code
            ).first()
            if not existing:
                break
            tracking_code = _generate_tracking_code()
            attempts += 1
        else:
            return False, "Could not generate unique tracking code"
        
        submission = CitizenSubmission(
            submission_type=submission_type,
            category=category,
            description=data.get("description"),
            location=data.get("location"),
            barangay_id=data.get("barangay_id"),
            reporter_name=data.get("reporter_name"),
            reporter_contact=data.get("reporter_contact"),
            reporter_email=data.get("reporter_email"),
            tracking_code=tracking_code,
            status="submitted",
        )
        session.add(submission)
        session.commit()
        
        logger.info(f"Citizen submission created: {tracking_code}")
        
        return True, tracking_code
    except Exception as e:
        session.rollback()
        logger.error(f"Create submission failed: {e}")
        return False, str(e)
    finally:
        session.close()


def update_submission_status(submission_id: int, new_status: str,
                         resolution_notes: str | None = None) -> tuple[bool, str]:
    session = get_session()
    try:
        submission = session.get(CitizenSubmission, submission_id)
        if not submission:
            return False, "Submission not found"
        
        if new_status not in VALID_STATUSES:
            return False, f"Invalid status. Must be one of: {VALID_STATUSES}"
        
        old_status = submission.status
        submission.status = new_status
        
        if new_status == "resolved":
            submission.resolved_at = datetime.utcnow()
        
        if resolution_notes:
            submission.resolution_notes = resolution_notes
        
        session.commit()
        
        log_action(None, "UPDATE", "citizen_submissions", submission_id,
                 old_values={"status": old_status},
                 new_values={"status": new_status})
        
        return True, f"Status updated to {new_status}"
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


# ── Routing Functions ─────────────────────────────────

def route_submission(submission_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        submission = session.get(CitizenSubmission, submission_id)
        if not submission:
            return False, "Submission not found"
        
        # Find matching routing rule
        rule = session.query(SubmissionRoutingRule).filter_by(
            category=submission.category
        ).order_by(SubmissionRoutingRule.priority.desc()).first()
        
        if not rule:
            # No rule found, just acknowledge
            submission.status = "acknowledged"
            session.commit()
            return True, "No routing rule found - submission acknowledged"
        
        # Update status to routed
        old_status = submission.status
        submission.status = "routed"
        session.commit()
        
        log_action(None, "UPDATE", "citizen_submissions", submission_id,
                 old_values={"status": old_status},
                 new_values={"status": "routed", "target_department_id": rule.department_id})
        
        return True, f"Routed to {rule.department.name if rule.department else 'department'}"
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def auto_categorize(description: str) -> str | None:
    if not description:
        return None
    
    description_lower = description.lower()
    
    # Score each category
    category_scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in description_lower)
        if score > 0:
            category_scores[category] = score
    
    if not category_scores:
        return None
    
    # Return highest scoring category
    return max(category_scores, key=category_scores.get)


# ── Get Functions ─────────────────────────────────

def get_submissions(status: str | None = None, category: str | None = None,
              limit: int = 100) -> list[dict]:
    session = get_session()
    try:
        query = session.query(CitizenSubmission).order_by(
            CitizenSubmission.created_at.desc()
        )
        
        if status:
            query = query.filter(CitizenSubmission.status == status)
        if category:
            query = query.filter(CitizenSubmission.category == category)
        
        results = query.limit(limit).all()
        
        return [
            {
                "id": s.id,
                "tracking_code": s.tracking_code,
                "submission_type": s.submission_type,
                "category": s.category,
                "description": s.description[:100] + "..." if s.description and len(s.description) > 100 else s.description or "",
                "location": s.location or "",
                "barangay_name": s.barangay.name if s.barangay else None,
                "reporter_name": s.reporter_name or "",
                "status": s.status,
                "created_at": s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else "",
                "resolved_at": s.resolved_at.strftime("%Y-%m-%d %H:%M") if s.resolved_at else "",
            }
            for s in results
        ]
    finally:
        session.close()


def get_submission_by_code(tracking_code: str) -> dict | None:
    session = get_session()
    try:
        submission = session.query(CitizenSubmission).filter_by(
            tracking_code=tracking_code
        ).first()
        
        if not submission:
            return None
        
        return {
            "tracking_code": submission.tracking_code,
            "submission_type": submission.submission_type,
            "category": submission.category,
            "description": submission.description,
            "location": submission.location,
            "status": submission.status,
            "created_at": submission.created_at.strftime("%Y-%m-%d %H:%M") if submission.created_at else "",
            "resolved_at": submission.resolved_at.strftime("%Y-%m-%d %H:%M") if submission.resolved_at else "",
            "resolution_notes": submission.resolution_notes or "",
        }
    finally:
        session.close()


def get_submission_counts() -> dict:
    session = get_session()
    try:
        from sqlalchemy import func
        
        total = session.query(CitizenSubmission).count()
        
        by_status = dict(session.query(
            CitizenSubmission.status,
            func.count(CitizenSubmission.id)
        ).group_by(CitizenSubmission.status).all())
        
        by_category = dict(session.query(
            CitizenSubmission.category,
            func.count(CitizenSubmission.id)
        ).group_by(CitizenSubmission.category).all())
        
        return {
            "total": total,
            "by_status": by_status,
            "by_category": by_category,
        }
    finally:
        session.close()