# README & CLAUDE.md Full Refresh

**Date:** 2026-04-08
**Scope:** Full rewrite of both README.md and CLAUDE.md to reflect Milestone 3 state
**Approach:** Hybrid — Technical README with domain context + Prioritized CLAUDE.md

## Context

Both files are stale. README.md and CLAUDE.md cover Phases 1-6 but are missing Milestone 3 (Phases 17-19): 9 new models, 6 new services, 4 new views, cross-department sync, dashboard alerts, and several performance improvements. The project structure counts are wrong (README lists 17 models, 15 services, 13 views — actual is 34 models, 29 services, 22 views).

This is a content + structure refresh. No code changes.

---

## README.md Design

**Audience:** General GitHub visitors
**Tone:** Neutral, technical documentation

### Structure

#### 1. Badges
Shields.io badges at the top:
- `Python 3.13` (blue)
- `Platform: Windows` (lightgrey)
- `License: MIT` (green)
- `Database: SQLite` (blue)

#### 2. Title + Description
One-liner: "A comprehensive desktop application for profiling all 182 barangays across the 3 congressional districts of Davao City."

Keep the existing description but trim "Built for the City Government of Davao" to just state what it does.

#### 3. Features (6 capability groups)

Reorganized by capability, not by development phase. Each group gets a heading with bullet points.

**Data Collection & Management**
- 8 data domains: population, economic, infrastructure, community, health & welfare, disaster risk, education, business permits
- Summary-level yearly data with upsert (population, health, education, disaster risk, social welfare, income, utilities)
- Individual record CRUD (crime incidents, traffic incidents, disaster incidents, emergency resources, business permits, businesses)
- Cross-department data sync with automated threshold alerts
- Submission tracking per barangay per domain

**Analytics & Dashboard**
- Dashboard with summary stat cards, population-by-district chart, recent activity, cross-department alert summary
- Population trends (year-over-year line charts, city/district/barangay scope)
- District comparison (grouped bar charts — population, businesses, utility coverage)
- Income distribution (donut chart per barangay)
- Utility coverage (water, power, internet comparison across districts)
- Cross-department KPIs (active alerts, departments synced, stale data warnings)

**Reports & Export**
- 4 report types: barangay profile, district summary, city-wide summary, comparative (2-5 barangays)
- PDF export with Davao City government branding (ReportLab)
- CSV export
- Auto-generated city-wide PDF on startup (every 24 hours)
- Live preview before export

**Crime & Safety**
- Full CRUD for crime and traffic incidents (type, severity, date, status)
- Crime overview charts (by type, severity, monthly trend)
- High-risk area ranking (top 20 barangays by incident count, last 12 months)
- 6-month crime trend forecast (linear regression)
- Crime types: theft, assault, robbery, drugs, homicide, vandalism, fraud, domestic violence
- Traffic types: accident, congestion, road hazard, pedestrian, hit-and-run

**Interactive Map**
- OpenStreetMap embedded via tkintermapview
- 4 overlay modes: by district, by crime risk, by population, all markers
- Info panel on marker click (population, crime, income, utilities, risk level)
- Barangay search with zoom

**System Administration**
- 3 user roles: Admin (full), Encoder (data entry + reports), Viewer (read-only)
- bcrypt password hashing (12 rounds), forced change on first login
- Immutable audit trail (every CREATE/UPDATE/DELETE with user, timestamp, old/new values)
- Automated backups (on startup, on-demand, keep last 10, auto-prune)
- One-click restore with safety pre-restore backup
- 8 integrity checks
- System monitoring (DB size, record counts, uptime)
- Log viewer with rotation (5 MB, 3 files)

**Action Plans**
- Auto-generated prioritized recommendations per barangay
- Based on crime trends, utility gaps, poverty rate, population growth
- Priority levels: HIGH/MEDIUM/LOW
- PDF export

#### 4. Tech Stack
Same table format, no changes needed. Content is still accurate.

#### 5. Requirements
No changes: Python 3.11+, Windows 10/11, internet for map tiles.

#### 6. Installation & First Run
Merge current "Installation" and "First Run" sections. Include the DB reset one-liner (replaces the separate "Resetting Data" section).

#### 7. Default Accounts
Same table, no changes.

#### 8. Data Sources
Expand table with new domains:

| Data | Source | Coverage |
|------|--------|----------|
| Population (2020) | PSA Census | 171/182 barangays matched |
| Registered Voters | COMELEC 2025 | Per-district ratios |
| Religious Demographics | PSA/Wikipedia | All barangays |
| Utility Providers | DLPC, DCWD | All barangays |
| Crime Statistics | PNP-DCPO 2024-2025 | Proportional distribution |
| Poverty Rate | PSA 2021 | Scaled per barangay |
| Barangay Coordinates | Approximate GPS | All 182 barangays |
| Health Statistics | Simulated (Davao-scaled) | All barangays, 2 years |
| Disaster Risk | Simulated (geography-based) | All barangays |
| Education Statistics | Simulated (DepEd-scaled) | All barangays, 2 years |
| Business Permits | Simulated (urbanization-scaled) | All barangays |

Note: New department data (health, disaster, education, business) is seed data using realistic distributions based on Davao City statistics, not sourced from actual government datasets.

#### 9. Project Structure
Full tree updated with accurate counts:
- 34 SQLAlchemy models
- 29 service modules (excluding `__init__.py`)
- 22 view modules (excluding `__init__.py`)
- 6 reusable components (excluding `__init__.py`)
- 2 dialogs
- 5 utility modules (excluding `__init__.py`)

Rewrite the full tree from scratch to reflect the actual filesystem. List all service, view, and component files (not just new additions). Update comment annotations (e.g., "17 SQLAlchemy ORM models" → "34 SQLAlchemy ORM models", "15 business logic modules" → "29 business logic modules").

#### 10. Backup & Recovery
Keep as-is, content is still accurate.

#### 11. User Roles & Permissions
Update table to include new department views:

| Action | Admin | Encoder | Viewer |
|--------|-------|---------|--------|
| View all data, dashboards, maps | Yes | Yes | Yes |
| Enter/edit data (all domains) | Yes | Yes | No |
| Generate reports & export | Yes | Yes | Yes |
| View analytics & charts | Yes | Yes | Yes |
| Generate action plans | Yes | Yes | Yes |
| Manage health/disaster/education/business data | Yes | Yes | No |
| Manage users | Yes | No | No |
| View audit log | Yes | No | No |
| System monitoring & backups | Yes | No | No |
| Delete records | Yes | No | No |

#### 12. License & Acknowledgments
No changes.

### Sections Removed
- **Resetting Data** — folded into Installation as a one-liner
- **Screenshots** — was just a text description of colors, not actual screenshots

---

## CLAUDE.md Design

**Purpose:** AI assistant context for code navigation and development
**Principle:** Most-referenced sections first, no phase history

### Structure

#### 1. Commands (unchanged)
```bash
# Run the application (use Laragon's Python)
/c/laragon/bin/python/python-3.13/python.exe main.py

# Install dependencies
/c/laragon/bin/python/python-3.13/python.exe -m pip install -r requirements.txt
```

#### 2. Architecture
Update the one-liner and file tree:

"Python 3.13 + CustomTkinter desktop app with SQLite (SQLAlchemy ORM)."

Updated bullet list:
- `main.py` — Entry point: init DB, launch UI
- `config.py` — All app constants (DB path, window size, auth config)
- `database/` — SQLAlchemy models (`models.py`, 34 models), engine/session (`db.py`), seed data (`seed.py`, `real_data.py`)
- `auth/` — Singleton `AuthManager` for login/session, `roles.py` for RBAC (admin/encoder/viewer)
- `services/` — 29 service modules: one per data domain, all write ops trigger audit logging
- `ui/` — CustomTkinter UI: `app.py` (main window + navigation), `components/` (6 reusable widgets), `views/` (22 screens), `dialogs/` (modals)
- `utils/` — Logging, input validators, CSV export (`export.py`), PDF generation (`pdf_builder.py` using ReportLab)
- `data/` — SQLite DB file (auto-created), `davao_barangays.json` (seed reference)

#### 3. Key Patterns
Existing patterns kept, 3 new ones added:

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

#### 4. Database
- SQLite with WAL mode and foreign keys enabled (see `database/db.py`)
- 34 models total: 3 core (District, Barangay, User), 14 data domain tables, 9 department tables (health, social welfare, disaster risk, disaster incidents, emergency resources, education, business permits, department sync, cross-department alerts), 8 system tables (audit, notifications, history, submissions, schedules, retry queue, etc.)
- Auto-seeds 3 districts, 182 barangays, default admin, and all department data on first run
- Default admin: `admin` / `admin123` (must change password on first login)
- Unique constraints on `(barangay_id, year)` for all yearly data tables

#### 5. Gotchas
- Python path: Use `/c/laragon/bin/python/python-3.13/python.exe`, not system `python` (Windows Store alias doesn't work)
- DB file created at `data/barangay_profiling.db` — delete it to reset and re-seed
- `TimestampMixin` uses `datetime.utcnow` — all timestamps are UTC
- CustomTkinter `CTkComboBox` with `state="readonly"` doesn't allow typing, only selection
- Cross-department service imports must be lazy (inside function body) to avoid circular imports between department services

#### Sections Removed
- **Phases** — Entirely removed. Development history is derivable from git log. Wastes AI context.

---

## Verification

1. Read both files after rewrite — confirm no stale counts or missing sections
2. Grep for old counts ("17 models", "15 services", "13 views") — should return zero matches
3. Confirm all 34 models listed in models.py are accounted for in CLAUDE.md database section
4. Confirm badges render correctly in GitHub markdown preview
