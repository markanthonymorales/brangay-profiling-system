import json
import logging
from datetime import datetime
from database.db import get_session
from database.models import Submission, User, Barangay
from services.audit_service import log_action

logger = logging.getLogger(__name__)

VALID_STATUSES = ["draft", "pending", "approved", "rejected"]

# Maps table_name to the service save function to call on approval
SAVE_HANDLERS = {
    # Yearly data (barangay_id, year, data, user_id)
    "population_records": ("services.population_service", "save_population_record"),
    "resident_categories": ("services.resident_service", "save_resident_category"),
    "income_data": ("services.economic_service", "save_income_record"),
    "utilities": ("services.infrastructure_service", "save_utility_record"),
    "waste_management": ("services.infrastructure_service", "save_waste_record"),
    # Non-yearly data (barangay_id, data, user_id)
    "businesses": ("services.economic_service", "save_business"),
    "food_sources": ("services.community_service", "save_food_source"),
    "government_facilities": ("services.community_service", "save_government_facility"),
    "religious_demographics": ("services.community_service", "save_religious_demographic"),
    "land_types": ("services.infrastructure_service", "save_land_type"),
}


def create_submission(user_id: int, table_name: str, barangay_id: int,
                      year: int | None, data: dict) -> tuple[bool, str]:
    session = get_session()
    try:
        submission = Submission(
            submitted_by=user_id,
            table_name=table_name,
            barangay_id=barangay_id,
            year=year,
            record_data=json.dumps(data, default=str),
            status="pending",
        )
        session.add(submission)
        session.commit()

        log_action(user_id, "CREATE", "submissions", submission.id,
                   new_values={"table_name": table_name, "barangay_id": barangay_id, "status": "pending"})

        return True, f"Submission #{submission.id} created and pending review."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def approve_submission(submission_id: int, reviewer_id: int,
                       notes: str = "") -> tuple[bool, str]:
    session = get_session()
    try:
        sub = session.get(Submission, submission_id)
        if not sub:
            return False, "Submission not found."
        if sub.status != "pending":
            return False, f"Submission is already {sub.status}."

        # Apply the data to the actual table FIRST
        success, msg = _apply_submission(sub.table_name, sub.barangay_id,
                                         sub.year, sub.record_data, reviewer_id)
        if not success:
            logger.warning(f"Submission #{sub.id} apply failed: {msg}")
            return False, f"Could not apply data: {msg}. Submission remains pending."

        # Refresh submission status tracking
        if sub.year:
            try:
                from services.schedule_service import refresh_submission_status
                refresh_submission_status(sub.barangay_id, sub.year)
            except Exception as e:
                logger.warning(f"Could not refresh submission status: {e}")

        # Only mark as approved AFTER successful apply
        sub.status = "approved"
        sub.reviewed_by = reviewer_id
        sub.review_notes = notes
        sub.reviewed_at = datetime.utcnow()
        session.commit()

        log_action(reviewer_id, "UPDATE", "submissions", sub.id,
                   old_values={"status": "pending"},
                   new_values={"status": "approved"})

        return True, f"Submission #{submission_id} approved and data saved."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def reject_submission(submission_id: int, reviewer_id: int,
                      notes: str = "") -> tuple[bool, str]:
    session = get_session()
    try:
        sub = session.get(Submission, submission_id)
        if not sub:
            return False, "Submission not found."
        if sub.status != "pending":
            return False, f"Submission is already {sub.status}."

        sub.status = "rejected"
        sub.reviewed_by = reviewer_id
        sub.review_notes = notes
        sub.reviewed_at = datetime.utcnow()
        session.commit()

        log_action(reviewer_id, "UPDATE", "submissions", sub.id,
                   old_values={"status": "pending"},
                   new_values={"status": "rejected", "notes": notes})

        return True, f"Submission #{submission_id} rejected."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def list_submissions(status: str | None = None, submitted_by: int | None = None,
                     limit: int = 100) -> list[dict]:
    session = get_session()
    try:
        query = session.query(Submission).order_by(Submission.created_at.desc())
        if status:
            query = query.filter(Submission.status == status)
        if submitted_by:
            query = query.filter(Submission.submitted_by == submitted_by)

        results = query.limit(limit).all()
        return [
            {
                "id": s.id,
                "submitted_by": s.submitted_by,
                "submitter_name": s.submitter.full_name if s.submitter else "Unknown",
                "table_name": s.table_name,
                "barangay_name": s.barangay.name if s.barangay else "N/A",
                "year": s.year,
                "status": s.status,
                "review_notes": s.review_notes or "",
                "reviewer_name": s.reviewer.full_name if s.reviewer else "",
                "created_at": s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else "",
                "reviewed_at": s.reviewed_at.strftime("%Y-%m-%d %H:%M") if s.reviewed_at else "",
            }
            for s in results
        ]
    finally:
        session.close()


def get_pending_count() -> int:
    session = get_session()
    try:
        return session.query(Submission).filter_by(status="pending").count()
    finally:
        session.close()


def get_submission_detail(submission_id: int) -> dict | None:
    session = get_session()
    try:
        s = session.get(Submission, submission_id)
        if not s:
            return None
        return {
            "id": s.id,
            "submitted_by": s.submitted_by,
            "submitter_name": s.submitter.full_name if s.submitter else "Unknown",
            "table_name": s.table_name,
            "barangay_id": s.barangay_id,
            "barangay_name": s.barangay.name if s.barangay else "N/A",
            "year": s.year,
            "record_data": json.loads(s.record_data) if s.record_data else {},
            "status": s.status,
            "review_notes": s.review_notes or "",
            "reviewer_name": s.reviewer.full_name if s.reviewer else "",
            "created_at": s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else "",
            "reviewed_at": s.reviewed_at.strftime("%Y-%m-%d %H:%M") if s.reviewed_at else "",
        }
    finally:
        session.close()


def _apply_submission(table_name: str, barangay_id: int, year: int | None,
                      record_data_json: str, user_id: int) -> tuple[bool, str]:
    """Apply approved submission data to the actual database table."""
    import importlib

    handler = SAVE_HANDLERS.get(table_name)
    if not handler:
        return False, f"No handler for table: {table_name}"

    module_path, func_name = handler
    try:
        module = importlib.import_module(module_path)
        save_func = getattr(module, func_name)
        data = json.loads(record_data_json)

        if year is not None:
            return save_func(barangay_id, year, data, user_id)
        else:
            return save_func(barangay_id, data, user_id)
    except Exception as e:
        return False, str(e)
