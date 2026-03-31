# Phase 6: Monitoring & Reliability — Design Specification

## Context

Phases 1-5 built the complete feature set: data collection, reports, charts, crime analytics, and mapping. Phase 6 adds operational reliability — automated backups, data integrity checks, system monitoring, and enhanced logging to ensure the system runs reliably for city government use.

## Scope

- Automated SQLite backups (on startup + on demand), keep last 10
- One-click restore from backup with confirmation
- Data integrity checks (FK consistency, duplicates, orphaned records)
- System monitoring dashboard (DB size, record counts, uptime, log viewer)
- Enhanced logging with file rotation (5 MB max, 3 rotated files)

## No New Dependencies

All features use Python standard library (shutil, os, logging.handlers, sqlite3).

## Files to Create

| File | Purpose |
|------|---------|
| `services/system_service.py` | Backup, restore, integrity checks, system stats |
| `ui/views/system_view.py` | System monitoring view (admin only, 4 tabs) |

## Files to Modify

| File | Change |
|------|--------|
| `utils/logger.py` | Add RotatingFileHandler (5 MB, 3 backups) |
| `main.py` | Call auto_backup_on_startup() after init_db() |
| `ui/components/sidebar.py` | Add "System" nav item (admin only) |
| `ui/app.py` | Add system view to navigation dispatch |
| `config.py` | Add BACKUP_DIR and MAX_BACKUPS constants |

## Config Additions (config.py)

```python
BACKUP_DIR = os.path.join(BASE_DIR, "data", "backups")
MAX_BACKUPS = 10
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT = 3
```

## Enhanced Logging (utils/logger.py)

Replace `FileHandler` with `RotatingFileHandler`:
- Max size: 5 MB per log file
- Keep 3 rotated files (app.log, app.log.1, app.log.2, app.log.3)
- Same format: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`

## System Service (services/system_service.py)

### create_backup() -> tuple[bool, str]

- Copies DB file to `data/backups/backup_YYYYMMDD_HHMMSS.db`
- Uses `shutil.copy2()` for metadata preservation
- After copy, prunes oldest backups if count > MAX_BACKUPS
- Returns success/failure with message

### restore_backup(backup_filename: str) -> tuple[bool, str]

- Confirms backup file exists
- Creates a pre-restore backup first (safety net)
- Replaces current DB with selected backup via `shutil.copy2()`
- Returns success message advising app restart

### list_backups() -> list[dict]

```python
[{"filename": str, "filepath": str, "size_mb": float, "created": str}, ...]
```
Sorted newest first.

### auto_backup_on_startup()

- Called from `main.py` after `init_db()`
- Creates a backup only if the last backup is older than 1 hour (avoids rapid restarts creating many backups)

### run_integrity_checks() -> list[dict]

Returns a list of check results:
```python
[{"check": str, "status": "pass"|"fail"|"warning", "details": str}, ...]
```

Checks performed:
1. **Barangay count** — verify 182 barangays exist
2. **District count** — verify 3 districts exist
3. **Foreign key integrity** — run `PRAGMA foreign_key_check`
4. **Orphaned population records** — population_records with invalid barangay_id
5. **Duplicate yearly records** — check unique constraints on (barangay_id, year) tables
6. **Admin user exists** — at least one active admin user
7. **Database file integrity** — run `PRAGMA integrity_check`
8. **Audit log health** — verify audit_log has no null user_ids

### get_system_stats() -> dict

```python
{
    "db_size_mb": float,
    "log_size_mb": float,
    "total_records": int,
    "table_counts": {"users": int, "barangays": int, "population_records": int, ...},
    "last_backup": str | None,  # timestamp of most recent backup
    "backup_count": int,
    "app_start_time": str,
}
```

### get_error_log(level: str = None, limit: int = 100) -> list[dict]

Reads app.log and parses entries:
```python
[{"timestamp": str, "level": str, "source": str, "message": str}, ...]
```
Optional filter by level (INFO, WARNING, ERROR).

## System View (ui/views/system_view.py)

Admin-only view with 4 tabs:

### Tab 1: Overview

- Stat cards: DB Size, Total Records, Last Backup, Backup Count
- Table showing record counts per database table
- App start time display

### Tab 2: Backups

- "Backup Now" button → creates backup, refreshes list
- Backup list table: filename, size, date created
- "Restore" button on each row → confirmation dialog → restores, shows restart message
- "Delete" button on each row → confirmation → deletes backup file

### Tab 3: Integrity

- "Run Integrity Check" button
- Results table: Check Name, Status (pass/fail/warning with color), Details
- Green check for pass, red X for fail, yellow ! for warning

### Tab 4: Logs

- Level filter dropdown: All, INFO, WARNING, ERROR
- "Refresh" button
- Scrollable log viewer showing parsed log entries with color-coded levels

## Sidebar Update

Add to admin section (after Audit Log):
```python
("system", "System", "\u2699"),
```

## Verification Plan

1. App startup creates automatic backup in `data/backups/`
2. "Backup Now" creates a new backup, shows in list
3. Restore from backup replaces DB, shows restart message
4. Integrity checks all pass on a healthy database
5. Integrity check detects issues when deliberately broken (e.g., delete a district)
6. System stats show correct DB size, record counts
7. Log viewer displays recent log entries with correct levels
8. Old backups beyond 10 are automatically pruned
9. Log rotation works when log exceeds 5 MB
