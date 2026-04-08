# README & CLAUDE.md Full Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite README.md and CLAUDE.md to accurately reflect the Milestone 3 state of the project (34 models, 29 services, 22 views, cross-department features).

**Architecture:** Two file rewrites. No code changes. README gets shields.io badges, capability-grouped features, and an accurate project tree. CLAUDE.md gets prioritized sections (commands first) with 3 new patterns and no phase history.

**Tech Stack:** Markdown only.

**Spec:** `docs/superpowers/specs/2026-04-08-readme-claudemd-refresh-design.md`

---

### Task 1: Rewrite README.md

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Write the complete README.md**

Replace the entire contents of `README.md` with the following:

```markdown
![Python](https://img.shields.io/badge/Python-3.13-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)
![Database](https://img.shields.io/badge/Database-SQLite-blue)

# Davao City Barangay Profiling System

A comprehensive desktop application for profiling all **182 barangays** across the **3 congressional districts** of Davao City. Enables informed decision-making, public safety monitoring, and efficient resource management through integrated data collection, analytics, and reporting.

## Features

### Data Collection & Management
- **8 data domains** — Population, economic, infrastructure, community, health & welfare, disaster risk, education, business permits
- **Summary-level yearly data** with upsert — population, health, education, disaster risk, social welfare, income, utilities
- **Individual record CRUD** — Crime incidents, traffic incidents, disaster incidents, emergency resources, business permits, businesses
- **Cross-department data sync** with automated threshold alerts (5 configurable rules)
- **Submission tracking** per barangay per domain

### Analytics & Dashboard
- **Dashboard** — Summary stat cards, population-by-district chart, recent activity, cross-department alert summary
- **Population Trends** — Year-over-year line charts (city/district/barangay scope)
- **District Comparison** — Grouped bar charts comparing population, businesses, utility coverage
- **Income Distribution** — Donut chart for income bracket breakdown per barangay
- **Utility Coverage** — Water, power, internet coverage comparison across districts
- **Cross-Department KPIs** — Active alerts, departments synced, stale data warnings

### Reports & Export
- **4 report types** — Barangay profile, district summary, city-wide summary, comparative (2-5 barangays)
- **PDF export** with Davao City government branding (ReportLab)
- **CSV export** for all data tables
- **Auto-generated** city-wide PDF on startup (every 24 hours)
- **Live preview** before export

### Crime & Safety
- **Incident tracking** — Full CRUD for crime and traffic incidents with type, severity, date, status
- **Crime overview** — Charts by type (bar), severity (pie), monthly trend (line)
- **High-risk areas** — Ranked table of top 20 barangays by incident count (last 12 months)
- **Predictive forecast** — 6-month crime trend projection using linear regression
- **Crime types** — Theft, assault, robbery, drugs, homicide, vandalism, fraud, domestic violence
- **Traffic types** — Accident, congestion, road hazard, pedestrian, hit-and-run

### Interactive Map
- **OpenStreetMap** embedded via tkintermapview
- **4 overlay modes** — By district (blue/green/orange), by crime risk (green-to-red), by population (sized markers), all markers
- **Info panel** — Click any marker for barangay details (population, crime, income, utilities, risk level)
- **Search** — Type a barangay name to zoom directly to it

### Action Plans
- **Auto-generated** prioritized recommendations per barangay
- **Based on** crime trends, utility gaps, poverty rate, population growth
- **Categories** — Public safety, infrastructure, community services, economic development
- **Priority levels** — HIGH (red), MEDIUM (orange), LOW (green)
- **PDF export** with government branding

### System Administration
- **3 user roles** — Admin (full access), Encoder (data entry + reports), Viewer (read-only)
- **Password security** — bcrypt hashing (12 rounds), forced change on first login
- **Audit trail** — Every CREATE/UPDATE/DELETE logged with user, timestamp, old/new values
- **Automated backups** — On startup (hourly), on-demand, keeps last 10, auto-prune
- **One-click restore** from any backup with safety pre-restore backup
- **8 integrity checks** — Barangay count, district count, FK integrity, DB integrity, orphaned records, admin user, audit health, coordinate coverage
- **Log viewer** — Filterable by level (INFO/WARNING/ERROR), rotating log files (5 MB, 3 backups)
- **System stats** — DB size, record counts per table, uptime, last backup/auto-report time

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.13 |
| UI Framework | CustomTkinter |
| Database | SQLite with WAL mode (SQLAlchemy ORM) |
| Charts | Matplotlib (embedded via FigureCanvasTkAgg) |
| Maps | tkintermapview (OpenStreetMap) |
| PDF Export | ReportLab |
| Password Hashing | bcrypt |
| Branding | Davao City government blue (#003366) and gold (#DAA520) |

## Requirements

- Python 3.11+ (tested with Python 3.13)
- Windows 10/11 (tested on Windows 11)
- Internet connection (for map tiles on first load)

## Installation & First Run

```bash
# Clone the repository
git clone <repository-url>
cd brangay-profiling-system

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

On first launch, the system automatically:

1. Creates the SQLite database with 34 tables
2. Seeds all **182 barangays** with GPS coordinates across 3 congressional districts
3. Loads **real Davao City data** from PSA 2020 Census (population, demographics)
4. Populates income, utilities, businesses, crime incidents, health, disaster, education, and business permit data
5. Creates test user accounts
6. Generates the app logo and icon
7. Creates the first startup backup

To reset and re-seed all data, delete `data/barangay_profiling.db` and relaunch.

**Default accounts:**

| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | Admin |
| encoder1 | password123 | Encoder |
| encoder2 | password123 | Encoder |
| viewer1 | password123 | Viewer |

The admin account requires a password change on first login.

## Data Sources

| Data | Source | Coverage |
|------|--------|----------|
| Population (2020) | Philippine Statistics Authority (PSA) Census | 171/182 barangays matched |
| Registered Voters | COMELEC 2025 (1,007,784 total) | Per-district ratios |
| Religious Demographics | PSA/Wikipedia (Catholic 78%, Islam 4%) | All barangays |
| Utility Providers | DLPC (power), DCWD (water) | All barangays |
| Crime Statistics | PNP-DCPO 2024-2025 (~518 focus crimes in 2025) | Proportional distribution |
| Poverty Rate | PSA 2021 (5.1% city-wide) | Scaled per barangay |
| Barangay Coordinates | Approximate GPS for all 182 barangays | All barangays |
| Health Statistics | Simulated (Davao-scaled distributions) | All barangays, 2 years |
| Disaster Risk | Simulated (geography-based risk profiles) | All barangays |
| Education Statistics | Simulated (DepEd-scaled distributions) | All barangays, 2 years |
| Business Permits | Simulated (urbanization-scaled) | All barangays |

New department data (health, disaster, education, business permits) uses realistic seed distributions based on Davao City statistics.

## Project Structure

```
brangay-profiling-system/
├── main.py                          # Application entry point
├── config.py                        # Configuration constants
├── requirements.txt                 # Python dependencies
├── CLAUDE.md                        # AI assistant context
├── README.md                        # This file
├── LICENSE                          # MIT License
│
├── database/
│   ├── models.py                    # 34 SQLAlchemy ORM models
│   ├── db.py                        # Engine, session factory, init
│   ├── seed.py                      # Auto-seed on first run
│   ├── real_data.py                 # Real Davao City data (PSA Census)
│   └── sample_data.py              # Random sample data generator
│
├── auth/
│   ├── auth_manager.py              # Login, logout, password hashing
│   └── roles.py                     # RBAC (admin/encoder/viewer)
│
├── services/                        # 29 business logic modules
│   ├── analytics_service.py         # Chart-specific queries
│   ├── anomaly_service.py           # Data anomaly detection
│   ├── audit_service.py             # Immutable audit trail
│   ├── barangay_service.py          # Barangay CRUD & queries
│   ├── business_permit_service.py   # Business permit CRUD
│   ├── community_service.py         # Food, facilities, religion CRUD
│   ├── comparison_service.py        # Barangay comparison queries
│   ├── crime_service.py             # Crime & traffic CRUD + forecasting
│   ├── cross_department_service.py  # Cross-department sync & alerts
│   ├── department_service.py        # Department metadata
│   ├── disaster_service.py          # Disaster risk & incidents CRUD
│   ├── economic_service.py          # Income & business CRUD
│   ├── education_service.py         # Education statistics CRUD
│   ├── forecast_service.py          # Predictive forecasting
│   ├── health_service.py            # Health statistics CRUD
│   ├── history_service.py           # Record change history
│   ├── infrastructure_service.py    # Utilities, land, waste CRUD
│   ├── map_service.py               # Map marker data
│   ├── notification_service.py      # User notifications
│   ├── plan_service.py              # Action plan generation
│   ├── population_service.py        # Population data CRUD
│   ├── report_service.py            # Report data aggregation
│   ├── resident_service.py          # Resident categories CRUD
│   ├── schedule_service.py          # Data collection scheduling
│   ├── social_welfare_service.py    # Social welfare data CRUD
│   ├── submission_service.py        # Submission tracking
│   ├── system_service.py            # Backups, integrity, monitoring
│   ├── user_service.py              # User management
│   └── validation_service.py        # Input validation rules
│
├── ui/
│   ├── app.py                       # Main window, navigation, view dispatch
│   ├── theme.py                     # Davao City government colors
│   ├── components/                  # 6 reusable widgets
│   │   ├── sidebar.py               # Navigation with logo
│   │   ├── data_table.py            # Paginated table with search
│   │   ├── form_fields.py           # Labeled inputs & dropdowns
│   │   ├── search_bar.py            # Search with filters
│   │   ├── stat_card.py             # Summary metric cards
│   │   └── chart_widget.py          # Matplotlib embed wrapper
│   ├── views/                       # 22 screen views
│   │   ├── login_view.py            # Branded login screen
│   │   ├── dashboard_view.py        # Summary + charts + alerts
│   │   ├── barangay_list_view.py    # Barangay directory
│   │   ├── barangay_profile_view.py # Individual barangay detail
│   │   ├── data_entry_view.py       # Multi-tab data entry
│   │   ├── reports_view.py          # 4 report types + export
│   │   ├── analytics_view.py        # 4 chart tabs
│   │   ├── crime_view.py            # 5 crime/safety tabs
│   │   ├── health_view.py           # 4 health & welfare tabs
│   │   ├── disaster_view.py         # 5 disaster & safety tabs
│   │   ├── education_view.py        # 3 education tabs
│   │   ├── business_permit_view.py  # 3 business permit tabs
│   │   ├── action_plan_view.py      # Plan generator + PDF export
│   │   ├── map_view.py              # Interactive OpenStreetMap
│   │   ├── comparison_view.py       # Barangay comparison
│   │   ├── forecast_view.py         # Predictive analytics
│   │   ├── notification_view.py     # User notifications
│   │   ├── submissions_view.py      # Submission tracking
│   │   ├── schedule_view.py         # Data collection schedules
│   │   ├── user_mgmt_view.py        # User CRUD (admin)
│   │   ├── audit_log_view.py        # Change history (admin)
│   │   └── system_view.py           # Monitoring 4 tabs (admin)
│   └── dialogs/
│       ├── confirm_dialog.py        # Confirmation modal
│       └── message_dialog.py        # Info/error modal
│
├── utils/
│   ├── logger.py                    # Rotating file handler
│   ├── validators.py                # Input validation
│   ├── export.py                    # CSV + PDF dispatch
│   ├── pdf_builder.py               # ReportLab PDF (Davao branding)
│   └── logo_generator.py            # App logo/icon generator
│
├── data/
│   ├── davao_barangays.json         # 182 barangays with GPS coordinates
│   ├── barangay_profiling.db        # SQLite database (auto-created)
│   ├── app.log                      # Application logs
│   ├── backups/                     # Database backups
│   └── reports/                     # Exported reports
│
├── assets/                          # Generated logo & icons (auto-created)
│
└── docs/                            # Design specs & implementation plans
```

## User Roles & Permissions

| Action | Admin | Encoder | Viewer |
|--------|-------|---------|--------|
| View all data, dashboards, maps | Yes | Yes | Yes |
| Enter/edit data (all domains) | Yes | Yes | No |
| Generate reports & export | Yes | Yes | Yes |
| View analytics & charts | Yes | Yes | Yes |
| Generate action plans | Yes | Yes | Yes |
| Manage department data (health, disaster, education, business) | Yes | Yes | No |
| Manage users | Yes | No | No |
| View audit log | Yes | No | No |
| System monitoring & backups | Yes | No | No |
| Delete records | Yes | No | No |

## Backup & Recovery

- **Automatic backup** on every app startup (skips if last backup < 1 hour old)
- **Manual backup** via System > Backups > "Backup Now"
- **Restore** from any backup with one-click (creates safety backup before restore)
- **Auto-prune** keeps last 10 backups, deletes older ones
- **Auto-reports** city-wide PDF generated every 24 hours on startup

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- Philippine Statistics Authority (PSA) for 2020 Census data
- Commission on Elections (COMELEC) for voter registration data
- Philippine National Police (PNP) Davao City Police Office for crime statistics
- City Government of Davao for barangay and district information
```

- [ ] **Step 2: Verify no stale counts remain**

Run: `grep -n "17 model\|15 business\|13 screen\|17 SQL" README.md`
Expected: No matches.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: rewrite README with milestone 3 features, accurate counts, and badges"
```

---

### Task 2: Rewrite CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Write the complete CLAUDE.md**

Replace the entire contents of `CLAUDE.md` with the following:

```markdown
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
- `database/` — SQLAlchemy models (`models.py`, 34 models), engine/session (`db.py`), seed data (`seed.py`, `real_data.py`)
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
- 34 models: 3 core (District, Barangay, User), 14 data domain tables, 9 department tables (health, social welfare, disaster risk/incidents, emergency resources, education, business permits, department sync, cross-department alerts), 8 system tables (audit, notifications, history, submissions, schedules, retry queue, etc.)
- Auto-seeds 3 districts, 182 barangays, default admin, and all department data on first run
- Default admin: `admin` / `admin123` (must change password on first login)
- Unique constraints on `(barangay_id, year)` for all yearly data tables

## Gotchas

- Python path: Use `/c/laragon/bin/python/python-3.13/python.exe`, not system `python` (Windows Store alias doesn't work)
- DB file created at `data/barangay_profiling.db` — delete it to reset and re-seed
- `TimestampMixin` uses `datetime.utcnow` — all timestamps are UTC
- CustomTkinter `CTkComboBox` with `state="readonly"` doesn't allow typing, only selection
- Cross-department service imports must be lazy (inside function body) to avoid circular imports between department services
```

- [ ] **Step 2: Verify Phases section is removed and no stale counts remain**

Run: `grep -n "Phase\|17 model\|15 business\|13 screen" CLAUDE.md`
Expected: No matches.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: rewrite CLAUDE.md with prioritized sections and milestone 3 patterns"
```

---

### Task 3: Verify Both Files

- [ ] **Step 1: Verify README renders valid markdown**

Run: `head -5 README.md`
Expected: Badge lines starting with `![Python]`.

- [ ] **Step 2: Verify CLAUDE.md starts with Commands**

Run: `head -10 CLAUDE.md`
Expected: Title, then `## Commands` as first section.

- [ ] **Step 3: Cross-check model count against actual codebase**

Run: `grep -c "^class.*Base)" database/models.py`
Expected: `34`

- [ ] **Step 4: Cross-check service count**

Run: `ls services/*.py | grep -v __init__ | wc -l`
Expected: `29`

- [ ] **Step 5: Cross-check view count**

Run: `ls ui/views/*.py | grep -v __init__ | wc -l`
Expected: `22`
