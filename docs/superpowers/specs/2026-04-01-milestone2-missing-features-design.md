# Milestone 2 Missing Features — Design Specification

**Date**: 2026-04-01
**Status**: Approved
**Scope**: Phases 14–16 — fills gaps between the M2 vision and the existing Phase 7–13 implementation

## Context

Milestone 2 was designed to transform the Davao City Barangay Profiling System from a static reporting platform into an operational decision-support system. Phases 7–13 cover department access, approval workflows, real-time dashboards, validation, notifications, map overlays, forecasting, enhanced recommendations, and retry handling.

Six gaps remain between the M2 description and the implemented features:
1. No side-by-side barangay/district comparisons across years
2. Forecasting missing food supply, transportation, and public safety domains
3. No scheduled data collection cycles or submission tracking
4. No field-level historical change tracking (only audit log)
5. No crime-specific prevention recommendations
6. No proactive anomaly detection for missing/unusual data

These are organized into three phases by theme.

---

## Phase 14: Comparisons & Historical Tracking

### 14.1 New Model: `RecordHistory`

**File**: `database/models.py`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | Integer | PK, autoincrement | |
| table_name | String(50) | NOT NULL | Source table (e.g., "population_records") |
| record_id | Integer | NOT NULL | ID of the changed record |
| field_name | String(100) | NOT NULL | Which field changed |
| old_value | Text | nullable | Previous value (as string) |
| new_value | Text | nullable | New value (as string) |
| changed_by | Integer | FK→users.id, NOT NULL | Who made the change |
| changed_at | DateTime | NOT NULL, default=utcnow | When |

Includes `TimestampMixin`. Index on `(table_name, record_id)` for fast lookups.

### 14.2 New Service: `services/comparison_service.py`

```
compare_barangays(barangay_ids: list[int], metrics: list[str], years: list[int]) -> dict
```
- Accepts 2–4 barangay IDs, a list of metric keys, and year range
- Queries relevant tables (PopulationRecord, IncomeData, Utility, CrimeIncident counts)
- Returns `{"barangays": [{"id", "name", "metrics": {"population": {2023: X, 2024: Y}, ...}}]}`
- Metrics supported: `population`, `income`, `water_coverage`, `power_coverage`, `internet_coverage`, `crime_count`, `waste_collection_rate`

```
compare_districts(metrics: list[str], years: list[int]) -> dict
```
- Aggregates metrics across all barangays per district
- Returns same structure but with district-level data

```
year_over_year(barangay_id: int, years: list[int]) -> dict
```
- All available metrics for one barangay across specified years
- Includes `growth_pct` per metric per year pair (% change from previous year)
- Adds `trend` classification: "increasing" / "decreasing" / "stable"

### 14.3 New Service: `services/history_service.py`

```
record_field_changes(table_name: str, record_id: int, old_data: dict, new_data: dict, user_id: int) -> int
```
- Compares old_data and new_data dicts field by field
- Creates a `RecordHistory` row for each changed field
- Returns count of changes recorded
- Skips fields: `id`, `created_at`, `updated_at`

```
get_record_history(table_name: str, record_id: int) -> list[dict]
```
- Returns all changes for a record, ordered by `changed_at` desc
- Each entry: `{"field_name", "old_value", "new_value", "changed_by_name", "changed_at"}`

```
get_barangay_history(barangay_id: int, limit: int = 50) -> list[dict]
```
- Returns recent changes across all tables for a barangay
- Implementation: query RecordHistory, then for each entry look up the source record's barangay_id using a `TABLE_MODEL_MAP` dict that maps table_name → SQLAlchemy model class (e.g., `{"population_records": PopulationRecord, "income_data": IncomeData, ...}`). Filter to entries where the source record belongs to the given barangay.

### 14.4 Integration: Hook into Existing Services

In each service that updates records (`population_service`, `economic_service`, `infrastructure_service`, `crime_service`, `community_service`), before committing an update:
1. Load the existing record into a dict (`old_data`)
2. Apply changes
3. Call `record_field_changes(table_name, record.id, old_data, new_data, user_id)`
4. Commit

This is the same pattern across all services — a ~5-line addition per update function.

### 14.5 New UI: `ui/views/comparison_view.py`

4-tab CTkTabview:

**Tab 1 — "Barangay vs Barangay"**
- Multi-select combo for 2–4 barangays (CTkComboBox with checkboxes or multiple selectors)
- Metric picker (checkboxes for available metrics)
- Year range selector
- "Compare" button
- Results: side-by-side bar charts (matplotlib) + data table below

**Tab 2 — "District vs District"**
- Auto-loads 3 districts (no selector needed)
- Metric picker + year range
- Results: grouped bar charts per metric

**Tab 3 — "Year over Year"**
- Single barangay selector
- Year range
- Results: table with metrics as rows, years as columns, growth % with color (green=growth, red=decline), trend arrows

**Tab 4 — "Change History"**
- Barangay selector → table selector (dropdown: Population, Income, Utilities, etc.)
- Record selector (auto-populated based on barangay + table)
- Results: scrollable timeline of field changes with who/when/what

### 14.6 Navigation

- Add "Comparisons" to main sidebar menu (between "Analytics" and "Forecasting")
- Icon: chart comparison icon or `\U0001F4CA`
- Available to all roles (read-only feature)

---

## Phase 15: Expanded Forecasting & Crime Prevention Recommendations

### 15.1 Enhanced `services/forecast_service.py` (3 new functions)

All three reuse the existing `forecast_metric()` linear regression engine.

```
forecast_food_supply(barangay_id: int) -> dict
```
- **Data sources**: PopulationRecord (population growth), LandType (agricultural_pct), FoodSource records
- **Projections**: 3-year forward population → food demand (population × avg per-capita consumption estimate)
- **Output**: `{"historical": [...], "forecast": [...], "trend", "demand_gap": "surplus"/"deficit"/"balanced", "notes"}`
- **Demand calculation**: If agricultural land % is declining while population grows → flag deficit risk

```
forecast_transportation(barangay_id: int) -> dict
```
- **Data sources**: PopulationRecord (density), TrafficIncident (yearly counts), Business (activity indicator)
- **Projections**: Traffic congestion index = (traffic_incidents / population) × 10000, projected forward
- **Output**: `{"historical": [...], "forecast": [...], "trend", "congestion_level": "low"/"moderate"/"high"/"critical", "recommended_infrastructure": [...]}`
- **Thresholds**: congestion index >5 = moderate, >10 = high, >20 = critical

```
forecast_public_safety(barangay_id: int) -> dict
```
- **Data sources**: CrimeIncident (yearly counts), PopulationRecord, GovernmentFacility (police stations)
- **Projections**: Crime rate = (incidents / population) × 10000, projected forward
- **Output**: `{"historical": [...], "forecast": [...], "trend", "safety_level": "safe"/"moderate"/"at_risk"/"critical", "police_ratio": current vs recommended (1:500), "facility_gap": int}`
- **Thresholds**: crime rate >20 = moderate, >50 = at_risk, >100 = critical

### 15.2 Enhanced `ui/views/forecast_view.py` (3 new tabs)

Add 3 tabs after existing Infrastructure tab:

**Tab 4 — "Food Supply"**
- Barangay selector
- Chart: population projection line + food supply capacity line (from agricultural land estimates)
- Status card: demand gap indicator (surplus/deficit/balanced)
- Notes section with specific recommendations

**Tab 5 — "Transportation"**
- Barangay selector
- Chart: congestion index projection
- Status card: congestion level badge with color
- Recommended infrastructure list

**Tab 6 — "Public Safety"**
- Barangay selector
- Chart: crime rate projection
- Status card: safety level badge, police-to-population ratio
- Facility gap indicator

All three tabs follow the same layout pattern as existing forecast tabs (barangay selector → chart → summary cards).

### 15.3 Enhanced `services/plan_service.py` — Crime Prevention

New function:
```
generate_crime_prevention_plan(barangay_id: int) -> dict
```

Returns:
```python
{
    "crime_summary": {
        "total_incidents": int,
        "top_types": [{"type": str, "count": int}, ...],  # top 5
        "trend": "increasing" / "decreasing" / "stable",
        "trend_pct": float,  # % change year-over-year
    },
    "patrol_schedule": [
        {"shift": "Morning (6AM-2PM)", "priority": "high"/"medium"/"low", "focus_areas": [str]},
        {"shift": "Afternoon (2PM-10PM)", "priority": ..., "focus_areas": [...]},
        {"shift": "Night (10PM-6AM)", "priority": ..., "focus_areas": [...]},
    ],
    "cctv_recommendations": [
        {"location_desc": str, "priority": "high"/"medium", "reason": str},
        ...
    ],
    "community_programs": [
        {"name": str, "target_group": str, "description": str, "triggered_by": str},
        ...
    ],
}
```

**Logic**:
- Patrol priority based on crime time-of-day distribution (if tracked) or default to night=high
- CCTV placement: top crime areas without existing coverage
- Community programs triggered by crime type patterns:
  - Drug-related crimes → Rehabilitation referral + drug awareness programs
  - Theft/robbery → Livelihood training + economic development
  - Violence/assault → Conflict resolution + community mediation
  - Juvenile crimes → Youth engagement + after-school programs
  - General high crime → Neighborhood watch + barangay tanod strengthening

### 15.4 Enhanced `ui/views/action_plan_view.py`

Wrap existing UI in a CTkTabview:
- **Tab 1 "Action Plan"** — Move current content here (no functional changes)
- **Tab 2 "Crime Prevention"** — Barangay selector, "Generate" button, scrollable results with sections:
  - Crime Summary card (total incidents, top types, trend)
  - Patrol Schedule table (3 shifts with priority and focus areas)
  - CCTV Recommendations list (prioritized)
  - Community Programs cards (name, target group, description)

---

## Phase 16: Scheduling & Anomaly Detection

### 16.1 New Model: `DataCollectionSchedule`

**File**: `database/models.py`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | Integer | PK, autoincrement | |
| year | Integer | NOT NULL, UNIQUE | One schedule per year |
| start_date | Date | NOT NULL | Collection period start |
| end_date | Date | NOT NULL | Collection period end |
| status | String(20) | NOT NULL, default="upcoming" | upcoming / active / closed |
| created_by | Integer | FK→users.id, NOT NULL | Admin who created it |
| notes | Text | nullable | Optional notes |

Includes `TimestampMixin`.

### 16.2 New Model: `BarangaySubmissionStatus`

**File**: `database/models.py`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | Integer | PK, autoincrement | |
| barangay_id | Integer | FK→barangays.id, NOT NULL | |
| year | Integer | NOT NULL | |
| population_submitted | Boolean | NOT NULL, default=False | |
| income_submitted | Boolean | NOT NULL, default=False | |
| utilities_submitted | Boolean | NOT NULL, default=False | |
| crime_submitted | Boolean | NOT NULL, default=False | |
| waste_submitted | Boolean | NOT NULL, default=False | |
| is_complete | Boolean | NOT NULL, default=False | All required tables submitted |
| completed_at | DateTime | nullable | When all were complete |

Unique constraint on `(barangay_id, year)`. Includes `TimestampMixin`.

### 16.3 New Service: `services/schedule_service.py`

```
create_schedule(year, start_date, end_date, user_id, notes="") -> tuple[bool, str]
```
- Creates DataCollectionSchedule row
- Initializes 182 BarangaySubmissionStatus rows (one per barangay) with all flags False
- Audit logged

```
get_schedule(year=None) -> dict | None
```
- If year provided, returns that year's schedule
- If None, returns the current active schedule (status="active")

```
get_all_schedules() -> list[dict]
```
- All schedules ordered by year desc

```
update_schedule(schedule_id, **kwargs) -> tuple[bool, str]
```
- Update start_date, end_date, status, notes

```
get_compliance_dashboard(year) -> dict
```
- Returns: total_barangays, complete_count, incomplete_count, completion_rate_pct
- Per-barangay: name, district, each table's status, missing_tables list
- Sorted by district then barangay name

```
refresh_submission_status(barangay_id, year) -> None
```
- Checks actual data tables for records matching (barangay_id, year)
- Updates BarangaySubmissionStatus flags accordingly
- Sets is_complete=True and completed_at if all flags True

```
check_overdue_and_notify(user_id) -> int
```
- Finds active schedules past end_date with incomplete barangays
- Creates notifications for admin users
- Returns notification count

```
get_missing_submissions(year) -> list[dict]
```
- Returns incomplete barangays with their missing table names

### 16.4 New Service: `services/anomaly_service.py`

```
detect_all_anomalies(notify_user_id=None) -> list[dict]
```
- Runs both missing submission checks and statistical anomaly checks
- Optionally creates notifications
- Returns list of anomaly dicts

```
detect_missing_submissions(year) -> list[dict]
```
- Checks each required table for records matching (barangay_id, year)
- Returns: barangay_id, barangay_name, table_name, message

```
detect_statistical_anomalies() -> list[dict]
```
- For each barangay, for each numeric metric:
  1. Gather all historical values (minimum 3 data points)
  2. Compute mean and std_dev of all values except the latest
  3. If latest deviates > 2.0 std_devs from mean, flag as anomaly
- **Metrics checked**: total_population, average_household_income, water/power/internet coverage %, yearly crime count
- Returns: type (spike/drop), severity (warning if >2σ, error if >3σ), barangay, table, field, message, current_value, historical_mean, std_dev

```
trigger_anomaly_notifications(anomalies, admin_user_ids) -> int
```
- Creates Notification entries for each anomaly for each admin
- Returns count created

### 16.5 New UI: `ui/views/schedule_view.py` (admin-only)

2-tab CTkTabview:

**Tab 1 — "Schedules"**
- List of all yearly schedules (year, start date, end date, status) in a scrollable frame
- "Create New Schedule" form: year entry, date pickers (or text fields YYYY-MM-DD), notes
- Edit/Close buttons per schedule row

**Tab 2 — "Compliance"**
- Year selector dropdown
- Progress bar showing X of 182 barangays complete (with percentage label)
- Summary stats: complete, incomplete, completion rate
- Scrollable table: barangay name, district, checkmark/X for each data type, "Complete" badge
- Filter toggle: "Show only incomplete"
- "Send Overdue Reminders" button → creates notifications for encoders of missing barangays

### 16.6 Enhanced `ui/views/dashboard_view.py`

Add below existing bottom frame:
- **Compliance card**: Current year's collection progress bar + "X/182 complete" label
- **Anomaly alert banner**: If anomalies detected, show count with warning icon. Click to navigate to notifications.
- Anomaly detection cached, re-checked every 5th refresh (every ~5 minutes at 60s interval)

### 16.7 Integration Points

1. **`services/submission_service.py`** — After `approve_submission()` writes data, call `refresh_submission_status(barangay_id, year)`
2. **`auth/roles.py`** — Add `manage_schedules` (admin only) and `view_compliance` (admin, city_official, district_coordinator)
3. **`ui/components/sidebar.py`** — Add "Data Collection" in admin section (before "System")
4. **`ui/app.py`** — Register `schedule` view key → `ScheduleView`
5. **`config.py`** — Add `ANOMALY_CHECK_INTERVAL = 5` (run every 5th dashboard refresh)

---

## Summary of All Changes

### New Files (6)
| File | Phase | Purpose |
|------|-------|---------|
| `services/comparison_service.py` | 14 | Multi-mode comparison engine |
| `services/history_service.py` | 14 | Field-level change tracking |
| `ui/views/comparison_view.py` | 14 | Comparison UI (4 tabs) |
| `services/schedule_service.py` | 16 | Data collection cycle management |
| `services/anomaly_service.py` | 16 | Statistical anomaly detection |
| `ui/views/schedule_view.py` | 16 | Schedule & compliance UI (2 tabs) |

### Modified Files (14)
| File | Phase | Change |
|------|-------|--------|
| `database/models.py` | 14, 16 | Add RecordHistory, DataCollectionSchedule, BarangaySubmissionStatus |
| `services/forecast_service.py` | 15 | Add forecast_food_supply, forecast_transportation, forecast_public_safety |
| `services/plan_service.py` | 15 | Add generate_crime_prevention_plan |
| `ui/views/forecast_view.py` | 15 | Add 3 new tabs (Food Supply, Transportation, Public Safety) |
| `ui/views/action_plan_view.py` | 15 | Wrap in CTkTabview, add Crime Prevention tab |
| `ui/views/dashboard_view.py` | 16 | Add compliance tracker + anomaly alert banner |
| `ui/app.py` | 14, 16 | Register comparison + schedule views |
| `ui/components/sidebar.py` | 14, 16 | Add Comparisons (main) + Data Collection (admin) |
| `auth/roles.py` | 16 | Add manage_schedules + view_compliance permissions |
| `config.py` | 16 | Add ANOMALY_CHECK_INTERVAL |
| `services/submission_service.py` | 16 | Hook refresh_submission_status after approval |
| `services/population_service.py` | 14 | Add record_field_changes call |
| `services/economic_service.py` | 14 | Add record_field_changes call |
| `services/infrastructure_service.py` | 14 | Add record_field_changes call |
| `services/crime_service.py` | 14 | Add record_field_changes call |
| `services/community_service.py` | 14 | Add record_field_changes call |

### Implementation Order
1. Phase 14 models → services → integration hooks → view → navigation
2. Phase 15 forecast functions → plan function → view enhancements
3. Phase 16 models → services → view → dashboard enhancements → integration hooks → navigation

### Seed Data
- `database/seed.py` — Add initial DataCollectionSchedule for 2026 (Jan 1 – Mar 31, status="active") so the system has a working schedule out of the box.
