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
- `database/` — SQLAlchemy models (`models.py`), engine/session (`db.py`), seed data (`seed.py`)
- `auth/` — Singleton `AuthManager` for login/session, `roles.py` for RBAC (admin/encoder/viewer)
- `services/` — Business logic layer: one service per data domain, all write ops trigger audit logging
- `ui/` — CustomTkinter UI: `app.py` (main window + navigation), `components/` (reusable widgets), `views/` (screens), `dialogs/` (modals)
- `utils/` — Logging, input validators, CSV export (`export.py`), PDF generation (`pdf_builder.py` using ReportLab)
- `data/` — SQLite DB file (auto-created), `davao_barangays.json` (seed reference)

## Key Patterns

- **Service layer pattern**: All DB operations go through `services/`. Services handle sessions, audit logging, and return `tuple[bool, str]`.
- **Audit trail**: Every CREATE/UPDATE/DELETE on data tables is logged via `services/audit_service.py`. Audit records are immutable.
- **Auth singleton**: `AuthManager()` returns the same instance. Current user stored in memory.
- **View caching**: `ui/app.py` caches view instances in `_views_cache` dict. Views implement `refresh()` for data reload.
- **Action plans**: `services/plan_service.py` generates prioritized recommendations per barangay based on crime trends, utility gaps, poverty rates, and population growth.
- **Auto-reports**: City-wide PDF auto-generated on startup (if >24h since last). Stored in `data/reports/auto/`.
- **Permission guards**: Data entry view blocks viewer role. Crime view hides "Add" buttons for viewers.

## Database

- SQLite with WAL mode and foreign keys enabled (see `database/db.py`)
- Auto-seeds 3 districts, 182 barangays, and default admin on first run
- Default admin: `admin` / `admin123` (must change password on first login)
- Unique constraints on `(barangay_id, year)` for all yearly data tables

## Gotchas

- Python path: Use `/c/laragon/bin/python/python-3.13/python.exe`, not system `python` (Windows Store alias doesn't work)
- DB file created at `data/barangay_profiling.db` — delete it to reset and re-seed
- `TimestampMixin` uses `datetime.utcnow` — all timestamps are UTC
- CustomTkinter `CTkComboBox` with `state="readonly"` doesn't allow typing, only selection

## Phases

- Phase 1 (done): Foundation, data collection, auth, audit trail
- Phase 2 (done): Reports (4 types: barangay profile, district, citywide, comparative), PDF/CSV export
- Phase 3 (done): Dashboard charts (matplotlib embedded via FigureCanvasTkAgg), Analytics view with 4 tabs (population trends, district comparison, income distribution, utility coverage)
- Phase 4 (done): Crime & traffic incident tracking, high-risk area ranking, linear regression forecast. New models: crime_incidents, traffic_incidents. Crime & Safety view with 5 tabs.
- Phase 5 (done): Interactive OpenStreetMap via tkintermapview. 4 overlay modes (district/crime risk/population/all). 182 barangays with coordinates seeded. Info panel on marker click.
- Phase 6 (done): Automated DB backups (on startup + on demand, keep 10), one-click restore, 8 integrity checks, system monitoring dashboard (DB size, record counts, uptime), log viewer with rotation (5MB, 3 files).
