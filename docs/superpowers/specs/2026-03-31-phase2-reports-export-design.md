# Phase 2: Reports & Export — Design Specification

## Context

Phase 1 delivered the data collection foundation: 182 barangays seeded, data entry forms, authentication, and audit logging. Phase 2 builds on this by adding report generation and data export capabilities so city officials can produce printable summaries and extract data for analysis.

## Scope

- 4 report types: Barangay Profile, District Summary, City-Wide Summary, Comparative
- 2 export formats: PDF (ReportLab) and CSV (built-in csv module)
- Updated Reports view with report type selection, dynamic filters, live preview, and export buttons

## New Dependency

Add `reportlab` to `requirements.txt`:
```
reportlab>=4.0
```

## Files to Modify

| File | Change |
|------|--------|
| `requirements.txt` | Add `reportlab>=4.0` |
| `services/report_service.py` | Add 4 new report query functions |
| `utils/export.py` | Replace stub with working CSV and PDF export dispatch |
| `ui/views/reports_view.py` | Complete rewrite with report type selector, preview, export |

## Files to Create

| File | Purpose |
|------|---------|
| `utils/pdf_builder.py` | ReportLab PDF builders for all 4 report types |

## Report Data Aggregation (report_service.py)

### get_barangay_full_profile(barangay_id: int) -> dict

Returns a complete profile for a single barangay:
```python
{
    "barangay": {"name", "district_name", "classification", "latitude", "longitude", "area_sqkm"},
    "population": [{"year", "total_population", "male_count", "female_count", "registered_voters", "non_registered_residents", "foreign_residents", "household_count"}],
    "resident_categories": [{"year", "renters_count", "homeowners_count", "squatters_count", "informal_settlers_count"}],
    "income": [{"year", "average_household_income", "below_poverty_count", "low_income_count", "middle_income_count", "high_income_count"}],
    "businesses": [{"name", "type", "is_active", "registered_date"}],
    "utilities": [{"year", "water_source", "water_coverage_pct", "power_provider", "power_coverage_pct", "internet_coverage_pct"}],
    "land_types": [{"type", "area_sqkm", "percentage"}],
    "waste_management": [{"year", "collection_frequency", "disposal_method", "coverage_pct"}],
    "food_sources": [{"type", "description"}],
    "government_facilities": [{"agency_name", "facility_type", "address"}],
    "religious_demographics": [{"year", "religion", "count", "percentage"}],
}
```

### get_district_report(district_id: int) -> dict

Aggregated data across all barangays in a district:
```python
{
    "district": {"name", "barangay_count"},
    "population": {"total_population", "total_male", "total_female", "total_households", "total_voters"},
    "income": {"average_household_income", "total_below_poverty"},
    "utilities": {"avg_water_coverage", "avg_power_coverage", "avg_internet_coverage"},
    "businesses": {"total_active", "total_inactive"},
    "barangay_list": [{"name", "population", "classification"}],  # sorted by name
}
```

### get_citywide_report() -> dict

Same structure as district report but across all 182 barangays, plus a per-district breakdown:
```python
{
    "city": {"total_barangays", "total_districts"},
    "population": {"total_population", "total_male", "total_female", "total_households", "total_voters"},
    "income": {"average_household_income", "total_below_poverty"},
    "utilities": {"avg_water_coverage", "avg_power_coverage", "avg_internet_coverage"},
    "businesses": {"total_active", "total_inactive"},
    "districts": [<district_report for each district>],
}
```

### get_comparative_report(barangay_ids: list[int]) -> dict

Side-by-side comparison of 2-5 barangays:
```python
{
    "barangays": [
        {
            "name", "district_name", "population", "household_count",
            "avg_income", "water_coverage", "power_coverage", "internet_coverage",
            "business_count",
        },
        ...
    ]
}
```

All functions use the latest year's data where applicable.

## CSV Export (utils/export.py)

### export_to_csv(data: list[dict], headers: list[str], filepath: str) -> tuple[bool, str]

- Uses Python's built-in `csv.DictWriter`
- Writes headers as the first row
- Returns `(True, "Exported to <filepath>")` on success, `(False, error_message)` on failure
- Handles file permission errors gracefully

### export_report_to_csv(report_type: str, report_data: dict, filepath: str) -> tuple[bool, str]

Transforms report data dict into flat rows appropriate for CSV, then calls `export_to_csv`:
- Barangay profile: single flat CSV file with a "Section" column to group rows (e.g., "Population", "Income", "Utilities")
- District/City-wide: summary rows
- Comparative: one row per barangay, columns are the metrics

## PDF Generation (utils/pdf_builder.py)

### Common PDF Elements

All reports share:
- **Page size:** Letter (8.5" x 11"), portrait. Comparative uses landscape.
- **Header:** "City Government of Davao" title, report name, generation date (YYYY-MM-DD)
- **Footer:** Page X of Y, "Generated by Davao City Barangay Profiling System"
- **Fonts:** Helvetica (built-in to ReportLab, no external font files needed)
- **Tables:** Alternating row colors (#FFFFFF / #F0F0F0), bold header row with #1E88E5 background and white text, 1px #CCCCCC grid lines

### BarangayProfilePDF

Generates a multi-page PDF for a single barangay:
- Page 1: Barangay name, district, classification, coordinates, area. Population summary table.
- Page 2+: Resident categories table, income data table, business list table, utilities table, land types table, waste management table, food sources, government facilities, religious demographics.
- Each section has a bold section header.

### DistrictSummaryPDF

- Page 1: District name, barangay count, population summary, income summary.
- Page 2: Utility coverage averages, business totals.
- Page 3+: Table listing all barangays in the district with key stats.

### CitywideReportPDF

- Page 1: City-wide totals (population, households, voters, income, utilities, businesses).
- Page 2+: Per-district breakdown sections (same data as district report but condensed).

### ComparativePDF

- Landscape orientation.
- Single large comparison table: rows are metrics, columns are barangay names.
- Metrics: Population, Households, Avg Income, Water Coverage %, Power Coverage %, Internet Coverage %, Business Count.

### Builder Interface

Each class follows:
```python
class BarangayProfilePDF:
    def __init__(self, data: dict):
        self._data = data

    def build(self, filepath: str) -> tuple[bool, str]:
        # Build PDF using ReportLab, save to filepath
        # Returns (True, "Report saved to ...") or (False, "Error: ...")
```

## Updated Reports View (ui/views/reports_view.py)

### Layout

```
+--------------------------------------------------+
| Reports                                          |
+--------------------------------------------------+
| Report Type: [Barangay Profile | District | City-Wide | Comparative] |
|                                                  |
| [Dynamic Selectors]                              |
|   Barangay type: District dropdown → Barangay dropdown |
|   District type: District dropdown               |
|   City-wide: (none)                              |
|   Comparative: District dropdown → Multi-check barangay list |
|                                                  |
| [Generate Preview]                               |
|                                                  |
| [Preview Area - scrollable card with tables]     |
|                                                  |
| [Export PDF]  [Export CSV]     (disabled until preview generated) |
+--------------------------------------------------+
```

### Behavior

1. User selects report type from segmented button or dropdown.
2. Dynamic selectors appear/hide based on type.
3. "Generate Preview" queries `report_service` and renders data as tables in the preview area.
4. "Export PDF" opens a file save dialog (tkinter `filedialog.asksaveasfilename`), calls the PDF builder, shows success/error dialog.
5. "Export CSV" same flow but saves as `.csv`.
6. Export buttons are disabled until a preview has been generated.

### Comparative Multi-Select

For comparative reports, the barangay picker:
- User selects a district first (or "All" for all districts).
- A scrollable checklist of barangays appears.
- User checks 2-5 barangays.
- Validation: minimum 2, maximum 5 selected.

## File Save Dialog

Uses `tkinter.filedialog.asksaveasfilename()`:
- PDF default: `Barangay_Profile_<name>_<date>.pdf`
- CSV default: `Barangay_Profile_<name>_<date>.csv`
- Default directory: `data/reports/` (auto-created if missing)

## Verification Plan

1. **Generate preview** for each report type — data displays correctly in preview area
2. **Export PDF** — file is created, opens in a PDF viewer, layout looks correct with headers/footers/tables
3. **Export CSV** — file opens in Excel/text editor, data is correct
4. **Empty data handling** — reports generated for barangays with no data show "No data available" instead of crashing
5. **Comparative validation** — cannot export with fewer than 2 or more than 5 barangays selected
6. **File dialog** — cancel dialog does not crash, invalid path shows error
