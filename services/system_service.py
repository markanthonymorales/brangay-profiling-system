import os
import re
import shutil
import sqlite3
import logging
from datetime import datetime, timedelta
from config import DB_PATH, LOG_PATH, BACKUP_DIR, MAX_BACKUPS, BASE_DIR
from database.db import get_session
from database.models import (
    User, District, Barangay, PopulationRecord, ResidentCategory,
    IncomeData, Business, Utility, LandType, WasteManagement,
    FoodSource, GovernmentFacility, ReligiousDemographic,
    CrimeIncident, TrafficIncident, AuditLog, RetryQueue,
)

logger = logging.getLogger(__name__)

_app_start_time = datetime.now()


# ── Backups ───────────────────────────────────────────────────

def create_backup() -> tuple[bool, str]:
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)

        if not os.path.exists(DB_PATH):
            return False, "Database file not found."

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}.db"
        backup_path = os.path.join(BACKUP_DIR, backup_name)

        shutil.copy2(DB_PATH, backup_path)
        logger.info(f"Backup created: {backup_name}")

        _prune_old_backups()

        size_mb = os.path.getsize(backup_path) / (1024 * 1024)
        return True, f"Backup created: {backup_name} ({size_mb:.2f} MB)"
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        return False, str(e)


def restore_backup(backup_filename: str) -> tuple[bool, str]:
    try:
        backup_path = os.path.join(BACKUP_DIR, backup_filename)
        if not os.path.exists(backup_path):
            return False, f"Backup file not found: {backup_filename}"

        # Create a pre-restore safety backup
        safety_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safety_name = f"pre_restore_{safety_timestamp}.db"
        safety_path = os.path.join(BACKUP_DIR, safety_name)
        shutil.copy2(DB_PATH, safety_path)
        logger.info(f"Pre-restore backup created: {safety_name}")

        # Restore
        shutil.copy2(backup_path, DB_PATH)
        logger.info(f"Database restored from: {backup_filename}")

        return True, f"Database restored from {backup_filename}. Please restart the application for changes to take effect."
    except Exception as e:
        logger.error(f"Restore failed: {e}")
        return False, str(e)


def delete_backup(backup_filename: str) -> tuple[bool, str]:
    try:
        backup_path = os.path.join(BACKUP_DIR, backup_filename)
        if not os.path.exists(backup_path):
            return False, "Backup file not found."
        os.remove(backup_path)
        logger.info(f"Backup deleted: {backup_filename}")
        return True, f"Backup deleted: {backup_filename}"
    except Exception as e:
        return False, str(e)


def list_backups() -> list[dict]:
    if not os.path.exists(BACKUP_DIR):
        return []

    backups = []
    for f in os.listdir(BACKUP_DIR):
        if f.endswith(".db"):
            path = os.path.join(BACKUP_DIR, f)
            size_mb = os.path.getsize(path) / (1024 * 1024)
            mtime = os.path.getmtime(path)
            created = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            backups.append({
                "filename": f,
                "filepath": path,
                "size_mb": round(size_mb, 2),
                "created": created,
            })

    backups.sort(key=lambda x: x["created"], reverse=True)
    return backups


def auto_backup_on_startup():
    try:
        if not os.path.exists(DB_PATH):
            return

        backups = list_backups()
        if backups:
            latest_time = datetime.strptime(backups[0]["created"], "%Y-%m-%d %H:%M:%S")
            if datetime.now() - latest_time < timedelta(hours=1):
                logger.info("Recent backup exists. Skipping startup backup.")
                return

        success, msg = create_backup()
        if success:
            logger.info(f"Startup backup: {msg}")
        else:
            logger.warning(f"Startup backup failed: {msg}")
    except Exception as e:
        logger.warning(f"Startup backup error: {e}")


def _prune_old_backups():
    backups = list_backups()
    # Don't prune pre_restore backups from the count
    regular_backups = [b for b in backups if not b["filename"].startswith("pre_restore_")]
    while len(regular_backups) > MAX_BACKUPS:
        oldest = regular_backups.pop()
        try:
            os.remove(oldest["filepath"])
            logger.info(f"Pruned old backup: {oldest['filename']}")
        except OSError:
            pass


# ── Integrity Checks ─────────────────────────────────────────

def run_integrity_checks() -> list[dict]:
    results = []
    session = get_session()
    try:
        # 1. Barangay count
        brgy_count = session.query(Barangay).count()
        results.append({
            "check": "Barangay Count",
            "status": "pass" if brgy_count == 182 else "warning",
            "details": f"{brgy_count} barangays found (expected 182)",
        })

        # 2. District count
        dist_count = session.query(District).count()
        results.append({
            "check": "District Count",
            "status": "pass" if dist_count == 3 else "warning",
            "details": f"{dist_count} districts found (expected 3)",
        })

        # 3. Admin user exists
        admin_count = session.query(User).filter_by(role="admin", is_active=True).count()
        results.append({
            "check": "Active Admin User",
            "status": "pass" if admin_count >= 1 else "fail",
            "details": f"{admin_count} active admin user(s)",
        })

        # 4. Foreign key check
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.execute("PRAGMA foreign_key_check")
            fk_errors = cursor.fetchall()
            conn.close()
            results.append({
                "check": "Foreign Key Integrity",
                "status": "pass" if not fk_errors else "fail",
                "details": f"{len(fk_errors)} violations found" if fk_errors else "All foreign keys valid",
            })
        except Exception as e:
            results.append({"check": "Foreign Key Integrity", "status": "fail", "details": str(e)})

        # 5. Database file integrity
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.execute("PRAGMA integrity_check")
            integrity = cursor.fetchone()[0]
            conn.close()
            results.append({
                "check": "Database File Integrity",
                "status": "pass" if integrity == "ok" else "fail",
                "details": integrity,
            })
        except Exception as e:
            results.append({"check": "Database File Integrity", "status": "fail", "details": str(e)})

        # 6. Audit log health
        null_audit = session.query(AuditLog).filter(AuditLog.user_id.is_(None)).count()
        results.append({
            "check": "Audit Log Health",
            "status": "pass" if null_audit == 0 else "warning",
            "details": f"{null_audit} entries with null user_id" if null_audit else "All audit entries have user references",
        })

        # 7. Orphaned population records
        orphaned = session.query(PopulationRecord).filter(
            ~PopulationRecord.barangay_id.in_(session.query(Barangay.id))
        ).count()
        results.append({
            "check": "Orphaned Population Records",
            "status": "pass" if orphaned == 0 else "warning",
            "details": f"{orphaned} orphaned records" if orphaned else "No orphaned records",
        })

        # 8. Coordinates coverage
        with_coords = session.query(Barangay).filter(
            Barangay.latitude.isnot(None), Barangay.longitude.isnot(None)
        ).count()
        results.append({
            "check": "Barangay Coordinates",
            "status": "pass" if with_coords == brgy_count else "warning",
            "details": f"{with_coords}/{brgy_count} barangays have coordinates",
        })

    except Exception as e:
        results.append({"check": "General Error", "status": "fail", "details": str(e)})
    finally:
        session.close()

    return results


# ── System Stats ──────────────────────────────────────────────

def get_system_stats() -> dict:
    session = get_session()
    try:
        db_size = os.path.getsize(DB_PATH) / (1024 * 1024) if os.path.exists(DB_PATH) else 0
        log_size = os.path.getsize(LOG_PATH) / (1024 * 1024) if os.path.exists(LOG_PATH) else 0

        table_counts = {
            "users": session.query(User).count(),
            "barangays": session.query(Barangay).count(),
            "districts": session.query(District).count(),
            "population_records": session.query(PopulationRecord).count(),
            "resident_categories": session.query(ResidentCategory).count(),
            "income_data": session.query(IncomeData).count(),
            "businesses": session.query(Business).count(),
            "utilities": session.query(Utility).count(),
            "land_types": session.query(LandType).count(),
            "waste_management": session.query(WasteManagement).count(),
            "food_sources": session.query(FoodSource).count(),
            "government_facilities": session.query(GovernmentFacility).count(),
            "religious_demographics": session.query(ReligiousDemographic).count(),
            "crime_incidents": session.query(CrimeIncident).count(),
            "traffic_incidents": session.query(TrafficIncident).count(),
            "audit_log": session.query(AuditLog).count(),
        }

        total_records = sum(table_counts.values())

        backups = list_backups()
        last_backup = backups[0]["created"] if backups else None

        return {
            "db_size_mb": round(db_size, 2),
            "log_size_mb": round(log_size, 2),
            "total_records": total_records,
            "table_counts": table_counts,
            "last_backup": last_backup,
            "backup_count": len(backups),
            "app_start_time": _app_start_time.strftime("%Y-%m-%d %H:%M:%S"),
        }
    finally:
        session.close()


# ── Error Log Reader ──────────────────────────────────────────

LOG_PATTERN = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \[(\w+)\] ([^:]+): (.+)$"
)


def get_error_log(level: str | None = None, limit: int = 100) -> list[dict]:
    if not os.path.exists(LOG_PATH):
        return []

    entries = []
    try:
        with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                match = LOG_PATTERN.match(line)
                if match:
                    entry = {
                        "timestamp": match.group(1),
                        "level": match.group(2),
                        "source": match.group(3),
                        "message": match.group(4),
                    }
                    if level is None or entry["level"] == level:
                        entries.append(entry)
    except Exception as e:
        logger.error(f"Failed to read log: {e}")

    # Return most recent entries first
    return entries[-limit:][::-1]


# ── Auto Report Generation ────────────────────────────────────

AUTO_REPORT_DIR = os.path.join(BASE_DIR, "data", "reports", "auto")


def auto_generate_reports():
    try:
        os.makedirs(AUTO_REPORT_DIR, exist_ok=True)

        # Check if last auto-report is recent enough (24 hours)
        existing = [f for f in os.listdir(AUTO_REPORT_DIR) if f.endswith(".pdf")]
        if existing:
            existing.sort(reverse=True)
            latest_path = os.path.join(AUTO_REPORT_DIR, existing[0])
            latest_mtime = datetime.fromtimestamp(os.path.getmtime(latest_path))
            if datetime.now() - latest_mtime < timedelta(hours=24):
                logger.info("Recent auto-report exists. Skipping.")
                return

        from services.report_service import get_citywide_report
        from utils.pdf_builder import build_pdf

        report_data = get_citywide_report()
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(AUTO_REPORT_DIR, f"citywide_auto_{date_str}.pdf")

        success, msg = build_pdf("citywide", report_data, filepath)
        if success:
            logger.info(f"Auto-report generated: {filepath}")
            _prune_auto_reports()
        else:
            logger.warning(f"Auto-report generation failed: {msg}")
    except Exception as e:
        logger.warning(f"Auto-report error: {e}")


def _prune_auto_reports():
    """Keep only the last 10 auto-generated reports."""
    existing = [f for f in os.listdir(AUTO_REPORT_DIR) if f.endswith(".pdf")]
    existing.sort(reverse=True)
    for old_file in existing[10:]:
        try:
            os.remove(os.path.join(AUTO_REPORT_DIR, old_file))
        except OSError:
            pass


def get_last_auto_report() -> dict | None:
    if not os.path.exists(AUTO_REPORT_DIR):
        return None
    existing = [f for f in os.listdir(AUTO_REPORT_DIR) if f.endswith(".pdf")]
    if not existing:
        return None
    existing.sort(reverse=True)
    latest = existing[0]
    path = os.path.join(AUTO_REPORT_DIR, latest)
    return {
        "filename": latest,
        "filepath": path,
        "size_mb": round(os.path.getsize(path) / (1024 * 1024), 2),
        "created": datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S"),
    }


# ── Retry Queue ──────────────────────────────────────────────

def add_to_retry_queue(operation: str, table_name: str, data: str,
                       error: str) -> tuple[bool, str]:
    """Add a failed operation to the retry queue."""
    import json
    session = get_session()
    try:
        entry = RetryQueue(
            operation=operation,
            table_name=table_name,
            data=data if isinstance(data, str) else json.dumps(data, default=str),
            error_message=error,
            attempts=0,
            max_attempts=3,
            status="pending",
        )
        session.add(entry)
        session.commit()
        logger.info(f"Added to retry queue: {operation} on {table_name} (id={entry.id})")
        return True, f"Added to retry queue (id={entry.id})"
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to add to retry queue: {e}")
        return False, str(e)
    finally:
        session.close()


def process_retry_queue() -> tuple[bool, str]:
    """Process pending items in the retry queue."""
    import importlib
    import json

    session = get_session()
    try:
        pending = (
            session.query(RetryQueue)
            .filter(RetryQueue.status == "pending", RetryQueue.attempts < RetryQueue.max_attempts)
            .order_by(RetryQueue.created_at)
            .all()
        )

        if not pending:
            return True, "No pending items in retry queue."

        processed = 0
        failed = 0
        for item in pending:
            item.attempts += 1
            try:
                # Attempt to re-run the operation
                # Operations are expected to be module_path.function_name format
                parts = item.operation.rsplit(".", 1)
                if len(parts) == 2:
                    module = importlib.import_module(parts[0])
                    func = getattr(module, parts[1])
                    data = json.loads(item.data) if item.data else {}
                    success, msg = func(**data)
                    if success:
                        item.status = "completed"
                        processed += 1
                    else:
                        item.error_message = msg
                        if item.attempts >= item.max_attempts:
                            item.status = "failed"
                        failed += 1
                else:
                    item.error_message = f"Invalid operation format: {item.operation}"
                    if item.attempts >= item.max_attempts:
                        item.status = "failed"
                    failed += 1
            except Exception as e:
                item.error_message = str(e)
                if item.attempts >= item.max_attempts:
                    item.status = "failed"
                failed += 1

            session.commit()

        return True, f"Processed {processed} items, {failed} failed out of {len(pending)} pending."
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to process retry queue: {e}")
        return False, str(e)
    finally:
        session.close()


def get_retry_queue(status: str | None = None, limit: int = 50) -> list[dict]:
    """Get items from the retry queue."""
    session = get_session()
    try:
        query = session.query(RetryQueue).order_by(RetryQueue.created_at.desc())
        if status:
            query = query.filter(RetryQueue.status == status)

        results = query.limit(limit).all()
        return [
            {
                "id": r.id,
                "operation": r.operation,
                "table_name": r.table_name,
                "error_message": r.error_message or "",
                "attempts": r.attempts,
                "max_attempts": r.max_attempts,
                "status": r.status,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
                "updated_at": r.updated_at.strftime("%Y-%m-%d %H:%M") if r.updated_at else "",
            }
            for r in results
        ]
    finally:
        session.close()
