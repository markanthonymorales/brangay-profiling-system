import json
import logging
from datetime import datetime, date
from database.db import get_session
from database.models import AuditLog

logger = logging.getLogger(__name__)


class _SafeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)


def log_action(user_id: int, action: str, table_name: str, record_id: int | None = None,
               old_values: dict | None = None, new_values: dict | None = None):
    session = get_session()
    try:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            table_name=table_name,
            record_id=record_id,
            old_values=json.dumps(old_values, cls=_SafeEncoder) if old_values else None,
            new_values=json.dumps(new_values, cls=_SafeEncoder) if new_values else None,
            timestamp=datetime.utcnow(),
        )
        session.add(entry)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Audit log failed: {e}")
    finally:
        session.close()


def get_audit_logs(user_id: int | None = None, action: str | None = None,
                   table_name: str | None = None, date_from: datetime | None = None,
                   date_to: datetime | None = None, limit: int = 100, offset: int = 0) -> list[dict]:
    session = get_session()
    try:
        query = session.query(AuditLog).order_by(AuditLog.timestamp.desc())

        if user_id is not None:
            query = query.filter(AuditLog.user_id == user_id)
        if action is not None:
            query = query.filter(AuditLog.action == action)
        if table_name is not None:
            query = query.filter(AuditLog.table_name == table_name)
        if date_from is not None:
            query = query.filter(AuditLog.timestamp >= date_from)
        if date_to is not None:
            query = query.filter(AuditLog.timestamp <= date_to)

        results = query.offset(offset).limit(limit).all()
        logs = []
        for r in results:
            logs.append({
                "id": r.id,
                "user_id": r.user_id,
                "username": r.user.username if r.user else "Unknown",
                "action": r.action,
                "table_name": r.table_name,
                "record_id": r.record_id,
                "old_values": json.loads(r.old_values) if r.old_values else None,
                "new_values": json.loads(r.new_values) if r.new_values else None,
                "timestamp": r.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            })
        return logs
    finally:
        session.close()


def get_recent_activity(limit: int = 20) -> list[dict]:
    return get_audit_logs(limit=limit)
