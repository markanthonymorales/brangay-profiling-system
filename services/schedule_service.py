import logging
from datetime import date, datetime
from database.db import get_session
from database.models import (
    DataCollectionSchedule, BarangaySubmissionStatus, Barangay,
    PopulationRecord, IncomeData, Utility, CrimeIncident, WasteManagement,
)
from services.audit_service import log_action
from services.notification_service import create_notification
from sqlalchemy import func, extract

logger = logging.getLogger(__name__)

# Maps submission status column -> (model, filter_type)
# filter_type: "year" means filter by year column, "date_year" means extract year from date
SUBMISSION_TABLE_MAP = {
    "population_submitted": (PopulationRecord, "year"),
    "income_submitted": (IncomeData, "year"),
    "utilities_submitted": (Utility, "year"),
    "crime_submitted": (CrimeIncident, "date_year"),
    "waste_submitted": (WasteManagement, "year"),
}


def create_schedule(year: int, start_date: date, end_date: date,
                    user_id: int, notes: str = "") -> tuple[bool, str]:
    """Create a new annual data collection schedule and initialize status rows."""
    session = get_session()
    try:
        existing = session.query(DataCollectionSchedule).filter_by(year=year).first()
        if existing:
            return False, f"Schedule for {year} already exists."

        schedule = DataCollectionSchedule(
            year=year,
            start_date=start_date,
            end_date=end_date,
            status="upcoming" if start_date > date.today() else "active",
            created_by=user_id,
            notes=notes,
        )
        session.add(schedule)
        session.flush()

        # Initialize submission status for all barangays
        barangays = session.query(Barangay).all()
        for brgy in barangays:
            status = BarangaySubmissionStatus(
                barangay_id=brgy.id,
                year=year,
            )
            session.add(status)

        session.commit()
        log_action(user_id, "CREATE", "data_collection_schedules", schedule.id,
                   new_values={"year": year, "start_date": str(start_date), "end_date": str(end_date)})

        return True, f"Schedule for {year} created with {len(barangays)} barangay tracking rows."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def get_schedule(year: int | None = None) -> dict | None:
    """Get schedule for a year, or current active schedule."""
    session = get_session()
    try:
        if year:
            sched = session.query(DataCollectionSchedule).filter_by(year=year).first()
        else:
            sched = session.query(DataCollectionSchedule).filter_by(status="active").first()

        if not sched:
            return None
        return {
            "id": sched.id,
            "year": sched.year,
            "start_date": sched.start_date.strftime("%Y-%m-%d") if sched.start_date else "",
            "end_date": sched.end_date.strftime("%Y-%m-%d") if sched.end_date else "",
            "status": sched.status,
            "notes": sched.notes or "",
            "created_by": sched.created_by,
        }
    finally:
        session.close()


def get_all_schedules() -> list[dict]:
    """All schedules ordered by year desc."""
    session = get_session()
    try:
        schedules = session.query(DataCollectionSchedule).order_by(DataCollectionSchedule.year.desc()).all()
        return [
            {
                "id": s.id,
                "year": s.year,
                "start_date": s.start_date.strftime("%Y-%m-%d") if s.start_date else "",
                "end_date": s.end_date.strftime("%Y-%m-%d") if s.end_date else "",
                "status": s.status,
                "notes": s.notes or "",
            }
            for s in schedules
        ]
    finally:
        session.close()


def update_schedule(schedule_id: int, user_id: int,
                    start_date: date | None = None, end_date: date | None = None,
                    status: str | None = None, notes: str | None = None) -> tuple[bool, str]:
    """Update schedule fields."""
    session = get_session()
    try:
        sched = session.get(DataCollectionSchedule, schedule_id)
        if not sched:
            return False, "Schedule not found."

        old_vals = {"status": sched.status}
        if start_date is not None:
            sched.start_date = start_date
        if end_date is not None:
            sched.end_date = end_date
        if status is not None:
            sched.status = status
        if notes is not None:
            sched.notes = notes

        session.commit()
        log_action(user_id, "UPDATE", "data_collection_schedules", sched.id,
                   old_values=old_vals, new_values={"status": sched.status})
        return True, "Schedule updated."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def get_compliance_dashboard(year: int) -> dict:
    """Return compliance status for all barangays for a given year."""
    session = get_session()
    try:
        sched = session.query(DataCollectionSchedule).filter_by(year=year).first()
        schedule_info = None
        if sched:
            schedule_info = {
                "start_date": sched.start_date.strftime("%Y-%m-%d") if sched.start_date else "",
                "end_date": sched.end_date.strftime("%Y-%m-%d") if sched.end_date else "",
                "status": sched.status,
            }

        statuses = (
            session.query(BarangaySubmissionStatus)
            .filter_by(year=year)
            .all()
        )

        total = len(statuses)
        complete = sum(1 for s in statuses if s.is_complete)
        incomplete = total - complete

        barangays = []
        for s in statuses:
            brgy = session.get(Barangay, s.barangay_id)
            if not brgy:
                continue
            missing = []
            for col, label in [
                ("population_submitted", "Population"),
                ("income_submitted", "Income"),
                ("utilities_submitted", "Utilities"),
                ("crime_submitted", "Crime"),
                ("waste_submitted", "Waste"),
            ]:
                if not getattr(s, col):
                    missing.append(label)

            barangays.append({
                "id": s.barangay_id,
                "name": brgy.name,
                "district_name": brgy.district.name if brgy.district else "",
                "population_submitted": s.population_submitted,
                "income_submitted": s.income_submitted,
                "utilities_submitted": s.utilities_submitted,
                "crime_submitted": s.crime_submitted,
                "waste_submitted": s.waste_submitted,
                "is_complete": s.is_complete,
                "missing_tables": missing,
            })

        barangays.sort(key=lambda b: (b["district_name"], b["name"]))

        return {
            "year": year,
            "schedule": schedule_info,
            "total_barangays": total,
            "complete_count": complete,
            "incomplete_count": incomplete,
            "completion_rate_pct": round((complete / total * 100) if total > 0 else 0, 1),
            "barangays": barangays,
        }
    finally:
        session.close()


def refresh_submission_status(barangay_id: int, year: int) -> None:
    """Recompute submission status by checking actual data tables."""
    session = get_session()
    try:
        status = (
            session.query(BarangaySubmissionStatus)
            .filter_by(barangay_id=barangay_id, year=year)
            .first()
        )
        if not status:
            return

        for col_name, (model, filter_type) in SUBMISSION_TABLE_MAP.items():
            if filter_type == "year":
                exists = session.query(model).filter_by(barangay_id=barangay_id, year=year).first() is not None
            else:  # date_year
                exists = (
                    session.query(model)
                    .filter(
                        model.barangay_id == barangay_id,
                        extract("year", model.date_occurred) == year,
                    )
                    .first()
                ) is not None
            setattr(status, col_name, exists)

        all_done = all(
            getattr(status, col) for col in SUBMISSION_TABLE_MAP.keys()
        )
        status.is_complete = all_done
        if all_done and not status.completed_at:
            status.completed_at = datetime.utcnow()

        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to refresh submission status: {e}")
    finally:
        session.close()


def check_overdue_and_notify(user_id: int) -> int:
    """Create notifications for overdue schedules with incomplete barangays."""
    session = get_session()
    try:
        overdue = (
            session.query(DataCollectionSchedule)
            .filter(
                DataCollectionSchedule.status == "active",
                DataCollectionSchedule.end_date < date.today(),
            )
            .all()
        )

        count = 0
        for sched in overdue:
            incomplete = (
                session.query(func.count(BarangaySubmissionStatus.id))
                .filter_by(year=sched.year, is_complete=False)
                .scalar()
            ) or 0

            if incomplete > 0:
                success, _ = create_notification(
                    user_id=user_id,
                    type="schedule_overdue",
                    title=f"Overdue: {sched.year} Data Collection",
                    message=f"{incomplete} barangays have not completed their submissions for {sched.year}. Deadline was {sched.end_date}.",
                    severity="warning",
                )
                if success:
                    count += 1

        return count
    finally:
        session.close()


def get_missing_submissions(year: int) -> list[dict]:
    """Return incomplete barangays with their missing table names."""
    session = get_session()
    try:
        statuses = (
            session.query(BarangaySubmissionStatus)
            .filter_by(year=year, is_complete=False)
            .all()
        )
        results = []
        for s in statuses:
            brgy = session.get(Barangay, s.barangay_id)
            if not brgy:
                continue
            missing = []
            for col, label in [
                ("population_submitted", "Population"),
                ("income_submitted", "Income"),
                ("utilities_submitted", "Utilities"),
                ("crime_submitted", "Crime"),
                ("waste_submitted", "Waste"),
            ]:
                if not getattr(s, col):
                    missing.append(label)
            results.append({
                "barangay_id": s.barangay_id,
                "barangay_name": brgy.name,
                "district_name": brgy.district.name if brgy.district else "",
                "missing_tables": missing,
            })
        return results
    finally:
        session.close()
