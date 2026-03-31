# Phase 5: Geographic Mapping & Location — Design Specification

## Context

Phases 1-4 delivered data collection, reports, charts, and crime analytics. Phase 5 adds geographic visualization — an interactive OpenStreetMap-based map embedded in the desktop app, showing all 182 barangays with multiple data overlay modes.

## Scope

- Embed interactive map using `tkintermapview` (OpenStreetMap tiles)
- 4 overlay modes: by district, by crime risk, by population, default markers
- Clickable markers with info panel
- Search/zoom to specific barangay
- Seed approximate coordinates for all 182 barangays

## New Dependency

Add `tkintermapview` to `requirements.txt`:
```
tkintermapview>=1.29
```

## Files to Create

| File | Purpose |
|------|---------|
| `services/map_service.py` | Map data queries (markers + overlay metrics) |
| `ui/views/map_view.py` | Full-page interactive map view |

## Files to Modify

| File | Change |
|------|--------|
| `requirements.txt` | Add `tkintermapview>=1.29` |
| `data/davao_barangays.json` | Add lat/lon coordinates per barangay |
| `database/seed.py` | Seed coordinates from JSON |
| `ui/components/sidebar.py` | Add "Map" nav item |
| `ui/app.py` | Add map view to navigation dispatch |

## Coordinate Seeding

Update `davao_barangays.json` to include approximate lat/lon for each barangay. Format change:

```json
{
  "districts": [
    {
      "name": "1st Congressional District",
      "barangays": [
        {"name": "1-A", "lat": 7.0660, "lon": 125.6110},
        ...
      ]
    }
  ]
}
```

Update `seed.py` to read the new format and populate `Barangay.latitude` and `Barangay.longitude`.

Davao City center: approximately lat 7.0707, lon 125.6087. Barangay coordinates are spread across roughly lat 6.95-7.25, lon 125.45-125.70.

## Map Service (services/map_service.py)

### get_map_markers(overlay: str) -> list[dict]

Returns all barangays with coordinates and overlay-specific data:

```python
[{
    "id": int,
    "name": str,
    "district_name": str,
    "district_id": int,
    "lat": float,
    "lon": float,
    "population": int | None,
    "crime_count": int,  # last 12 months
    "classification": str,
}, ...]
```

Only returns barangays that have coordinates (lat/lon not null).

### get_barangay_map_info(barangay_id: int) -> dict

Detailed info for the info panel when a marker is clicked:

```python
{
    "name": str,
    "district_name": str,
    "classification": str,
    "population": int | None,
    "households": int | None,
    "crime_count_12m": int,
    "traffic_count_12m": int,
    "top_crime_type": str | None,
    "avg_income": float | None,
    "water_coverage": float | None,
    "power_coverage": float | None,
}
```

## Map View (ui/views/map_view.py)

### Layout

```
+--------------------------------------------------+
| Map                                              |
+------+-------------------------------------------+
| [Overlay: By District v] [Search: ___] [Go]     |
+------+-------------------------------------------+
|                                                  |
|            [Interactive Map]                     |
|            (tkintermapview)                      |
|                                                  |
|                                                  |
+------+-------------------------------------------+
| Info Panel (bottom or right sidebar)             |
| Barangay: Ma-a                                   |
| District: 1st Congressional District             |
| Population: 25,000 | Households: 5,000           |
| Crime (12mo): 7 | Traffic (12mo): 2              |
| Top crime: theft | Avg income: PHP 25,000        |
+--------------------------------------------------+
```

### Overlay Modes

**By District (default):**
- 1st District markers: blue
- 2nd District markers: green
- 3rd District markers: orange

**By Crime Risk:**
- 0 incidents: green marker
- 1-5 incidents: yellow marker
- 6-15 incidents: orange marker
- 16+ incidents: red marker

**By Population:**
- No data: small grey marker
- < 10,000: small blue marker
- 10,000-30,000: medium blue marker
- 30,000+: large dark blue marker

**All Markers:**
- Uniform blue markers for all barangays

### Behavior

1. Map initializes centered on Davao City (7.0707, 125.6087) at zoom level 12
2. All barangays with coordinates are plotted as markers
3. Overlay dropdown changes marker colors/sizes and re-renders
4. Clicking a marker populates the info panel with detailed barangay data
5. Search bar: type barangay name → map pans and zooms to that barangay
6. Info panel starts with "Click a marker to view details"

### Marker Implementation

tkintermapview supports `set_marker(lat, lon, text, marker_color_circle, marker_color_outside)`. We use these color parameters to implement overlays. All markers are deleted and re-created when switching overlays.

## Sidebar Update

Add between "Crime & Safety" and admin separator:
```python
("map", "Map", "\U0001F5FA"),
```

## Verification Plan

1. Map loads centered on Davao City with markers for barangays that have coordinates
2. Overlay switching (district/crime/population/all) changes marker colors correctly
3. Clicking a marker shows detailed info in the panel
4. Search for "Ma-a" → map pans to that barangay
5. Barangays without coordinates are silently skipped (no crash)
6. Works offline-ish: map tiles cache after first load, markers always render
