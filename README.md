# Davao City Barangay Profiling System

A comprehensive desktop application for profiling all **182 barangays** across the **3 congressional districts** of Davao City. Built for the **City Government of Davao** to enable informed decision-making, public safety monitoring, and efficient resource management.

## Features

### Data Collection & Management
- **Population Data** — Total population, male/female counts, registered voters, non-registered residents, foreign residents, household counts (PSA 2020 Census data pre-loaded)
- **Resident Categories** — Renters, homeowners, squatters, informal settlers
- **Economic Data** — Income levels (poverty/low/middle/high brackets), business registry with type and status
- **Infrastructure** — Utilities (DCWD water, DLPC power, internet coverage %), land types, waste management
- **Community** — Food sources, government facilities, religious demographics
- **Classification** — Urban/rural classification for all 182 barangays

### Reports & Export
- **4 Report Types** — Barangay profile, district summary, city-wide summary, comparative (2-5 barangays)
- **Export Formats** — PDF (ReportLab with Davao City government branding) and CSV
- **Auto-Reports** — City-wide summary PDF auto-generated on startup every 24 hours
- **Live Preview** — Preview report data before exporting

### Dashboard & Analytics
- **Dashboard** — Summary stat cards, population-by-district chart, district overview, recent activity feed
- **Population Trends** — Year-over-year line charts (city/district/barangay scope)
- **District Comparison** — Grouped bar charts comparing population, businesses, utility coverage
- **Income Distribution** — Donut chart for income bracket breakdown per barangay
- **Utility Coverage** — Water, power, internet coverage comparison across districts

### Crime & Traffic Analytics
- **Incident Tracking** — Full CRUD for crime and traffic incidents with type, severity, date, status
- **Crime Overview** — Charts by type (bar), severity (pie), monthly trend (line)
- **High-Risk Areas** — Ranked table of top 20 barangays by incident count (last 12 months)
- **Predictive Forecast** — 6-month crime trend projection using linear regression (numpy)
- **Crime Types** — Theft, assault, robbery, drugs, homicide, vandalism, fraud, domestic violence
- **Traffic Types** — Accident, congestion, road hazard, pedestrian, hit-and-run

### Action Plans
- **Auto-Generated** — Prioritized recommendations per barangay based on crime trends, utility gaps, poverty rate, population growth
- **Categories** — Public safety, infrastructure, community services, economic development
- **Priority Levels** — HIGH (red), MEDIUM (orange), LOW (green)
- **PDF Export** — Export action plans as branded PDF documents

### Interactive Map
- **OpenStreetMap** — Embedded interactive map centered on Davao City
- **4 Overlay Modes** — By district (blue/green/orange), by crime risk (green-to-red), by population (sized markers), all markers
- **Info Panel** — Click any marker for detailed barangay info (population, crime, income, utilities, risk level)
- **Search** — Type a barangay name to zoom directly to it

### System Monitoring & Reliability
- **Automated Backups** — On startup (hourly), on-demand, keeps last 10, auto-prune
- **One-Click Restore** — Restore from any backup with safety pre-restore backup
- **8 Integrity Checks** — Barangay count, district count, FK integrity, DB integrity, orphaned records, admin user, audit health, coordinate coverage
- **Log Viewer** — Filterable by level (INFO/WARNING/ERROR), rotating log files (5 MB, 3 backups)
- **System Stats** — DB size, record counts per table, uptime, last backup/auto-report time

### Security & Access Control
- **3 User Roles** — Admin (full access), Encoder (data entry + reports), Viewer (read-only)
- **Password Security** — bcrypt hashing (12 rounds), forced password change on first login
- **Audit Trail** — Every CREATE/UPDATE/DELETE logged with user, timestamp, old/new values
- **Permission Guards** — Data entry blocked for viewers, admin views hidden for non-admins

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

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd brangay-profiling-system

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## First Run

On first launch, the system automatically:

1. Creates the SQLite database
2. Seeds all **182 barangays** with GPS coordinates across 3 congressional districts
3. Loads **real Davao City data** from PSA 2020 Census (population, demographics)
4. Populates income, utilities, businesses, crime incidents, and all other data categories
5. Creates test user accounts
6. Generates the app logo and icon
7. Creates the first startup backup

**Default admin account:** `admin` / `admin123` (must change password on first login)

**Test accounts created automatically:**

| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | Admin |
| encoder1 | password123 | Encoder |
| encoder2 | password123 | Encoder |
| viewer1 | password123 | Viewer |

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

## Resetting Data

To start fresh with all real data re-seeded:

```bash
# Delete the database (Windows)
del data\barangay_profiling.db

# Re-launch — auto-seeds everything
python main.py
```

To seed only random sample data (30 barangays) instead of real data:

```bash
python -m database.sample_data
```

## User Roles & Permissions

| Action | Admin | Encoder | Viewer |
|--------|-------|---------|--------|
| View all data & dashboards | Yes | Yes | Yes |
| Enter/edit data | Yes | Yes | No |
| Generate reports & export | Yes | Yes | Yes |
| View analytics & charts | Yes | Yes | Yes |
| Generate action plans | Yes | Yes | Yes |
| Manage users | Yes | No | No |
| View audit log | Yes | No | No |
| System monitoring & backups | Yes | No | No |
| Delete records | Yes | No | No |

## Project Structure

```
brangay-profiling-system/
├── main.py                     # Application entry point
├── config.py                   # Configuration constants
├── requirements.txt            # Python dependencies (7 packages)
├── CLAUDE.md                   # AI assistant context
├── README.md                   # This file
├── LICENSE                     # MIT License
│
├── database/
│   ├── models.py               # 17 SQLAlchemy ORM models
│   ├── db.py                   # Engine, session factory, init
│   ├── seed.py                 # Auto-seed on first run
│   ├── real_data.py            # Real Davao City data (PSA Census)
│   └── sample_data.py          # Random sample data generator
│
├── auth/
│   ├── auth_manager.py         # Login, logout, password hashing
│   └── roles.py                # RBAC (admin/encoder/viewer)
│
├── services/                   # 15 business logic modules
│   ├── audit_service.py        # Immutable audit trail
│   ├── barangay_service.py     # Barangay CRUD & queries
│   ├── population_service.py   # Population data CRUD
│   ├── resident_service.py     # Resident categories CRUD
│   ├── economic_service.py     # Income & business CRUD
│   ├── infrastructure_service.py # Utilities, land, waste CRUD
│   ├── community_service.py    # Food, facilities, religion CRUD
│   ├── crime_service.py        # Crime & traffic CRUD + forecasting
│   ├── report_service.py       # Report data aggregation
│   ├── analytics_service.py    # Chart-specific queries
│   ├── map_service.py          # Map marker data
│   ├── plan_service.py         # Action plan generation
│   ├── user_service.py         # User management
│   └── system_service.py       # Backups, integrity, monitoring
│
├── ui/
│   ├── app.py                  # Main window, navigation, view dispatch
│   ├── theme.py                # Davao City government colors
│   ├── components/             # 6 reusable widgets
│   │   ├── sidebar.py          # Navigation with logo
│   │   ├── data_table.py       # Paginated table with search
│   │   ├── form_fields.py      # Labeled inputs & dropdowns
│   │   ├── search_bar.py       # Search with filters
│   │   ├── stat_card.py        # Summary metric cards
│   │   └── chart_widget.py     # Matplotlib embed wrapper
│   ├── views/                  # 13 screen views
│   │   ├── login_view.py       # Branded login screen
│   │   ├── dashboard_view.py   # Summary + population chart
│   │   ├── barangay_list_view.py
│   │   ├── barangay_profile_view.py
│   │   ├── data_entry_view.py  # 5 data category tabs
│   │   ├── reports_view.py     # 4 report types + export
│   │   ├── analytics_view.py   # 4 chart tabs
│   │   ├── crime_view.py       # 5 crime/safety tabs
│   │   ├── action_plan_view.py # Plan generator + PDF export
│   │   ├── map_view.py         # Interactive OpenStreetMap
│   │   ├── user_mgmt_view.py   # User CRUD (admin)
│   │   ├── audit_log_view.py   # Change history (admin)
│   │   └── system_view.py      # Monitoring 4 tabs (admin)
│   └── dialogs/
│       ├── confirm_dialog.py
│       └── message_dialog.py
│
├── utils/
│   ├── logger.py               # Rotating file handler
│   ├── validators.py           # Input validation
│   ├── export.py               # CSV + PDF dispatch
│   ├── pdf_builder.py          # ReportLab PDF (Davao branding)
│   └── logo_generator.py       # App logo/icon generator
│
├── data/
│   ├── davao_barangays.json    # 182 barangays with GPS coordinates
│   ├── barangay_profiling.db   # SQLite database (auto-created)
│   ├── app.log                 # Application logs
│   ├── backups/                # Database backups
│   └── reports/                # Exported reports
│
├── assets/                     # Generated logo & icons (auto-created)
│
└── docs/superpowers/specs/     # 6 design specification documents
```

## Backup & Recovery

- **Automatic backup** on every app startup (skips if last backup < 1 hour old)
- **Manual backup** via System > Backups > "Backup Now"
- **Restore** from any backup with one-click (creates safety backup before restore)
- **Auto-prune** keeps last 10 backups, deletes older ones
- **Auto-reports** city-wide PDF generated every 24 hours on startup

## Screenshots

The application features a Davao City government-themed interface with:
- Deep blue (#003366) header with gold (#DAA520) accent line
- Government-style logo seal
- Professional sidebar navigation with branding
- Branded PDF reports with official header/footer

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- Philippine Statistics Authority (PSA) for 2020 Census data
- Commission on Elections (COMELEC) for voter registration data
- Philippine National Police (PNP) Davao City Police Office for crime statistics
- City Government of Davao for barangay and district information
