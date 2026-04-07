# Milestone 3 Sub-Project 1: Multi-Department Data Integration

**Date:** 2026-04-07
**Scope:** Phases 17-19 — New department data models, services, views, and cross-department sync
**Approach:** Phased Build (Phase 17: models+services+seed → Phase 18: views → Phase 19: sync+notifications)

## Context

The barangay profiling system currently covers population, economics, infrastructure, community resources, and crime/safety data across 182 barangays in 3 districts. Milestone 3 transforms it into a fully integrated city intelligence platform. This first sub-project establishes the data foundation by adding 4 new government department domains (Health, Disaster, Education, Business Permits) with full CRUD, cross-department sync, and automated alert generation.

This builds on the existing service-layer architecture (18 models, 24 services, 18 views) without changing any existing functionality.

---

## Phase 17: New Models + Services + Seed Data

### 17.1 Data Models (9 new tables in `database/models.py`)

All models use `TimestampMixin`, `Base`, `ForeignKey("barangays.id")`. Summary-level tables have `UniqueConstraint("barangay_id", "year")`.

#### HealthStatistics (summary-level)

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK, autoincrement |
| barangay_id | Integer | FK → barangays.id, NOT NULL |
| year | Integer | NOT NULL |
| dengue_cases | Integer | nullable |
| tuberculosis_cases | Integer | nullable |
| covid_cases | Integer | nullable |
| diarrhea_cases | Integer | nullable |
| pneumonia_cases | Integer | nullable |
| hypertension_cases | Integer | nullable |
| diabetes_cases | Integer | nullable |
| other_disease_cases | Integer | nullable |
| vaccination_coverage_pct | Float | nullable, 0-100 |
| hospital_count | Integer | nullable |
| clinic_count | Integer | nullable |
| health_worker_count | Integer | nullable |
| maternal_mortality | Integer | nullable |
| infant_mortality | Integer | nullable |
| malnutrition_rate | Float | nullable, 0-100 |

Unique: `(barangay_id, year)`

#### SocialWelfareData (summary-level)

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK, autoincrement |
| barangay_id | Integer | FK → barangays.id, NOT NULL |
| year | Integer | NOT NULL |
| fourps_beneficiaries | Integer | nullable |
| senior_citizen_count | Integer | nullable |
| pwd_count | Integer | nullable |
| solo_parent_count | Integer | nullable |
| indigent_families | Integer | nullable |
| nutrition_program_beneficiaries | Integer | nullable |

Unique: `(barangay_id, year)`

#### DisasterRiskProfile (summary-level)

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK, autoincrement |
| barangay_id | Integer | FK → barangays.id, NOT NULL |
| year | Integer | NOT NULL |
| flood_prone | Boolean | NOT NULL, default False |
| landslide_prone | Boolean | NOT NULL, default False |
| fire_risk_level | String(20) | nullable (low/medium/high) |
| earthquake_risk | String(20) | nullable (low/medium/high) |
| storm_surge_risk | String(20) | nullable (low/medium/high) |
| evacuation_center_count | Integer | nullable |
| evacuation_capacity | Integer | nullable (persons) |

Unique: `(barangay_id, year)`

#### DisasterIncident (individual records)

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK, autoincrement |
| barangay_id | Integer | FK → barangays.id, NOT NULL |
| disaster_type | String(50) | NOT NULL (flood/fire/earthquake/typhoon/landslide/storm_surge) |
| severity | String(20) | NOT NULL, default "low" (low/medium/high/critical) |
| date_occurred | Date | NOT NULL |
| affected_families | Integer | nullable |
| casualties | Integer | nullable |
| damages_estimated | Float | nullable (PHP) |
| status | String(20) | NOT NULL, default "reported" (reported/responding/resolved/recovery) |
| response_team | String(200) | nullable |
| description | Text | nullable |

#### EmergencyResource (individual records)

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK, autoincrement |
| barangay_id | Integer | FK → barangays.id, NOT NULL |
| resource_type | String(50) | NOT NULL (food/water/medicine/shelter/equipment) |
| name | String(200) | NOT NULL |
| quantity | Float | nullable |
| unit | String(50) | nullable (packs/liters/boxes/units/persons/kg) |
| location_description | Text | nullable |
| last_restocked | Date | nullable |
| expiry_date | Date | nullable |

#### EducationStatistics (summary-level)

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK, autoincrement |
| barangay_id | Integer | FK → barangays.id, NOT NULL |
| year | Integer | NOT NULL |
| total_enrollees | Integer | nullable |
| elementary_count | Integer | nullable |
| highschool_count | Integer | nullable |
| college_count | Integer | nullable |
| out_of_school_youth | Integer | nullable |
| literacy_rate | Float | nullable, 0-100 |
| school_count | Integer | nullable |
| teacher_count | Integer | nullable |
| classroom_count | Integer | nullable |
| dropout_rate | Float | nullable, 0-100 |

Unique: `(barangay_id, year)`

#### BusinessPermit (individual records)

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK, autoincrement |
| barangay_id | Integer | FK → barangays.id, NOT NULL |
| business_name | String(200) | NOT NULL |
| owner_name | String(200) | NOT NULL |
| business_type | String(100) | nullable |
| permit_number | String(50) | nullable, UNIQUE |
| date_issued | Date | nullable |
| date_expiry | Date | nullable |
| status | String(20) | NOT NULL, default "active" (active/expired/revoked/pending) |
| annual_revenue | Float | nullable |
| employee_count | Integer | nullable |
| address | Text | nullable |

#### DepartmentDataSync (tracking)

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK, autoincrement |
| department_name | String(100) | NOT NULL (health/social_welfare/disaster/education/business_permits) |
| barangay_id | Integer | FK → barangays.id, NOT NULL |
| last_synced | DateTime | nullable |
| sync_status | String(20) | NOT NULL, default "pending" (pending/synced/error) |
| record_count | Integer | nullable |
| synced_by | Integer | FK → users.id, nullable |

Unique: `(department_name, barangay_id)`

#### CrossDepartmentAlert (auto-generated)

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK, autoincrement |
| barangay_id | Integer | FK → barangays.id, NOT NULL |
| alert_type | String(100) | NOT NULL |
| severity | String(20) | NOT NULL, default "warning" (info/warning/critical) |
| title | String(200) | NOT NULL |
| message | Text | nullable |
| source_tables | Text | nullable (JSON list) |
| is_resolved | Boolean | NOT NULL, default False |
| resolved_by | Integer | FK → users.id, nullable |
| resolved_at | DateTime | nullable |

### 17.2 Barangay Model Updates

Add relationship back-references to existing `Barangay` class:
- `health_statistics`, `social_welfare_data`, `disaster_risk_profiles`, `disaster_incidents`, `emergency_resources`, `education_statistics`, `business_permits`

### 17.3 BarangaySubmissionStatus Updates

Add columns to existing model:
- `health_submitted`, `social_welfare_submitted`, `disaster_submitted`, `education_submitted`, `business_permits_submitted` (all Boolean, default False)

Note: For existing databases, use ALTER TABLE to add these columns with defaults. Handle gracefully in `init_db()`.

### 17.4 Service Layer (6 new files in `services/`)

All follow the established pattern: `tuple[bool, str]` returns, `get_session()` with try/finally, `audit_service.log_action()` on writes, `history_service.record_field_changes()` on updates.

#### `services/health_service.py`

Handles HealthStatistics CRUD only. SocialWelfareData has its own service.

Constants: `DISEASE_TYPES = ["dengue", "tuberculosis", "covid", "diarrhea", "pneumonia", "hypertension", "diabetes", "other"]`

Functions:
- `save_health_statistics(barangay_id, year, data, user_id) -> tuple[bool, str]` — upsert by (barangay_id, year)
- `get_health_statistics(barangay_id) -> list[dict]` — all years for a barangay
- `get_health_stats_by_year(year, district_id=None) -> list[dict]` — for analytics
- `get_disease_trend(barangay_id=None, district_id=None) -> list[dict]` — yearly trend
- `get_health_summary(barangay_id=None, district_id=None, year=None) -> dict` — dashboard totals

#### `services/social_welfare_service.py`

Functions:
- `save_social_welfare_data(barangay_id, year, data, user_id) -> tuple[bool, str]`
- `get_social_welfare_data(barangay_id) -> list[dict]`
- `get_welfare_stats_by_year(year, district_id=None) -> list[dict]`
- `get_welfare_summary(barangay_id=None, district_id=None, year=None) -> dict`

#### `services/disaster_service.py`

Constants: `DISASTER_TYPES`, `RISK_LEVELS`, `DISASTER_SEVERITY`, `DISASTER_STATUSES`, `RESOURCE_TYPES`, `RESOURCE_UNITS`

Functions:
- `save_disaster_risk_profile(barangay_id, year, data, user_id) -> tuple[bool, str]`
- `get_disaster_risk_profiles(barangay_id) -> list[dict]`
- `save_disaster_incident(barangay_id, data, user_id) -> tuple[bool, str]` — create/update by id
- `delete_disaster_incident(incident_id, user_id) -> tuple[bool, str]`
- `get_disaster_incidents(barangay_id=None, disaster_type=None, severity=None, status=None, limit=200) -> list[dict]`
- `save_emergency_resource(barangay_id, data, user_id) -> tuple[bool, str]`
- `delete_emergency_resource(resource_id, user_id) -> tuple[bool, str]`
- `get_emergency_resources(barangay_id=None, resource_type=None, limit=200) -> list[dict]`
- `get_disaster_stats(barangay_id=None, district_id=None) -> dict`
- `get_disaster_trend(barangay_id=None, district_id=None) -> list[dict]`
- `get_high_risk_barangays_disaster(limit=20) -> list[dict]`
- `get_expiring_resources(days_ahead=30) -> list[dict]`

#### `services/education_service.py`

Functions:
- `save_education_statistics(barangay_id, year, data, user_id) -> tuple[bool, str]`
- `get_education_statistics(barangay_id) -> list[dict]`
- `get_education_stats_by_year(year, district_id=None) -> list[dict]`
- `get_education_summary(barangay_id=None, district_id=None, year=None) -> dict`
- `get_education_trend(barangay_id=None, district_id=None) -> list[dict]`

#### `services/business_permit_service.py`

Constants: `PERMIT_STATUSES`, `BUSINESS_TYPES`

Functions:
- `save_business_permit(barangay_id, data, user_id) -> tuple[bool, str]`
- `delete_business_permit(permit_id, user_id) -> tuple[bool, str]`
- `get_business_permits(barangay_id=None, business_type=None, status=None, limit=200) -> list[dict]`
- `get_permit_stats(barangay_id=None, district_id=None) -> dict`
- `get_expiring_permits(days_ahead=30) -> list[dict]`

#### `services/cross_department_service.py`

5 threshold rules:

| Rule | Condition | Severity |
|------|-----------|----------|
| disease_poverty_correlation | dengue_cases >= 10 AND poverty_pct >= 20% | warning |
| disaster_health_impact | active_disasters >= 1 AND malnutrition_rate >= 15% | critical |
| education_poverty_gap | dropout_rate >= 10% AND poverty_pct >= 15% | warning |
| resource_shortage | risk_flags >= 2 AND resource_count < 3 | critical |
| business_disaster_impact | active_disasters >= 1 AND active_permits >= 20 | warning |

Functions:
- `on_department_data_saved(department_name, barangay_id, year, user_id)` — hook called after saves
- `check_cross_department_thresholds(barangay_id, year) -> list[dict]`
- `generate_alerts(barangay_id, year, user_id) -> tuple[bool, str]`
- `resolve_alert(alert_id, user_id) -> tuple[bool, str]`
- `get_cross_department_alerts(barangay_id=None, alert_type=None, unresolved_only=False, limit=100) -> list[dict]`
- `update_sync_status(department_name, barangay_id, user_id) -> tuple[bool, str]`
- `get_sync_status(barangay_id=None, department_name=None) -> list[dict]`
- `get_cross_department_kpis(year=None) -> dict`

### 17.5 Existing File Updates

- `history_service.py` — Add 9 new entries to `TABLE_MODEL_MAP`
- `validation_service.py` — Add required fields and percentage fields for new tables
- `database/real_data.py` — Add seed functions for all new data (see Section 17.6)

### 17.6 Seed Data

All seed data in `database/real_data.py`, using realistic distributions based on Davao City statistics.

| Domain | Records | Distribution Logic |
|--------|---------|-------------------|
| HealthStatistics | ~364 (182 x 2 years) | Disease rates proportional to population; dengue higher in flood-prone; vaccination 75-95% |
| SocialWelfareData | ~364 | 4Ps ~5-15% of households (higher in low-income); seniors ~7-10% of pop |
| DisasterRiskProfile | ~182 (year 2025) | Flood-prone: coastal/river barangays (~40%); fire risk: high in dense urban |
| DisasterIncident | ~300-500 | Seasonal: floods June-Nov, typhoons Sep-Dec; distributed by risk profile |
| EmergencyResource | ~900-1400 (3-8 per brgy) | ~10% expired for realism; quantities scaled to population |
| EducationStatistics | ~364 | Enrollees ~15-25% of pop; literacy 93-99%; dropout 1-8% (higher rural) |
| BusinessPermit | ~2000-4000 | Proportional to population + urbanization; 85% active, 8% expired |
| DepartmentDataSync | 910 (5 depts x 182) | All seeded as "synced" |
| CrossDepartmentAlert | ~20-30 samples | ~60% resolved |

---

## Phase 18: Department Views (4 new sidebar views)

### 18.1 Sidebar Updates (`ui/components/sidebar.py`)

Add 4 new nav items after "Crime & Safety":
- "Health & Welfare" (health)
- "Disaster & Safety" (disaster)
- "Education" (education)
- "Business Permits" (business_permits)

### 18.2 App.py Navigation

Add 4 new cases in `_create_view` method with lazy imports.

### 18.3 View Designs

All views follow the `CrimeView` pattern: CTkFrame, CTkTabview, DataTable for lists, FormFields for CRUD, ChartWidget for analytics. Permission-guarded.

#### `ui/views/health_view.py` — HealthView (4 tabs)

1. **Health Statistics** — District/Barangay/Year selectors + DataTable + Add/Edit form (LabeledNumberEntry for counts, LabeledEntry for percentages)
2. **Social Welfare** — Same pattern for 4Ps, senior, PWD, solo parent, indigent counts
3. **Health Overview** — Charts: disease breakdown bar chart, vaccination coverage by district, mortality trends line chart
4. **High Risk Areas** — DataTable ranked by malnutrition_rate + disease burden composite

#### `ui/views/disaster_view.py` — DisasterView (5 tabs)

1. **Risk Profiles** — DataTable + form with Boolean checkboxes and risk level dropdowns
2. **Disaster Incidents** — Full CRUD with type/severity/status filters (mirrors CrimeView incident tab)
3. **Emergency Resources** — DataTable with expiry highlighting (red for expiring, bold red for expired)
4. **Disaster Overview** — Charts: incidents by type pie, monthly trend line, affected families by district bar
5. **Resource Status** — Resource coverage by type across districts, expiring resource alerts

#### `ui/views/education_view.py` — EducationView (3 tabs)

1. **Education Statistics** — DataTable + Add/Edit form
2. **Education Overview** — Charts: enrollment by level stacked bar, literacy by district, dropout trend line, OSY by district bar
3. **School Capacity** — Student-teacher and student-classroom ratio analysis

#### `ui/views/business_permit_view.py` — BusinessPermitView (3 tabs)

1. **Permits** — Full CRUD DataTable with type/status/barangay filters
2. **Permit Overview** — Charts: permits by type pie, revenue by type bar, active vs expired donut
3. **Expiring Permits** — Permits expiring within 30/60/90 days

### 18.4 Data Entry View Updates

Add summary-level data tabs to `ui/views/data_entry_view.py`:
- Health statistics tab
- Social welfare tab
- Disaster risk profile tab
- Education statistics tab

Individual records (incidents, permits, resources) are managed in their dedicated views.

---

## Phase 19: Cross-Department Sync + Notifications

### 19.1 Hook Integration

Each department service's save function calls `cross_department_service.on_department_data_saved()` after successful commit. Uses lazy import to avoid circular dependency.

Hooked save functions:
- `health_service.save_health_statistics` → department="health"
- `social_welfare_service.save_social_welfare_data` → department="social_welfare"
- `disaster_service.save_disaster_risk_profile` → department="disaster"
- `disaster_service.save_disaster_incident` → department="disaster"
- `education_service.save_education_statistics` → department="education"
- `business_permit_service.save_business_permit` → department="business_permits"

### 19.2 Sync Flow

```
Data Saved → on_department_data_saved()
  ├── 1. Update DepartmentDataSync (last_synced, sync_status="synced")
  ├── 2. check_cross_department_thresholds(barangay_id, year)
  │     ├── Query HealthStatistics, SocialWelfareData, IncomeData,
  │     │   EducationStatistics, DisasterRiskProfile, PopulationRecord,
  │     │   active DisasterIncidents, active BusinessPermits, EmergencyResources
  │     └── Evaluate 5 threshold rules → list of triggered alerts
  └── 3. For each triggered alert:
        ├── Check if unresolved alert of same type exists for barangay
        ├── If new → Create CrossDepartmentAlert record
        └── Create Notification for all ADMIN + CITY_OFFICIAL users
```

### 19.3 Dashboard Integration

Add to `ui/views/dashboard_view.py`:
- **KPI Cards:** Active Cross-Department Alerts (count, colored by severity), Departments Synced Today, Stale Data Warnings (>30 days since sync)
- **Alert Summary Table:** Recent 10 unresolved alerts (barangay, type, severity, date)

Data source: `cross_department_service.get_cross_department_kpis()` and `get_cross_department_alerts(unresolved_only=True, limit=10)`

---

## Implementation Notes

### Migration Strategy
- New tables auto-created by `Base.metadata.create_all(engine)` on startup
- New columns on `BarangaySubmissionStatus` require ALTER TABLE for existing DBs — handle in `init_db()` with try/except
- Alternatively: document that deleting DB and re-seeding is the clean path

### Circular Import Prevention
- `cross_department_service.py` imports from multiple services
- Hook calls from other services use lazy imports: `from services.cross_department_service import on_department_data_saved` inside function body

### Performance
- Cross-department threshold check queries 5-6 tables per save
- Acceptable for single-save operations on SQLite
- If bulk saves needed later, consider batching threshold checks

### Critical Files to Modify
- `database/models.py` — 9 new models + Barangay relationships + BarangaySubmissionStatus columns
- `database/real_data.py` — seed functions for all new data
- `services/history_service.py` — TABLE_MODEL_MAP updates
- `services/validation_service.py` — new required/percentage fields
- `ui/components/sidebar.py` — 4 new nav items
- `ui/app.py` — 4 new view cases in `_create_view`
- `ui/views/dashboard_view.py` — cross-department KPI cards + alert table

### Critical Files to Create
- `services/health_service.py`
- `services/social_welfare_service.py`
- `services/disaster_service.py`
- `services/education_service.py`
- `services/business_permit_service.py`
- `services/cross_department_service.py`
- `ui/views/health_view.py`
- `ui/views/disaster_view.py`
- `ui/views/education_view.py`
- `ui/views/business_permit_view.py`

### Reference Patterns
- `services/crime_service.py` — pattern for individual record CRUD services
- `services/population_service.py` — pattern for summary-level upsert services
- `ui/views/crime_view.py` — pattern for multi-tab views with charts and CRUD

---

## Verification

### Phase 17 (Models + Services + Seed)
1. Delete `data/barangay_profiling.db`
2. Run `python main.py` — verify all 27 tables created (18 existing + 9 new)
3. Check seed data: query each new table for expected record counts
4. Test each service function via Python console

### Phase 18 (Views)
1. Run application, verify 4 new sidebar entries appear
2. Navigate to each view — verify tabs load without errors
3. Test CRUD: add, edit, delete records in each view
4. Verify charts render with seed data
5. Test permission guards: viewer role cannot add/edit/delete

### Phase 19 (Sync + Notifications)
1. Save health data for a high-poverty barangay with high dengue — verify alert generated
2. Check Notifications view for cross-department alerts
3. Check Dashboard for new KPI cards and alert summary
4. Resolve an alert — verify it disappears from unresolved list
5. Test all 5 threshold rules trigger correctly
