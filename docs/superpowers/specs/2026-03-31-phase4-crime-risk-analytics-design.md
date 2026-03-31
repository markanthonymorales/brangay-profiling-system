# Phase 4: Crime & Risk Analytics — Design Specification

## Context

Phases 1-3 delivered data collection, reports, exports, and visual analytics. Phase 4 adds crime and traffic incident tracking, high-risk area identification, and predictive trend projection. This directly supports the system goal of identifying high-risk areas and generating actionable insights for public safety.

## Scope

- 2 new database models: crime_incidents, traffic_incidents
- Crime & traffic incident CRUD with audit logging
- Crime/traffic analytics: stats by type/severity, trend lines, high-risk ranking
- Simple linear regression for crime trend forecasting (numpy)
- New "Crime & Safety" sidebar view with 5 tabs

## No New Dependencies

numpy ships with matplotlib (already installed). No additional packages needed.

## Database Models

### crime_incidents

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| barangay_id | INTEGER FK | References barangays |
| crime_type | VARCHAR(50) | theft, assault, robbery, drugs, homicide, vandalism, fraud, domestic_violence, other |
| severity | VARCHAR(20) | low / medium / high / critical |
| date_occurred | DATE | When the crime happened |
| status | VARCHAR(20) | reported / under_investigation / resolved |
| description | TEXT | Optional notes |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### traffic_incidents

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Auto-increment |
| barangay_id | INTEGER FK | References barangays |
| incident_type | VARCHAR(50) | accident, congestion, road_hazard, pedestrian, hit_and_run, other |
| severity | VARCHAR(20) | low / medium / high / critical |
| date_occurred | DATE | |
| status | VARCHAR(20) | reported / under_investigation / resolved |
| description | TEXT | Optional notes |
| created_at | DATETIME | |
| updated_at | DATETIME | |

## Constants

```python
CRIME_TYPES = ["theft", "assault", "robbery", "drugs", "homicide", "vandalism", "fraud", "domestic_violence", "other"]
TRAFFIC_TYPES = ["accident", "congestion", "road_hazard", "pedestrian", "hit_and_run", "other"]
SEVERITY_LEVELS = ["low", "medium", "high", "critical"]
INCIDENT_STATUSES = ["reported", "under_investigation", "resolved"]
```

## Files to Create

| File | Purpose |
|------|---------|
| `services/crime_service.py` | Crime & traffic CRUD, analytics queries, forecasting |
| `ui/views/crime_view.py` | Crime & Safety view with 5 tabs |

## Files to Modify

| File | Change |
|------|--------|
| `database/models.py` | Add CrimeIncident and TrafficIncident models |
| `ui/components/sidebar.py` | Add "Crime & Safety" nav item |
| `ui/app.py` | Add crime view to navigation dispatch |

## Crime Service (services/crime_service.py)

### CRUD Operations

- `save_crime_incident(barangay_id, data, user_id)` — create/update crime incident
- `delete_crime_incident(incident_id, user_id)` — delete with audit
- `get_crime_incidents(barangay_id, filters)` — list with optional type/severity/status/date filters
- `save_traffic_incident(barangay_id, data, user_id)` — create/update traffic incident
- `delete_traffic_incident(incident_id, user_id)` — delete with audit
- `get_traffic_incidents(barangay_id, filters)` — list with filters

### Analytics Queries

- `get_crime_stats(barangay_id=None, district_id=None)` — counts by type and severity
- `get_traffic_stats(barangay_id=None, district_id=None)` — counts by type and severity
- `get_crime_trend(barangay_id=None, district_id=None)` — monthly crime counts for trend chart
- `get_traffic_trend(barangay_id=None, district_id=None)` — monthly traffic counts
- `get_high_risk_barangays(risk_type="crime"|"traffic", limit=20)` — barangays ranked by incident count (last 12 months)
- `get_crime_forecast(barangay_id=None, district_id=None, months_ahead=6)` — linear regression projection

### Forecast Algorithm

```python
def get_crime_forecast(barangay_id, district_id, months_ahead=6):
    # 1. Get monthly crime counts for past data
    # 2. If fewer than 3 data points, return empty (not enough data)
    # 3. Use numpy polyfit (degree=1) for linear regression
    # 4. Project forward `months_ahead` months
    # 5. Return historical + projected data points
    # Returns: {"historical": [...], "forecast": [...], "trend": "increasing"|"decreasing"|"stable"}
```

## Crime & Safety View (ui/views/crime_view.py)

### Layout

5 tabs in a CTkTabview:

### Tab 1: Crime Incidents

- Filter bar: barangay dropdown, crime type, severity, status, date range
- Data table showing incidents
- "Add Incident" button → dialog with: barangay, crime type, severity, date, status, description
- Edit/delete on row click (admin only for delete)

### Tab 2: Traffic Incidents

- Same layout as Crime Incidents but for traffic data
- Filter by traffic incident type instead of crime type

### Tab 3: Crime Overview

- Selector: scope (city-wide / by district / by barangay)
- Charts:
  - Bar chart: crime count by type
  - Pie chart: severity distribution
  - Line chart: monthly crime trend

### Tab 4: High-Risk Areas

- Toggle: Crime / Traffic
- Ranked table: top 20 barangays by incident count (last 12 months)
- Color-coded severity column (red=critical, orange=high, yellow=medium)
- Shows: rank, barangay name, district, incident count, most common type, dominant severity

### Tab 5: Forecast

- Selector: scope (by district / by barangay)
- Line chart: historical monthly crime count (solid blue) + forecast (dashed red)
- Text summary: "Trend: Increasing/Decreasing/Stable" with projected count
- Minimum 3 months of historical data required; shows "Insufficient data" otherwise

## Sidebar Update

Add between "Analytics" and admin separator:
```python
("crime", "Crime & Safety", "\U0001F6E1"),
```

## Verification Plan

1. Add crime incidents for multiple barangays via the Incidents tab
2. Add traffic incidents for multiple barangays
3. Crime Overview charts render correctly (bar, pie, trend line)
4. High-Risk Areas tab shows ranked barangays with correct counts
5. Forecast tab shows projected trend line (need 3+ months of data)
6. Audit log captures all incident CRUD operations
7. Filter/search works on both incident tables
8. Empty state: graceful "no data" messages, no crashes
