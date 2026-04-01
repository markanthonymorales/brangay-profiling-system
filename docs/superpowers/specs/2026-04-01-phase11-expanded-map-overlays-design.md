# Phase 11: Expanded Map Overlays — Design Specification

## Context

Milestone 1 map had 4 overlays (district, crime risk, population, all markers). Phase 11 adds 4 more for traffic, waste, business activity, and infrastructure coverage — totaling 8 overlay modes.

## What Was Built

### New Overlay Modes (4 added)

| Overlay | Color Scheme | Data Source |
|---------|-------------|-------------|
| By Traffic Risk | green(0) → yellow(1-3) → orange(4-8) → red(9+) | TrafficIncident count (12 months) |
| By Waste Coverage | red(<50%) → orange(50-70%) → yellow(70-85%) → green(85%+) | WasteManagement.coverage_pct |
| By Business Activity | grey(0) → light blue(<5) → blue(5-15) → dark blue(15+) | Business active count |
| By Infrastructure | red(<60%) → orange(60-75%) → yellow(75-90%) → green(90%+) | Average of water/power/internet % |

### Full Overlay List (8 total)
1. By District (blue/green/orange per congressional district)
2. By Crime Risk (green→red by crime incident count)
3. By Population (grey→dark blue by population size)
4. All Markers (uniform blue)
5. By Traffic Risk (green→red by traffic incident count)
6. By Waste Coverage (red→green by waste collection %)
7. By Business Activity (grey→dark blue by active business count)
8. By Infrastructure (red→green by avg utility coverage %)

### Map Marker Data
`get_map_markers()` now returns per barangay:
- `traffic_count` — TrafficIncident count (last 12 months)
- `waste_coverage` — latest WasteManagement.coverage_pct
- `business_count` — active Business count
- `utility_avg` — average of water/power/internet coverage %

## Files Modified
- `services/map_service.py` — expanded `get_map_markers()` with 4 new fields
- `ui/views/map_view.py` — 4 new overlay modes, 4 new color helper functions
