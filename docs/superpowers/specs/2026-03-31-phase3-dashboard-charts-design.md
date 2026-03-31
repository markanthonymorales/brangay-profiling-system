# Phase 3: Dashboard Charts & Analytics — Design Specification

## Context

Phases 1-2 delivered data collection, reports, and PDF/CSV export. Phase 3 adds visual analytics — embedded matplotlib charts on the dashboard and a dedicated Analytics view for trend exploration and district comparisons.

## Scope

- Embed matplotlib charts into CustomTkinter using `FigureCanvasTkAgg`
- Enhance Dashboard with a population-by-district bar chart
- New Analytics view with 4 chart tabs: Population Trends, District Comparison, Income Distribution, Utility Coverage
- New analytics data service for chart-specific queries

## No New Dependencies

matplotlib and its backend (`matplotlib.backends.backend_tkagg`) are already installed from Phase 1.

## Files to Create

| File | Purpose |
|------|---------|
| `ui/components/chart_widget.py` | Reusable widget wrapping matplotlib Figure into CTk frame |
| `ui/views/analytics_view.py` | Full analytics view with 4 tabbed chart pages |
| `services/analytics_service.py` | Chart-specific data aggregation queries |

## Files to Modify

| File | Change |
|------|--------|
| `ui/views/dashboard_view.py` | Add population-by-district bar chart below stat cards |
| `ui/app.py` | Add "analytics" to `_create_view()` dispatch |
| `ui/components/sidebar.py` | Add Analytics nav item between Reports and admin section |

## Chart Widget (ui/components/chart_widget.py)

Reusable component that embeds a matplotlib figure into a CustomTkinter frame:

```python
class ChartWidget(ctk.CTkFrame):
    def __init__(self, master, figsize=(6, 4), **kwargs)
    def update_chart(self, draw_func: Callable[[Figure, Axes], None])
    def clear(self)
```

- `draw_func` receives a `(fig, ax)` tuple and draws onto them
- Widget handles canvas creation, figure cleanup, and re-rendering
- Uses `FigureCanvasTkAgg` from `matplotlib.backends.backend_tkagg`
- Sets figure facecolor to match app background for seamless integration
- Non-interactive (no toolbar needed)

## Analytics Service (services/analytics_service.py)

### get_population_by_district() -> list[dict]

Returns population totals per district for the latest year:
```python
[{"district_name": str, "total_population": int}, ...]
```

### get_population_trend(barangay_id: int | None, district_id: int | None) -> list[dict]

Year-over-year population for a specific barangay or district:
```python
[{"year": int, "total_population": int, "male_count": int, "female_count": int}, ...]
```
If both are None, returns city-wide trend.

### get_district_comparison() -> list[dict]

All 3 districts compared on multiple metrics:
```python
[{
    "district_name": str,
    "total_population": int,
    "avg_income": float,
    "avg_water_coverage": float,
    "avg_power_coverage": float,
    "avg_internet_coverage": float,
    "active_businesses": int,
}, ...]
```

### get_income_distribution(barangay_id: int) -> dict

Income bracket breakdown for a single barangay (latest year):
```python
{
    "barangay_name": str,
    "year": int,
    "below_poverty": int,
    "low_income": int,
    "middle_income": int,
    "high_income": int,
}
```

### get_utility_coverage_by_district() -> list[dict]

Average utility coverage per district:
```python
[{
    "district_name": str,
    "water_coverage": float,
    "power_coverage": float,
    "internet_coverage": float,
}, ...]
```

## Dashboard Enhancement (dashboard_view.py)

Add a population-by-district bar chart between the stat cards row and the bottom row:

- Compact chart (figsize ~6x3) showing 3 bars (one per district)
- Blue bars with district names on x-axis, population on y-axis
- Title: "Population by District"
- Refreshes on `refresh()` along with existing stat cards

## Analytics View (ui/views/analytics_view.py)

### Layout

```
+--------------------------------------------------+
| Analytics                                        |
+--------------------------------------------------+
| [Population Trends] [District Comparison] [Income] [Utilities] |
|                                                  |
| [Tab Content - varies per tab]                   |
|                                                  |
|   [Selectors if needed]                          |
|   [Chart Area]                                   |
|                                                  |
+--------------------------------------------------+
```

### Tab 1: Population Trends

- Selector: Radio buttons for "City-Wide" / "By District" / "By Barangay"
- If by district: district dropdown
- If by barangay: district dropdown → barangay dropdown
- "Update Chart" button
- Line chart with years on x-axis, population on y-axis
- Two lines: male (blue) and female (pink), with total as bar/area background
- Legend and grid

### Tab 2: District Comparison

- No selectors needed (always shows all 3 districts)
- Grouped bar chart: 3 groups (one per district), bars for population, avg income, utility coverage
- Since metrics have different scales, use two sub-charts stacked vertically:
  - Top: Population + Businesses (counts)
  - Bottom: Utility coverages (percentages 0-100)

### Tab 3: Income Distribution

- Selector: district dropdown → barangay dropdown
- "Update Chart" button
- Donut/pie chart showing income bracket proportions (below poverty, low, middle, high)
- Color-coded: red for below poverty, orange for low, blue for middle, green for high
- Shows "No income data" message if no data exists

### Tab 4: Utility Coverage

- No selectors needed
- Grouped bar chart: 3 districts, 3 bars each (water, power, internet)
- Y-axis: 0-100%
- Color-coded: blue for water, yellow for power, green for internet

## Sidebar Update

Add "Analytics" nav item:
```python
("analytics", "Analytics", "\U0001F4C8"),
```
Positioned after "Reports" and before the admin separator.

## Verification Plan

1. Dashboard loads with population bar chart showing 3 district bars
2. Analytics view opens from sidebar
3. Population Trends tab: select a barangay with data → line chart renders
4. District Comparison tab: grouped bars show for all 3 districts
5. Income Distribution tab: select barangay → donut chart renders (or "no data" message)
6. Utility Coverage tab: grouped bars show water/power/internet per district
7. Charts re-render cleanly when switching tabs or updating selectors
8. Empty data: charts show graceful "No data" messages, no crashes
