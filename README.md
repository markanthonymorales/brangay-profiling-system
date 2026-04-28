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
- **Citizen portal** — Public submissions (incidents/concerns/feedback) with auto-categorization and routing to departments
- **Resource management** — Track equipment, personnel, budget allocations per barangay/department

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

### Policy Recommendations (Milestone 4)
- **Automated recommendation engine** — Generates policy recommendations using configurable templates with condition rules
- **Urgency & impact scoring** — Each recommendation scored by urgency and impact for prioritization
- **Domain-specific templates** — Crime, health, disaster, infrastructure, economic domains
- **Budget allocation estimates** — Recommended budget per policy recommendation

### Urban Planning & Forecasting (Milestone 4)
- **Long-term projections** — 10+ year housing, infrastructure, and disaster resilience projections
- **Logistic growth models** — Population-based housing demand projections with carrying capacity
- **Scenario simulation** — Create and compare development scenarios (optimistic, pessimistic, baseline)
- **Infrastructure planning** — School, health center, evacuation center capacity projections
- **Disaster resilience** — Flood-prone area identification, evacuation capacity, response time projections

### Coordinated Response Workflows (Milestone 4)
- **Multi-agency coordination** — Auto-assign multiple departments to incidents (crime, disaster, fire, health, traffic, infrastructure)
- **Workflow status tracking** — Initiated → in-progress → resolved workflow lifecycle
- **Department assignments** — Track which departments assigned to which incidents with status per department

### Governance & Decision Tracking (Milestone 4)
- **Decision records** — Track every decision with context, options considered, rationale, and outcome
- **Approval workflow** — Pending → approved → implemented decision lifecycle
- **Decision audit trail** — Full transparency of who decided what, when, and why

### Anomaly Detection (Milestone 4)
- **Continuous monitoring** — Automated detection of data quality issues and inconsistencies
- **Flagged records** — System automatically flags anomalies for review
- **Data validation** — Continuous validation of incoming data across all domains

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

1. Creates the SQLite database with 33 tables
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
│   ├── models.py                    # 45 SQLAlchemy ORM models
│   ├── db.py                        # Engine, session factory, init
│   ├── seed.py                      # Auto-seed on first run
│   ├── real_data.py                 # Real Davao City data (PSA Census)
│   └── sample_data.py              # Random sample data generator
│
├── auth/
│   ├── auth_manager.py              # Login, logout, password hashing
│   └── roles.py                     # RBAC (admin/encoder/viewer)
│
├── services/                        # 36 business logic modules
│   ├── analytics_service.py         # Chart-specific queries
│   ├── anomaly_service.py           # Data anomaly detection
│   ├── audit_service.py             # Immutable audit trail
│   ├── barangay_service.py          # Barangay CRUD & queries
│   ├── business_permit_service.py   # Business permit CRUD
│   ├── citizen_portal_service.py    # Public submissions & routing
│   ├── community_service.py         # Food, facilities, religion CRUD
│   ├── comparison_service.py        # Barangay comparison queries
│   ├── crime_service.py             # Crime & traffic CRUD + forecasting
│   ├── cross_department_service.py  # Cross-department sync & alerts
│   ├── department_service.py        # Department metadata
│   ├── disaster_service.py          # Disaster risk & incidents CRUD
│   ├── economic_service.py          # Income & business CRUD
│   ├── education_service.py         # Education statistics CRUD
│   ├── forecast_service.py          # Predictive forecasting
│   ├── governance_service.py        # Decision tracking & approval
│   ├── health_service.py            # Health statistics CRUD
│   ├── history_service.py           # Record change history
│   ├── infrastructure_service.py    # Utilities, land, waste CRUD
│   ├── map_service.py               # Map marker data
│   ├── notification_service.py      # User notifications
│   ├── plan_service.py              # Action plan generation
│   ├── population_service.py        # Population data CRUD
│   ├── recommendation_engine_service.py # Policy recommendation engine
│   ├── report_service.py            # Report data aggregation
│   ├── resident_service.py          # Resident categories CRUD
│   ├── resource_service.py          # Equipment, personnel, budget tracking
│   ├── schedule_service.py          # Data collection scheduling
│   ├── social_welfare_service.py    # Social welfare data CRUD
│   ├── submission_service.py        # Submission tracking
│   ├── system_service.py            # Backups, integrity, monitoring
│   ├── urban_planning_service.py   # Long-term projections & scenarios
│   ├── user_service.py              # User management
│   ├── validation_service.py        # Input validation rules
│   └── workflow_service.py          # Coordinated response workflows
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
│   ├── views/                       # 26 screen views
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
│   │   ├── user_mgmt_view.py       # User CRUD (admin)
│   │   ├── audit_log_view.py        # Change history (admin)
│   │   ├── system_view.py           # Monitoring 4 tabs (admin)
│   │   ├── urban_planning_view.py  # Long-term projections & scenarios
│   │   ├── citizen_portal_view.py  # Public submission form
│   │   └── governance_view.py       # Decision tracking & approval
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
