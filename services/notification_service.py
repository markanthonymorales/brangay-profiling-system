import logging
from datetime import datetime
from database.db import get_session
from database.models import Notification

logger = logging.getLogger(__name__)

VALID_SEVERITIES = ("info", "warning", "error")


def create_notification(user_id: int, type: str, title: str,
                        message: str = "", severity: str = "info") -> tuple[bool, str]:
    """Create a notification for a user."""
    if severity not in VALID_SEVERITIES:
        severity = "info"

    session = get_session()
    try:
        notif = Notification(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            severity=severity,
            is_read=False,
        )
        session.add(notif)
        session.commit()
        return True, f"Notification created (id={notif.id})"
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to create notification: {e}")
        return False, str(e)
    finally:
        session.close()


def get_notifications(user_id: int, unread_only: bool = False,
                      limit: int = 50) -> list[dict]:
    """Get notifications for a user."""
    session = get_session()
    try:
        query = (
            session.query(Notification)
            .filter(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
        )
        if unread_only:
            query = query.filter(Notification.is_read == False)

        results = query.limit(limit).all()
        return [
            {
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "message": n.message or "",
                "severity": n.severity,
                "is_read": n.is_read,
                "created_at": n.created_at.strftime("%Y-%m-%d %H:%M") if n.created_at else "",
            }
            for n in results
        ]
    finally:
        session.close()


def mark_read(notification_id: int) -> tuple[bool, str]:
    """Mark a notification as read."""
    session = get_session()
    try:
        notif = session.get(Notification, notification_id)
        if not notif:
            return False, "Notification not found."
        notif.is_read = True
        session.commit()
        return True, "Notification marked as read."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def mark_all_read(user_id: int) -> tuple[bool, str]:
    """Mark all notifications for a user as read."""
    session = get_session()
    try:
        session.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False,
        ).update({"is_read": True})
        session.commit()
        return True, "All notifications marked as read."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def get_unread_count(user_id: int) -> int:
    """Get count of unread notifications for a user."""
    session = get_session()
    try:
        return (
            session.query(Notification)
            .filter(Notification.user_id == user_id, Notification.is_read == False)
            .count()
        )
    finally:
        session.close()
