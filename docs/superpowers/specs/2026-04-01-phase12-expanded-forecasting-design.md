# Phase 12: Expanded Forecasting — Design Specification

## Context

Milestone 1 only had crime trend forecasting (linear regression). Phase 12 expands forecasting to population growth, utility demand, and infrastructure needs — enabling long-term planning for housing, schools, healthcare, and utilities.

## What Was Built

### Forecast Service
`services/forecast_service.py` — generic forecasting engine + domain wrappers.

**Generic Engine:**
- `forecast_metric(data_points, years_ahead=3)` — numpy polyfit (degree=1) on historical data
- Requires minimum 2 data points for projection
- Returns `{"historical": [...], "forecast": [...], "trend": "increasing"|"decreasing"|"stable"}`
- Trend threshold: slope > 0.5% of mean = increasing, < -0.5% = decreasing

**Domain Forecasts:**

| Function | Input | Output |
|----------|-------|--------|
| `forecast_population(barangay_id)` | PopulationRecord by year | Population growth projection → housing needs estimate |
| `forecast_utility_demand(barangay_id)` | Utility coverage by year | Water/power/internet demand trends |
| `forecast_infrastructure_needs(barangay_id)` | Population projections | Schools needed (1 per 5,000), health centers (1 per 10,000), housing units |

**Helper:**
- `get_all_barangays_for_forecast()` — lists barangays with enough data for forecasting

### Forecast View
`ui/views/forecast_view.py` — new sidebar item "Forecasting" with crystal ball icon.

**Layout:**
- Barangay selector (district → barangay dropdowns)
- 3 tabs:
  1. **Population** — line chart: historical population + projected 3 years, trend label
  2. **Utilities** — line chart: water/power/internet coverage trends + projections
  3. **Infrastructure** — chart showing projected needs (schools, health centers, housing)
- Each tab has "Update Chart" button and trend indicator (color-coded)

## Files Created
- `services/forecast_service.py`
- `ui/views/forecast_view.py`

## Files Modified
- `ui/components/sidebar.py` — "Forecasting" nav item with crystal ball icon
- `ui/app.py` — forecast view dispatch
