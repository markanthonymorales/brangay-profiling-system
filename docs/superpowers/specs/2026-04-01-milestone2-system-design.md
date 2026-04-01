# Milestone 2: System Design Overview

## Summary

Milestone 2 transforms the Davao City Barangay Profiling System from a static reporting platform into an **advanced planning and operational decision-support system**. It introduces 7 new phases (Phases 7-13) building on the Milestone 1 foundation.

## Architecture Evolution

### Milestone 1 (Phases 1-6)
Data collection → Reports → Charts → Crime analytics → Maps → Monitoring

### Milestone 2 (Phases 7-13)
Department access → Approval workflows → Real-time dashboard → Validation & alerts → Expanded maps → Forecasting → Enhanced recommendations

## Phase Summary

| Phase | Feature | Key Deliverable |
|-------|---------|-----------------|
| 7 | Department-Based Access | 5 roles, 6 departments, scope-filtered queries |
| 8 | Approval Workflows | Submit→review→approve pipeline for data entry |
| 9 | Real-Time Dashboard | 60s auto-refresh, pending submissions indicator |
| 10 | Validation & Notifications | Cross-field validation, notification center |
| 11 | Expanded Map Overlays | 8 total overlays (traffic, waste, business, infrastructure added) |
| 12 | Expanded Forecasting | Population, utility, infrastructure projections |
| 13 | Enhanced Recommendations | Budget allocation, emergency readiness, social services, retry queue |

## New Database Models (Milestone 2)

| Model | Purpose | Key Fields |
|-------|---------|------------|
| Department | Organizational units | name, level (city/district/barangay), district_id, barangay_id |
| Submission | Approval workflow | submitted_by, reviewed_by, table_name, record_data (JSON), status |
| Notification | User alerts | user_id, type, title, message, severity, is_read |
| RetryQueue | Failed operation recovery | operation, table_name, data (JSON), attempts, status |

## New Services (Milestone 2)

| Service | Functions | Purpose |
|---------|-----------|---------|
| department_service.py | create_department, list_departments, get_user_scope, seed_default_departments | Department CRUD + scope resolution |
| submission_service.py | create_submission, approve_submission, reject_submission, list_submissions, get_pending_count | Approval workflow engine |
| validation_service.py | validate_submission | Cross-field, range, completeness checks |
| notification_service.py | create_notification, get_notifications, mark_read, get_unread_count | Alert system |
| forecast_service.py | forecast_metric, forecast_population, forecast_utility_demand, forecast_infrastructure_needs | Multi-domain forecasting |

## New Views (Milestone 2)

| View | Sidebar Item | Purpose |
|------|-------------|---------|
| submissions_view.py | Submissions | Approval queue with filter, detail dialog, approve/reject |
| notification_view.py | Notifications | Alert center with severity cards, dismiss, mark all read |
| forecast_view.py | Forecasting | 3-tab forecast view (population, utilities, infrastructure) |

## Role Hierarchy

```
admin (full access, all data)
  └── city_official (view + approve, all data)
       └── district_coordinator (enter/edit + approve, own district)
            └── encoder (enter/edit, own department scope)
                 └── viewer (read-only, own department scope)
```

## Data Flow: Submission Approval

```
Encoder fills form
    │
    ▼
create_submission()  →  status: "pending"
    │                        │
    │                        ▼
    │               Submissions Queue View
    │                        │
    ├──── approve_submission()  →  _apply_submission()  →  save to actual table + audit log
    │
    └──── reject_submission()  →  status: "rejected" + notes
```

## Map Overlay Modes (8 total)

| # | Overlay | Color Logic | Data Source |
|---|---------|-------------|-------------|
| 1 | By District | Blue/Green/Orange | district_id |
| 2 | By Crime Risk | Green→Red (0→16+) | CrimeIncident count |
| 3 | By Population | Grey→Dark Blue | PopulationRecord |
| 4 | All Markers | Uniform Blue | — |
| 5 | By Traffic Risk | Green→Red (0→9+) | TrafficIncident count |
| 6 | By Waste Coverage | Red→Green (<50%→85%+) | WasteManagement.coverage_pct |
| 7 | By Business Activity | Grey→Dark Blue (0→15+) | Business active count |
| 8 | By Infrastructure | Red→Green (<60%→90%+) | Avg utility coverage % |

## Forecasting Engine

```
forecast_metric(data_points, years_ahead=3)
    │
    ├── numpy.polyfit(degree=1)  →  linear regression
    │
    ├── slope analysis  →  trend: increasing / decreasing / stable
    │
    └── project forward N years  →  {"historical": [...], "forecast": [...], "trend": "..."}
```

**Domain Wrappers:**
- `forecast_population()` → housing needs (1 unit per 4 people)
- `forecast_utility_demand()` → water/power/internet gap projections
- `forecast_infrastructure_needs()` → schools (1 per 5,000), health centers (1 per 10,000)

## Action Plan Recommendations (Enhanced)

| Category | Recommendation Type | Trigger |
|----------|-------------------|---------|
| Public Safety | Law enforcement deployment | Crime count >= 16 |
| Public Safety | Rising crime intervention | Forecast trend = increasing |
| Public Safety | Emergency readiness score | Facility/crime/density analysis |
| Infrastructure | Water/power/internet expansion | Coverage < target % |
| Economic | Budget allocation estimate | Population * per_capita * weights |
| Economic | Business development potential | Commercial land + businesses + income |
| Community | Social services (DSWD/4Ps) | Below poverty count > 0 |
| Community | Population growth management | Growth > 5% year-over-year |

## Full Navigation (14 items + 3 admin)

**Main:**
1. Dashboard (auto-refreshing)
2. Barangays (paginated list)
3. Data Entry (permission-gated)
4. Submissions (approval queue)
5. Reports (4 types + PDF/CSV)
6. Analytics (4 chart tabs)
7. Forecasting (population/utilities/infrastructure)
8. Crime & Safety (5 tabs)
9. Action Plans (auto-generated + PDF export)
10. Map (8 overlay modes)
11. Notifications (alert center)

**Admin Only:**
12. User Management (with departments)
13. Audit Log
14. System Monitoring (backups, integrity, logs)

## Technology Stack (unchanged from Milestone 1)

- Python 3.13 + CustomTkinter
- SQLite (SQLAlchemy ORM) with WAL mode
- Matplotlib (embedded charts via FigureCanvasTkAgg)
- tkintermapview (OpenStreetMap)
- ReportLab (PDF generation with Davao City branding)
- bcrypt (password hashing)
- numpy (linear regression forecasting)
