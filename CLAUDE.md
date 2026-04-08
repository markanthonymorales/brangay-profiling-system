# Davao City Barangay Profiling System

## Commands

```bash
# Run the application (use Laragon's Python)
/c/laragon/bin/python/python-3.13/python.exe main.py

# Install dependencies
/c/laragon/bin/python/python-3.13/python.exe -m pip install -r requirements.txt
```

## Architecture

Python 3.13 + CustomTkinter desktop app with SQLite (SQLAlchemy ORM).

- `main.py` — Entry point: init DB, launch UI
- `config.py` — All app constants (DB path, window size, auth config)
- `database/` — SQLAlchemy models (`models.py`, 33 models), engine/session (`db.py`), seed data (`seed.py`, `real_data.py`)
- `auth/` — Singleton `AuthManager` for login/session, `roles.py` for RBAC (admin/encoder/viewer)
- `services/` — 29 service modules: one per data domain, all write ops trigger audit logging
- `ui/` — CustomTkinter UI: `app.py` (main window + navigation), `components/` (6 reusable widgets), `views/` (22 screens), `dialogs/` (modals)
- `utils/` — Logging, input validators, CSV export (`export.py`), PDF generation (`pdf_builder.py` using ReportLab)
- `data/` — SQLite DB file (auto-created), `davao_barangays.json` (seed reference)

## Key Patterns

- **Service layer pattern**: All DB operations go through `services/`. Services handle sessions, audit logging, and return `tuple[bool, str]`.
- **Audit trail**: Every CREATE/UPDATE/DELETE on data tables is logged via `services/audit_service.py`. Audit records are immutable.
- **Auth singleton**: `AuthManager()` returns the same instance. Current user stored in memory.
- **View caching**: `ui/app.py` caches view instances in `_views_cache` dict. Views implement `refresh()` for data reload.
- **Lazy tab building**: Views with tabs (CTkTabview) defer tab content construction until tab is selected. Reduces dropdown allocation on init.
- **Cross-department hooks**: Department service save functions call `cross_department_service.on_department_data_saved()` after successful commit. Uses lazy import inside function body to avoid circular dependency.
- **Navigator caching**: District and barangay dropdown queries are cached to avoid repeated DB hits during view navigation.
- **Permission guards**: Data entry views block viewer role. Department views hide "Add" buttons for viewers.
- **Auto-reports**: City-wide PDF auto-generated on startup (if >24h since last). Stored in `data/reports/auto/`.
- **Action plans**: `services/plan_service.py` generates prioritized recommendations per barangay based on crime trends, utility gaps, poverty rates, and population growth.

## Database

- SQLite with WAL mode and foreign keys enabled (see `database/db.py`)
- 33 models: 3 core (District, Barangay, User), 14 data domain tables, 9 department tables (health, social welfare, disaster risk/incidents, emergency resources, education, business permits, department sync, cross-department alerts), 8 system tables (audit, notifications, history, submissions, schedules, retry queue, etc.)
- Auto-seeds 3 districts, 182 barangays, default admin, and all department data on first run
- Default admin: `admin` / `admin123` (must change password on first login)
- Unique constraints on `(barangay_id, year)` for all yearly data tables

## Gotchas

- Python path: Use `/c/laragon/bin/python/python-3.13/python.exe`, not system `python` (Windows Store alias doesn't work)
- DB file created at `data/barangay_profiling.db` — delete it to reset and re-seed
- `TimestampMixin` uses `datetime.utcnow` — all timestamps are UTC
- CustomTkinter `CTkComboBox` with `state="readonly"` doesn't allow typing, only selection
- Cross-department service imports must be lazy (inside function body) to avoid circular imports between department services
