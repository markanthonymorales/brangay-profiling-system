import logging
from database.db import get_session
from database.models import User
from auth.auth_manager import AuthManager
from services.audit_service import log_action

logger = logging.getLogger(__name__)


def create_user(username: str, password: str, full_name: str, role: str,
                created_by_user_id: int, department_id: int | None = None) -> tuple[bool, str]:
    session = get_session()
    try:
        existing = session.query(User).filter_by(username=username).first()
        if existing:
            return False, f"Username '{username}' already exists."

        auth = AuthManager()
        user = User(
            username=username,
            password_hash=auth.hash_password(password),
            full_name=full_name,
            role=role,
            is_active=True,
            must_change_password=True,
            department_id=department_id,
        )
        session.add(user)
        session.commit()

        log_action(created_by_user_id, "CREATE", "users", user.id,
                   new_values={"username": username, "full_name": full_name, "role": role,
                               "department_id": department_id})

        return True, f"User '{username}' created successfully."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def update_user(user_id: int, full_name: str | None = None, role: str | None = None,
                department_id: int | None = -1,
                updated_by_user_id: int = 0) -> tuple[bool, str]:
    session = get_session()
    try:
        user = session.get(User, user_id)
        if user is None:
            return False, "User not found."

        old_values = {"full_name": user.full_name, "role": user.role,
                      "department_id": user.department_id}
        if full_name is not None:
            user.full_name = full_name
        if role is not None:
            user.role = role
        if department_id != -1:  # -1 means "don't change"
            user.department_id = department_id

        session.commit()
        new_values = {"full_name": user.full_name, "role": user.role,
                      "department_id": user.department_id}

        log_action(updated_by_user_id, "UPDATE", "users", user.id,
                   old_values=old_values, new_values=new_values)

        return True, "User updated successfully."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def deactivate_user(user_id: int, deactivated_by_user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        user = session.get(User, user_id)
        if user is None:
            return False, "User not found."
        if user_id == deactivated_by_user_id:
            return False, "You cannot deactivate your own account."

        user.is_active = False
        session.commit()

        log_action(deactivated_by_user_id, "UPDATE", "users", user.id,
                   old_values={"is_active": True}, new_values={"is_active": False})

        return True, f"User '{user.username}' deactivated."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def activate_user(user_id: int, activated_by_user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        user = session.get(User, user_id)
        if user is None:
            return False, "User not found."

        user.is_active = True
        session.commit()

        log_action(activated_by_user_id, "UPDATE", "users", user.id,
                   old_values={"is_active": False}, new_values={"is_active": True})

        return True, f"User '{user.username}' activated."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def list_users(include_inactive: bool = False) -> list[dict]:
    session = get_session()
    try:
        query = session.query(User)
        if not include_inactive:
            query = query.filter_by(is_active=True)
        users = query.order_by(User.username).all()
        return [
            {
                "id": u.id,
                "username": u.username,
                "full_name": u.full_name,
                "role": u.role,
                "is_active": u.is_active,
                "department_id": u.department_id,
                "department_name": u.department.name if u.department else "None",
                "created_at": u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else "",
            }
            for u in users
        ]
    finally:
        session.close()


def get_user(user_id: int) -> dict | None:
    session = get_session()
    try:
        user = session.get(User, user_id)
        if user is None:
            return None
        return {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
        }
    finally:
        session.close()
