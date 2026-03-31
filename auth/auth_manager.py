import bcrypt
import logging
from config import BCRYPT_ROUNDS, MIN_PASSWORD_LENGTH
from database.db import get_session
from database.models import User
from auth.roles import has_permission

logger = logging.getLogger(__name__)


class AuthManager:
    _instance = None
    _current_user: User | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("utf-8")

    def verify_password(self, password: str, password_hash: str) -> bool:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))

    def login(self, username: str, password: str) -> tuple[bool, str]:
        session = get_session()
        try:
            user = session.query(User).filter_by(username=username, is_active=True).first()
            if user is None:
                return False, "Invalid username or password."
            if not self.verify_password(password, user.password_hash):
                return False, "Invalid username or password."

            self._current_user = user
            logger.info(f"User '{username}' logged in.")
            return True, "Login successful."
        finally:
            session.close()

    def logout(self):
        if self._current_user:
            logger.info(f"User '{self._current_user.username}' logged out.")
        self._current_user = None

    def get_current_user(self) -> User | None:
        return self._current_user

    def is_logged_in(self) -> bool:
        return self._current_user is not None

    def check_permission(self, permission: str) -> bool:
        if self._current_user is None:
            return False
        return has_permission(self._current_user.role, permission)

    def change_password(self, user_id: int, new_password: str) -> tuple[bool, str]:
        if len(new_password) < MIN_PASSWORD_LENGTH:
            return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters."

        session = get_session()
        try:
            user = session.query(User).get(user_id)
            if user is None:
                return False, "User not found."
            user.password_hash = self.hash_password(new_password)
            user.must_change_password = False
            session.commit()
            if self._current_user and self._current_user.id == user_id:
                self._current_user = user
            logger.info(f"Password changed for user '{user.username}'.")
            return True, "Password changed successfully."
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()
