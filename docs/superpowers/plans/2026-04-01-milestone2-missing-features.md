# Milestone 2 Missing Features (Phases 14–16) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fill six feature gaps in Milestone 2 — comparisons, expanded forecasting, crime prevention recommendations, historical change tracking, data collection scheduling, and anomaly detection.

**Architecture:** Three phases layered on the existing service-layer pattern. Phase 14 adds comparison/history services + a new Comparison view. Phase 15 extends forecast_service and plan_service + enhances existing views. Phase 16 adds scheduling/anomaly services + a new Schedule view + dashboard enhancements. All new services follow the existing `get_session()` / `tuple[bool, str]` pattern.

**Tech Stack:** Python 3.13, CustomTkinter, SQLAlchemy, SQLite, matplotlib, numpy

**Spec:** `docs/superpowers/specs/2026-04-01-milestone2-missing-features-design.md`

**Note:** This project has no test framework. Verification is done by running the app with `/c/laragon/bin/python/python-3.13/python.exe main.py` and manually checking features. Delete `data/barangay_profiling.db` to reset and re-seed when schema changes are made.

---

## File Map

### New Files
| File | Phase | Responsibility |
|------|-------|----------------|
| `services/comparison_service.py` | 14 | Barangay/district/year-over-year comparison queries |
| `services/history_service.py` | 14 | Field-level change recording and retrieval |
| `ui/views/comparison_view.py` | 14 | 4-tab comparison UI (Brgy vs Brgy, District vs District, Year-over-Year, Change History) |
| `services/schedule_service.py` | 16 | Data collection schedule CRUD + compliance dashboard |
| `services/anomaly_service.py` | 16 | Statistical anomaly detection + missing submission detection |
| `ui/views/schedule_view.py` | 16 | 2-tab schedule management UI (Schedules, Compliance) |

### Modified Files
| File | Phase | What Changes |
|------|-------|-------------|
| `database/models.py` | 14, 16 | Add 3 new models: RecordHistory, DataCollectionSchedule, BarangaySubmissionStatus |
| `config.py` | 16 | Add ANOMALY_CHECK_INTERVAL constant |
| `auth/roles.py` | 16 | Add manage_schedules + view_compliance permissions |
| `ui/components/sidebar.py` | 14, 16 | Add "Comparisons" nav item + "Data Collection" admin item |
| `ui/app.py` | 14, 16 | Register comparisons + schedule views in _create_view() |
| `services/forecast_service.py` | 15 | Add 3 new forecast functions |
| `services/plan_service.py` | 15 | Add generate_crime_prevention_plan() |
| `ui/views/forecast_view.py` | 15 | Add 3 new tabs |
| `ui/views/action_plan_view.py` | 15 | Wrap in CTkTabview, add Crime Prevention tab |
| `ui/views/dashboard_view.py` | 16 | Add compliance card + anomaly alert banner |
| `services/submission_service.py` | 16 | Hook refresh_submission_status after approval |
| `services/population_service.py` | 14 | Add history tracking hook |
| `services/economic_service.py` | 14 | Add history tracking hook |
| `services/infrastructure_service.py` | 14 | Add history tracking hook |
| `services/crime_service.py` | 14 | Add history tracking hook |
| `services/community_service.py` | 14 | Add history tracking hook |
| `database/seed.py` | 16 | Seed initial DataCollectionSchedule for 2026 |

---

## Phase 14: Comparisons & Historical Tracking

### Task 1: Add RecordHistory Model

**Files:**
- Modify: `database/models.py`

- [ ] **Step 1: Add the RecordHistory model**

Add after the `RetryQueue` class at the end of `database/models.py`:

```python
# ── Record History (Field-Level Change Tracking) ────────────

class RecordHistory(TimestampMixin, Base):
    __tablename__ = "record_history"
    __table_args__ = (
        Index("ix_record_history_lookup", "table_name", "record_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(50), nullable=False)
    record_id = Column(Integer, nullable=False)
    field_name = Column(String(100), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User")
```

Also add `Index` to the imports at the top of the file:

```python
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, Date, DateTime,
    ForeignKey, UniqueConstraint, create_engine, Index
)
```

- [ ] **Step 2: Delete DB and verify schema creation**

```bash
rm -f data/barangay_profiling.db
/c/laragon/bin/python/python-3.13/python.exe main.py
```

Verify the app starts and login works (admin/admin123). Close the app.

- [ ] **Step 3: Commit**

```bash
git add database/models.py
git commit -m "feat: add RecordHistory model for field-level change tracking (Phase 14)"
```

---

### Task 2: Create History Service

**Files:**
- Create: `services/history_service.py`

- [ ] **Step 1: Write the history service**

Create `services/history_service.py`:

```python
import logging
from datetime import datetime
from database.db import get_session
from database.models import (
    RecordHistory, User,
    PopulationRecord, IncomeData, Utility, WasteManagement,
    CrimeIncident, TrafficIncident, FoodSource, GovernmentFacility,
    ReligiousDemographic, Business, LandType, ResidentCategory,
)

logger = logging.getLogger(__name__)

SKIP_FIELDS = {"id", "created_at", "updated_at"}

# Maps table_name -> model class (for barangay_id lookups)
TABLE_MODEL_MAP = {
    "population_records": PopulationRecord,
    "income_data": IncomeData,
    "utilities": Utility,
    "waste_management": WasteManagement,
    "crime_incidents": CrimeIncident,
    "traffic_incidents": TrafficIncident,
    "food_sources": FoodSource,
    "government_facilities": GovernmentFacility,
    "religious_demographics": ReligiousDemographic,
    "businesses": Business,
    "land_types": LandType,
    "resident_categories": ResidentCategory,
}


def record_field_changes(table_name: str, record_id: int,
                         old_data: dict, new_data: dict,
                         user_id: int) -> int:
    """Compare old and new data dicts, store a RecordHistory row per changed field.
    Returns the count of changes recorded.
    """
    session = get_session()
    try:
        count = 0
        for key, new_val in new_data.items():
            if key in SKIP_FIELDS:
                continue
            old_val = old_data.get(key)
            # Normalize for comparison (both to str or both None)
            old_str = str(old_val) if old_val is not None else None
            new_str = str(new_val) if new_val is not None else None
            if old_str != new_str:
                entry = RecordHistory(
                    table_name=table_name,
                    record_id=record_id,
                    field_name=key,
                    old_value=old_str,
                    new_value=new_str,
                    changed_by=user_id,
                    changed_at=datetime.utcnow(),
                )
                session.add(entry)
                count += 1
        if count > 0:
            session.commit()
            logger.info(f"Recorded {count} field changes for {table_name}#{record_id}")
        return count
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to record field changes: {e}")
        return 0
    finally:
        session.close()


def get_record_history(table_name: str, record_id: int) -> list[dict]:
    """Return all field changes for a specific record, newest first."""
    session = get_session()
    try:
        entries = (
            session.query(RecordHistory)
            .filter_by(table_name=table_name, record_id=record_id)
            .order_by(RecordHistory.changed_at.desc())
            .all()
        )
        results = []
        for e in entries:
            user = session.get(User, e.changed_by)
            results.append({
                "field_name": e.field_name,
                "old_value": e.old_value,
                "new_value": e.new_value,
                "changed_by_name": user.full_name if user else "Unknown",
                "changed_at": e.changed_at.strftime("%Y-%m-%d %H:%M") if e.changed_at else "",
            })
        return results
    finally:
        session.close()


def get_barangay_history(barangay_id: int, limit: int = 50) -> list[dict]:
    """Return recent field changes across all tables for a given barangay."""
    session = get_session()
    try:
        all_entries = (
            session.query(RecordHistory)
            .order_by(RecordHistory.changed_at.desc())
            .limit(limit * 5)  # fetch extra, then filter
            .all()
        )
        results = []
        for e in all_entries:
            if len(results) >= limit:
                break
            model_cls = TABLE_MODEL_MAP.get(e.table_name)
            if not model_cls:
                continue
            record = session.get(model_cls, e.record_id)
            if record and hasattr(record, "barangay_id") and record.barangay_id == barangay_id:
                user = session.get(User, e.changed_by)
                results.append({
                    "table_name": e.table_name,
                    "record_id": e.record_id,
                    "field_name": e.field_name,
                    "old_value": e.old_value,
                    "new_value": e.new_value,
                    "changed_by_name": user.full_name if user else "Unknown",
                    "changed_at": e.changed_at.strftime("%Y-%m-%d %H:%M") if e.changed_at else "",
                })
        return results
    finally:
        session.close()
```

- [ ] **Step 2: Commit**

```bash
git add services/history_service.py
git commit -m "feat: add history service for field-level change tracking (Phase 14)"
```

---

### Task 3: Hook History Tracking into Existing Services

**Files:**
- Modify: `services/population_service.py`
- Modify: `services/economic_service.py`
- Modify: `services/infrastructure_service.py`
- Modify: `services/crime_service.py`
- Modify: `services/community_service.py`

The pattern is identical across all services. In every `save_*` function that updates an existing record, add these lines **before** the `setattr` loop:

```python
from services.history_service import record_field_changes

# Capture old data before update
old_data = {c.key: getattr(existing, c.key) for c in existing.__table__.columns}
```

And **after** the `setattr` loop (before `session.commit()`):

```python
new_data = {c.key: getattr(existing, c.key) for c in existing.__table__.columns}
record_field_changes("TABLE_NAME", existing.id, old_data, new_data, user_id)
```

- [ ] **Step 1: Add hook to population_service.py**

In `save_population_record()` (~line 46-68), the function checks `if existing:` then loops `for key, value in data.items(): setattr(existing, key, value)`.

Add the import at top of file:
```python
from services.history_service import record_field_changes
```

Inside the `if existing:` block, BEFORE the setattr loop, add:
```python
                old_data = {c.key: getattr(existing, c.key) for c in existing.__table__.columns}
```

AFTER the setattr loop and BEFORE `session.commit()`, add:
```python
                new_data = {c.key: getattr(existing, c.key) for c in existing.__table__.columns}
                record_field_changes("population_records", existing.id, old_data, new_data, user_id)
```

- [ ] **Step 2: Add hook to economic_service.py**

Same pattern in `save_income_record()` and `save_business()`:

Add import at top:
```python
from services.history_service import record_field_changes
```

In `save_income_record()` — inside `if existing:` block, before setattr loop:
```python
                old_data = {c.key: getattr(existing, c.key) for c in existing.__table__.columns}
```
After setattr loop, before commit:
```python
                new_data = {c.key: getattr(existing, c.key) for c in existing.__table__.columns}
                record_field_changes("income_data", existing.id, old_data, new_data, user_id)
```

In `save_business()` — inside `if business_id and business:` block (the update path), before setattr loop:
```python
                old_data = {c.key: getattr(business, c.key) for c in business.__table__.columns}
```
After setattr loop, before commit:
```python
                new_data = {c.key: getattr(business, c.key) for c in business.__table__.columns}
                record_field_changes("businesses", business.id, old_data, new_data, user_id)
```

- [ ] **Step 3: Add hook to infrastructure_service.py**

Same pattern in `save_utility_record()`, `save_land_type()`, and `save_waste_record()`:

Add import at top:
```python
from services.history_service import record_field_changes
```

In `save_utility_record()` — use table name `"utilities"`, variable name `existing`.
In `save_land_type()` — use table name `"land_types"`, variable name `record`.
In `save_waste_record()` — use table name `"waste_management"`, variable name `existing`.

Each follows the same old_data/new_data/record_field_changes pattern shown above.

- [ ] **Step 4: Add hook to crime_service.py**

Add import, then hook `save_crime_incident()` (table `"crime_incidents"`, var `record`) and `save_traffic_incident()` (table `"traffic_incidents"`, var `record`).

- [ ] **Step 5: Add hook to community_service.py**

Add import, then hook `save_food_source()` (table `"food_sources"`, var `record`), `save_government_facility()` (table `"government_facilities"`, var `record`), and `save_religious_demographic()` (table `"religious_demographics"`, var `record`).

- [ ] **Step 6: Commit**

```bash
git add services/population_service.py services/economic_service.py services/infrastructure_service.py services/crime_service.py services/community_service.py
git commit -m "feat: hook field-level history tracking into all update services (Phase 14)"
```

---

### Task 4: Create Comparison Service

**Files:**
- Create: `services/comparison_service.py`

- [ ] **Step 1: Write the comparison service**

Create `services/comparison_service.py`:

```python
import logging
from database.db import get_session
from database.models import (
    Barangay, District, PopulationRecord, IncomeData, Utility,
    CrimeIncident, WasteManagement,
)
from sqlalchemy import func, extract

logger = logging.getLogger(__name__)

# Supported metrics and which table/column they query
METRIC_CONFIG = {
    "population": {"model": PopulationRecord, "column": "total_population"},
    "income": {"model": IncomeData, "column": "average_household_income"},
    "water_coverage": {"model": Utility, "column": "water_coverage_pct"},
    "power_coverage": {"model": Utility, "column": "power_coverage_pct"},
    "internet_coverage": {"model": Utility, "column": "internet_coverage_pct"},
    "crime_count": {"model": CrimeIncident, "aggregate": True},
    "waste_collection_rate": {"model": WasteManagement, "column": "coverage_pct"},
}

ALL_METRICS = list(METRIC_CONFIG.keys())


def _get_metric_value(session, metric_key: str, barangay_id: int, year: int):
    """Fetch a single metric value for a barangay in a given year."""
    cfg = METRIC_CONFIG.get(metric_key)
    if not cfg:
        return None

    if cfg.get("aggregate"):
        # Crime count: count incidents in that year
        count = (
            session.query(func.count(CrimeIncident.id))
            .filter(
                CrimeIncident.barangay_id == barangay_id,
                extract("year", CrimeIncident.date_occurred) == year,
            )
            .scalar()
        ) or 0
        return count

    model = cfg["model"]
    col_name = cfg["column"]
    record = (
        session.query(model)
        .filter_by(barangay_id=barangay_id, year=year)
        .first()
    )
    if record:
        val = getattr(record, col_name, None)
        return round(float(val), 2) if val is not None else None
    return None


def compare_barangays(barangay_ids: list[int], metrics: list[str],
                      years: list[int]) -> dict:
    """Compare 2-4 barangays across selected metrics and years."""
    if len(barangay_ids) < 2 or len(barangay_ids) > 4:
        return {"error": "Select 2-4 barangays", "barangays": []}

    session = get_session()
    try:
        result = {"barangays": []}
        for bid in barangay_ids:
            brgy = session.get(Barangay, bid)
            if not brgy:
                continue
            brgy_data = {
                "id": brgy.id,
                "name": brgy.name,
                "district_name": brgy.district.name,
                "metrics": {},
            }
            for metric in metrics:
                brgy_data["metrics"][metric] = {}
                for year in sorted(years):
                    brgy_data["metrics"][metric][year] = _get_metric_value(
                        session, metric, bid, year
                    )
            result["barangays"].append(brgy_data)
        return result
    finally:
        session.close()


def compare_districts(metrics: list[str], years: list[int]) -> dict:
    """Compare all 3 districts on aggregated metrics."""
    session = get_session()
    try:
        districts = session.query(District).order_by(District.id).all()
        result = {"districts": []}

        for dist in districts:
            brgy_ids = [b.id for b in dist.barangays]
            dist_data = {
                "id": dist.id,
                "name": dist.name,
                "metrics": {},
            }
            for metric in metrics:
                dist_data["metrics"][metric] = {}
                for year in sorted(years):
                    values = []
                    for bid in brgy_ids:
                        val = _get_metric_value(session, metric, bid, year)
                        if val is not None:
                            values.append(val)
                    # Sum for population/crime, average for percentages/income
                    if values:
                        if metric in ("population", "crime_count"):
                            dist_data["metrics"][metric][year] = round(sum(values), 2)
                        else:
                            dist_data["metrics"][metric][year] = round(
                                sum(values) / len(values), 2
                            )
                    else:
                        dist_data["metrics"][metric][year] = None
            result["districts"].append(dist_data)
        return result
    finally:
        session.close()


def year_over_year(barangay_id: int, years: list[int]) -> dict:
    """All metrics for one barangay across years with growth percentages."""
    session = get_session()
    try:
        brgy = session.get(Barangay, barangay_id)
        if not brgy:
            return {"error": "Barangay not found"}

        sorted_years = sorted(years)
        result = {
            "barangay_name": brgy.name,
            "district_name": brgy.district.name,
            "metrics": {},
        }

        for metric in ALL_METRICS:
            metric_data = {"values": {}, "growth_pct": {}, "trend": "stable"}
            prev_val = None
            for year in sorted_years:
                val = _get_metric_value(session, metric, barangay_id, year)
                metric_data["values"][year] = val
                if prev_val is not None and val is not None and prev_val != 0:
                    pct = round(((val - prev_val) / prev_val) * 100, 1)
                    metric_data["growth_pct"][year] = pct
                prev_val = val

            # Determine trend from first to last non-None value
            vals = [v for v in metric_data["values"].values() if v is not None]
            if len(vals) >= 2:
                change = vals[-1] - vals[0]
                mean = sum(vals) / len(vals)
                if mean != 0 and abs(change / mean) > 0.05:
                    metric_data["trend"] = "increasing" if change > 0 else "decreasing"

            result["metrics"][metric] = metric_data
        return result
    finally:
        session.close()


def get_available_years() -> list[int]:
    """Return all years that have data across any table."""
    session = get_session()
    try:
        years = set()
        for record in session.query(PopulationRecord.year).distinct():
            years.add(record[0])
        for record in session.query(IncomeData.year).distinct():
            years.add(record[0])
        for record in session.query(Utility.year).distinct():
            years.add(record[0])
        return sorted(years)
    finally:
        session.close()
```

- [ ] **Step 2: Commit**

```bash
git add services/comparison_service.py
git commit -m "feat: add comparison service with barangay/district/year-over-year modes (Phase 14)"
```

---

### Task 5: Create Comparison View

**Files:**
- Create: `ui/views/comparison_view.py`

- [ ] **Step 1: Write the comparison view**

Create `ui/views/comparison_view.py`:

```python
import customtkinter as ctk
from ui.theme import (
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_SMALL, FONT_SIZE_TITLE,
    TEXT_PRIMARY, TEXT_SECONDARY, PRIMARY_COLOR, ACCENT_COLOR, WARNING_COLOR,
    SUCCESS_COLOR, DANGER_COLOR, TEXT_LIGHT,
    CARD_BG, BG_COLOR, PADDING_LARGE, PADDING_NORMAL,
)
from ui.components.chart_widget import ChartWidget
from services.comparison_service import (
    compare_barangays, compare_districts, year_over_year,
    get_available_years, ALL_METRICS,
)
from services.history_service import get_record_history, get_barangay_history, TABLE_MODEL_MAP
from services.barangay_service import get_all_districts, get_barangays_by_district
from database.db import get_session
from database.models import Barangay

METRIC_LABELS = {
    "population": "Population",
    "income": "Avg Household Income",
    "water_coverage": "Water Coverage %",
    "power_coverage": "Power Coverage %",
    "internet_coverage": "Internet Coverage %",
    "crime_count": "Crime Count",
    "waste_collection_rate": "Waste Collection %",
}

TABLE_LABELS = {
    "population_records": "Population",
    "income_data": "Income",
    "utilities": "Utilities",
    "waste_management": "Waste Management",
    "crime_incidents": "Crime Incidents",
    "traffic_incidents": "Traffic Incidents",
    "food_sources": "Food Sources",
    "government_facilities": "Government Facilities",
    "religious_demographics": "Religious Demographics",
    "businesses": "Businesses",
    "land_types": "Land Types",
    "resident_categories": "Resident Categories",
}


class ComparisonView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, **kwargs)
        self._districts = get_all_districts()
        self._all_barangays = self._load_all_barangays()
        self._available_years = get_available_years()
        self._build_ui()

    def _load_all_barangays(self):
        session = get_session()
        try:
            return [
                {"id": b.id, "name": b.name}
                for b in session.query(Barangay).order_by(Barangay.name).all()
            ]
        finally:
            session.close()

    def _build_ui(self):
        ctk.CTkLabel(
            self, text="Comparisons",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_NORMAL))

        self._tabview = ctk.CTkTabview(self, fg_color=CARD_BG, corner_radius=12)
        self._tabview.pack(fill="both", expand=True, padx=PADDING_LARGE, pady=(0, PADDING_LARGE))

        self._build_brgy_vs_brgy_tab(self._tabview.add("Barangay vs Barangay"))
        self._build_district_tab(self._tabview.add("District vs District"))
        self._build_yoy_tab(self._tabview.add("Year over Year"))
        self._build_history_tab(self._tabview.add("Change History"))

    # ── Tab 1: Barangay vs Barangay ──────────────────────────

    def _build_brgy_vs_brgy_tab(self, tab):
        ctrl = ctk.CTkFrame(tab, fg_color="transparent")
        ctrl.pack(fill="x", padx=PADDING_NORMAL, pady=PADDING_NORMAL)

        brgy_names = [b["name"] for b in self._all_barangays]

        ctk.CTkLabel(ctrl, text="Select Barangays (2-4):", font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
                     text_color=TEXT_PRIMARY).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 5))

        self._brgy_combos = []
        for i in range(4):
            combo = ctk.CTkComboBox(ctrl, values=["(none)"] + brgy_names, width=180,
                                    font=(FONT_FAMILY, FONT_SIZE_SMALL), state="readonly")
            combo.set("(none)")
            combo.grid(row=1, column=i, padx=(0, 5))
            self._brgy_combos.append(combo)

        # Metric checkboxes
        ctk.CTkLabel(ctrl, text="Metrics:", font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
                     text_color=TEXT_PRIMARY).grid(row=2, column=0, columnspan=4, sticky="w", pady=(10, 5))

        self._metric_vars = {}
        for i, metric in enumerate(ALL_METRICS):
            var = ctk.BooleanVar(value=(metric == "population"))
            cb = ctk.CTkCheckBox(ctrl, text=METRIC_LABELS[metric], variable=var,
                                 font=(FONT_FAMILY, FONT_SIZE_SMALL))
            cb.grid(row=3 + i // 4, column=i % 4, sticky="w", padx=(0, 5), pady=2)
            self._metric_vars[metric] = var

        ctk.CTkButton(ctrl, text="Compare", command=self._run_brgy_compare,
                       font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
                       fg_color=PRIMARY_COLOR, text_color=TEXT_LIGHT, width=120, height=34,
                       ).grid(row=6, column=0, pady=(10, 0), sticky="w")

        self._brgy_chart = ChartWidget(tab, figsize=(7, 3.5))
        self._brgy_chart.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

    def _run_brgy_compare(self):
        selected_ids = []
        for combo in self._brgy_combos:
            name = combo.get()
            if name != "(none)":
                for b in self._all_barangays:
                    if b["name"] == name:
                        selected_ids.append(b["id"])
                        break

        if len(selected_ids) < 2:
            return

        metrics = [m for m, var in self._metric_vars.items() if var.get()]
        if not metrics:
            metrics = ["population"]

        years = self._available_years if self._available_years else [2024, 2025]
        data = compare_barangays(selected_ids, metrics, years)

        if "error" in data:
            return

        def draw(fig, ax):
            barangays = data["barangays"]
            if not barangays or not metrics:
                return

            metric = metrics[0]  # Chart shows first metric
            colors = ["#1E88E5", "#43A047", "#FB8C00", "#E53935"]

            for i, brgy in enumerate(barangays):
                metric_data = brgy["metrics"].get(metric, {})
                yrs = sorted(metric_data.keys())
                vals = [metric_data[y] for y in yrs if metric_data[y] is not None]
                valid_yrs = [y for y in yrs if metric_data[y] is not None]
                if valid_yrs:
                    ax.plot(valid_yrs, vals, "o-", color=colors[i % len(colors)],
                            linewidth=2, markersize=6, label=brgy["name"])

            ax.set_title(f"Comparison: {METRIC_LABELS.get(metric, metric)}", fontsize=11)
            ax.set_ylabel(METRIC_LABELS.get(metric, metric))
            ax.set_xlabel("Year")
            ax.legend(fontsize=8)

        self._brgy_chart.update_chart(draw)

    # ── Tab 2: District vs District ──────────────────────────

    def _build_district_tab(self, tab):
        ctrl = ctk.CTkFrame(tab, fg_color="transparent")
        ctrl.pack(fill="x", padx=PADDING_NORMAL, pady=PADDING_NORMAL)

        ctk.CTkLabel(ctrl, text="Metric:", font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
                     text_color=TEXT_PRIMARY).pack(side="left", padx=(0, 5))

        metric_labels = [METRIC_LABELS[m] for m in ALL_METRICS]
        self._dist_metric_combo = ctk.CTkComboBox(ctrl, values=metric_labels, width=200,
                                                   font=(FONT_FAMILY, FONT_SIZE_SMALL), state="readonly")
        self._dist_metric_combo.set(metric_labels[0])
        self._dist_metric_combo.pack(side="left", padx=(0, 10))

        ctk.CTkButton(ctrl, text="Compare Districts", command=self._run_district_compare,
                       font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
                       fg_color=PRIMARY_COLOR, text_color=TEXT_LIGHT, width=140, height=34,
                       ).pack(side="left")

        self._dist_chart = ChartWidget(tab, figsize=(7, 3.5))
        self._dist_chart.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

    def _run_district_compare(self):
        label = self._dist_metric_combo.get()
        metric = None
        for key, lbl in METRIC_LABELS.items():
            if lbl == label:
                metric = key
                break
        if not metric:
            return

        years = self._available_years if self._available_years else [2024, 2025]
        data = compare_districts([metric], years)

        def draw(fig, ax):
            districts = data.get("districts", [])
            if not districts:
                return
            colors = ["#1E88E5", "#43A047", "#FB8C00"]
            for i, dist in enumerate(districts):
                metric_data = dist["metrics"].get(metric, {})
                yrs = sorted(metric_data.keys())
                vals = [metric_data[y] for y in yrs if metric_data[y] is not None]
                valid_yrs = [y for y in yrs if metric_data[y] is not None]
                if valid_yrs:
                    short_name = dist["name"].replace("Congressional ", "").replace("District", "Dist.")
                    ax.plot(valid_yrs, vals, "o-", color=colors[i % len(colors)],
                            linewidth=2, markersize=6, label=short_name)

            ax.set_title(f"District Comparison: {METRIC_LABELS.get(metric, metric)}", fontsize=11)
            ax.set_ylabel(METRIC_LABELS.get(metric, metric))
            ax.set_xlabel("Year")
            ax.legend(fontsize=8)

        self._dist_chart.update_chart(draw)

    # ── Tab 3: Year over Year ────────────────────────────────

    def _build_yoy_tab(self, tab):
        ctrl = ctk.CTkFrame(tab, fg_color="transparent")
        ctrl.pack(fill="x", padx=PADDING_NORMAL, pady=PADDING_NORMAL)

        brgy_names = [b["name"] for b in self._all_barangays]

        ctk.CTkLabel(ctrl, text="Barangay:", font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
                     text_color=TEXT_PRIMARY).pack(side="left", padx=(0, 5))

        self._yoy_combo = ctk.CTkComboBox(ctrl, values=brgy_names, width=250,
                                           font=(FONT_FAMILY, FONT_SIZE_SMALL), state="readonly")
        if brgy_names:
            self._yoy_combo.set(brgy_names[0])
        self._yoy_combo.pack(side="left", padx=(0, 10))

        ctk.CTkButton(ctrl, text="Analyze", command=self._run_yoy,
                       font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
                       fg_color=PRIMARY_COLOR, text_color=TEXT_LIGHT, width=100, height=34,
                       ).pack(side="left")

        self._yoy_results = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self._yoy_results.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(5, PADDING_NORMAL))

    def _run_yoy(self):
        name = self._yoy_combo.get()
        brgy_id = None
        for b in self._all_barangays:
            if b["name"] == name:
                brgy_id = b["id"]
                break
        if not brgy_id:
            return

        years = self._available_years if self._available_years else [2024, 2025]
        data = year_over_year(brgy_id, years)

        for w in self._yoy_results.winfo_children():
            w.destroy()

        if "error" in data:
            ctk.CTkLabel(self._yoy_results, text=data["error"],
                         font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=DANGER_COLOR).pack(pady=20)
            return

        ctk.CTkLabel(
            self._yoy_results,
            text=f"{data['barangay_name']} — {data['district_name']}",
            font=(FONT_FAMILY, 14, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, 10))

        sorted_years = sorted(years)
        for metric_key, metric_data in data["metrics"].items():
            row = ctk.CTkFrame(self._yoy_results, fg_color="#F5F5F5", corner_radius=8)
            row.pack(fill="x", pady=3)

            # Metric name + trend
            trend = metric_data["trend"]
            trend_icon = {"increasing": "\u2191", "decreasing": "\u2193", "stable": "\u2192"}
            trend_color = {"increasing": WARNING_COLOR, "decreasing": DANGER_COLOR, "stable": SUCCESS_COLOR}

            header = ctk.CTkFrame(row, fg_color="transparent")
            header.pack(fill="x", padx=PADDING_NORMAL, pady=(8, 2))

            ctk.CTkLabel(
                header, text=METRIC_LABELS.get(metric_key, metric_key),
                font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"), text_color=TEXT_PRIMARY,
            ).pack(side="left")

            ctk.CTkLabel(
                header, text=f"  {trend_icon.get(trend, '')} {trend.capitalize()}",
                font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=trend_color.get(trend, TEXT_SECONDARY),
            ).pack(side="left")

            # Values row
            vals_frame = ctk.CTkFrame(row, fg_color="transparent")
            vals_frame.pack(fill="x", padx=PADDING_NORMAL, pady=(0, 8))

            for yr in sorted_years:
                val = metric_data["values"].get(yr)
                growth = metric_data["growth_pct"].get(yr)
                val_text = f"{val:,.1f}" if val is not None else "N/A"
                growth_text = ""
                growth_color = TEXT_SECONDARY
                if growth is not None:
                    growth_text = f" ({growth:+.1f}%)"
                    growth_color = SUCCESS_COLOR if growth >= 0 else DANGER_COLOR

                cell = ctk.CTkFrame(vals_frame, fg_color="transparent")
                cell.pack(side="left", expand=True, fill="x")

                ctk.CTkLabel(cell, text=str(yr), font=(FONT_FAMILY, 10), text_color=TEXT_SECONDARY).pack()
                ctk.CTkLabel(cell, text=val_text, font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
                             text_color=TEXT_PRIMARY).pack()
                if growth_text:
                    ctk.CTkLabel(cell, text=growth_text, font=(FONT_FAMILY, 10),
                                 text_color=growth_color).pack()

    # ── Tab 4: Change History ────────────────────────────────

    def _build_history_tab(self, tab):
        ctrl = ctk.CTkFrame(tab, fg_color="transparent")
        ctrl.pack(fill="x", padx=PADDING_NORMAL, pady=PADDING_NORMAL)

        brgy_names = [b["name"] for b in self._all_barangays]

        ctk.CTkLabel(ctrl, text="Barangay:", font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
                     text_color=TEXT_PRIMARY).pack(side="left", padx=(0, 5))

        self._hist_brgy_combo = ctk.CTkComboBox(ctrl, values=brgy_names, width=200,
                                                 font=(FONT_FAMILY, FONT_SIZE_SMALL), state="readonly")
        if brgy_names:
            self._hist_brgy_combo.set(brgy_names[0])
        self._hist_brgy_combo.pack(side="left", padx=(0, 10))

        ctk.CTkButton(ctrl, text="Load History", command=self._load_history,
                       font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
                       fg_color=PRIMARY_COLOR, text_color=TEXT_LIGHT, width=120, height=34,
                       ).pack(side="left")

        self._hist_results = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self._hist_results.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(5, PADDING_NORMAL))

    def _load_history(self):
        name = self._hist_brgy_combo.get()
        brgy_id = None
        for b in self._all_barangays:
            if b["name"] == name:
                brgy_id = b["id"]
                break
        if not brgy_id:
            return

        history = get_barangay_history(brgy_id, limit=50)

        for w in self._hist_results.winfo_children():
            w.destroy()

        if not history:
            ctk.CTkLabel(self._hist_results, text="No change history found for this barangay.",
                         font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_SECONDARY).pack(pady=20)
            return

        for entry in history:
            row = ctk.CTkFrame(self._hist_results, fg_color="#F5F5F5", corner_radius=8)
            row.pack(fill="x", pady=2)

            left = ctk.CTkFrame(row, fg_color="transparent")
            left.pack(fill="x", padx=PADDING_NORMAL, pady=8)

            table_label = TABLE_LABELS.get(entry["table_name"], entry["table_name"])
            ctk.CTkLabel(
                left, text=f"{table_label} — {entry['field_name']}",
                font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"), text_color=TEXT_PRIMARY,
            ).pack(anchor="w")

            ctk.CTkLabel(
                left,
                text=f"{entry['old_value'] or '(empty)'} \u2192 {entry['new_value'] or '(empty)'}",
                font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=ACCENT_COLOR,
            ).pack(anchor="w")

            ctk.CTkLabel(
                left,
                text=f"by {entry['changed_by_name']} on {entry['changed_at']}",
                font=(FONT_FAMILY, 10), text_color=TEXT_SECONDARY,
            ).pack(anchor="w")

    def refresh(self):
        self._available_years = get_available_years()
        self._all_barangays = self._load_all_barangays()
```

- [ ] **Step 2: Commit**

```bash
git add ui/views/comparison_view.py
git commit -m "feat: add comparison view with 4 tabs (Phase 14)"
```

---

### Task 6: Wire Phase 14 Navigation

**Files:**
- Modify: `ui/components/sidebar.py`
- Modify: `ui/app.py`

- [ ] **Step 1: Add Comparisons to sidebar**

In `ui/components/sidebar.py`, in the `nav_items` list (~line 72-84), add after the `("analytics", "Analytics", "\U0001F4C8")` entry:

```python
            ("comparisons", "Comparisons", "\U0001F4CA"),
```

So it reads:
```python
            ("analytics", "Analytics", "\U0001F4C8"),
            ("comparisons", "Comparisons", "\U0001F4CA"),
            ("forecasting", "Forecasting", "\U0001F52E"),
```

- [ ] **Step 2: Register comparison view in app.py**

In `ui/app.py`, in the `_create_view()` method (~line 192-235), add after the `elif view_key == "analytics":` block:

```python
        elif view_key == "comparisons":
            from ui.views.comparison_view import ComparisonView
            return ComparisonView(self._content_frame)
```

- [ ] **Step 3: Delete DB and test**

```bash
rm -f data/barangay_profiling.db
/c/laragon/bin/python/python-3.13/python.exe main.py
```

Verify: Login → "Comparisons" appears in sidebar between Analytics and Forecasting → click it → 4 tabs visible → no errors.

- [ ] **Step 4: Commit**

```bash
git add ui/components/sidebar.py ui/app.py
git commit -m "feat: wire Comparisons view into sidebar navigation (Phase 14)"
```

---

## Phase 15: Expanded Forecasting & Crime Prevention

### Task 7: Add 3 New Forecast Functions

**Files:**
- Modify: `services/forecast_service.py`

- [ ] **Step 1: Add imports for new models**

At the top of `services/forecast_service.py`, update the import to include new models:

```python
from database.models import (
    Barangay, PopulationRecord, Utility, GovernmentFacility,
    CrimeIncident, TrafficIncident, LandType, FoodSource, Business,
)
from sqlalchemy import func, extract
```

- [ ] **Step 2: Add forecast_food_supply()**

Add after `forecast_infrastructure_needs()` (~line 165):

```python
def forecast_food_supply(barangay_id: int) -> dict:
    """Food supply projection based on population growth and agricultural land."""
    session = get_session()
    try:
        # Get population data for demand projection
        pop_records = (
            session.query(PopulationRecord)
            .filter_by(barangay_id=barangay_id)
            .order_by(PopulationRecord.year)
            .all()
        )

        if not pop_records:
            return {"historical": [], "forecast": [], "trend": "stable",
                    "demand_gap": "balanced", "notes": "No population data available."}

        # Population-based food demand index
        # Higher population + lower agricultural land = higher demand pressure
        agri_land = (
            session.query(LandType)
            .filter(LandType.barangay_id == barangay_id, LandType.type.ilike("%agri%"))
            .first()
        )
        agri_pct = agri_land.percentage if agri_land and agri_land.percentage else 0

        food_source_count = (
            session.query(func.count(FoodSource.id))
            .filter_by(barangay_id=barangay_id)
            .scalar()
        ) or 0

        # Food demand index: population / (agri_factor * food_source_factor)
        # Higher = more demand pressure
        agri_factor = max(agri_pct, 1) / 10  # normalize: 10% agri = factor 1
        source_factor = max(food_source_count, 1)

        data_points = []
        for r in pop_records:
            if r.total_population is not None:
                demand_index = round(r.total_population / (agri_factor * source_factor), 2)
                data_points.append((r.year, demand_index))

        result = forecast_metric(data_points, years_ahead=3)

        # Determine gap
        if agri_pct < 5 and pop_records[-1].total_population and pop_records[-1].total_population > 10000:
            result["demand_gap"] = "deficit"
            result["notes"] = (
                f"Low agricultural land ({agri_pct:.1f}%) with large population. "
                f"Food supply sources: {food_source_count}. Consider food security programs."
            )
        elif agri_pct >= 20:
            result["demand_gap"] = "surplus"
            result["notes"] = f"Good agricultural base ({agri_pct:.1f}%). {food_source_count} food sources registered."
        else:
            result["demand_gap"] = "balanced"
            result["notes"] = f"Agricultural land: {agri_pct:.1f}%, Food sources: {food_source_count}."

        return result
    finally:
        session.close()
```

- [ ] **Step 3: Add forecast_transportation()**

```python
def forecast_transportation(barangay_id: int) -> dict:
    """Transportation demand projection based on traffic incidents and population."""
    session = get_session()
    try:
        pop_records = (
            session.query(PopulationRecord)
            .filter_by(barangay_id=barangay_id)
            .order_by(PopulationRecord.year)
            .all()
        )

        if not pop_records:
            return {"historical": [], "forecast": [], "trend": "stable",
                    "congestion_level": "low", "recommended_infrastructure": []}

        # Build congestion index per year: (traffic_incidents / population) * 10000
        data_points = []
        for r in pop_records:
            if r.total_population and r.total_population > 0:
                traffic_count = (
                    session.query(func.count(TrafficIncident.id))
                    .filter(
                        TrafficIncident.barangay_id == barangay_id,
                        extract("year", TrafficIncident.date_occurred) == r.year,
                    )
                    .scalar()
                ) or 0
                index = round((traffic_count / r.total_population) * 10000, 2)
                data_points.append((r.year, index))

        result = forecast_metric(data_points, years_ahead=3)

        # Determine congestion level from latest value
        latest_index = data_points[-1][1] if data_points else 0
        if latest_index > 20:
            result["congestion_level"] = "critical"
        elif latest_index > 10:
            result["congestion_level"] = "high"
        elif latest_index > 5:
            result["congestion_level"] = "moderate"
        else:
            result["congestion_level"] = "low"

        # Recommendations
        recs = []
        if result["congestion_level"] in ("high", "critical"):
            recs.append("Traffic management review and road widening")
            recs.append("Public transportation route optimization")
        if result["congestion_level"] in ("moderate", "high", "critical"):
            recs.append("Traffic signal improvements at key intersections")
            recs.append("Pedestrian and cycling infrastructure")
        result["recommended_infrastructure"] = recs

        return result
    finally:
        session.close()
```

- [ ] **Step 4: Add forecast_public_safety()**

```python
def forecast_public_safety(barangay_id: int) -> dict:
    """Public safety projection based on crime trends and population."""
    session = get_session()
    try:
        pop_records = (
            session.query(PopulationRecord)
            .filter_by(barangay_id=barangay_id)
            .order_by(PopulationRecord.year)
            .all()
        )

        if not pop_records:
            return {"historical": [], "forecast": [], "trend": "stable",
                    "safety_level": "safe", "police_ratio": "N/A", "facility_gap": 0}

        # Crime rate per year: (incidents / population) * 10000
        data_points = []
        for r in pop_records:
            if r.total_population and r.total_population > 0:
                crime_count = (
                    session.query(func.count(CrimeIncident.id))
                    .filter(
                        CrimeIncident.barangay_id == barangay_id,
                        extract("year", CrimeIncident.date_occurred) == r.year,
                    )
                    .scalar()
                ) or 0
                rate = round((crime_count / r.total_population) * 10000, 2)
                data_points.append((r.year, rate))

        result = forecast_metric(data_points, years_ahead=3)

        # Safety level from latest crime rate
        latest_rate = data_points[-1][1] if data_points else 0
        if latest_rate > 100:
            result["safety_level"] = "critical"
        elif latest_rate > 50:
            result["safety_level"] = "at_risk"
        elif latest_rate > 20:
            result["safety_level"] = "moderate"
        else:
            result["safety_level"] = "safe"

        # Police ratio: recommended 1:500
        latest_pop = pop_records[-1].total_population or 0
        police_stations = (
            session.query(func.count(GovernmentFacility.id))
            .filter(
                GovernmentFacility.barangay_id == barangay_id,
                GovernmentFacility.facility_type.ilike("%police%"),
            )
            .scalar()
        ) or 0

        if latest_pop > 0:
            recommended_officers = latest_pop // 500
            result["police_ratio"] = f"{police_stations} stations (recommended officers: {recommended_officers})"
        else:
            result["police_ratio"] = "N/A"

        # Facility gap
        recommended_facilities = max(1, latest_pop // 10000)
        all_facilities = (
            session.query(func.count(GovernmentFacility.id))
            .filter_by(barangay_id=barangay_id)
            .scalar()
        ) or 0
        result["facility_gap"] = max(0, recommended_facilities - all_facilities)

        return result
    finally:
        session.close()
```

- [ ] **Step 5: Commit**

```bash
git add services/forecast_service.py
git commit -m "feat: add food supply, transportation, and public safety forecasting (Phase 15)"
```

---

### Task 8: Add Forecast View Tabs

**Files:**
- Modify: `ui/views/forecast_view.py`

- [ ] **Step 1: Update imports**

At the top of `ui/views/forecast_view.py`, update the import:

```python
from services.forecast_service import (
    forecast_population, forecast_utility_demand,
    forecast_infrastructure_needs, get_all_barangays_for_forecast,
    forecast_food_supply, forecast_transportation, forecast_public_safety,
)
```

Also add `DANGER_COLOR` to the theme import if not present:

```python
from ui.theme import (
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_SMALL, FONT_SIZE_TITLE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_LIGHT, PRIMARY_COLOR, ACCENT_COLOR,
    WARNING_COLOR, SUCCESS_COLOR, DANGER_COLOR,
    CARD_BG, BG_COLOR, PADDING_LARGE, PADDING_NORMAL,
)
```

- [ ] **Step 2: Add 3 new tabs in _build_ui()**

After the Infrastructure tab block (~line 75), add:

```python
        # Food Supply tab
        food_tab = self._tabview.add("Food Supply")
        self._food_trend_label = ctk.CTkLabel(
            food_tab, text="", font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_SECONDARY,
        )
        self._food_trend_label.pack(anchor="w", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))
        self._food_status_label = ctk.CTkLabel(
            food_tab, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
        )
        self._food_status_label.pack(anchor="w", padx=PADDING_NORMAL, pady=(0, 5))
        self._food_chart = ChartWidget(food_tab, figsize=(7, 3))
        self._food_chart.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

        # Transportation tab
        trans_tab = self._tabview.add("Transportation")
        self._trans_trend_label = ctk.CTkLabel(
            trans_tab, text="", font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_SECONDARY,
        )
        self._trans_trend_label.pack(anchor="w", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))
        self._trans_status_label = ctk.CTkLabel(
            trans_tab, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
        )
        self._trans_status_label.pack(anchor="w", padx=PADDING_NORMAL, pady=(0, 5))
        self._trans_chart = ChartWidget(trans_tab, figsize=(7, 3))
        self._trans_chart.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

        # Public Safety tab
        safety_tab = self._tabview.add("Public Safety")
        self._safety_trend_label = ctk.CTkLabel(
            safety_tab, text="", font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_SECONDARY,
        )
        self._safety_trend_label.pack(anchor="w", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))
        self._safety_status_label = ctk.CTkLabel(
            safety_tab, text="", font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
        )
        self._safety_status_label.pack(anchor="w", padx=PADDING_NORMAL, pady=(0, 5))
        self._safety_chart = ChartWidget(safety_tab, figsize=(7, 3))
        self._safety_chart.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))
```

- [ ] **Step 3: Add update logic in _update_forecasts()**

At the end of `_update_forecasts()` (~after line 122), add:

```python
        # Food supply forecast
        food_data = forecast_food_supply(bid)
        gap = food_data.get("demand_gap", "balanced")
        gap_colors = {"surplus": SUCCESS_COLOR, "balanced": PRIMARY_COLOR, "deficit": DANGER_COLOR}
        self._food_status_label.configure(
            text=f"Demand Gap: {gap.capitalize()} — {food_data.get('notes', '')}",
            text_color=gap_colors.get(gap, TEXT_SECONDARY),
        )
        self._render_forecast_chart(
            self._food_chart, self._food_trend_label, food_data,
            title="Food Supply Demand Index", ylabel="Demand Index",
        )

        # Transportation forecast
        trans_data = forecast_transportation(bid)
        congestion = trans_data.get("congestion_level", "low")
        cong_colors = {"low": SUCCESS_COLOR, "moderate": WARNING_COLOR, "high": DANGER_COLOR, "critical": DANGER_COLOR}
        recs = trans_data.get("recommended_infrastructure", [])
        rec_text = " | ".join(recs) if recs else "No recommendations"
        self._trans_status_label.configure(
            text=f"Congestion: {congestion.capitalize()} — {rec_text}",
            text_color=cong_colors.get(congestion, TEXT_SECONDARY),
        )
        self._render_forecast_chart(
            self._trans_chart, self._trans_trend_label, trans_data,
            title="Transportation Congestion Index", ylabel="Congestion Index",
        )

        # Public safety forecast
        safety_data = forecast_public_safety(bid)
        level = safety_data.get("safety_level", "safe")
        level_colors = {"safe": SUCCESS_COLOR, "moderate": WARNING_COLOR, "at_risk": DANGER_COLOR, "critical": DANGER_COLOR}
        self._safety_status_label.configure(
            text=f"Safety: {level.capitalize()} | {safety_data.get('police_ratio', 'N/A')} | Facility gap: {safety_data.get('facility_gap', 0)}",
            text_color=level_colors.get(level, TEXT_SECONDARY),
        )
        self._render_forecast_chart(
            self._safety_chart, self._safety_trend_label, safety_data,
            title="Public Safety Crime Rate Index", ylabel="Crime Rate (per 10K)",
        )
```

- [ ] **Step 4: Delete DB and test**

```bash
rm -f data/barangay_profiling.db
/c/laragon/bin/python/python-3.13/python.exe main.py
```

Verify: Login → Forecasting → 6 tabs visible (Population, Utilities, Infrastructure, Food Supply, Transportation, Public Safety) → select a barangay → charts render.

- [ ] **Step 5: Commit**

```bash
git add ui/views/forecast_view.py
git commit -m "feat: add Food Supply, Transportation, Public Safety forecast tabs (Phase 15)"
```

---

### Task 9: Add Crime Prevention Recommendations

**Files:**
- Modify: `services/plan_service.py`

- [ ] **Step 1: Add generate_crime_prevention_plan()**

At the end of `services/plan_service.py`, add:

```python
def generate_crime_prevention_plan(barangay_id: int) -> dict | None:
    """Generate a crime prevention plan with patrol schedules, CCTV recs, and community programs."""
    session = get_session()
    try:
        brgy = session.get(Barangay, barangay_id)
        if not brgy:
            return None

        cutoff_1yr = date.today() - timedelta(days=365)
        cutoff_2yr = date.today() - timedelta(days=730)

        # Crime summary
        recent_crimes = (
            session.query(CrimeIncident)
            .filter(CrimeIncident.barangay_id == barangay_id,
                    CrimeIncident.date_occurred >= cutoff_1yr)
            .all()
        )
        prev_crimes = (
            session.query(CrimeIncident)
            .filter(CrimeIncident.barangay_id == barangay_id,
                    CrimeIncident.date_occurred >= cutoff_2yr,
                    CrimeIncident.date_occurred < cutoff_1yr)
            .all()
        )

        total_recent = len(recent_crimes)
        total_prev = len(prev_crimes)

        # Trend
        if total_prev > 0:
            trend_pct = round(((total_recent - total_prev) / total_prev) * 100, 1)
        else:
            trend_pct = 0.0

        if trend_pct > 10:
            trend = "increasing"
        elif trend_pct < -10:
            trend = "decreasing"
        else:
            trend = "stable"

        # Top types
        type_counts = {}
        for c in recent_crimes:
            type_counts[c.crime_type] = type_counts.get(c.crime_type, 0) + 1
        top_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        crime_summary = {
            "total_incidents": total_recent,
            "top_types": [{"type": t, "count": c} for t, c in top_types],
            "trend": trend,
            "trend_pct": trend_pct,
        }

        # Patrol schedule
        patrol_schedule = [
            {
                "shift": "Morning (6AM-2PM)",
                "priority": "medium",
                "focus_areas": ["School zones", "Market areas", "Public parks"],
            },
            {
                "shift": "Afternoon (2PM-10PM)",
                "priority": "high" if total_recent >= 10 else "medium",
                "focus_areas": ["Commercial areas", "Transport terminals", "Busy intersections"],
            },
            {
                "shift": "Night (10PM-6AM)",
                "priority": "high",
                "focus_areas": ["Dark alleys and unlit streets", "Residential perimeters", "Establishments"],
            },
        ]

        # CCTV recommendations
        cctv_recommendations = []
        if total_recent >= 5:
            cctv_recommendations.append({
                "location_desc": "Main entry/exit points of the barangay",
                "priority": "high",
                "reason": f"High traffic area with {total_recent} incidents in 12 months",
            })
        if type_counts.get("theft", 0) >= 2 or type_counts.get("robbery", 0) >= 2:
            cctv_recommendations.append({
                "location_desc": "Commercial and market areas",
                "priority": "high",
                "reason": "Theft/robbery hotspot",
            })
        if total_recent >= 3:
            cctv_recommendations.append({
                "location_desc": "Barangay hall and public facilities perimeter",
                "priority": "medium",
                "reason": "Public safety monitoring",
            })

        # Community programs
        community_programs = []
        program_triggers = {
            "drugs": {
                "name": "Anti-Drug Awareness & Rehabilitation Referral",
                "target_group": "At-risk youth and affected families",
                "description": "Partner with PDEA and DSWD for drug awareness seminars and rehabilitation program referrals.",
            },
            "theft": {
                "name": "Livelihood Training Program",
                "target_group": "Unemployed and underemployed residents",
                "description": "Skills training and micro-enterprise support to address economic roots of theft.",
            },
            "robbery": {
                "name": "Economic Development & Livelihood Support",
                "target_group": "Low-income households",
                "description": "DSWD coordination for livelihood grants and employment assistance.",
            },
            "assault": {
                "name": "Conflict Resolution & Mediation Program",
                "target_group": "Community members and families",
                "description": "Barangay-level conflict resolution training and community mediation services.",
            },
            "domestic_violence": {
                "name": "VAWC Support & Family Welfare",
                "target_group": "Victims and at-risk families",
                "description": "Strengthen VAWC desk, partner with DSWD for counseling and shelter services.",
            },
        }

        for crime_type, count in type_counts.items():
            ct_lower = crime_type.lower()
            for trigger_key, program in program_triggers.items():
                if trigger_key in ct_lower and count >= 2:
                    prog = dict(program)
                    prog["triggered_by"] = f"{crime_type} ({count} incidents)"
                    community_programs.append(prog)
                    break

        # Always add neighborhood watch if crime count >= 5
        if total_recent >= 5:
            community_programs.append({
                "name": "Neighborhood Watch & Barangay Tanod Strengthening",
                "target_group": "All community members",
                "description": "Organize block-level neighborhood watch groups and strengthen barangay tanod patrols.",
                "triggered_by": f"General high crime ({total_recent} incidents)",
            })

        # Youth engagement for any significant crime
        if total_recent >= 3:
            community_programs.append({
                "name": "Youth Engagement & After-School Programs",
                "target_group": "Youth aged 13-21",
                "description": "Sports leagues, skills workshops, and mentorship programs to keep youth engaged.",
                "triggered_by": f"Crime prevention through youth engagement",
            })

        return {
            "barangay_name": brgy.name,
            "district_name": brgy.district.name,
            "generated_date": date.today().strftime("%Y-%m-%d"),
            "crime_summary": crime_summary,
            "patrol_schedule": patrol_schedule,
            "cctv_recommendations": cctv_recommendations,
            "community_programs": community_programs,
        }
    finally:
        session.close()
```

- [ ] **Step 2: Commit**

```bash
git add services/plan_service.py
git commit -m "feat: add crime prevention plan generator (Phase 15)"
```

---

### Task 10: Add Crime Prevention Tab to Action Plan View

**Files:**
- Modify: `ui/views/action_plan_view.py`

- [ ] **Step 1: Add import**

At the top of `ui/views/action_plan_view.py`, update the plan_service import:

```python
from services.plan_service import generate_action_plan, generate_crime_prevention_plan
```

- [ ] **Step 2: Wrap existing UI in CTkTabview**

Replace the `_build_ui` method. The key change: move the title outside the tabview, create a tabview, put existing action plan UI in Tab 1, and add crime prevention in Tab 2.

Replace the `_build_ui()` method entirely with:

```python
    def _build_ui(self):
        ctk.CTkLabel(
            self, text="Action Plans",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_NORMAL))

        # Shared selector row
        selector = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=12)
        selector.pack(fill="x", padx=PADDING_LARGE, pady=(0, PADDING_NORMAL))

        inner = ctk.CTkFrame(selector, fg_color="transparent")
        inner.pack(fill="x", padx=PADDING_NORMAL, pady=PADDING_NORMAL)

        district_names = [d["name"] for d in self._districts]
        self._district_dd = LabeledDropdown(
            inner, label="District", values=district_names,
            command=self._on_district_change,
        )
        self._district_dd.pack(side="left", padx=(0, 10), fill="x", expand=True)

        self._barangay_dd = LabeledDropdown(inner, label="Barangay", values=[])
        self._barangay_dd.pack(side="left", padx=(0, 10), fill="x", expand=True)

        # Tabview
        self._tabview = ctk.CTkTabview(self, fg_color=CARD_BG, corner_radius=12)
        self._tabview.pack(fill="both", expand=True, padx=PADDING_LARGE, pady=(0, PADDING_LARGE))

        # Tab 1: Action Plan (existing)
        plan_tab = self._tabview.add("Action Plan")
        btn_row = ctk.CTkFrame(plan_tab, fg_color="transparent")
        btn_row.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        ctk.CTkButton(
            btn_row, text="Generate Plan", command=self._generate,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg_color=PRIMARY_COLOR, text_color=TEXT_LIGHT, width=140, height=38,
        ).pack(side="left", padx=(0, 5))

        self._export_btn = ctk.CTkButton(
            btn_row, text="Export PDF", command=self._export_pdf,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg_color=ACCENT_COLOR, text_color=TEXT_LIGHT, width=120, height=38,
            state="disabled",
        )
        self._export_btn.pack(side="left")

        self._results = ctk.CTkScrollableFrame(plan_tab, fg_color="transparent")
        self._results.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

        self._placeholder = ctk.CTkLabel(
            self._results, text="Select a barangay and click 'Generate Plan' to create an action plan.",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_SECONDARY,
        )
        self._placeholder.pack(pady=40)

        # Tab 2: Crime Prevention
        crime_tab = self._tabview.add("Crime Prevention")
        crime_btn_row = ctk.CTkFrame(crime_tab, fg_color="transparent")
        crime_btn_row.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        ctk.CTkButton(
            crime_btn_row, text="Generate Crime Prevention Plan",
            command=self._generate_crime_plan,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            fg_color=PRIMARY_COLOR, text_color=TEXT_LIGHT, width=260, height=38,
        ).pack(side="left")

        self._crime_results = ctk.CTkScrollableFrame(crime_tab, fg_color="transparent")
        self._crime_results.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

        ctk.CTkLabel(
            self._crime_results, text="Select a barangay and click 'Generate Crime Prevention Plan'.",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_SECONDARY,
        ).pack(pady=40)

        if district_names:
            self._on_district_change(district_names[0])
```

- [ ] **Step 3: Add crime plan generation and rendering methods**

Add after the `_export_pdf` method:

```python
    def _generate_crime_plan(self):
        brgy_name = self._barangay_dd.get()
        brgy_id = self._barangay_map.get(brgy_name)
        if not brgy_id:
            MessageDialog(self, title="Error", message="Please select a barangay.", dialog_type="error")
            return

        data = generate_crime_prevention_plan(brgy_id)
        if not data:
            MessageDialog(self, title="Error", message="Could not generate plan.", dialog_type="error")
            return

        self._render_crime_plan(data)

    def _render_crime_plan(self, data: dict):
        for w in self._crime_results.winfo_children():
            w.destroy()

        # Header
        ctk.CTkLabel(
            self._crime_results,
            text=f"Crime Prevention Plan: Brgy. {data['barangay_name']}",
            font=(FONT_FAMILY, 18, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 2))

        ctk.CTkLabel(
            self._crime_results,
            text=f"{data['district_name']}  |  Generated: {data['generated_date']}",
            font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
        ).pack(anchor="w", padx=PADDING_NORMAL, pady=(0, 15))

        summary = data["crime_summary"]

        # Crime Summary Card
        summary_card = ctk.CTkFrame(self._crime_results, fg_color="#FAFAFA", corner_radius=10)
        summary_card.pack(fill="x", padx=PADDING_NORMAL, pady=5)

        ctk.CTkLabel(
            summary_card, text="\U0001F4CA Crime Summary",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        trend_color = {"increasing": DANGER_COLOR, "decreasing": ACCENT_COLOR, "stable": TEXT_SECONDARY}
        ctk.CTkLabel(
            summary_card,
            text=f"Total incidents (12mo): {summary['total_incidents']}  |  Trend: {summary['trend'].capitalize()} ({summary['trend_pct']:+.1f}%)",
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            text_color=trend_color.get(summary["trend"], TEXT_SECONDARY),
        ).pack(anchor="w", padx=PADDING_NORMAL, pady=(0, 5))

        if summary["top_types"]:
            types_text = ", ".join(f"{t['type']} ({t['count']})" for t in summary["top_types"])
            ctk.CTkLabel(
                summary_card, text=f"Top types: {types_text}",
                font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
            ).pack(anchor="w", padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

        # Patrol Schedule
        patrol_card = ctk.CTkFrame(self._crime_results, fg_color="#FAFAFA", corner_radius=10)
        patrol_card.pack(fill="x", padx=PADDING_NORMAL, pady=5)

        ctk.CTkLabel(
            patrol_card, text="\U0001F6A8 Patrol Schedule",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        for sched in data["patrol_schedule"]:
            priority_color = PRIORITY_COLORS.get(sched["priority"].upper(), TEXT_SECONDARY)
            row = ctk.CTkFrame(patrol_card, fg_color="transparent")
            row.pack(fill="x", padx=PADDING_NORMAL, pady=2)

            ctk.CTkLabel(
                row, text=sched["priority"].upper(),
                font=(FONT_FAMILY, 9, "bold"), text_color=TEXT_LIGHT,
                fg_color=priority_color, corner_radius=4, padx=6, pady=2,
            ).pack(side="left", padx=(0, 8))

            ctk.CTkLabel(
                row, text=f"{sched['shift']} — {', '.join(sched['focus_areas'])}",
                font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_PRIMARY,
            ).pack(side="left")

        ctk.CTkFrame(patrol_card, height=8, fg_color="transparent").pack()

        # CCTV Recommendations
        if data["cctv_recommendations"]:
            cctv_card = ctk.CTkFrame(self._crime_results, fg_color="#FAFAFA", corner_radius=10)
            cctv_card.pack(fill="x", padx=PADDING_NORMAL, pady=5)

            ctk.CTkLabel(
                cctv_card, text="\U0001F4F7 CCTV Recommendations",
                font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), text_color=TEXT_PRIMARY,
            ).pack(anchor="w", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

            for rec in data["cctv_recommendations"]:
                row = ctk.CTkFrame(cctv_card, fg_color="transparent")
                row.pack(fill="x", padx=PADDING_NORMAL, pady=2)

                badge_color = DANGER_COLOR if rec["priority"] == "high" else WARNING_COLOR
                ctk.CTkLabel(
                    row, text=rec["priority"].upper(),
                    font=(FONT_FAMILY, 9, "bold"), text_color=TEXT_LIGHT,
                    fg_color=badge_color, corner_radius=4, padx=6, pady=2,
                ).pack(side="left", padx=(0, 8))

                ctk.CTkLabel(
                    row, text=f"{rec['location_desc']} — {rec['reason']}",
                    font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_PRIMARY,
                ).pack(side="left")

            ctk.CTkFrame(cctv_card, height=8, fg_color="transparent").pack()

        # Community Programs
        if data["community_programs"]:
            prog_card = ctk.CTkFrame(self._crime_results, fg_color="#FAFAFA", corner_radius=10)
            prog_card.pack(fill="x", padx=PADDING_NORMAL, pady=5)

            ctk.CTkLabel(
                prog_card, text="\U0001F465 Community Programs",
                font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"), text_color=TEXT_PRIMARY,
            ).pack(anchor="w", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

            for prog in data["community_programs"]:
                prow = ctk.CTkFrame(prog_card, fg_color="#F0F0F0", corner_radius=8)
                prow.pack(fill="x", padx=PADDING_NORMAL, pady=3)

                ctk.CTkLabel(
                    prow, text=prog["name"],
                    font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"), text_color=TEXT_PRIMARY,
                ).pack(anchor="w", padx=PADDING_NORMAL, pady=(8, 0))

                ctk.CTkLabel(
                    prow, text=f"Target: {prog['target_group']}  |  Triggered by: {prog['triggered_by']}",
                    font=(FONT_FAMILY, 10), text_color=PRIMARY_COLOR,
                ).pack(anchor="w", padx=PADDING_NORMAL, pady=2)

                ctk.CTkLabel(
                    prow, text=prog["description"],
                    font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
                    wraplength=700, justify="left",
                ).pack(anchor="w", padx=PADDING_NORMAL, pady=(0, 8))

            ctk.CTkFrame(prog_card, height=8, fg_color="transparent").pack()
```

- [ ] **Step 4: Delete DB and test**

```bash
rm -f data/barangay_profiling.db
/c/laragon/bin/python/python-3.13/python.exe main.py
```

Verify: Login → Action Plans → 2 tabs (Action Plan, Crime Prevention) → select barangay → Generate both plans → no errors.

- [ ] **Step 5: Commit**

```bash
git add ui/views/action_plan_view.py
git commit -m "feat: add Crime Prevention tab to Action Plans view (Phase 15)"
```

---

## Phase 16: Scheduling & Anomaly Detection

### Task 11: Add Phase 16 Models

**Files:**
- Modify: `database/models.py`

- [ ] **Step 1: Add DataCollectionSchedule and BarangaySubmissionStatus models**

At the end of `database/models.py`, after the `RecordHistory` class, add:

```python
# ── Data Collection Scheduling ──────────────────────────────

class DataCollectionSchedule(TimestampMixin, Base):
    __tablename__ = "data_collection_schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False, unique=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, default="upcoming")  # upcoming/active/closed
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    notes = Column(Text, nullable=True)

    creator = relationship("User")


class BarangaySubmissionStatus(TimestampMixin, Base):
    __tablename__ = "barangay_submission_status"
    __table_args__ = (
        UniqueConstraint("barangay_id", "year", name="uq_submission_status_barangay_year"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    barangay_id = Column(Integer, ForeignKey("barangays.id"), nullable=False)
    year = Column(Integer, nullable=False)
    population_submitted = Column(Boolean, default=False, nullable=False)
    income_submitted = Column(Boolean, default=False, nullable=False)
    utilities_submitted = Column(Boolean, default=False, nullable=False)
    crime_submitted = Column(Boolean, default=False, nullable=False)
    waste_submitted = Column(Boolean, default=False, nullable=False)
    is_complete = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    barangay = relationship("Barangay")
```

- [ ] **Step 2: Add ANOMALY_CHECK_INTERVAL to config.py**

At the end of `config.py`, add:

```python
ANOMALY_CHECK_INTERVAL = 5  # run anomaly detection every 5th dashboard refresh
```

- [ ] **Step 3: Add new permissions to roles.py**

In `auth/roles.py`, add `"manage_schedules"` and `"view_compliance"` to the ADMIN role permissions set. Add `"view_compliance"` to CITY_OFFICIAL and DISTRICT_COORDINATOR.

In `ROLE_PERMISSIONS`:

```python
    Role.ADMIN: {
        "view_data", "enter_data", "edit_data", "delete_data",
        "manage_users", "view_audit_log", "generate_reports", "export_data",
        "manage_departments", "approve_submissions", "view_system",
        "view_all_districts", "view_all_barangays",
        "manage_schedules", "view_compliance",
    },
    Role.CITY_OFFICIAL: {
        "view_data", "generate_reports", "export_data",
        "approve_submissions", "view_audit_log",
        "view_all_districts", "view_all_barangays",
        "view_compliance",
    },
    Role.DISTRICT_COORDINATOR: {
        "view_data", "enter_data", "edit_data",
        "generate_reports", "export_data",
        "approve_submissions",
        "view_compliance",
    },
```

- [ ] **Step 4: Delete DB and verify**

```bash
rm -f data/barangay_profiling.db
/c/laragon/bin/python/python-3.13/python.exe main.py
```

Verify the app starts. Close.

- [ ] **Step 5: Commit**

```bash
git add database/models.py config.py auth/roles.py
git commit -m "feat: add Phase 16 models (DataCollectionSchedule, BarangaySubmissionStatus) and permissions"
```

---

### Task 12: Create Schedule Service

**Files:**
- Create: `services/schedule_service.py`

- [ ] **Step 1: Write the schedule service**

Create `services/schedule_service.py`:

```python
import logging
from datetime import date, datetime
from database.db import get_session
from database.models import (
    DataCollectionSchedule, BarangaySubmissionStatus, Barangay,
    PopulationRecord, IncomeData, Utility, CrimeIncident, WasteManagement,
)
from services.audit_service import log_action
from services.notification_service import create_notification
from sqlalchemy import func, extract

logger = logging.getLogger(__name__)

# Maps submission status column -> (model, filter_type)
# filter_type: "year" means filter by year column, "date_year" means extract year from date
SUBMISSION_TABLE_MAP = {
    "population_submitted": (PopulationRecord, "year"),
    "income_submitted": (IncomeData, "year"),
    "utilities_submitted": (Utility, "year"),
    "crime_submitted": (CrimeIncident, "date_year"),
    "waste_submitted": (WasteManagement, "year"),
}


def create_schedule(year: int, start_date: date, end_date: date,
                    user_id: int, notes: str = "") -> tuple[bool, str]:
    """Create a new annual data collection schedule and initialize status rows."""
    session = get_session()
    try:
        existing = session.query(DataCollectionSchedule).filter_by(year=year).first()
        if existing:
            return False, f"Schedule for {year} already exists."

        schedule = DataCollectionSchedule(
            year=year,
            start_date=start_date,
            end_date=end_date,
            status="upcoming" if start_date > date.today() else "active",
            created_by=user_id,
            notes=notes,
        )
        session.add(schedule)
        session.flush()

        # Initialize submission status for all barangays
        barangays = session.query(Barangay).all()
        for brgy in barangays:
            status = BarangaySubmissionStatus(
                barangay_id=brgy.id,
                year=year,
            )
            session.add(status)

        session.commit()
        log_action(user_id, "CREATE", "data_collection_schedules", schedule.id,
                   new_values={"year": year, "start_date": str(start_date), "end_date": str(end_date)})

        return True, f"Schedule for {year} created with {len(barangays)} barangay tracking rows."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def get_schedule(year: int | None = None) -> dict | None:
    """Get schedule for a year, or current active schedule."""
    session = get_session()
    try:
        if year:
            sched = session.query(DataCollectionSchedule).filter_by(year=year).first()
        else:
            sched = session.query(DataCollectionSchedule).filter_by(status="active").first()

        if not sched:
            return None
        return {
            "id": sched.id,
            "year": sched.year,
            "start_date": sched.start_date.strftime("%Y-%m-%d") if sched.start_date else "",
            "end_date": sched.end_date.strftime("%Y-%m-%d") if sched.end_date else "",
            "status": sched.status,
            "notes": sched.notes or "",
            "created_by": sched.created_by,
        }
    finally:
        session.close()


def get_all_schedules() -> list[dict]:
    """All schedules ordered by year desc."""
    session = get_session()
    try:
        schedules = session.query(DataCollectionSchedule).order_by(DataCollectionSchedule.year.desc()).all()
        return [
            {
                "id": s.id,
                "year": s.year,
                "start_date": s.start_date.strftime("%Y-%m-%d") if s.start_date else "",
                "end_date": s.end_date.strftime("%Y-%m-%d") if s.end_date else "",
                "status": s.status,
                "notes": s.notes or "",
            }
            for s in schedules
        ]
    finally:
        session.close()


def update_schedule(schedule_id: int, user_id: int,
                    start_date: date | None = None, end_date: date | None = None,
                    status: str | None = None, notes: str | None = None) -> tuple[bool, str]:
    """Update schedule fields."""
    session = get_session()
    try:
        sched = session.get(DataCollectionSchedule, schedule_id)
        if not sched:
            return False, "Schedule not found."

        old_vals = {"status": sched.status}
        if start_date is not None:
            sched.start_date = start_date
        if end_date is not None:
            sched.end_date = end_date
        if status is not None:
            sched.status = status
        if notes is not None:
            sched.notes = notes

        session.commit()
        log_action(user_id, "UPDATE", "data_collection_schedules", sched.id,
                   old_values=old_vals, new_values={"status": sched.status})
        return True, "Schedule updated."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def get_compliance_dashboard(year: int) -> dict:
    """Return compliance status for all barangays for a given year."""
    session = get_session()
    try:
        sched = session.query(DataCollectionSchedule).filter_by(year=year).first()
        schedule_info = None
        if sched:
            schedule_info = {
                "start_date": sched.start_date.strftime("%Y-%m-%d") if sched.start_date else "",
                "end_date": sched.end_date.strftime("%Y-%m-%d") if sched.end_date else "",
                "status": sched.status,
            }

        statuses = (
            session.query(BarangaySubmissionStatus)
            .filter_by(year=year)
            .all()
        )

        total = len(statuses)
        complete = sum(1 for s in statuses if s.is_complete)
        incomplete = total - complete

        barangays = []
        for s in statuses:
            brgy = session.get(Barangay, s.barangay_id)
            if not brgy:
                continue
            missing = []
            for col, label in [
                ("population_submitted", "Population"),
                ("income_submitted", "Income"),
                ("utilities_submitted", "Utilities"),
                ("crime_submitted", "Crime"),
                ("waste_submitted", "Waste"),
            ]:
                if not getattr(s, col):
                    missing.append(label)

            barangays.append({
                "id": s.barangay_id,
                "name": brgy.name,
                "district_name": brgy.district.name if brgy.district else "",
                "population_submitted": s.population_submitted,
                "income_submitted": s.income_submitted,
                "utilities_submitted": s.utilities_submitted,
                "crime_submitted": s.crime_submitted,
                "waste_submitted": s.waste_submitted,
                "is_complete": s.is_complete,
                "missing_tables": missing,
            })

        barangays.sort(key=lambda b: (b["district_name"], b["name"]))

        return {
            "year": year,
            "schedule": schedule_info,
            "total_barangays": total,
            "complete_count": complete,
            "incomplete_count": incomplete,
            "completion_rate_pct": round((complete / total * 100) if total > 0 else 0, 1),
            "barangays": barangays,
        }
    finally:
        session.close()


def refresh_submission_status(barangay_id: int, year: int) -> None:
    """Recompute submission status by checking actual data tables."""
    session = get_session()
    try:
        status = (
            session.query(BarangaySubmissionStatus)
            .filter_by(barangay_id=barangay_id, year=year)
            .first()
        )
        if not status:
            return

        for col_name, (model, filter_type) in SUBMISSION_TABLE_MAP.items():
            if filter_type == "year":
                exists = session.query(model).filter_by(barangay_id=barangay_id, year=year).first() is not None
            else:  # date_year
                exists = (
                    session.query(model)
                    .filter(
                        model.barangay_id == barangay_id,
                        extract("year", model.date_occurred) == year,
                    )
                    .first()
                ) is not None
            setattr(status, col_name, exists)

        all_done = all(
            getattr(status, col) for col in SUBMISSION_TABLE_MAP.keys()
        )
        status.is_complete = all_done
        if all_done and not status.completed_at:
            status.completed_at = datetime.utcnow()

        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to refresh submission status: {e}")
    finally:
        session.close()


def check_overdue_and_notify(user_id: int) -> int:
    """Create notifications for overdue schedules with incomplete barangays."""
    session = get_session()
    try:
        overdue = (
            session.query(DataCollectionSchedule)
            .filter(
                DataCollectionSchedule.status == "active",
                DataCollectionSchedule.end_date < date.today(),
            )
            .all()
        )

        count = 0
        for sched in overdue:
            incomplete = (
                session.query(func.count(BarangaySubmissionStatus.id))
                .filter_by(year=sched.year, is_complete=False)
                .scalar()
            ) or 0

            if incomplete > 0:
                success, _ = create_notification(
                    user_id=user_id,
                    type="schedule_overdue",
                    title=f"Overdue: {sched.year} Data Collection",
                    message=f"{incomplete} barangays have not completed their submissions for {sched.year}. Deadline was {sched.end_date}.",
                    severity="warning",
                )
                if success:
                    count += 1

        return count
    finally:
        session.close()


def get_missing_submissions(year: int) -> list[dict]:
    """Return incomplete barangays with their missing table names."""
    session = get_session()
    try:
        statuses = (
            session.query(BarangaySubmissionStatus)
            .filter_by(year=year, is_complete=False)
            .all()
        )
        results = []
        for s in statuses:
            brgy = session.get(Barangay, s.barangay_id)
            if not brgy:
                continue
            missing = []
            for col, label in [
                ("population_submitted", "Population"),
                ("income_submitted", "Income"),
                ("utilities_submitted", "Utilities"),
                ("crime_submitted", "Crime"),
                ("waste_submitted", "Waste"),
            ]:
                if not getattr(s, col):
                    missing.append(label)
            results.append({
                "barangay_id": s.barangay_id,
                "barangay_name": brgy.name,
                "district_name": brgy.district.name if brgy.district else "",
                "missing_tables": missing,
            })
        return results
    finally:
        session.close()
```

- [ ] **Step 2: Commit**

```bash
git add services/schedule_service.py
git commit -m "feat: add schedule service for data collection management (Phase 16)"
```

---

### Task 13: Create Anomaly Service

**Files:**
- Create: `services/anomaly_service.py`

- [ ] **Step 1: Write the anomaly service**

Create `services/anomaly_service.py`:

```python
import logging
import numpy as np
from database.db import get_session
from database.models import (
    Barangay, PopulationRecord, IncomeData, Utility, CrimeIncident,
)
from services.notification_service import create_notification
from services.schedule_service import get_schedule
from sqlalchemy import func, extract

logger = logging.getLogger(__name__)

ANOMALY_THRESHOLD = 2.0  # standard deviations


def detect_all_anomalies(notify_user_id: int | None = None) -> list[dict]:
    """Run all anomaly detection checks. Optionally create notifications."""
    anomalies = []

    # Check missing submissions for active schedule
    schedule = get_schedule()
    if schedule:
        anomalies.extend(detect_missing_submissions(schedule["year"]))

    # Statistical anomalies
    anomalies.extend(detect_statistical_anomalies())

    # Optionally notify
    if notify_user_id and anomalies:
        trigger_anomaly_notifications(anomalies, [notify_user_id])

    return anomalies


def detect_missing_submissions(year: int) -> list[dict]:
    """Detect barangays with no data for a given year."""
    session = get_session()
    try:
        barangays = session.query(Barangay).all()
        anomalies = []

        checks = [
            ("population_records", PopulationRecord, "year"),
            ("income_data", IncomeData, "year"),
            ("utilities", Utility, "year"),
        ]

        for table_name, model, filter_type in checks:
            for brgy in barangays:
                if filter_type == "year":
                    exists = session.query(model).filter_by(
                        barangay_id=brgy.id, year=year
                    ).first()
                else:
                    exists = (
                        session.query(model)
                        .filter(
                            model.barangay_id == brgy.id,
                            extract("year", model.date_occurred) == year,
                        )
                        .first()
                    )

                if not exists:
                    anomalies.append({
                        "type": "missing",
                        "severity": "warning",
                        "barangay_id": brgy.id,
                        "barangay_name": brgy.name,
                        "table_name": table_name,
                        "field_name": "",
                        "message": f"No {table_name.replace('_', ' ')} data for {brgy.name} in {year}",
                        "current_value": None,
                        "historical_mean": None,
                        "std_dev": None,
                    })

        return anomalies
    finally:
        session.close()


def detect_statistical_anomalies() -> list[dict]:
    """Detect values that deviate >2 std devs from historical mean."""
    session = get_session()
    try:
        barangays = session.query(Barangay).all()
        anomalies = []

        for brgy in barangays:
            # Population
            pop_records = (
                session.query(PopulationRecord)
                .filter_by(barangay_id=brgy.id)
                .order_by(PopulationRecord.year)
                .all()
            )
            values = [(r.year, float(r.total_population)) for r in pop_records
                       if r.total_population is not None]
            anomaly = _check_metric_anomaly(values, brgy.id, brgy.name,
                                            "population_records", "total_population")
            if anomaly:
                anomalies.append(anomaly)

            # Income
            income_records = (
                session.query(IncomeData)
                .filter_by(barangay_id=brgy.id)
                .order_by(IncomeData.year)
                .all()
            )
            values = [(r.year, float(r.average_household_income)) for r in income_records
                       if r.average_household_income is not None]
            anomaly = _check_metric_anomaly(values, brgy.id, brgy.name,
                                            "income_data", "average_household_income")
            if anomaly:
                anomalies.append(anomaly)

            # Utility coverages
            util_records = (
                session.query(Utility)
                .filter_by(barangay_id=brgy.id)
                .order_by(Utility.year)
                .all()
            )
            for field in ["water_coverage_pct", "power_coverage_pct", "internet_coverage_pct"]:
                values = [(r.year, float(getattr(r, field))) for r in util_records
                           if getattr(r, field) is not None]
                anomaly = _check_metric_anomaly(values, brgy.id, brgy.name,
                                                "utilities", field)
                if anomaly:
                    anomalies.append(anomaly)

            # Crime count by year
            crime_years = (
                session.query(
                    extract("year", CrimeIncident.date_occurred).label("yr"),
                    func.count(CrimeIncident.id).label("cnt"),
                )
                .filter(CrimeIncident.barangay_id == brgy.id)
                .group_by("yr")
                .order_by("yr")
                .all()
            )
            values = [(int(r.yr), float(r.cnt)) for r in crime_years]
            anomaly = _check_metric_anomaly(values, brgy.id, brgy.name,
                                            "crime_incidents", "yearly_count")
            if anomaly:
                anomalies.append(anomaly)

        return anomalies
    finally:
        session.close()


def _check_metric_anomaly(
    values: list[tuple[int, float]],
    barangay_id: int,
    barangay_name: str,
    table_name: str,
    field_name: str,
) -> dict | None:
    """Check if the latest value is anomalous (>2 std devs from historical mean).
    Requires at least 3 data points.
    """
    if len(values) < 3:
        return None

    historical = [v[1] for v in values[:-1]]
    latest_year, latest_value = values[-1]

    mean = float(np.mean(historical))
    std = float(np.std(historical))

    if std < 0.001:  # effectively constant
        return None

    z_score = abs(latest_value - mean) / std
    if z_score > ANOMALY_THRESHOLD:
        direction = "spike" if latest_value > mean else "drop"
        return {
            "type": direction,
            "severity": "error" if z_score > 3.0 else "warning",
            "barangay_id": barangay_id,
            "barangay_name": barangay_name,
            "table_name": table_name,
            "field_name": field_name,
            "message": (
                f"Unusual {direction} in {field_name.replace('_', ' ')} for {barangay_name} "
                f"(year {latest_year}): {latest_value:,.1f} vs historical mean {mean:,.1f}"
            ),
            "current_value": latest_value,
            "historical_mean": round(mean, 2),
            "std_dev": round(std, 2),
        }
    return None


def trigger_anomaly_notifications(anomalies: list[dict], admin_user_ids: list[int]) -> int:
    """Create notification entries for detected anomalies."""
    count = 0
    for anomaly in anomalies:
        for uid in admin_user_ids:
            success, _ = create_notification(
                user_id=uid,
                type="anomaly_detection",
                title=f"Data Anomaly: {anomaly['barangay_name']}",
                message=anomaly["message"],
                severity=anomaly["severity"],
            )
            if success:
                count += 1
    return count
```

- [ ] **Step 2: Commit**

```bash
git add services/anomaly_service.py
git commit -m "feat: add anomaly detection service (Phase 16)"
```

---

### Task 14: Create Schedule View

**Files:**
- Create: `ui/views/schedule_view.py`

- [ ] **Step 1: Write the schedule view**

Create `ui/views/schedule_view.py`:

```python
import customtkinter as ctk
from datetime import date
from ui.theme import (
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_SMALL, FONT_SIZE_TITLE,
    TEXT_PRIMARY, TEXT_SECONDARY, PRIMARY_COLOR, ACCENT_COLOR, WARNING_COLOR,
    SUCCESS_COLOR, DANGER_COLOR, TEXT_LIGHT,
    CARD_BG, BG_COLOR, PADDING_LARGE, PADDING_NORMAL,
)
from ui.dialogs.message_dialog import MessageDialog
from auth.auth_manager import AuthManager
from services.schedule_service import (
    create_schedule, get_all_schedules, update_schedule,
    get_compliance_dashboard, check_overdue_and_notify,
)


class ScheduleView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=BG_COLOR, **kwargs)
        self._auth = AuthManager()
        self._build_ui()

    def _build_ui(self):
        ctk.CTkLabel(
            self, text="Data Collection",
            font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_NORMAL))

        self._tabview = ctk.CTkTabview(self, fg_color=CARD_BG, corner_radius=12)
        self._tabview.pack(fill="both", expand=True, padx=PADDING_LARGE, pady=(0, PADDING_LARGE))

        self._build_schedules_tab(self._tabview.add("Schedules"))
        self._build_compliance_tab(self._tabview.add("Compliance"))

    # ── Tab 1: Schedules ─────────────────────────────────────

    def _build_schedules_tab(self, tab):
        # Create form
        form = ctk.CTkFrame(tab, fg_color="#F5F5F5", corner_radius=8)
        form.pack(fill="x", padx=PADDING_NORMAL, pady=PADDING_NORMAL)

        ctk.CTkLabel(form, text="Create New Schedule", font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
                     text_color=TEXT_PRIMARY).pack(anchor="w", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        row = ctk.CTkFrame(form, fg_color="transparent")
        row.pack(fill="x", padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

        ctk.CTkLabel(row, text="Year:", font=(FONT_FAMILY, FONT_SIZE_SMALL)).pack(side="left", padx=(0, 3))
        self._year_entry = ctk.CTkEntry(row, width=80, font=(FONT_FAMILY, FONT_SIZE_SMALL))
        self._year_entry.insert(0, str(date.today().year))
        self._year_entry.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(row, text="Start:", font=(FONT_FAMILY, FONT_SIZE_SMALL)).pack(side="left", padx=(0, 3))
        self._start_entry = ctk.CTkEntry(row, width=110, placeholder_text="YYYY-MM-DD",
                                          font=(FONT_FAMILY, FONT_SIZE_SMALL))
        self._start_entry.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(row, text="End:", font=(FONT_FAMILY, FONT_SIZE_SMALL)).pack(side="left", padx=(0, 3))
        self._end_entry = ctk.CTkEntry(row, width=110, placeholder_text="YYYY-MM-DD",
                                        font=(FONT_FAMILY, FONT_SIZE_SMALL))
        self._end_entry.pack(side="left", padx=(0, 10))

        ctk.CTkButton(row, text="Create", command=self._create_schedule,
                       font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
                       fg_color=PRIMARY_COLOR, text_color=TEXT_LIGHT, width=80, height=30,
                       ).pack(side="left")

        # Schedule list
        self._schedule_list = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self._schedule_list.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

    def _create_schedule(self):
        try:
            year = int(self._year_entry.get())
        except ValueError:
            MessageDialog(self, title="Error", message="Invalid year.", dialog_type="error")
            return

        try:
            parts = self._start_entry.get().split("-")
            start = date(int(parts[0]), int(parts[1]), int(parts[2]))
            parts = self._end_entry.get().split("-")
            end = date(int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError):
            MessageDialog(self, title="Error", message="Invalid date format. Use YYYY-MM-DD.", dialog_type="error")
            return

        user = self._auth.get_current_user()
        if not user:
            return

        success, msg = create_schedule(year, start, end, user.id)
        if success:
            MessageDialog(self, title="Success", message=msg, dialog_type="success")
            self._refresh_schedule_list()
        else:
            MessageDialog(self, title="Error", message=msg, dialog_type="error")

    def _refresh_schedule_list(self):
        for w in self._schedule_list.winfo_children():
            w.destroy()

        schedules = get_all_schedules()
        if not schedules:
            ctk.CTkLabel(self._schedule_list, text="No schedules created yet.",
                         font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_SECONDARY).pack(pady=20)
            return

        for sched in schedules:
            row = ctk.CTkFrame(self._schedule_list, fg_color="#F5F5F5", corner_radius=8)
            row.pack(fill="x", pady=3)

            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(fill="x", padx=PADDING_NORMAL, pady=8)

            status_colors = {"upcoming": PRIMARY_COLOR, "active": SUCCESS_COLOR, "closed": TEXT_SECONDARY}
            ctk.CTkLabel(
                info, text=sched["status"].upper(),
                font=(FONT_FAMILY, 9, "bold"), text_color=TEXT_LIGHT,
                fg_color=status_colors.get(sched["status"], TEXT_SECONDARY),
                corner_radius=4, padx=6, pady=2,
            ).pack(side="left", padx=(0, 8))

            ctk.CTkLabel(
                info, text=f"{sched['year']}  |  {sched['start_date']} to {sched['end_date']}",
                font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"), text_color=TEXT_PRIMARY,
            ).pack(side="left")

            if sched["notes"]:
                ctk.CTkLabel(
                    info, text=f"  ({sched['notes']})",
                    font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
                ).pack(side="left")

            if sched["status"] != "closed":
                user = self._auth.get_current_user()

                def close_sched(sid=sched["id"], uid=user.id if user else 0):
                    update_schedule(sid, uid, status="closed")
                    self._refresh_schedule_list()

                ctk.CTkButton(
                    info, text="Close", command=close_sched,
                    font=(FONT_FAMILY, FONT_SIZE_SMALL),
                    fg_color=DANGER_COLOR, text_color=TEXT_LIGHT, width=60, height=26,
                ).pack(side="right")

            if sched["status"] == "upcoming":
                user = self._auth.get_current_user()

                def activate_sched(sid=sched["id"], uid=user.id if user else 0):
                    update_schedule(sid, uid, status="active")
                    self._refresh_schedule_list()

                ctk.CTkButton(
                    info, text="Activate", command=activate_sched,
                    font=(FONT_FAMILY, FONT_SIZE_SMALL),
                    fg_color=SUCCESS_COLOR, text_color=TEXT_LIGHT, width=70, height=26,
                ).pack(side="right", padx=(0, 5))

    # ── Tab 2: Compliance ────────────────────────────────────

    def _build_compliance_tab(self, tab):
        ctrl = ctk.CTkFrame(tab, fg_color="transparent")
        ctrl.pack(fill="x", padx=PADDING_NORMAL, pady=PADDING_NORMAL)

        ctk.CTkLabel(ctrl, text="Year:", font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
                     text_color=TEXT_PRIMARY).pack(side="left", padx=(0, 5))

        self._compliance_year = ctk.CTkEntry(ctrl, width=80, font=(FONT_FAMILY, FONT_SIZE_SMALL))
        self._compliance_year.insert(0, str(date.today().year))
        self._compliance_year.pack(side="left", padx=(0, 10))

        ctk.CTkButton(ctrl, text="Load", command=self._load_compliance,
                       font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
                       fg_color=PRIMARY_COLOR, text_color=TEXT_LIGHT, width=80, height=30,
                       ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(ctrl, text="Send Overdue Reminders", command=self._send_reminders,
                       font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
                       fg_color=WARNING_COLOR, text_color=TEXT_LIGHT, width=170, height=30,
                       ).pack(side="left")

        self._show_incomplete_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(ctrl, text="Show only incomplete", variable=self._show_incomplete_var,
                        command=self._load_compliance,
                        font=(FONT_FAMILY, FONT_SIZE_SMALL)).pack(side="left", padx=(15, 0))

        # Progress bar
        self._progress_frame = ctk.CTkFrame(tab, fg_color="transparent")
        self._progress_frame.pack(fill="x", padx=PADDING_NORMAL, pady=(0, 5))

        self._progress_bar = ctk.CTkProgressBar(self._progress_frame, width=400, height=16)
        self._progress_bar.set(0)
        self._progress_bar.pack(side="left", padx=(0, 10))

        self._progress_label = ctk.CTkLabel(self._progress_frame, text="0/0 (0%)",
                                             font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"),
                                             text_color=TEXT_PRIMARY)
        self._progress_label.pack(side="left")

        # Compliance table
        self._compliance_list = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        self._compliance_list.pack(fill="both", expand=True, padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))

    def _load_compliance(self):
        try:
            year = int(self._compliance_year.get())
        except ValueError:
            return

        data = get_compliance_dashboard(year)

        # Update progress
        total = data["total_barangays"]
        complete = data["complete_count"]
        rate = data["completion_rate_pct"]
        self._progress_bar.set(rate / 100 if total > 0 else 0)
        self._progress_label.configure(text=f"{complete}/{total} ({rate}%)")

        # Render table
        for w in self._compliance_list.winfo_children():
            w.destroy()

        if not data["barangays"]:
            ctk.CTkLabel(self._compliance_list,
                         text=f"No submission tracking data for {year}. Create a schedule first.",
                         font=(FONT_FAMILY, FONT_SIZE_NORMAL), text_color=TEXT_SECONDARY).pack(pady=20)
            return

        show_incomplete = self._show_incomplete_var.get()

        for brgy in data["barangays"]:
            if show_incomplete and brgy["is_complete"]:
                continue

            row = ctk.CTkFrame(self._compliance_list, fg_color="#F5F5F5", corner_radius=8)
            row.pack(fill="x", pady=2)

            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(fill="x", padx=PADDING_NORMAL, pady=6)

            # Completion badge
            if brgy["is_complete"]:
                ctk.CTkLabel(
                    info, text="COMPLETE", font=(FONT_FAMILY, 9, "bold"),
                    text_color=TEXT_LIGHT, fg_color=SUCCESS_COLOR,
                    corner_radius=4, padx=6, pady=2,
                ).pack(side="left", padx=(0, 8))
            else:
                ctk.CTkLabel(
                    info, text="INCOMPLETE", font=(FONT_FAMILY, 9, "bold"),
                    text_color=TEXT_LIGHT, fg_color=WARNING_COLOR,
                    corner_radius=4, padx=6, pady=2,
                ).pack(side="left", padx=(0, 8))

            ctk.CTkLabel(
                info, text=f"{brgy['name']}  ({brgy['district_name']})",
                font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"), text_color=TEXT_PRIMARY,
            ).pack(side="left")

            # Status icons
            checks = ctk.CTkFrame(info, fg_color="transparent")
            checks.pack(side="right")

            for col, label in [
                ("population_submitted", "Pop"),
                ("income_submitted", "Inc"),
                ("utilities_submitted", "Util"),
                ("crime_submitted", "Crime"),
                ("waste_submitted", "Waste"),
            ]:
                submitted = brgy[col]
                icon = "\u2713" if submitted else "\u2717"
                color = SUCCESS_COLOR if submitted else DANGER_COLOR
                ctk.CTkLabel(
                    checks, text=f"{label}:{icon}",
                    font=(FONT_FAMILY, 10), text_color=color,
                ).pack(side="left", padx=3)

    def _send_reminders(self):
        user = self._auth.get_current_user()
        if not user:
            return
        count = check_overdue_and_notify(user.id)
        MessageDialog(self, title="Reminders Sent",
                      message=f"Created {count} overdue notifications.",
                      dialog_type="success" if count > 0 else "info")

    def refresh(self):
        self._refresh_schedule_list()
        self._load_compliance()
```

- [ ] **Step 2: Commit**

```bash
git add ui/views/schedule_view.py
git commit -m "feat: add schedule view with schedules and compliance tabs (Phase 16)"
```

---

### Task 15: Enhance Dashboard with Compliance & Anomaly Alerts

**Files:**
- Modify: `ui/views/dashboard_view.py`

- [ ] **Step 1: Add imports**

At the top of `ui/views/dashboard_view.py`, add:

```python
from config import DASHBOARD_REFRESH_SECONDS, ANOMALY_CHECK_INTERVAL
from services.schedule_service import get_schedule, get_compliance_dashboard
from services.anomaly_service import detect_all_anomalies
```

Remove the existing `from config import DASHBOARD_REFRESH_SECONDS` line (replace with the updated one above).

- [ ] **Step 2: Add compliance and anomaly UI elements in _build_ui()**

After the `bottom_frame` section (~line 80, after the activity card grid), add:

```python
        # Compliance tracker
        compliance_card = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=12)
        compliance_card.pack(fill="x", padx=PADDING_LARGE, pady=(0, PADDING_NORMAL))

        compliance_header = ctk.CTkFrame(compliance_card, fg_color="transparent")
        compliance_header.pack(fill="x", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        ctk.CTkLabel(
            compliance_header, text="Data Collection Compliance",
            font=(FONT_FAMILY, 14, "bold"), text_color=TEXT_PRIMARY,
        ).pack(side="left")

        self._anomaly_badge = ctk.CTkLabel(
            compliance_header, text="",
            font=(FONT_FAMILY, FONT_SIZE_SMALL, "bold"), text_color=TEXT_LIGHT,
            fg_color=WARNING_COLOR, corner_radius=4, padx=8, pady=2,
        )
        self._anomaly_badge.pack(side="right")
        self._anomaly_badge.pack_forget()  # hidden by default

        self._compliance_progress = ctk.CTkProgressBar(compliance_card, width=400, height=14)
        self._compliance_progress.set(0)
        self._compliance_progress.pack(anchor="w", padx=PADDING_NORMAL, pady=(0, 3))

        self._compliance_label = ctk.CTkLabel(
            compliance_card, text="No active schedule",
            font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
        )
        self._compliance_label.pack(anchor="w", padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))
```

- [ ] **Step 3: Add anomaly check counter in __init__**

In `__init__` (~line 19), after `self._refresh_job = None`, add:

```python
        self._anomaly_check_counter = 0
        self._cached_anomalies = []
```

- [ ] **Step 4: Add compliance and anomaly refresh logic in refresh()**

At the end of the `refresh()` method, after the recent activity section, add:

```python
        # Compliance tracker
        schedule = get_schedule()
        if schedule:
            compliance = get_compliance_dashboard(schedule["year"])
            rate = compliance["completion_rate_pct"]
            self._compliance_progress.set(rate / 100)
            self._compliance_label.configure(
                text=f"{compliance['complete_count']}/{compliance['total_barangays']} barangays complete for {schedule['year']} ({rate}%)",
            )
        else:
            self._compliance_progress.set(0)
            self._compliance_label.configure(text="No active schedule")

        # Anomaly detection (throttled)
        self._anomaly_check_counter += 1
        if self._anomaly_check_counter >= ANOMALY_CHECK_INTERVAL:
            self._anomaly_check_counter = 0
            self._cached_anomalies = detect_all_anomalies()

        if self._cached_anomalies:
            count = len(self._cached_anomalies)
            self._anomaly_badge.configure(text=f"\u26A0 {count} anomalies detected")
            self._anomaly_badge.pack(side="right")
        else:
            self._anomaly_badge.pack_forget()
```

- [ ] **Step 5: Commit**

```bash
git add ui/views/dashboard_view.py
git commit -m "feat: add compliance tracker and anomaly alerts to dashboard (Phase 16)"
```

---

### Task 16: Wire Phase 16 Navigation & Integration

**Files:**
- Modify: `ui/components/sidebar.py`
- Modify: `ui/app.py`
- Modify: `services/submission_service.py`

- [ ] **Step 1: Add Data Collection to admin sidebar**

In `ui/components/sidebar.py`, in the `admin_items` list (~line 86-90), add before `("system", "System", "\u2699")`:

```python
            ("schedule", "Data Collection", "\U0001F4C5"),
```

So it reads:
```python
        admin_items = [
            ("users", "User Management", "\U0001F465"),
            ("audit_log", "Audit Log", "\U0001F4DC"),
            ("schedule", "Data Collection", "\U0001F4C5"),
            ("system", "System", "\u2699"),
        ]
```

- [ ] **Step 2: Register schedule view in app.py**

In `ui/app.py`, in the `_create_view()` method, add before the `elif view_key == "system":` block:

```python
        elif view_key == "schedule":
            from ui.views.schedule_view import ScheduleView
            return ScheduleView(self._content_frame)
```

- [ ] **Step 3: Hook submission status refresh into approval flow**

In `services/submission_service.py`, in the `approve_submission()` function, after the successful `_apply_submission` call and before `sub.status = "approved"` (~line 72), add:

```python
        # Refresh submission status tracking
        if sub.year:
            try:
                from services.schedule_service import refresh_submission_status
                refresh_submission_status(sub.barangay_id, sub.year)
            except Exception as e:
                logger.warning(f"Could not refresh submission status: {e}")
```

- [ ] **Step 4: Delete DB and test**

```bash
rm -f data/barangay_profiling.db
/c/laragon/bin/python/python-3.13/python.exe main.py
```

Verify:
1. Login as admin → "Data Collection" appears in admin section of sidebar
2. Click Data Collection → 2 tabs visible (Schedules, Compliance)
3. Create a schedule for 2026 (2026-01-01 to 2026-03-31)
4. Check Compliance tab → shows 182 barangays, all incomplete
5. Dashboard → compliance card shows 0/182 complete
6. No crashes

- [ ] **Step 5: Commit**

```bash
git add ui/components/sidebar.py ui/app.py services/submission_service.py
git commit -m "feat: wire Phase 16 navigation, schedule view, and submission status hook"
```

---

### Task 17: Seed Initial Schedule Data

**Files:**
- Modify: `database/seed.py`

- [ ] **Step 1: Add schedule seeding**

In `database/seed.py`, add an import for the new model and date:

```python
from database.models import DataCollectionSchedule, BarangaySubmissionStatus
from datetime import date
```

At the end of the seed function (after barangays are seeded), add:

```python
    # Seed initial data collection schedule for 2026
    existing_sched = session.query(DataCollectionSchedule).filter_by(year=2026).first()
    if not existing_sched:
        admin = session.query(User).filter_by(username="admin").first()
        if admin:
            sched = DataCollectionSchedule(
                year=2026,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 3, 31),
                status="active",
                created_by=admin.id,
                notes="Initial data collection cycle",
            )
            session.add(sched)
            session.flush()

            # Initialize status rows for all barangays
            barangays = session.query(Barangay).all()
            for brgy in barangays:
                status = BarangaySubmissionStatus(
                    barangay_id=brgy.id,
                    year=2026,
                )
                session.add(status)
            session.commit()
            logger.info(f"Seeded 2026 data collection schedule with {len(barangays)} tracking rows")
```

Note: Ensure `User` and `Barangay` are already imported in `seed.py`. Check existing imports and add if needed.

- [ ] **Step 2: Delete DB and verify**

```bash
rm -f data/barangay_profiling.db
/c/laragon/bin/python/python-3.13/python.exe main.py
```

Verify: Login → Dashboard → compliance card shows "0/182 barangays complete for 2026" → Data Collection → Schedules tab shows 2026 schedule with "ACTIVE" badge.

- [ ] **Step 3: Commit**

```bash
git add database/seed.py
git commit -m "feat: seed initial 2026 data collection schedule (Phase 16)"
```

---

## Verification

After all tasks are complete:

1. **Delete DB and fresh start**: `rm -f data/barangay_profiling.db`
2. **Launch**: `/c/laragon/bin/python/python-3.13/python.exe main.py`
3. **Login**: admin / admin123 → change password
4. **Dashboard**: Verify compliance card shows 0/182 for 2026, no anomaly badge on fresh data
5. **Comparisons** (sidebar): 4 tabs load, district comparison chart renders
6. **Forecasting**: 6 tabs load (Population, Utilities, Infrastructure, Food Supply, Transportation, Public Safety)
7. **Action Plans**: 2 tabs (Action Plan, Crime Prevention), both generate successfully
8. **Data Collection** (admin): Create/view schedules, compliance table with 182 rows
9. **Data Entry**: Enter a population record → go to Comparisons → Change History → verify field changes appear
10. **Sidebar order**: Dashboard, Barangays, Data Entry, Submissions, Reports, Analytics, **Comparisons**, Forecasting, Crime & Safety, Action Plans, Map, Notifications | Admin: Users, Audit Log, **Data Collection**, System
