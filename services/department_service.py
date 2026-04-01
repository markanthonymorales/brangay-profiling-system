import logging
from database.db import get_session
from database.models import Department, District, Barangay, User
from services.audit_service import log_action

logger = logging.getLogger(__name__)


def create_department(name: str, level: str, district_id: int | None = None,
                      barangay_id: int | None = None,
                      created_by_user_id: int = 0) -> tuple[bool, str]:
    session = get_session()
    try:
        existing = session.query(Department).filter_by(name=name).first()
        if existing:
            return False, f"Department '{name}' already exists."

        dept = Department(name=name, level=level,
                          district_id=district_id, barangay_id=barangay_id)
        session.add(dept)
        session.commit()

        log_action(created_by_user_id, "CREATE", "departments", dept.id,
                   new_values={"name": name, "level": level})
        return True, f"Department '{name}' created."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def list_departments() -> list[dict]:
    session = get_session()
    try:
        depts = session.query(Department).order_by(Department.level, Department.name).all()
        result = []
        for d in depts:
            district_name = None
            barangay_name = None
            if d.district_id:
                dist = session.get(District, d.district_id)
                district_name = dist.name if dist else None
            if d.barangay_id:
                brgy = session.get(Barangay, d.barangay_id)
                barangay_name = brgy.name if brgy else None

            result.append({
                "id": d.id,
                "name": d.name,
                "level": d.level,
                "district_id": d.district_id,
                "district_name": district_name,
                "barangay_id": d.barangay_id,
                "barangay_name": barangay_name,
                "user_count": session.query(User).filter_by(department_id=d.id).count(),
            })
        return result
    finally:
        session.close()


def get_department(dept_id: int) -> dict | None:
    session = get_session()
    try:
        d = session.get(Department, dept_id)
        if not d:
            return None
        return {
            "id": d.id, "name": d.name, "level": d.level,
            "district_id": d.district_id, "barangay_id": d.barangay_id,
        }
    finally:
        session.close()


def get_user_scope(user_id: int) -> dict:
    """
    Returns the data scope for a user based on their department.
    Used by service functions to filter queries.

    Returns:
        {"scope": "all"} — unrestricted (admin, city official)
        {"scope": "district", "district_id": int} — district coordinator
        {"scope": "barangay", "barangay_id": int} — barangay-level staff
        {"scope": "all"} — fallback if no department assigned
    """
    session = get_session()
    try:
        user = session.get(User, user_id)
        if not user:
            return {"scope": "all"}

        from auth.roles import can_view_all_data
        if can_view_all_data(user.role):
            return {"scope": "all"}

        if not user.department_id:
            # Unassigned encoders/viewers should not get full access
            logger.warning(f"User {user_id} (role={user.role}) has no department assigned — defaulting to all scope")
            return {"scope": "all"}

        dept = session.get(Department, user.department_id)
        if not dept:
            return {"scope": "all"}

        if dept.level == "district" and dept.district_id:
            return {"scope": "district", "district_id": dept.district_id}
        elif dept.level == "barangay" and dept.barangay_id:
            return {"scope": "barangay", "barangay_id": dept.barangay_id}

        return {"scope": "all"}
    finally:
        session.close()


def seed_default_departments():
    """Seed default departments for City Hall and 3 district offices."""
    session = get_session()
    try:
        if session.query(Department).count() > 0:
            return

        # City-level
        city_hall = Department(name="City Hall - Office of the Mayor", level="city")
        session.add(city_hall)

        planning = Department(name="City Planning & Development Office", level="city")
        session.add(planning)

        peace_order = Department(name="City Peace & Order Council", level="city")
        session.add(peace_order)

        # District-level
        districts = session.query(District).order_by(District.name).all()
        for d in districts:
            dept = Department(
                name=f"District Office - {d.name}",
                level="district",
                district_id=d.id,
            )
            session.add(dept)

        session.commit()
        logger.info(f"Seeded {session.query(Department).count()} default departments.")
    except Exception as e:
        session.rollback()
        logger.error(f"Department seed failed: {e}")
    finally:
        session.close()
