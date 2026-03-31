# Davao City Barangay Profiling System - Design Specification

## Context

The City Government of Davao needs a comprehensive profiling tool covering all 182 barangays across 3 congressional districts. Currently, there is no centralized system for collecting, organizing, and analyzing barangay-level data. This system will enable informed decision-making and efficient resource management by city officials.

This spec covers **Phase 1: Foundation & Data Collection** — the core data entry, profiling, and user management system that all future phases build upon.

## System Overview

- **Type:** Desktop application (not web-based)
- **Language:** Python 3.11+
- **UI Framework:** CustomTkinter
- **Database:** SQLite with SQLAlchemy ORM
- **Architecture:** Monolithic single-process application
- **Users:** Multi-user with role-based access and full audit trail

## Project Structure

```
brangay-profiling-system/
├── main.py                      # Application entry point
├── requirements.txt             # Python dependencies
├── config.py                    # App configuration (DB path, app name, version)
├── database/
│   ├── db.py                    # SQLAlchemy engine, session factory, init
│   ├── models.py                # All ORM models
│   └── seed.py                  # Seed 182 barangays, 3 districts, default admin
├── auth/
│   ├── auth_manager.py          # Login, logout, password hashing, current session
│   └── roles.py                 # Role enum, permission checks
├── ui/
│   ├── app.py                   # Main CTk window, sidebar, content frame switching
│   ├── theme.py                 # Color palette, fonts, spacing constants
│   ├── components/
│   │   ├── sidebar.py           # Collapsible sidebar navigation
│   │   ├── data_table.py        # Reusable sortable/filterable table widget
│   │   ├── form_fields.py       # Reusable form input widgets (text, dropdown, number)
│   │   ├── search_bar.py        # Search input with filter dropdowns
│   │   └── stat_card.py         # Summary statistic card widget
│   ├── views/
│   │   ├── login_view.py        # Login screen
│   │   ├── dashboard_view.py    # Dashboard with summary cards
│   │   ├── barangay_list_view.py # Searchable list of all 182 barangays
│   │   ├── barangay_profile_view.py # Tabbed profile for a single barangay
│   │   ├── data_entry_view.py   # Data entry forms
│   │   ├── user_mgmt_view.py    # User CRUD (admin only)
│   │   └── audit_log_view.py    # Audit log viewer (admin only)
│   └── dialogs/
│       ├── confirm_dialog.py    # Yes/No confirmation
│       └── message_dialog.py    # Info/error message
├── services/
│   ├── barangay_service.py      # Barangay CRUD + queries
│   ├── population_service.py    # Population data CRUD
│   ├── economic_service.py      # Income & business data CRUD
│   ├── infrastructure_service.py # Utilities, land, waste CRUD
│   ├── community_service.py     # Food, religion, gov facilities CRUD
│   ├── user_service.py          # User CRUD
│   ├── audit_service.py         # Audit log write + query
│   └── report_service.py        # Aggregation queries for summaries
├── utils/
│   ├── logger.py                # Python logging config
│   ├── validators.py            # Input validation helpers
│   └── export.py                # CSV/PDF export (Phase 2, stub for now)
└── data/
    └── davao_barangays.json     # Static reference: 182 barangays with districts
```

## Dependencies

```
customtkinter>=5.2.0
sqlalchemy>=2.0
bcrypt>=4.0
pillow>=10.0
matplotlib>=3.8
```

## Database Schema

### Users & Authentication

**users**
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| username | VARCHAR(50) UNIQUE | Login identifier |
| password_hash | VARCHAR(255) | bcrypt hash |
| full_name | VARCHAR(100) | Display name |
| role | VARCHAR(20) | admin / encoder / viewer |
| is_active | BOOLEAN | Soft delete flag |
| created_at | DATETIME | Auto-set |
| updated_at | DATETIME | Auto-set |

**audit_log**
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| user_id | INTEGER FK | Who made the change |
| action | VARCHAR(20) | CREATE / UPDATE / DELETE |
| table_name | VARCHAR(50) | Which table was affected |
| record_id | INTEGER | Which record was affected |
| old_values | TEXT (JSON) | Previous state (null for CREATE) |
| new_values | TEXT (JSON) | New state (null for DELETE) |
| timestamp | DATETIME | When the change occurred |

### Geography

**districts**
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| name | VARCHAR(100) | e.g., "1st Congressional District" |
| description | TEXT | Optional notes |

**barangays**
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| district_id | INTEGER FK | References districts |
| name | VARCHAR(100) | Barangay name |
| latitude | FLOAT | GPS coordinate |
| longitude | FLOAT | GPS coordinate |
| area_sqkm | FLOAT | Area in square kilometers |
| classification | VARCHAR(20) | urban / rural |
| created_at | DATETIME | Auto-set |
| updated_at | DATETIME | Auto-set |

### Population & Demographics

**population_records**
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| barangay_id | INTEGER FK | References barangays |
| year | INTEGER | Data collection year |
| total_population | INTEGER | Total head count |
| male_count | INTEGER | |
| female_count | INTEGER | |
| registered_voters | INTEGER | |
| non_registered_residents | INTEGER | |
| foreign_residents | INTEGER | |
| household_count | INTEGER | |
| created_at | DATETIME | Auto-set |
| updated_at | DATETIME | Auto-set |

UNIQUE constraint on (barangay_id, year).

**age_demographics**
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| population_record_id | INTEGER FK | References population_records |
| age_group | VARCHAR(20) | e.g., "0-4", "5-9", ..., "80+" |
| male_count | INTEGER | |
| female_count | INTEGER | |
| created_at | DATETIME | Auto-set |
| updated_at | DATETIME | Auto-set |

### Resident Categories

**resident_categories**
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| barangay_id | INTEGER FK | References barangays |
| year | INTEGER | Data collection year |
| renters_count | INTEGER | |
| homeowners_count | INTEGER | |
| squatters_count | INTEGER | |
| informal_settlers_count | INTEGER | |
| created_at | DATETIME | Auto-set |
| updated_at | DATETIME | Auto-set |

UNIQUE constraint on (barangay_id, year).

### Economic Data

**income_data**
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| barangay_id | INTEGER FK | References barangays |
| year | INTEGER | Data collection year |
| average_household_income | FLOAT | In PHP |
| below_poverty_count | INTEGER | Households below poverty line |
| low_income_count | INTEGER | |
| middle_income_count | INTEGER | |
| high_income_count | INTEGER | |
| created_at | DATETIME | Auto-set |
| updated_at | DATETIME | Auto-set |

UNIQUE constraint on (barangay_id, year).

**businesses**
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| barangay_id | INTEGER FK | References barangays |
| name | VARCHAR(200) | Business name |
| type | VARCHAR(100) | Category (retail, food, services, etc.) |
| is_active | BOOLEAN | Still operating |
| registered_date | DATE | When registered |
| created_at | DATETIME | Auto-set |
| updated_at | DATETIME | Auto-set |

### Infrastructure & Utilities

**utilities**
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| barangay_id | INTEGER FK | References barangays |
| year | INTEGER | |
| water_source | VARCHAR(100) | e.g., DCWD, deep well, spring |
| water_coverage_pct | FLOAT | 0-100 |
| power_provider | VARCHAR(100) | e.g., DLPC |
| power_coverage_pct | FLOAT | 0-100 |
| internet_coverage_pct | FLOAT | 0-100 |
| created_at | DATETIME | Auto-set |
| updated_at | DATETIME | Auto-set |

UNIQUE constraint on (barangay_id, year).

**land_types**
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| barangay_id | INTEGER FK | References barangays |
| type | VARCHAR(50) | residential / commercial / agricultural / industrial |
| area_sqkm | FLOAT | |
| percentage | FLOAT | Of total barangay area |
| created_at | DATETIME | Auto-set |
| updated_at | DATETIME | Auto-set |

**waste_management**
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| barangay_id | INTEGER FK | References barangays |
| year | INTEGER | |
| collection_frequency | VARCHAR(50) | daily / weekly / bi-weekly |
| disposal_method | VARCHAR(100) | landfill / recycling / composting |
| coverage_pct | FLOAT | 0-100 |
| created_at | DATETIME | Auto-set |
| updated_at | DATETIME | Auto-set |

UNIQUE constraint on (barangay_id, year).

### Community

**food_sources**
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| barangay_id | INTEGER FK | References barangays |
| type | VARCHAR(50) | market / farm / fishing / imported |
| description | TEXT | Additional details |
| created_at | DATETIME | Auto-set |
| updated_at | DATETIME | Auto-set |

**government_facilities**
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| barangay_id | INTEGER FK | References barangays |
| agency_name | VARCHAR(200) | e.g., PNP, BFP, DSWD |
| facility_type | VARCHAR(100) | police station, fire station, health center, etc. |
| address | TEXT | |
| created_at | DATETIME | Auto-set |
| updated_at | DATETIME | Auto-set |

**religious_demographics**
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| barangay_id | INTEGER FK | References barangays |
| year | INTEGER | |
| religion | VARCHAR(100) | Catholic, Islam, INC, Protestant, etc. |
| count | INTEGER | Number of adherents |
| percentage | FLOAT | Of total barangay population |
| created_at | DATETIME | Auto-set |
| updated_at | DATETIME | Auto-set |

## Authentication & Authorization

### Password Handling
- Passwords hashed with bcrypt (12 rounds)
- Default admin account created on first run: username `admin`, password `admin123` (must change on first login)
- Minimum password length: 8 characters

### Session Management
- Current user stored in-memory (singleton `AuthManager`)
- Session lasts until app close or explicit logout
- No token-based auth needed (desktop app, not web)

### Roles & Permissions

| Action | Admin | Encoder | Viewer |
|--------|-------|---------|--------|
| View all barangay data | Yes | Yes | Yes |
| Enter new data | Yes | Yes | No |
| Edit existing data | Yes | Yes | No |
| Delete records | Yes | No | No |
| Manage users | Yes | No | No |
| View audit log | Yes | No | No |
| Generate reports | Yes | Yes | Yes |
| Export data | Yes | Yes | Yes |

Permission checks implemented as decorators/guards in the service layer.

## User Interface Design

### Theme
- CustomTkinter dark/light mode toggle
- Primary color: Blue (#1E88E5) for government/official feel
- Accent color: Green (#43A047) for success states
- Clean, professional aesthetic suitable for government use
- Font: System default, 13px base size

### Layout
```
+--------------------------------------------------+
| [App Logo] Davao Barangay Profiling    [User] [Logout] |
+----------+---------------------------------------+
|          |                                       |
| Dashboard|   [ Content Area ]                    |
| Barangays|                                       |
| Data Entry|  Dynamically switches based on       |
| Reports  |  selected sidebar item                |
| ---------|                                       |
| Users    |                                       |
| Audit Log|                                       |
|          |                                       |
+----------+---------------------------------------+
```

### Login View
- Centered card with username, password fields, and login button
- Error message display for invalid credentials
- App title and version displayed

### Dashboard View
- Top row: 4 stat cards (Total Population, Total Barangays, Total Households, Active Users)
- Middle: Quick summary per district (3 columns)
- Bottom: Recent data entry activity feed

### Barangay List View
- Search bar at top (search by name)
- Filter dropdowns: District, Classification (urban/rural)
- Table columns: Name, District, Population (latest), Classification, Last Updated
- Click row to open Barangay Profile

### Barangay Profile View
- Header: Barangay name, district, classification badge
- Tabbed interface with tabs:
  - **Overview** — key stats summary, location coordinates
  - **Population** — population records by year, age demographics table
  - **Residents** — renters, homeowners, squatters, informal settlers
  - **Economic** — income data, business list
  - **Infrastructure** — utilities, land types, waste management
  - **Community** — food sources, government facilities, religious demographics
- Each tab shows data in tables with "Add/Edit" buttons (hidden for Viewer role)

### Data Entry View
- Dropdown to select barangay and data year
- Category tabs matching the profile sections
- Form fields with validation (required fields, numeric ranges, percentages 0-100)
- Save button with confirmation dialog
- All saves trigger audit log entries

### User Management View (Admin only)
- Table of all users with columns: Username, Full Name, Role, Status, Created
- Add User button opens form dialog
- Edit/Deactivate buttons per row
- Cannot deactivate own account

### Audit Log View (Admin only)
- Date range filter
- User filter dropdown
- Action type filter (CREATE/UPDATE/DELETE)
- Table filter dropdown
- Results table: Timestamp, User, Action, Table, Record, Details (expandable)

## Audit Trail System

Every CREATE, UPDATE, and DELETE operation on any data table (except audit_log itself) is logged:

1. Service layer calls `audit_service.log()` after each DB operation
2. For UPDATE: captures both old and new values as JSON
3. For DELETE: captures the deleted record's values
4. For CREATE: captures the new record's values
5. Audit records are immutable — no UPDATE or DELETE on audit_log table
6. Queryable by date range, user, action type, and table

## Seed Data

On first run, the system seeds:
- 3 congressional districts of Davao City
- All 182 barangays mapped to their correct districts
- 1 default admin user (username: `admin`, password: `admin123`)

The barangay list is stored in `data/davao_barangays.json` and loaded by `database/seed.py`.

## Data Integrity & Reliability

- SQLite WAL mode enabled for safe concurrent reads
- All write operations wrapped in transactions
- Foreign key constraints enforced (`PRAGMA foreign_keys = ON`)
- Input validation at both UI and service layers
- Unique constraints on (barangay_id, year) for yearly data tables to prevent duplicates
- Soft delete for users (is_active flag) to preserve audit trail references

## Verification Plan

1. **App launches** — `python main.py` opens the login window
2. **Login works** — default admin can log in, incorrect password shows error
3. **Navigation** — all sidebar items switch views correctly, role-based items hidden for non-admins
4. **Seed data** — all 182 barangays visible in list, grouped by 3 districts
5. **Data entry** — can enter population data for a barangay, validation catches bad input
6. **Audit trail** — after data entry, audit log shows the creation event with correct details
7. **User management** — admin can create encoder/viewer users, new users can log in with correct permissions
8. **Search/filter** — barangay list search and filter work correctly

## Future Phases (Out of Scope for Phase 1)

- **Phase 2:** Report generation, PDF/CSV export
- **Phase 3:** Dashboard charts, district comparisons, trends
- **Phase 4:** Crime & risk analytics, predictive models
- **Phase 5:** Geographic mapping and visualization
- **Phase 6:** Monitoring, automated backups, reliability features
