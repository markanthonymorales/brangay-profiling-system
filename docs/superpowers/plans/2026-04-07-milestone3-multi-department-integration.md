# Milestone 3 Sub-Project 1: Multi-Department Data Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 4 new government department data domains (Health, Disaster, Education, Business Permits) with full CRUD, cross-department sync, and automated alert generation to the barangay profiling system.

**Architecture:** Service-layer pattern extending the existing codebase — 9 new SQLAlchemy models in `database/models.py`, 6 new service modules, 4 new CustomTkinter views, seed data in `database/real_data.py`, and a cross-department sync engine that generates alerts when multi-domain thresholds are crossed. All writes go through services that return `tuple[bool, str]` and trigger audit logging.

**Tech Stack:** Python 3.13, CustomTkinter, SQLAlchemy ORM, SQLite (WAL mode), matplotlib (FigureCanvasTkAgg)

**Python path:** `/c/laragon/bin/python/python-3.13/python.exe`

**Design spec:** `docs/superpowers/specs/2026-04-07-milestone3-multi-department-integration-design.md`

---

## File Structure

### Files to Create
| File | Responsibility |
|------|---------------|
| `services/health_service.py` | HealthStatistics CRUD + analytics queries |
| `services/social_welfare_service.py` | SocialWelfareData CRUD + analytics queries |
| `services/disaster_service.py` | DisasterRiskProfile, DisasterIncident, EmergencyResource CRUD + analytics |
| `services/education_service.py` | EducationStatistics CRUD + analytics queries |
| `services/business_permit_service.py` | BusinessPermit CRUD + analytics queries |
| `services/cross_department_service.py` | Sync tracking, threshold checks, alert generation |
| `ui/views/health_view.py` | Health & Welfare view (4 tabs) |
| `ui/views/disaster_view.py` | Disaster & Safety view (5 tabs) |
| `ui/views/education_view.py` | Education view (3 tabs) |
| `ui/views/business_permit_view.py` | Business Permits view (3 tabs) |

### Files to Modify
| File | Changes |
|------|---------|
| `database/models.py` | Add 9 new model classes + Barangay relationships + BarangaySubmissionStatus columns |
| `database/real_data.py` | Add seed data functions for all new domains |
| `services/history_service.py` | Add 9 entries to `TABLE_MODEL_MAP` |
| `services/validation_service.py` | Add required/percentage fields for new tables |
| `ui/components/sidebar.py` | Add 4 new nav items |
| `ui/app.py` | Add 4 new view cases in `_create_view` |
| `ui/views/dashboard_view.py` | Add cross-department KPI cards + alert summary |

### Key Reference Files
| File | Pattern to Follow |
|------|------------------|
| `services/crime_service.py` | Individual record CRUD (save/delete/get/stats/trend) |
| `services/population_service.py` | Summary-level upsert (query by barangay_id+year, update or create) |
| `ui/views/crime_view.py` | Multi-tab view with DataTable, filters, charts, CRUD dialogs |

---

## Phase 17: Models + Services + Seed Data

### Task 1: Add 9 New Models to database/models.py

**Files:**
- Modify: `database/models.py`

- [ ] **Step 1: Add Health & Social Welfare models**

Add after the `TrafficIncident` class (line ~310) and before the `Notification` class:

```python
# ── Health & Social Welfare ──────────────────────────────────

class HealthStatistics(TimestampMixin, Base):
    __tablename__ = "health_statistics"
    __table_args__ = (UniqueConstraint("barangay_id", "year", name="uq_health_barangay_year"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    barangay_id = Column(Integer, ForeignKey("barangays.id"), nullable=False)
    year = Column(Integer, nullable=False)
    dengue_cases = Column(Integer, nullable=True)
    tuberculosis_cases = Column(Integer, nullable=True)
    covid_cases = Column(Integer, nullable=True)
    diarrhea_cases = Column(Integer, nullable=True)
    pneumonia_cases = Column(Integer, nullable=True)
    hypertension_cases = Column(Integer, nullable=True)
    diabetes_cases = Column(Integer, nullable=True)
    other_disease_cases = Column(Integer, nullable=True)
    vaccination_coverage_pct = Column(Float, nullable=True)
    hospital_count = Column(Integer, nullable=True)
    clinic_count = Column(Integer, nullable=True)
    health_worker_count = Column(Integer, nullable=True)
    maternal_mortality = Column(Integer, nullable=True)
    infant_mortality = Column(Integer, nullable=True)
    malnutrition_rate = Column(Float, nullable=True)

    barangay = relationship("Barangay", back_populates="health_statistics")


class SocialWelfareData(TimestampMixin, Base):
    __tablename__ = "social_welfare_data"
    __table_args__ = (UniqueConstraint("barangay_id", "year", name="uq_social_welfare_barangay_year"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    barangay_id = Column(Integer, ForeignKey("barangays.id"), nullable=False)
    year = Column(Integer, nullable=False)
    fourps_beneficiaries = Column(Integer, nullable=True)
    senior_citizen_count = Column(Integer, nullable=True)
    pwd_count = Column(Integer, nullable=True)
    solo_parent_count = Column(Integer, nullable=True)
    indigent_families = Column(Integer, nullable=True)
    nutrition_program_beneficiaries = Column(Integer, nullable=True)

    barangay = relationship("Barangay", back_populates="social_welfare_data")
```

- [ ] **Step 2: Add Disaster models**

```python
# ── Disaster & Safety ────────────────────────────────────────

class DisasterRiskProfile(TimestampMixin, Base):
    __tablename__ = "disaster_risk_profiles"
    __table_args__ = (UniqueConstraint("barangay_id", "year", name="uq_disaster_risk_barangay_year"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    barangay_id = Column(Integer, ForeignKey("barangays.id"), nullable=False)
    year = Column(Integer, nullable=False)
    flood_prone = Column(Boolean, default=False, nullable=False)
    landslide_prone = Column(Boolean, default=False, nullable=False)
    fire_risk_level = Column(String(20), nullable=True)
    earthquake_risk = Column(String(20), nullable=True)
    storm_surge_risk = Column(String(20), nullable=True)
    evacuation_center_count = Column(Integer, nullable=True)
    evacuation_capacity = Column(Integer, nullable=True)

    barangay = relationship("Barangay", back_populates="disaster_risk_profiles")


class DisasterIncident(TimestampMixin, Base):
    __tablename__ = "disaster_incidents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    barangay_id = Column(Integer, ForeignKey("barangays.id"), nullable=False)
    disaster_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False, default="low")
    date_occurred = Column(Date, nullable=False)
    affected_families = Column(Integer, nullable=True)
    casualties = Column(Integer, nullable=True)
    damages_estimated = Column(Float, nullable=True)
    status = Column(String(20), nullable=False, default="reported")
    response_team = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)

    barangay = relationship("Barangay", back_populates="disaster_incidents")


class EmergencyResource(TimestampMixin, Base):
    __tablename__ = "emergency_resources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    barangay_id = Column(Integer, ForeignKey("barangays.id"), nullable=False)
    resource_type = Column(String(50), nullable=False)
    name = Column(String(200), nullable=False)
    quantity = Column(Float, nullable=True)
    unit = Column(String(50), nullable=True)
    location_description = Column(Text, nullable=True)
    last_restocked = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)

    barangay = relationship("Barangay", back_populates="emergency_resources")
```

- [ ] **Step 3: Add Education and Business Permit models**

```python
# ── Education ────────────────────────────────────────────────

class EducationStatistics(TimestampMixin, Base):
    __tablename__ = "education_statistics"
    __table_args__ = (UniqueConstraint("barangay_id", "year", name="uq_education_barangay_year"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    barangay_id = Column(Integer, ForeignKey("barangays.id"), nullable=False)
    year = Column(Integer, nullable=False)
    total_enrollees = Column(Integer, nullable=True)
    elementary_count = Column(Integer, nullable=True)
    highschool_count = Column(Integer, nullable=True)
    college_count = Column(Integer, nullable=True)
    out_of_school_youth = Column(Integer, nullable=True)
    literacy_rate = Column(Float, nullable=True)
    school_count = Column(Integer, nullable=True)
    teacher_count = Column(Integer, nullable=True)
    classroom_count = Column(Integer, nullable=True)
    dropout_rate = Column(Float, nullable=True)

    barangay = relationship("Barangay", back_populates="education_statistics")


# ── Business Permits ─────────────────────────────────────────

class BusinessPermit(TimestampMixin, Base):
    __tablename__ = "business_permits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    barangay_id = Column(Integer, ForeignKey("barangays.id"), nullable=False)
    business_name = Column(String(200), nullable=False)
    owner_name = Column(String(200), nullable=False)
    business_type = Column(String(100), nullable=True)
    permit_number = Column(String(50), nullable=True, unique=True)
    date_issued = Column(Date, nullable=True)
    date_expiry = Column(Date, nullable=True)
    status = Column(String(20), nullable=False, default="active")
    annual_revenue = Column(Float, nullable=True)
    employee_count = Column(Integer, nullable=True)
    address = Column(Text, nullable=True)

    barangay = relationship("Barangay", back_populates="business_permits")
```

- [ ] **Step 4: Add cross-department tracking models**

```python
# ── Cross-Department Sync & Alerts ───────────────────────────

class DepartmentDataSync(TimestampMixin, Base):
    __tablename__ = "department_data_sync"
    __table_args__ = (
        UniqueConstraint("department_name", "barangay_id", name="uq_dept_sync_dept_brgy"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    department_name = Column(String(100), nullable=False)
    barangay_id = Column(Integer, ForeignKey("barangays.id"), nullable=False)
    last_synced = Column(DateTime, nullable=True)
    sync_status = Column(String(20), nullable=False, default="pending")
    record_count = Column(Integer, nullable=True)
    synced_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    barangay = relationship("Barangay")
    user = relationship("User")


class CrossDepartmentAlert(TimestampMixin, Base):
    __tablename__ = "cross_department_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    barangay_id = Column(Integer, ForeignKey("barangays.id"), nullable=False)
    alert_type = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False, default="warning")
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=True)
    source_tables = Column(Text, nullable=True)
    is_resolved = Column(Boolean, default=False, nullable=False)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    barangay = relationship("Barangay")
    resolver = relationship("User")
```

- [ ] **Step 5: Add Barangay relationship back-references**

Add these lines inside the `Barangay` class (after line 117, after `traffic_incidents`):

```python
    health_statistics = relationship("HealthStatistics", back_populates="barangay")
    social_welfare_data = relationship("SocialWelfareData", back_populates="barangay")
    disaster_risk_profiles = relationship("DisasterRiskProfile", back_populates="barangay")
    disaster_incidents = relationship("DisasterIncident", back_populates="barangay")
    emergency_resources = relationship("EmergencyResource", back_populates="barangay")
    education_statistics = relationship("EducationStatistics", back_populates="barangay")
    business_permits = relationship("BusinessPermit", back_populates="barangay")
```

- [ ] **Step 6: Add BarangaySubmissionStatus columns**

Add these columns inside the `BarangaySubmissionStatus` class (after `waste_submitted`, before `is_complete`):

```python
    health_submitted = Column(Boolean, default=False, nullable=False)
    social_welfare_submitted = Column(Boolean, default=False, nullable=False)
    disaster_submitted = Column(Boolean, default=False, nullable=False)
    education_submitted = Column(Boolean, default=False, nullable=False)
    business_permits_submitted = Column(Boolean, default=False, nullable=False)
```

- [ ] **Step 7: Verify models compile**

Run: `/c/laragon/bin/python/python-3.13/python.exe -c "from database.models import *; print('All models loaded OK')"`

Expected: `All models loaded OK`

- [ ] **Step 8: Commit**

```bash
git add database/models.py
git commit -m "feat: add 9 new department data models (health, disaster, education, business permits, sync, alerts)"
```

---

### Task 2: Update history_service.py and validation_service.py

**Files:**
- Modify: `services/history_service.py`
- Modify: `services/validation_service.py`

- [ ] **Step 1: Update history_service.py imports and TABLE_MODEL_MAP**

Add to the import block at top of `services/history_service.py` (line 5-8):

```python
from database.models import (
    RecordHistory, User,
    PopulationRecord, IncomeData, Utility, WasteManagement,
    CrimeIncident, TrafficIncident, FoodSource, GovernmentFacility,
    ReligiousDemographic, Business, LandType, ResidentCategory,
    HealthStatistics, SocialWelfareData, DisasterRiskProfile,
    DisasterIncident, EmergencyResource, EducationStatistics,
    BusinessPermit, DepartmentDataSync, CrossDepartmentAlert,
)
```

Add to `TABLE_MODEL_MAP` dict (after `"resident_categories": ResidentCategory,`):

```python
    "health_statistics": HealthStatistics,
    "social_welfare_data": SocialWelfareData,
    "disaster_risk_profiles": DisasterRiskProfile,
    "disaster_incidents": DisasterIncident,
    "emergency_resources": EmergencyResource,
    "education_statistics": EducationStatistics,
    "business_permits": BusinessPermit,
    "department_data_sync": DepartmentDataSync,
    "cross_department_alerts": CrossDepartmentAlert,
```

- [ ] **Step 2: Update validation_service.py**

Add to `REQUIRED_FIELDS` dict:

```python
    "health_statistics": ["vaccination_coverage_pct"],
    "social_welfare_data": ["fourps_beneficiaries"],
    "education_statistics": ["total_enrollees", "school_count"],
    "disaster_risk_profiles": [],
    "business_permits": ["business_name", "owner_name"],
```

Add to `PERCENTAGE_FIELDS` dict:

```python
    "health_statistics": ["vaccination_coverage_pct", "malnutrition_rate"],
    "education_statistics": ["literacy_rate", "dropout_rate"],
```

- [ ] **Step 3: Verify imports**

Run: `/c/laragon/bin/python/python-3.13/python.exe -c "from services.history_service import TABLE_MODEL_MAP; print(f'{len(TABLE_MODEL_MAP)} tables mapped')"`

Expected: `21 tables mapped`

- [ ] **Step 4: Commit**

```bash
git add services/history_service.py services/validation_service.py
git commit -m "feat: register new department models in history and validation services"
```

---

### Task 3: Create health_service.py

**Files:**
- Create: `services/health_service.py`

- [ ] **Step 1: Create the health service**

Create `services/health_service.py` following the `population_service.py` upsert pattern:

```python
import logging
from sqlalchemy import func
from database.db import get_session
from database.models import HealthStatistics, Barangay, District
from services.audit_service import log_action
from services.history_service import record_field_changes

logger = logging.getLogger(__name__)

DISEASE_TYPES = ["dengue", "tuberculosis", "covid", "diarrhea", "pneumonia", "hypertension", "diabetes", "other"]


def save_health_statistics(barangay_id: int, year: int, data: dict,
                           user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        existing = (
            session.query(HealthStatistics)
            .filter_by(barangay_id=barangay_id, year=year)
            .first()
        )

        if existing:
            old_data = {c.key: getattr(existing, c.key) for c in existing.__table__.columns}
            old_values = {k: v for k, v in old_data.items() if k not in ("id", "created_at", "updated_at")}
            for key, value in data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            new_data = {c.key: getattr(existing, c.key) for c in existing.__table__.columns}
            record_field_changes("health_statistics", existing.id, old_data, new_data, user_id)
            session.commit()
            log_action(user_id, "UPDATE", "health_statistics", existing.id,
                       old_values=old_values, new_values=data)
            return True, "Health statistics updated."
        else:
            record = HealthStatistics(barangay_id=barangay_id, year=year, **data)
            session.add(record)
            session.commit()
            log_action(user_id, "CREATE", "health_statistics", record.id,
                       new_values={"barangay_id": barangay_id, "year": year, **data})
            return True, "Health statistics created."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def get_health_statistics(barangay_id: int) -> list[dict]:
    session = get_session()
    try:
        records = (
            session.query(HealthStatistics)
            .filter_by(barangay_id=barangay_id)
            .order_by(HealthStatistics.year.desc())
            .all()
        )
        return [
            {
                "id": r.id, "barangay_id": r.barangay_id, "year": r.year,
                "dengue_cases": r.dengue_cases, "tuberculosis_cases": r.tuberculosis_cases,
                "covid_cases": r.covid_cases, "diarrhea_cases": r.diarrhea_cases,
                "pneumonia_cases": r.pneumonia_cases, "hypertension_cases": r.hypertension_cases,
                "diabetes_cases": r.diabetes_cases, "other_disease_cases": r.other_disease_cases,
                "vaccination_coverage_pct": r.vaccination_coverage_pct,
                "hospital_count": r.hospital_count, "clinic_count": r.clinic_count,
                "health_worker_count": r.health_worker_count,
                "maternal_mortality": r.maternal_mortality, "infant_mortality": r.infant_mortality,
                "malnutrition_rate": r.malnutrition_rate,
            }
            for r in records
        ]
    finally:
        session.close()


def _get_brgy_ids(session, barangay_id=None, district_id=None) -> list[int] | None:
    if barangay_id:
        return [barangay_id]
    if district_id:
        return [b.id for b in session.query(Barangay.id).filter_by(district_id=district_id).all()]
    return None


def get_health_stats_by_year(year: int, district_id: int | None = None) -> list[dict]:
    session = get_session()
    try:
        query = session.query(HealthStatistics).join(Barangay).filter(HealthStatistics.year == year)
        if district_id:
            query = query.filter(Barangay.district_id == district_id)
        records = query.all()
        return [
            {
                "barangay_id": r.barangay_id, "barangay_name": r.barangay.name,
                "dengue_cases": r.dengue_cases or 0, "tuberculosis_cases": r.tuberculosis_cases or 0,
                "covid_cases": r.covid_cases or 0, "vaccination_coverage_pct": r.vaccination_coverage_pct or 0,
                "malnutrition_rate": r.malnutrition_rate or 0,
                "maternal_mortality": r.maternal_mortality or 0, "infant_mortality": r.infant_mortality or 0,
            }
            for r in records
        ]
    finally:
        session.close()


def get_disease_trend(barangay_id: int | None = None, district_id: int | None = None) -> list[dict]:
    session = get_session()
    try:
        brgy_ids = _get_brgy_ids(session, barangay_id, district_id)
        query = session.query(
            HealthStatistics.year,
            func.sum(HealthStatistics.dengue_cases).label("dengue"),
            func.sum(HealthStatistics.tuberculosis_cases).label("tb"),
            func.sum(HealthStatistics.covid_cases).label("covid"),
            func.sum(HealthStatistics.diarrhea_cases).label("diarrhea"),
            func.sum(HealthStatistics.pneumonia_cases).label("pneumonia"),
        )
        if brgy_ids:
            query = query.filter(HealthStatistics.barangay_id.in_(brgy_ids))
        rows = query.group_by(HealthStatistics.year).order_by(HealthStatistics.year).all()
        return [
            {"year": r[0], "dengue": r[1] or 0, "tb": r[2] or 0, "covid": r[3] or 0,
             "diarrhea": r[4] or 0, "pneumonia": r[5] or 0}
            for r in rows
        ]
    finally:
        session.close()


def get_health_summary(barangay_id: int | None = None, district_id: int | None = None,
                       year: int | None = None) -> dict:
    session = get_session()
    try:
        brgy_ids = _get_brgy_ids(session, barangay_id, district_id)
        query = session.query(HealthStatistics)
        if brgy_ids:
            query = query.filter(HealthStatistics.barangay_id.in_(brgy_ids))
        if year:
            query = query.filter(HealthStatistics.year == year)
        records = query.all()
        if not records:
            return {"total_disease_cases": 0, "avg_vaccination": 0, "avg_malnutrition": 0,
                    "total_hospitals": 0, "total_clinics": 0}

        total_diseases = sum(
            (r.dengue_cases or 0) + (r.tuberculosis_cases or 0) + (r.covid_cases or 0) +
            (r.diarrhea_cases or 0) + (r.pneumonia_cases or 0) + (r.hypertension_cases or 0) +
            (r.diabetes_cases or 0) + (r.other_disease_cases or 0)
            for r in records
        )
        vax = [r.vaccination_coverage_pct for r in records if r.vaccination_coverage_pct is not None]
        mal = [r.malnutrition_rate for r in records if r.malnutrition_rate is not None]
        return {
            "total_disease_cases": total_diseases,
            "avg_vaccination": round(sum(vax) / len(vax), 1) if vax else 0,
            "avg_malnutrition": round(sum(mal) / len(mal), 1) if mal else 0,
            "total_hospitals": sum(r.hospital_count or 0 for r in records),
            "total_clinics": sum(r.clinic_count or 0 for r in records),
        }
    finally:
        session.close()
```

- [ ] **Step 2: Verify import**

Run: `/c/laragon/bin/python/python-3.13/python.exe -c "from services.health_service import DISEASE_TYPES; print('health_service OK')"`

Expected: `health_service OK`

- [ ] **Step 3: Commit**

```bash
git add services/health_service.py
git commit -m "feat: add health_service with CRUD and analytics queries"
```

---

### Task 4: Create social_welfare_service.py

**Files:**
- Create: `services/social_welfare_service.py`

- [ ] **Step 1: Create the social welfare service**

```python
import logging
from sqlalchemy import func
from database.db import get_session
from database.models import SocialWelfareData, Barangay
from services.audit_service import log_action
from services.history_service import record_field_changes

logger = logging.getLogger(__name__)


def save_social_welfare_data(barangay_id: int, year: int, data: dict,
                             user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        existing = (
            session.query(SocialWelfareData)
            .filter_by(barangay_id=barangay_id, year=year)
            .first()
        )

        if existing:
            old_data = {c.key: getattr(existing, c.key) for c in existing.__table__.columns}
            old_values = {k: v for k, v in old_data.items() if k not in ("id", "created_at", "updated_at")}
            for key, value in data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            new_data = {c.key: getattr(existing, c.key) for c in existing.__table__.columns}
            record_field_changes("social_welfare_data", existing.id, old_data, new_data, user_id)
            session.commit()
            log_action(user_id, "UPDATE", "social_welfare_data", existing.id,
                       old_values=old_values, new_values=data)
            return True, "Social welfare data updated."
        else:
            record = SocialWelfareData(barangay_id=barangay_id, year=year, **data)
            session.add(record)
            session.commit()
            log_action(user_id, "CREATE", "social_welfare_data", record.id,
                       new_values={"barangay_id": barangay_id, "year": year, **data})
            return True, "Social welfare data created."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def get_social_welfare_data(barangay_id: int) -> list[dict]:
    session = get_session()
    try:
        records = (
            session.query(SocialWelfareData)
            .filter_by(barangay_id=barangay_id)
            .order_by(SocialWelfareData.year.desc())
            .all()
        )
        return [
            {
                "id": r.id, "barangay_id": r.barangay_id, "year": r.year,
                "fourps_beneficiaries": r.fourps_beneficiaries,
                "senior_citizen_count": r.senior_citizen_count,
                "pwd_count": r.pwd_count,
                "solo_parent_count": r.solo_parent_count,
                "indigent_families": r.indigent_families,
                "nutrition_program_beneficiaries": r.nutrition_program_beneficiaries,
            }
            for r in records
        ]
    finally:
        session.close()


def get_welfare_stats_by_year(year: int, district_id: int | None = None) -> list[dict]:
    session = get_session()
    try:
        query = session.query(SocialWelfareData).join(Barangay).filter(SocialWelfareData.year == year)
        if district_id:
            query = query.filter(Barangay.district_id == district_id)
        records = query.all()
        return [
            {
                "barangay_id": r.barangay_id, "barangay_name": r.barangay.name,
                "fourps_beneficiaries": r.fourps_beneficiaries or 0,
                "senior_citizen_count": r.senior_citizen_count or 0,
                "pwd_count": r.pwd_count or 0,
                "solo_parent_count": r.solo_parent_count or 0,
                "indigent_families": r.indigent_families or 0,
            }
            for r in records
        ]
    finally:
        session.close()


def get_welfare_summary(barangay_id: int | None = None, district_id: int | None = None,
                        year: int | None = None) -> dict:
    session = get_session()
    try:
        query = session.query(SocialWelfareData)
        if barangay_id:
            query = query.filter(SocialWelfareData.barangay_id == barangay_id)
        elif district_id:
            brgy_ids = [b.id for b in session.query(Barangay.id).filter_by(district_id=district_id).all()]
            query = query.filter(SocialWelfareData.barangay_id.in_(brgy_ids))
        if year:
            query = query.filter(SocialWelfareData.year == year)
        records = query.all()
        return {
            "total_fourps": sum(r.fourps_beneficiaries or 0 for r in records),
            "total_seniors": sum(r.senior_citizen_count or 0 for r in records),
            "total_pwd": sum(r.pwd_count or 0 for r in records),
            "total_solo_parents": sum(r.solo_parent_count or 0 for r in records),
            "total_indigent": sum(r.indigent_families or 0 for r in records),
        }
    finally:
        session.close()
```

- [ ] **Step 2: Verify import**

Run: `/c/laragon/bin/python/python-3.13/python.exe -c "from services.social_welfare_service import get_welfare_summary; print('social_welfare_service OK')"`

Expected: `social_welfare_service OK`

- [ ] **Step 3: Commit**

```bash
git add services/social_welfare_service.py
git commit -m "feat: add social_welfare_service with CRUD and analytics queries"
```

---

### Task 5: Create disaster_service.py

**Files:**
- Create: `services/disaster_service.py`

- [ ] **Step 1: Create the disaster service**

```python
import logging
from datetime import date, datetime, timedelta
from sqlalchemy import func
from database.db import get_session
from database.models import (
    DisasterRiskProfile, DisasterIncident, EmergencyResource, Barangay, District
)
from services.audit_service import log_action
from services.history_service import record_field_changes

logger = logging.getLogger(__name__)

DISASTER_TYPES = ["flood", "fire", "earthquake", "typhoon", "landslide", "storm_surge"]
RISK_LEVELS = ["low", "medium", "high"]
DISASTER_SEVERITY = ["low", "medium", "high", "critical"]
DISASTER_STATUSES = ["reported", "responding", "resolved", "recovery"]
RESOURCE_TYPES = ["food", "water", "medicine", "shelter", "equipment"]
RESOURCE_UNITS = ["packs", "liters", "boxes", "units", "persons", "kg"]


# ── Disaster Risk Profile CRUD ───────────────────────────────

def save_disaster_risk_profile(barangay_id: int, year: int, data: dict,
                               user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        existing = (
            session.query(DisasterRiskProfile)
            .filter_by(barangay_id=barangay_id, year=year)
            .first()
        )

        if existing:
            old_data = {c.key: getattr(existing, c.key) for c in existing.__table__.columns}
            old_values = {k: v for k, v in old_data.items() if k not in ("id", "created_at", "updated_at")}
            for key, value in data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            new_data = {c.key: getattr(existing, c.key) for c in existing.__table__.columns}
            record_field_changes("disaster_risk_profiles", existing.id, old_data, new_data, user_id)
            session.commit()
            log_action(user_id, "UPDATE", "disaster_risk_profiles", existing.id,
                       old_values=old_values, new_values=data)
            return True, "Disaster risk profile updated."
        else:
            record = DisasterRiskProfile(barangay_id=barangay_id, year=year, **data)
            session.add(record)
            session.commit()
            log_action(user_id, "CREATE", "disaster_risk_profiles", record.id,
                       new_values={"barangay_id": barangay_id, "year": year, **data})
            return True, "Disaster risk profile created."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def get_disaster_risk_profiles(barangay_id: int) -> list[dict]:
    session = get_session()
    try:
        records = (
            session.query(DisasterRiskProfile)
            .filter_by(barangay_id=barangay_id)
            .order_by(DisasterRiskProfile.year.desc())
            .all()
        )
        return [
            {
                "id": r.id, "barangay_id": r.barangay_id, "year": r.year,
                "flood_prone": r.flood_prone, "landslide_prone": r.landslide_prone,
                "fire_risk_level": r.fire_risk_level or "", "earthquake_risk": r.earthquake_risk or "",
                "storm_surge_risk": r.storm_surge_risk or "",
                "evacuation_center_count": r.evacuation_center_count,
                "evacuation_capacity": r.evacuation_capacity,
            }
            for r in records
        ]
    finally:
        session.close()


# ── Disaster Incident CRUD ───────────────────────────────────

def save_disaster_incident(barangay_id: int, data: dict, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        incident_id = data.pop("id", None)
        if incident_id:
            record = session.get(DisasterIncident, incident_id)
            if not record:
                return False, "Disaster incident not found."
            old_data = {c.key: getattr(record, c.key) for c in record.__table__.columns}
            old_values = {
                "disaster_type": record.disaster_type, "severity": record.severity,
                "status": record.status, "date_occurred": str(record.date_occurred),
            }
            for key, value in data.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            new_data = {c.key: getattr(record, c.key) for c in record.__table__.columns}
            record_field_changes("disaster_incidents", record.id, old_data, new_data, user_id)
            session.commit()
            log_action(user_id, "UPDATE", "disaster_incidents", record.id,
                       old_values=old_values, new_values=data)
            return True, "Disaster incident updated."
        else:
            record = DisasterIncident(barangay_id=barangay_id, **data)
            session.add(record)
            session.commit()
            log_action(user_id, "CREATE", "disaster_incidents", record.id,
                       new_values={"barangay_id": barangay_id, **{k: str(v) for k, v in data.items()}})
            return True, "Disaster incident recorded."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def delete_disaster_incident(incident_id: int, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        record = session.get(DisasterIncident, incident_id)
        if not record:
            return False, "Disaster incident not found."
        old_values = {"disaster_type": record.disaster_type, "barangay_id": record.barangay_id}
        session.delete(record)
        session.commit()
        log_action(user_id, "DELETE", "disaster_incidents", incident_id, old_values=old_values)
        return True, "Disaster incident deleted."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def get_disaster_incidents(barangay_id: int | None = None, disaster_type: str | None = None,
                           severity: str | None = None, status: str | None = None,
                           limit: int = 200) -> list[dict]:
    session = get_session()
    try:
        query = session.query(DisasterIncident).join(Barangay)
        if barangay_id:
            query = query.filter(DisasterIncident.barangay_id == barangay_id)
        if disaster_type:
            query = query.filter(DisasterIncident.disaster_type == disaster_type)
        if severity:
            query = query.filter(DisasterIncident.severity == severity)
        if status:
            query = query.filter(DisasterIncident.status == status)

        records = query.order_by(DisasterIncident.date_occurred.desc()).limit(limit).all()
        return [
            {
                "id": r.id, "barangay_id": r.barangay_id,
                "barangay_name": r.barangay.name,
                "district_name": r.barangay.district.name if r.barangay.district else "",
                "disaster_type": r.disaster_type, "severity": r.severity,
                "date_occurred": r.date_occurred.strftime("%Y-%m-%d") if r.date_occurred else "",
                "affected_families": r.affected_families or 0,
                "casualties": r.casualties or 0,
                "damages_estimated": r.damages_estimated or 0,
                "status": r.status, "response_team": r.response_team or "",
                "description": r.description or "",
            }
            for r in records
        ]
    finally:
        session.close()


# ── Emergency Resource CRUD ──────────────────────────────────

def save_emergency_resource(barangay_id: int, data: dict, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        resource_id = data.pop("id", None)
        if resource_id:
            record = session.get(EmergencyResource, resource_id)
            if not record:
                return False, "Emergency resource not found."
            old_data = {c.key: getattr(record, c.key) for c in record.__table__.columns}
            old_values = {"resource_type": record.resource_type, "name": record.name}
            for key, value in data.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            new_data = {c.key: getattr(record, c.key) for c in record.__table__.columns}
            record_field_changes("emergency_resources", record.id, old_data, new_data, user_id)
            session.commit()
            log_action(user_id, "UPDATE", "emergency_resources", record.id,
                       old_values=old_values, new_values=data)
            return True, "Emergency resource updated."
        else:
            record = EmergencyResource(barangay_id=barangay_id, **data)
            session.add(record)
            session.commit()
            log_action(user_id, "CREATE", "emergency_resources", record.id,
                       new_values={"barangay_id": barangay_id, **{k: str(v) for k, v in data.items()}})
            return True, "Emergency resource recorded."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def delete_emergency_resource(resource_id: int, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        record = session.get(EmergencyResource, resource_id)
        if not record:
            return False, "Emergency resource not found."
        old_values = {"resource_type": record.resource_type, "name": record.name}
        session.delete(record)
        session.commit()
        log_action(user_id, "DELETE", "emergency_resources", resource_id, old_values=old_values)
        return True, "Emergency resource deleted."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def get_emergency_resources(barangay_id: int | None = None, resource_type: str | None = None,
                            limit: int = 200) -> list[dict]:
    session = get_session()
    try:
        query = session.query(EmergencyResource).join(Barangay)
        if barangay_id:
            query = query.filter(EmergencyResource.barangay_id == barangay_id)
        if resource_type:
            query = query.filter(EmergencyResource.resource_type == resource_type)

        records = query.order_by(EmergencyResource.created_at.desc()).limit(limit).all()
        return [
            {
                "id": r.id, "barangay_id": r.barangay_id,
                "barangay_name": r.barangay.name,
                "resource_type": r.resource_type, "name": r.name,
                "quantity": r.quantity, "unit": r.unit or "",
                "location_description": r.location_description or "",
                "last_restocked": r.last_restocked.strftime("%Y-%m-%d") if r.last_restocked else "",
                "expiry_date": r.expiry_date.strftime("%Y-%m-%d") if r.expiry_date else "",
            }
            for r in records
        ]
    finally:
        session.close()


# ── Analytics Queries ────────────────────────────────────────

def _get_brgy_ids(session, barangay_id=None, district_id=None) -> list[int] | None:
    if barangay_id:
        return [barangay_id]
    if district_id:
        return [b.id for b in session.query(Barangay.id).filter_by(district_id=district_id).all()]
    return None


def get_disaster_stats(barangay_id: int | None = None, district_id: int | None = None) -> dict:
    session = get_session()
    try:
        brgy_ids = _get_brgy_ids(session, barangay_id, district_id)

        query = session.query(DisasterIncident.disaster_type, func.count(DisasterIncident.id))
        if brgy_ids:
            query = query.filter(DisasterIncident.barangay_id.in_(brgy_ids))
        by_type = dict(query.group_by(DisasterIncident.disaster_type).all())

        query = session.query(DisasterIncident.severity, func.count(DisasterIncident.id))
        if brgy_ids:
            query = query.filter(DisasterIncident.barangay_id.in_(brgy_ids))
        by_severity = dict(query.group_by(DisasterIncident.severity).all())

        query = session.query(func.count(DisasterIncident.id))
        if brgy_ids:
            query = query.filter(DisasterIncident.barangay_id.in_(brgy_ids))
        total = query.scalar() or 0

        query = session.query(func.sum(DisasterIncident.affected_families))
        if brgy_ids:
            query = query.filter(DisasterIncident.barangay_id.in_(brgy_ids))
        total_affected = query.scalar() or 0

        return {"total": total, "by_type": by_type, "by_severity": by_severity,
                "total_affected_families": total_affected}
    finally:
        session.close()


def get_disaster_trend(barangay_id: int | None = None, district_id: int | None = None) -> list[dict]:
    session = get_session()
    try:
        from sqlalchemy import extract
        brgy_ids = _get_brgy_ids(session, barangay_id, district_id)
        query = session.query(
            extract("year", DisasterIncident.date_occurred).label("yr"),
            extract("month", DisasterIncident.date_occurred).label("mo"),
            func.count(DisasterIncident.id),
        )
        if brgy_ids:
            query = query.filter(DisasterIncident.barangay_id.in_(brgy_ids))
        rows = query.group_by("yr", "mo").order_by("yr", "mo").all()
        return [{"year": int(r[0]), "month": int(r[1]), "count": r[2]} for r in rows]
    finally:
        session.close()


def get_high_risk_barangays_disaster(limit: int = 20) -> list[dict]:
    session = get_session()
    try:
        cutoff = date.today() - timedelta(days=365)
        query = (
            session.query(
                Barangay.id, Barangay.name,
                func.count(DisasterIncident.id).label("incident_count"),
            )
            .join(DisasterIncident, Barangay.id == DisasterIncident.barangay_id)
            .filter(DisasterIncident.date_occurred >= cutoff)
            .group_by(Barangay.id, Barangay.name)
            .order_by(func.count(DisasterIncident.id).desc())
            .limit(limit)
        )
        rows = query.all()
        result = []
        for brgy_id, brgy_name, count in rows:
            brgy = session.get(Barangay, brgy_id)
            district_name = brgy.district.name if brgy and brgy.district else ""
            common_type_row = (
                session.query(DisasterIncident.disaster_type, func.count(DisasterIncident.id))
                .filter(DisasterIncident.barangay_id == brgy_id, DisasterIncident.date_occurred >= cutoff)
                .group_by(DisasterIncident.disaster_type)
                .order_by(func.count(DisasterIncident.id).desc())
                .first()
            )
            common_type = common_type_row[0] if common_type_row else "N/A"
            result.append({
                "rank": len(result) + 1, "barangay_name": brgy_name,
                "district_name": district_name, "incident_count": count,
                "common_type": common_type,
            })
        return result
    finally:
        session.close()


def get_expiring_resources(days_ahead: int = 30) -> list[dict]:
    session = get_session()
    try:
        cutoff = date.today() + timedelta(days=days_ahead)
        records = (
            session.query(EmergencyResource)
            .join(Barangay)
            .filter(EmergencyResource.expiry_date != None, EmergencyResource.expiry_date <= cutoff)
            .order_by(EmergencyResource.expiry_date)
            .all()
        )
        today = date.today()
        return [
            {
                "id": r.id, "barangay_name": r.barangay.name,
                "resource_type": r.resource_type, "name": r.name,
                "quantity": r.quantity, "unit": r.unit or "",
                "expiry_date": r.expiry_date.strftime("%Y-%m-%d") if r.expiry_date else "",
                "is_expired": r.expiry_date < today if r.expiry_date else False,
            }
            for r in records
        ]
    finally:
        session.close()
```

- [ ] **Step 2: Verify import**

Run: `/c/laragon/bin/python/python-3.13/python.exe -c "from services.disaster_service import DISASTER_TYPES; print('disaster_service OK')"`

Expected: `disaster_service OK`

- [ ] **Step 3: Commit**

```bash
git add services/disaster_service.py
git commit -m "feat: add disaster_service with risk profiles, incidents, resources, and analytics"
```

---

### Task 6: Create education_service.py

**Files:**
- Create: `services/education_service.py`

- [ ] **Step 1: Create the education service**

```python
import logging
from sqlalchemy import func
from database.db import get_session
from database.models import EducationStatistics, Barangay
from services.audit_service import log_action
from services.history_service import record_field_changes

logger = logging.getLogger(__name__)


def save_education_statistics(barangay_id: int, year: int, data: dict,
                              user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        existing = (
            session.query(EducationStatistics)
            .filter_by(barangay_id=barangay_id, year=year)
            .first()
        )

        if existing:
            old_data = {c.key: getattr(existing, c.key) for c in existing.__table__.columns}
            old_values = {k: v for k, v in old_data.items() if k not in ("id", "created_at", "updated_at")}
            for key, value in data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            new_data = {c.key: getattr(existing, c.key) for c in existing.__table__.columns}
            record_field_changes("education_statistics", existing.id, old_data, new_data, user_id)
            session.commit()
            log_action(user_id, "UPDATE", "education_statistics", existing.id,
                       old_values=old_values, new_values=data)
            return True, "Education statistics updated."
        else:
            record = EducationStatistics(barangay_id=barangay_id, year=year, **data)
            session.add(record)
            session.commit()
            log_action(user_id, "CREATE", "education_statistics", record.id,
                       new_values={"barangay_id": barangay_id, "year": year, **data})
            return True, "Education statistics created."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def get_education_statistics(barangay_id: int) -> list[dict]:
    session = get_session()
    try:
        records = (
            session.query(EducationStatistics)
            .filter_by(barangay_id=barangay_id)
            .order_by(EducationStatistics.year.desc())
            .all()
        )
        return [
            {
                "id": r.id, "barangay_id": r.barangay_id, "year": r.year,
                "total_enrollees": r.total_enrollees,
                "elementary_count": r.elementary_count,
                "highschool_count": r.highschool_count,
                "college_count": r.college_count,
                "out_of_school_youth": r.out_of_school_youth,
                "literacy_rate": r.literacy_rate,
                "school_count": r.school_count,
                "teacher_count": r.teacher_count,
                "classroom_count": r.classroom_count,
                "dropout_rate": r.dropout_rate,
            }
            for r in records
        ]
    finally:
        session.close()


def get_education_stats_by_year(year: int, district_id: int | None = None) -> list[dict]:
    session = get_session()
    try:
        query = session.query(EducationStatistics).join(Barangay).filter(EducationStatistics.year == year)
        if district_id:
            query = query.filter(Barangay.district_id == district_id)
        records = query.all()
        return [
            {
                "barangay_id": r.barangay_id, "barangay_name": r.barangay.name,
                "total_enrollees": r.total_enrollees or 0,
                "literacy_rate": r.literacy_rate or 0,
                "dropout_rate": r.dropout_rate or 0,
                "out_of_school_youth": r.out_of_school_youth or 0,
                "school_count": r.school_count or 0,
            }
            for r in records
        ]
    finally:
        session.close()


def get_education_summary(barangay_id: int | None = None, district_id: int | None = None,
                          year: int | None = None) -> dict:
    session = get_session()
    try:
        query = session.query(EducationStatistics)
        if barangay_id:
            query = query.filter(EducationStatistics.barangay_id == barangay_id)
        elif district_id:
            brgy_ids = [b.id for b in session.query(Barangay.id).filter_by(district_id=district_id).all()]
            query = query.filter(EducationStatistics.barangay_id.in_(brgy_ids))
        if year:
            query = query.filter(EducationStatistics.year == year)
        records = query.all()
        if not records:
            return {"total_enrollees": 0, "avg_literacy": 0, "avg_dropout": 0,
                    "total_schools": 0, "total_osy": 0}
        lit = [r.literacy_rate for r in records if r.literacy_rate is not None]
        drop = [r.dropout_rate for r in records if r.dropout_rate is not None]
        return {
            "total_enrollees": sum(r.total_enrollees or 0 for r in records),
            "avg_literacy": round(sum(lit) / len(lit), 1) if lit else 0,
            "avg_dropout": round(sum(drop) / len(drop), 1) if drop else 0,
            "total_schools": sum(r.school_count or 0 for r in records),
            "total_osy": sum(r.out_of_school_youth or 0 for r in records),
        }
    finally:
        session.close()


def get_education_trend(barangay_id: int | None = None, district_id: int | None = None) -> list[dict]:
    session = get_session()
    try:
        query = session.query(EducationStatistics)
        if barangay_id:
            query = query.filter(EducationStatistics.barangay_id == barangay_id)
        elif district_id:
            brgy_ids = [b.id for b in session.query(Barangay.id).filter_by(district_id=district_id).all()]
            query = query.filter(EducationStatistics.barangay_id.in_(brgy_ids))

        from sqlalchemy import func as f
        rows = (
            session.query(
                EducationStatistics.year,
                f.sum(EducationStatistics.total_enrollees).label("enrollees"),
                f.avg(EducationStatistics.literacy_rate).label("avg_literacy"),
                f.avg(EducationStatistics.dropout_rate).label("avg_dropout"),
                f.sum(EducationStatistics.out_of_school_youth).label("osy"),
            )
        )
        if barangay_id:
            rows = rows.filter(EducationStatistics.barangay_id == barangay_id)
        elif district_id:
            brgy_ids = [b.id for b in session.query(Barangay.id).filter_by(district_id=district_id).all()]
            rows = rows.filter(EducationStatistics.barangay_id.in_(brgy_ids))

        results = rows.group_by(EducationStatistics.year).order_by(EducationStatistics.year).all()
        return [
            {"year": r[0], "enrollees": r[1] or 0, "avg_literacy": round(r[2] or 0, 1),
             "avg_dropout": round(r[3] or 0, 1), "osy": r[4] or 0}
            for r in results
        ]
    finally:
        session.close()
```

- [ ] **Step 2: Verify import**

Run: `/c/laragon/bin/python/python-3.13/python.exe -c "from services.education_service import get_education_summary; print('education_service OK')"`

Expected: `education_service OK`

- [ ] **Step 3: Commit**

```bash
git add services/education_service.py
git commit -m "feat: add education_service with CRUD and analytics queries"
```

---

### Task 7: Create business_permit_service.py

**Files:**
- Create: `services/business_permit_service.py`

- [ ] **Step 1: Create the business permit service**

```python
import logging
from datetime import date, timedelta
from sqlalchemy import func
from database.db import get_session
from database.models import BusinessPermit, Barangay
from services.audit_service import log_action
from services.history_service import record_field_changes

logger = logging.getLogger(__name__)

PERMIT_STATUSES = ["active", "expired", "revoked", "pending"]
BUSINESS_TYPES = ["retail", "food", "services", "manufacturing", "agriculture",
                  "construction", "transportation", "finance", "real_estate", "other"]


def save_business_permit(barangay_id: int, data: dict, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        permit_id = data.pop("id", None)
        if permit_id:
            record = session.get(BusinessPermit, permit_id)
            if not record:
                return False, "Business permit not found."
            old_data = {c.key: getattr(record, c.key) for c in record.__table__.columns}
            old_values = {
                "business_name": record.business_name, "status": record.status,
                "permit_number": record.permit_number,
            }
            for key, value in data.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            new_data = {c.key: getattr(record, c.key) for c in record.__table__.columns}
            record_field_changes("business_permits", record.id, old_data, new_data, user_id)
            session.commit()
            log_action(user_id, "UPDATE", "business_permits", record.id,
                       old_values=old_values, new_values=data)
            return True, "Business permit updated."
        else:
            record = BusinessPermit(barangay_id=barangay_id, **data)
            session.add(record)
            session.commit()
            log_action(user_id, "CREATE", "business_permits", record.id,
                       new_values={"barangay_id": barangay_id, **{k: str(v) for k, v in data.items()}})
            return True, "Business permit recorded."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def delete_business_permit(permit_id: int, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        record = session.get(BusinessPermit, permit_id)
        if not record:
            return False, "Business permit not found."
        old_values = {"business_name": record.business_name, "barangay_id": record.barangay_id}
        session.delete(record)
        session.commit()
        log_action(user_id, "DELETE", "business_permits", permit_id, old_values=old_values)
        return True, "Business permit deleted."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def get_business_permits(barangay_id: int | None = None, business_type: str | None = None,
                         status: str | None = None, limit: int = 200) -> list[dict]:
    session = get_session()
    try:
        query = session.query(BusinessPermit).join(Barangay)
        if barangay_id:
            query = query.filter(BusinessPermit.barangay_id == barangay_id)
        if business_type:
            query = query.filter(BusinessPermit.business_type == business_type)
        if status:
            query = query.filter(BusinessPermit.status == status)

        records = query.order_by(BusinessPermit.date_issued.desc()).limit(limit).all()
        return [
            {
                "id": r.id, "barangay_id": r.barangay_id,
                "barangay_name": r.barangay.name,
                "business_name": r.business_name, "owner_name": r.owner_name,
                "business_type": r.business_type or "",
                "permit_number": r.permit_number or "",
                "date_issued": r.date_issued.strftime("%Y-%m-%d") if r.date_issued else "",
                "date_expiry": r.date_expiry.strftime("%Y-%m-%d") if r.date_expiry else "",
                "status": r.status,
                "annual_revenue": r.annual_revenue or 0,
                "employee_count": r.employee_count or 0,
                "address": r.address or "",
            }
            for r in records
        ]
    finally:
        session.close()


def get_permit_stats(barangay_id: int | None = None, district_id: int | None = None) -> dict:
    session = get_session()
    try:
        query = session.query(BusinessPermit)
        if barangay_id:
            query = query.filter(BusinessPermit.barangay_id == barangay_id)
        elif district_id:
            brgy_ids = [b.id for b in session.query(Barangay.id).filter_by(district_id=district_id).all()]
            query = query.filter(BusinessPermit.barangay_id.in_(brgy_ids))

        by_type = dict(
            query.with_entities(BusinessPermit.business_type, func.count(BusinessPermit.id))
            .group_by(BusinessPermit.business_type).all()
        )
        by_status = dict(
            query.with_entities(BusinessPermit.status, func.count(BusinessPermit.id))
            .group_by(BusinessPermit.status).all()
        )
        total = query.count()
        total_revenue = query.with_entities(func.sum(BusinessPermit.annual_revenue)).scalar() or 0
        total_employees = query.with_entities(func.sum(BusinessPermit.employee_count)).scalar() or 0

        return {
            "total": total, "by_type": by_type, "by_status": by_status,
            "total_revenue": total_revenue, "total_employees": total_employees,
        }
    finally:
        session.close()


def get_expiring_permits(days_ahead: int = 30) -> list[dict]:
    session = get_session()
    try:
        cutoff = date.today() + timedelta(days=days_ahead)
        records = (
            session.query(BusinessPermit)
            .join(Barangay)
            .filter(
                BusinessPermit.date_expiry != None,
                BusinessPermit.date_expiry <= cutoff,
                BusinessPermit.status == "active",
            )
            .order_by(BusinessPermit.date_expiry)
            .all()
        )
        today = date.today()
        return [
            {
                "id": r.id, "barangay_name": r.barangay.name,
                "business_name": r.business_name, "owner_name": r.owner_name,
                "permit_number": r.permit_number or "",
                "date_expiry": r.date_expiry.strftime("%Y-%m-%d") if r.date_expiry else "",
                "is_expired": r.date_expiry < today if r.date_expiry else False,
            }
            for r in records
        ]
    finally:
        session.close()
```

- [ ] **Step 2: Verify import**

Run: `/c/laragon/bin/python/python-3.13/python.exe -c "from services.business_permit_service import PERMIT_STATUSES; print('business_permit_service OK')"`

Expected: `business_permit_service OK`

- [ ] **Step 3: Commit**

```bash
git add services/business_permit_service.py
git commit -m "feat: add business_permit_service with CRUD and analytics queries"
```

---

### Task 8: Create cross_department_service.py

**Files:**
- Create: `services/cross_department_service.py`

- [ ] **Step 1: Create the cross-department service**

```python
import logging
from datetime import datetime, timedelta, date
from database.db import get_session
from database.models import (
    DepartmentDataSync, CrossDepartmentAlert, HealthStatistics,
    SocialWelfareData, IncomeData, EducationStatistics, DisasterRiskProfile,
    PopulationRecord, DisasterIncident, BusinessPermit, EmergencyResource,
    Barangay, User,
)
from services.audit_service import log_action

logger = logging.getLogger(__name__)

DEPARTMENT_NAMES = ["health", "social_welfare", "disaster", "education", "business_permits"]

THRESHOLDS = {
    "disease_poverty_correlation": {
        "description": "High disease cases in high-poverty barangay",
        "severity": "warning",
    },
    "disaster_health_impact": {
        "description": "Active disaster + high disease/malnutrition",
        "severity": "critical",
    },
    "education_poverty_gap": {
        "description": "High dropout rate in high-poverty area",
        "severity": "warning",
    },
    "resource_shortage": {
        "description": "High-risk barangay with low emergency resources",
        "severity": "critical",
    },
    "business_disaster_impact": {
        "description": "Active disaster in area with many active permits",
        "severity": "warning",
    },
}


def on_department_data_saved(department_name: str, barangay_id: int, year: int, user_id: int):
    try:
        update_sync_status(department_name, barangay_id, user_id)
        triggered = check_cross_department_thresholds(barangay_id, year)
        for alert_data in triggered:
            _create_alert_if_new(barangay_id, alert_data, user_id)
    except Exception as e:
        logger.error(f"Cross-department hook error: {e}")


def update_sync_status(department_name: str, barangay_id: int, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        existing = (
            session.query(DepartmentDataSync)
            .filter_by(department_name=department_name, barangay_id=barangay_id)
            .first()
        )
        if existing:
            existing.last_synced = datetime.utcnow()
            existing.sync_status = "synced"
            existing.synced_by = user_id
        else:
            record = DepartmentDataSync(
                department_name=department_name,
                barangay_id=barangay_id,
                last_synced=datetime.utcnow(),
                sync_status="synced",
                synced_by=user_id,
            )
            session.add(record)
        session.commit()
        return True, "Sync status updated."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def check_cross_department_thresholds(barangay_id: int, year: int) -> list[dict]:
    session = get_session()
    try:
        health = session.query(HealthStatistics).filter_by(barangay_id=barangay_id, year=year).first()
        income = session.query(IncomeData).filter_by(barangay_id=barangay_id, year=year).first()
        education = session.query(EducationStatistics).filter_by(barangay_id=barangay_id, year=year).first()
        risk = session.query(DisasterRiskProfile).filter_by(barangay_id=barangay_id, year=year).first()
        population = session.query(PopulationRecord).filter_by(barangay_id=barangay_id, year=year).first()

        active_disasters = (
            session.query(DisasterIncident)
            .filter(
                DisasterIncident.barangay_id == barangay_id,
                DisasterIncident.status.in_(["reported", "responding"]),
            ).count()
        )
        active_permits = (
            session.query(BusinessPermit)
            .filter(BusinessPermit.barangay_id == barangay_id, BusinessPermit.status == "active")
            .count()
        )
        resource_count = session.query(EmergencyResource).filter_by(barangay_id=barangay_id).count()

        barangay = session.get(Barangay, barangay_id)
        brgy_name = barangay.name if barangay else f"Barangay #{barangay_id}"

        triggered = []

        # Calculate poverty percentage
        poverty_pct = 0
        if income and population and population.household_count and population.household_count > 0:
            poverty_pct = (income.below_poverty_count or 0) / population.household_count * 100

        # 1. Disease + Poverty
        dengue = (health.dengue_cases or 0) if health else 0
        if dengue >= 10 and poverty_pct >= 20:
            triggered.append({
                "alert_type": "disease_poverty_correlation",
                "severity": "warning",
                "title": f"Disease-Poverty Alert: {brgy_name}",
                "message": f"High dengue cases ({dengue}) in high-poverty area ({poverty_pct:.0f}% poverty rate).",
                "source_tables": '["health_statistics", "income_data"]',
            })

        # 2. Disaster + Health
        malnutrition = (health.malnutrition_rate or 0) if health else 0
        if active_disasters >= 1 and malnutrition >= 15:
            triggered.append({
                "alert_type": "disaster_health_impact",
                "severity": "critical",
                "title": f"Disaster-Health Crisis: {brgy_name}",
                "message": f"Active disaster ({active_disasters}) with high malnutrition ({malnutrition:.1f}%).",
                "source_tables": '["disaster_incidents", "health_statistics"]',
            })

        # 3. Education + Poverty
        dropout = (education.dropout_rate or 0) if education else 0
        if dropout >= 10 and poverty_pct >= 15:
            triggered.append({
                "alert_type": "education_poverty_gap",
                "severity": "warning",
                "title": f"Education-Poverty Gap: {brgy_name}",
                "message": f"High dropout rate ({dropout:.1f}%) in high-poverty area ({poverty_pct:.0f}%).",
                "source_tables": '["education_statistics", "income_data"]',
            })

        # 4. Resource shortage
        risk_flags = 0
        if risk:
            risk_flags += int(risk.flood_prone)
            risk_flags += int(risk.landslide_prone)
            risk_flags += int(risk.fire_risk_level == "high") if risk.fire_risk_level else 0
            risk_flags += int(risk.earthquake_risk == "high") if risk.earthquake_risk else 0
            risk_flags += int(risk.storm_surge_risk == "high") if risk.storm_surge_risk else 0
        if risk_flags >= 2 and resource_count < 3:
            triggered.append({
                "alert_type": "resource_shortage",
                "severity": "critical",
                "title": f"Resource Shortage Alert: {brgy_name}",
                "message": f"High-risk barangay ({risk_flags} risk flags) with only {resource_count} emergency resources.",
                "source_tables": '["disaster_risk_profiles", "emergency_resources"]',
            })

        # 5. Business + Disaster
        if active_disasters >= 1 and active_permits >= 20:
            triggered.append({
                "alert_type": "business_disaster_impact",
                "severity": "warning",
                "title": f"Business-Disaster Impact: {brgy_name}",
                "message": f"Active disaster affecting area with {active_permits} active business permits.",
                "source_tables": '["disaster_incidents", "business_permits"]',
            })

        return triggered
    finally:
        session.close()


def _create_alert_if_new(barangay_id: int, alert_data: dict, user_id: int):
    session = get_session()
    try:
        existing = (
            session.query(CrossDepartmentAlert)
            .filter_by(
                barangay_id=barangay_id,
                alert_type=alert_data["alert_type"],
                is_resolved=False,
            )
            .first()
        )
        if existing:
            return

        alert = CrossDepartmentAlert(
            barangay_id=barangay_id,
            alert_type=alert_data["alert_type"],
            severity=alert_data["severity"],
            title=alert_data["title"],
            message=alert_data.get("message"),
            source_tables=alert_data.get("source_tables"),
        )
        session.add(alert)
        session.commit()

        # Notify admin and city_official users
        from services.notification_service import create_notification
        admin_users = session.query(User).filter(
            User.role.in_(["admin", "city_official"]),
            User.is_active == True,
        ).all()
        for user in admin_users:
            create_notification(
                user_id=user.id,
                type="cross_department_alert",
                title=alert_data["title"],
                message=alert_data.get("message", ""),
                severity=alert_data["severity"],
            )
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to create cross-department alert: {e}")
    finally:
        session.close()


def resolve_alert(alert_id: int, user_id: int) -> tuple[bool, str]:
    session = get_session()
    try:
        alert = session.get(CrossDepartmentAlert, alert_id)
        if not alert:
            return False, "Alert not found."
        alert.is_resolved = True
        alert.resolved_by = user_id
        alert.resolved_at = datetime.utcnow()
        session.commit()
        log_action(user_id, "UPDATE", "cross_department_alerts", alert_id,
                   old_values={"is_resolved": False}, new_values={"is_resolved": True})
        return True, "Alert resolved."
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()


def get_cross_department_alerts(barangay_id: int | None = None, alert_type: str | None = None,
                                unresolved_only: bool = False, limit: int = 100) -> list[dict]:
    session = get_session()
    try:
        query = session.query(CrossDepartmentAlert).join(Barangay)
        if barangay_id:
            query = query.filter(CrossDepartmentAlert.barangay_id == barangay_id)
        if alert_type:
            query = query.filter(CrossDepartmentAlert.alert_type == alert_type)
        if unresolved_only:
            query = query.filter(CrossDepartmentAlert.is_resolved == False)

        records = query.order_by(CrossDepartmentAlert.created_at.desc()).limit(limit).all()
        return [
            {
                "id": r.id, "barangay_id": r.barangay_id,
                "barangay_name": r.barangay.name,
                "alert_type": r.alert_type, "severity": r.severity,
                "title": r.title, "message": r.message or "",
                "is_resolved": r.is_resolved,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
            }
            for r in records
        ]
    finally:
        session.close()


def get_sync_status(barangay_id: int | None = None, department_name: str | None = None) -> list[dict]:
    session = get_session()
    try:
        query = session.query(DepartmentDataSync)
        if barangay_id:
            query = query.filter(DepartmentDataSync.barangay_id == barangay_id)
        if department_name:
            query = query.filter(DepartmentDataSync.department_name == department_name)
        records = query.all()
        return [
            {
                "id": r.id, "department_name": r.department_name,
                "barangay_id": r.barangay_id,
                "last_synced": r.last_synced.strftime("%Y-%m-%d %H:%M") if r.last_synced else "",
                "sync_status": r.sync_status,
            }
            for r in records
        ]
    finally:
        session.close()


def get_cross_department_kpis(year: int | None = None) -> dict:
    session = get_session()
    try:
        # Active alerts
        active_alerts = session.query(CrossDepartmentAlert).filter_by(is_resolved=False).count()
        critical_alerts = session.query(CrossDepartmentAlert).filter_by(
            is_resolved=False, severity="critical"
        ).count()

        # Sync freshness
        today = datetime.utcnow()
        stale_cutoff = today - timedelta(days=30)
        synced_today = session.query(DepartmentDataSync).filter(
            DepartmentDataSync.last_synced >= today.replace(hour=0, minute=0, second=0)
        ).count()
        stale_count = session.query(DepartmentDataSync).filter(
            DepartmentDataSync.last_synced < stale_cutoff
        ).count()

        return {
            "active_alerts": active_alerts,
            "critical_alerts": critical_alerts,
            "synced_today": synced_today,
            "stale_data_warnings": stale_count,
        }
    finally:
        session.close()
```

- [ ] **Step 2: Verify import**

Run: `/c/laragon/bin/python/python-3.13/python.exe -c "from services.cross_department_service import DEPARTMENT_NAMES; print('cross_department_service OK')"`

Expected: `cross_department_service OK`

- [ ] **Step 3: Commit**

```bash
git add services/cross_department_service.py
git commit -m "feat: add cross_department_service with sync tracking, threshold alerts, and KPIs"
```

---

### Task 9: Add Seed Data to database/real_data.py

**Files:**
- Modify: `database/real_data.py`

- [ ] **Step 1: Add new imports at top of file**

Add to the import block (after existing service imports around line 24):

```python
from services.health_service import save_health_statistics
from services.social_welfare_service import save_social_welfare_data
from services.disaster_service import (
    save_disaster_risk_profile, save_disaster_incident, save_emergency_resource
)
from services.education_service import save_education_statistics
from services.business_permit_service import save_business_permit
```

- [ ] **Step 2: Add seed data constants after existing constants (after line ~148)**

Add after the `BUSINESS_TEMPLATES` list:

```python
# ── Milestone 3: Department Data Constants ───────────────────

DISASTER_TYPE_WEIGHTS = {
    "flood": 0.35, "fire": 0.20, "typhoon": 0.15,
    "landslide": 0.12, "earthquake": 0.08, "storm_surge": 0.10,
}

RESOURCE_TEMPLATES = [
    ("Emergency Food Packs", "food", "packs"),
    ("Drinking Water Supply", "water", "liters"),
    ("First Aid Kits", "medicine", "boxes"),
    ("Medical Supplies", "medicine", "boxes"),
    ("Emergency Shelter Kits", "shelter", "units"),
    ("Rescue Equipment", "equipment", "units"),
    ("Blankets and Mats", "shelter", "packs"),
    ("Water Purification Tablets", "water", "boxes"),
]

PERMIT_BUSINESS_TEMPLATES = [
    ("Sari-Sari Store", "retail"), ("Restaurant", "food"), ("Bakeshop", "food"),
    ("Hardware Supply", "retail"), ("Pharmacy", "retail"), ("Water Station", "services"),
    ("Beauty Salon", "services"), ("Vulcanizing Shop", "services"),
    ("Internet Cafe", "services"), ("Laundry Shop", "services"),
    ("Rice Mill", "manufacturing"), ("Construction Supply", "construction"),
    ("Transport Service", "transportation"), ("Real Estate", "real_estate"),
    ("Money Lending", "finance"), ("Farm Supply", "agriculture"),
]
```

- [ ] **Step 3: Add seed functions inside `_seed_barangay`**

Add at the end of the `_seed_barangay` function (after the traffic incidents section, around line ~450):

```python
    # ── Health Statistics (2023, 2025) ───────────────────────────
    for year in [2023, 2025]:
        # Disease rates proportional to population
        dengue_rate = random.uniform(2, 8) / 10000
        tb_rate = random.uniform(3, 6) / 10000
        covid_rate = random.uniform(1, 3) / 10000
        diarrhea_rate = random.uniform(5, 12) / 10000
        pneumonia_rate = random.uniform(2, 5) / 10000
        hypertension_rate = random.uniform(15, 30) / 10000 if is_urban_core else random.uniform(10, 20) / 10000
        diabetes_rate = random.uniform(8, 15) / 10000

        save_health_statistics(barangay_id, year, {
            "dengue_cases": int(pop_latest * dengue_rate),
            "tuberculosis_cases": int(pop_latest * tb_rate),
            "covid_cases": int(pop_latest * covid_rate),
            "diarrhea_cases": int(pop_latest * diarrhea_rate),
            "pneumonia_cases": int(pop_latest * pneumonia_rate),
            "hypertension_cases": int(pop_latest * hypertension_rate),
            "diabetes_cases": int(pop_latest * diabetes_rate),
            "other_disease_cases": random.randint(0, max(1, int(pop_latest * 0.0005))),
            "vaccination_coverage_pct": round(random.uniform(80, 97) if is_urban_core else random.uniform(70, 90), 1),
            "hospital_count": 1 if pop_latest > 40000 and random.random() > 0.5 else 0,
            "clinic_count": max(1, int(pop_latest / 15000) + random.randint(0, 1)),
            "health_worker_count": max(1, int(pop_latest / 3000) + random.randint(0, 2)),
            "maternal_mortality": random.choices([0, 0, 0, 1, 2], weights=[60, 20, 10, 8, 2])[0],
            "infant_mortality": random.choices([0, 0, 1, 2, 3], weights=[40, 25, 20, 10, 5])[0],
            "malnutrition_rate": round(random.uniform(3, 8) if is_urban_core else random.uniform(6, 15), 1),
        }, user_id)

    # ── Social Welfare Data (2023, 2025) ─────────────────────────
    for year in [2023, 2025]:
        fourps_pct = random.uniform(0.08, 0.18) if not is_urban_core else random.uniform(0.03, 0.10)
        senior_pct = random.uniform(0.07, 0.10)
        pwd_pct = random.uniform(0.015, 0.03)
        solo_parent_pct = random.uniform(0.02, 0.05)

        save_social_welfare_data(barangay_id, year, {
            "fourps_beneficiaries": int(households * fourps_pct),
            "senior_citizen_count": int(pop_latest * senior_pct),
            "pwd_count": int(pop_latest * pwd_pct),
            "solo_parent_count": int(households * solo_parent_pct),
            "indigent_families": int(households * random.uniform(0.03, 0.12)),
            "nutrition_program_beneficiaries": int(pop_latest * random.uniform(0.02, 0.06)),
        }, user_id)

    # ── Disaster Risk Profile (2025) ─────────────────────────────
    # Coastal/lowland = flood-prone; upland = landslide-prone; dense urban = fire risk
    is_coastal = random.random() < 0.15
    is_upland = random.random() < 0.25 and not is_coastal
    save_disaster_risk_profile(barangay_id, 2025, {
        "flood_prone": is_coastal or random.random() < 0.30,
        "landslide_prone": is_upland or random.random() < 0.10,
        "fire_risk_level": "high" if is_urban_core and random.random() < 0.3 else random.choice(["low", "medium"]),
        "earthquake_risk": random.choice(["medium", "medium", "high"]),
        "storm_surge_risk": "high" if is_coastal else random.choice(["low", "low", "medium"]),
        "evacuation_center_count": random.randint(1, 3),
        "evacuation_capacity": random.randint(200, 2000),
    }, user_id)

    # ── Disaster Incidents (2024-2025) ───────────────────────────
    disaster_count = random.randint(0, 4) if is_coastal or is_upland else random.randint(0, 2)
    for _ in range(disaster_count):
        r = random.random()
        cumulative = 0
        d_type = "flood"
        for dt, prob in DISASTER_TYPE_WEIGHTS.items():
            cumulative += prob
            if r <= cumulative:
                d_type = dt
                break

        year = 2025 if random.random() < 0.6 else 2024
        # Floods peak Jun-Nov, typhoons Sep-Dec
        if d_type in ("flood", "storm_surge"):
            month = random.choice([6, 7, 8, 9, 10, 11])
        elif d_type == "typhoon":
            month = random.choice([9, 10, 11, 12])
        else:
            month = random.randint(1, 12)

        save_disaster_incident(barangay_id, {
            "disaster_type": d_type,
            "severity": random.choices(["low", "medium", "high", "critical"], weights=[30, 35, 25, 10])[0],
            "date_occurred": date(year, month, random.randint(1, 28)),
            "affected_families": random.randint(5, max(10, int(households * 0.05))),
            "casualties": random.choices([0, 0, 0, 1, 2], weights=[70, 15, 8, 5, 2])[0],
            "damages_estimated": round(random.uniform(50000, 5000000), 2),
            "status": random.choices(["reported", "responding", "resolved", "recovery"], weights=[10, 15, 50, 25])[0],
            "response_team": random.choice(["CDRRMO", "BFP", "PNP", "Barangay DRRM", "Red Cross"]),
            "description": f"{d_type.capitalize()} incident in Brgy. {name}",
        }, user_id)

    # ── Emergency Resources ──────────────────────────────────────
    num_resources = random.randint(3, 8)
    for i in range(num_resources):
        template = random.choice(RESOURCE_TEMPLATES)
        restock = date(2025, random.randint(1, 6), random.randint(1, 28))
        months_until_expiry = random.randint(6, 18)
        expiry = date(restock.year + (restock.month + months_until_expiry - 1) // 12,
                      (restock.month + months_until_expiry - 1) % 12 + 1,
                      min(restock.day, 28))
        # ~10% already expired
        if random.random() < 0.10:
            expiry = date(2025, random.randint(1, 3), random.randint(1, 28))

        save_emergency_resource(barangay_id, {
            "resource_type": template[1],
            "name": template[0],
            "quantity": round(random.uniform(10, 500) * (pop_latest / 10000), 0),
            "unit": template[2],
            "location_description": f"Brgy. {name} Evacuation Center",
            "last_restocked": restock,
            "expiry_date": expiry,
        }, user_id)

    # ── Education Statistics (2023, 2025) ────────────────────────
    for year in [2023, 2025]:
        enrollee_pct = random.uniform(0.15, 0.25)
        total_enrollees = int(pop_latest * enrollee_pct)
        elem_pct = random.uniform(0.50, 0.60)
        hs_pct = random.uniform(0.30, 0.38)
        col_pct = 1 - elem_pct - hs_pct if is_urban_core else random.uniform(0, 0.05)

        save_education_statistics(barangay_id, year, {
            "total_enrollees": total_enrollees,
            "elementary_count": int(total_enrollees * elem_pct),
            "highschool_count": int(total_enrollees * hs_pct),
            "college_count": int(total_enrollees * max(0, col_pct)),
            "out_of_school_youth": int(pop_latest * random.uniform(0.02, 0.08)),
            "literacy_rate": round(random.uniform(95, 99) if is_urban_core else random.uniform(90, 97), 1),
            "school_count": max(1, int(pop_latest / 10000) + random.randint(0, 2)),
            "teacher_count": max(1, int(total_enrollees / random.uniform(35, 45))),
            "classroom_count": max(1, int(total_enrollees / random.uniform(40, 50))),
            "dropout_rate": round(random.uniform(1, 5) if is_urban_core else random.uniform(3, 10), 1),
        }, user_id)

    # ── Business Permits ─────────────────────────────────────────
    num_permits = max(3, int(pop_latest / 1500) + random.randint(0, 8))
    num_permits = min(num_permits, 30)
    for i in range(num_permits):
        template = random.choice(PERMIT_BUSINESS_TEMPLATES)
        issue_year = random.randint(2022, 2025)
        issue_date = date(issue_year, random.randint(1, 12), random.randint(1, 28))
        expiry_date = date(issue_year + 1, issue_date.month, min(issue_date.day, 28))

        status = random.choices(["active", "expired", "revoked", "pending"],
                                weights=[85, 8, 2, 5])[0]

        save_business_permit(barangay_id, {
            "business_name": f"{template[0]} - {name} #{i+1}",
            "owner_name": random.choice([
                "Juan Dela Cruz", "Maria Santos", "Pedro Reyes", "Ana Garcia",
                "Jose Mendoza", "Rosa Flores", "Antonio Cruz", "Carmen Ramos",
                "Miguel Torres", "Elena Bautista",
            ]),
            "business_type": template[1],
            "permit_number": f"BP-{issue_year}-{barangay_id:03d}-{i+1:04d}",
            "date_issued": issue_date,
            "date_expiry": expiry_date,
            "status": status,
            "annual_revenue": round(random.uniform(50000, 5000000), 2),
            "employee_count": random.randint(1, 50),
            "address": f"Brgy. {name}, Davao City",
        }, user_id)
```

- [ ] **Step 4: Verify the seed file compiles**

Run: `/c/laragon/bin/python/python-3.13/python.exe -c "from database.real_data import seed_real_data; print('real_data imports OK')"`

Expected: `real_data imports OK`

- [ ] **Step 5: Commit**

```bash
git add database/real_data.py
git commit -m "feat: add seed data for health, disaster, education, business permits, and resources"
```

---

### Task 10: Test Database Creation and Seeding

**Files:** None (verification only)

- [ ] **Step 1: Delete existing DB and re-seed**

```bash
rm -f data/barangay_profiling.db
/c/laragon/bin/python/python-3.13/python.exe main.py
```

The app should launch, create all tables, and seed data. Close the app after it loads.

- [ ] **Step 2: Verify table counts**

```bash
/c/laragon/bin/python/python-3.13/python.exe -c "
from database.db import get_session, init_db
from database.models import *
init_db()
s = get_session()
tables = {
    'HealthStatistics': s.query(HealthStatistics).count(),
    'SocialWelfareData': s.query(SocialWelfareData).count(),
    'DisasterRiskProfile': s.query(DisasterRiskProfile).count(),
    'DisasterIncident': s.query(DisasterIncident).count(),
    'EmergencyResource': s.query(EmergencyResource).count(),
    'EducationStatistics': s.query(EducationStatistics).count(),
    'BusinessPermit': s.query(BusinessPermit).count(),
}
s.close()
for name, count in tables.items():
    print(f'{name}: {count} records')
print('All new tables populated!' if all(v > 0 for v in tables.values()) else 'ERROR: Some tables empty!')
"
```

Expected: All tables show positive record counts.

- [ ] **Step 3: Commit (if any fixes were needed)**

```bash
git add -A
git commit -m "fix: resolve any seeding issues found during verification"
```

---

## Phase 18: Department Views

### Task 11: Update Sidebar and App Navigation

**Files:**
- Modify: `ui/components/sidebar.py`
- Modify: `ui/app.py`

- [ ] **Step 1: Add 4 new nav items to sidebar**

In `ui/components/sidebar.py`, add 4 items to `nav_items` list after `("crime", "Crime & Safety", "\U0001F6E1")` (line 88):

```python
            ("health", "Health & Welfare", "\U0001F3E5"),
            ("disaster", "Disaster & Safety", "\U0001F6A8"),
            ("education", "Education", "\U0001F393"),
            ("business_permits", "Business Permits", "\U0001F4BC"),
```

- [ ] **Step 2: Add 4 new view cases to app.py**

In `ui/app.py`, add after the `elif view_key == "crime":` block (line ~217), before `elif view_key == "action_plans":`:

```python
        elif view_key == "health":
            from ui.views.health_view import HealthView
            return HealthView(self._content_frame)
        elif view_key == "disaster":
            from ui.views.disaster_view import DisasterView
            return DisasterView(self._content_frame)
        elif view_key == "education":
            from ui.views.education_view import EducationView
            return EducationView(self._content_frame)
        elif view_key == "business_permits":
            from ui.views.business_permit_view import BusinessPermitView
            return BusinessPermitView(self._content_frame)
```

- [ ] **Step 3: Commit**

```bash
git add ui/components/sidebar.py ui/app.py
git commit -m "feat: add sidebar nav items and app routing for 4 new department views"
```

---

### Task 12: Create Health & Welfare View

**Files:**
- Create: `ui/views/health_view.py`

- [ ] **Step 1: Create the health view**

Create `ui/views/health_view.py` following the `CrimeView` pattern. This is a large file — the agent implementing this task should create it with 4 tabs:

1. **Health Statistics tab** — District/Barangay/Year filter dropdowns + DataTable showing health fields + Add/Edit dialog
2. **Social Welfare tab** — Same pattern for 4Ps, senior, PWD, solo parent, indigent counts
3. **Health Overview tab** — ChartWidget with 2x2 subplot: disease breakdown bar chart, vaccination coverage by district bar, mortality trends, malnutrition by district
4. **High Risk Areas tab** — DataTable ranked by malnutrition + disease burden

Key imports and patterns to follow from `crime_view.py`:
- Import `AuthManager`, `get_all_districts`, `get_barangays_by_district`, all theme constants
- Import from `services/health_service.py` and `services/social_welfare_service.py`
- Use `LabeledEntry`, `LabeledNumberEntry`, `LabeledDropdown` from `ui/components/form_fields.py`
- Use `DataTable` from `ui/components/data_table.py`
- Use `ChartWidget` from `ui/components/chart_widget.py`
- Permission guard: `auth.check_permission("enter_data")` for Add/Edit buttons
- Dialog pattern: `ctk.CTkToplevel` with `transient(self)`, `grab_set()`
- Implement `refresh(self)` method (can be pass or reload data)

- [ ] **Step 2: Verify the view loads**

Run app, navigate to "Health & Welfare" in sidebar, verify all 4 tabs render without errors.

- [ ] **Step 3: Commit**

```bash
git add ui/views/health_view.py
git commit -m "feat: add Health & Welfare view with 4 tabs (statistics, welfare, overview, high-risk)"
```

---

### Task 13: Create Disaster & Safety View

**Files:**
- Create: `ui/views/disaster_view.py`

- [ ] **Step 1: Create the disaster view**

Create `ui/views/disaster_view.py` with 5 tabs:

1. **Risk Profiles tab** — District/Barangay/Year filter + DataTable + Add/Edit dialog with CTkCheckBox for boolean fields (flood_prone, landslide_prone) and LabeledDropdown for risk levels
2. **Disaster Incidents tab** — Full CRUD mirrors CrimeView incident tab exactly. Filters for type/severity/status. Add/Edit/Delete dialog with all incident fields including affected_families, casualties, damages_estimated
3. **Emergency Resources tab** — DataTable with type/name/quantity/unit/expiry. Add/Edit/Delete. Highlight expired resources with red text
4. **Disaster Overview tab** — Charts: incidents by type pie, monthly trend line, affected families by district bar
5. **Resource Status tab** — Chart showing expiring resources count, resource coverage by type

Key imports: `services/disaster_service.py` constants and functions.

- [ ] **Step 2: Verify the view loads**

Run app, navigate to "Disaster & Safety", verify all 5 tabs render without errors.

- [ ] **Step 3: Commit**

```bash
git add ui/views/disaster_view.py
git commit -m "feat: add Disaster & Safety view with 5 tabs (risk, incidents, resources, overview, status)"
```

---

### Task 14: Create Education View

**Files:**
- Create: `ui/views/education_view.py`

- [ ] **Step 1: Create the education view**

Create `ui/views/education_view.py` with 3 tabs:

1. **Education Statistics tab** — District/Barangay/Year filter + DataTable + Add/Edit dialog with all education fields
2. **Education Overview tab** — Charts: enrollment by level stacked bar, literacy rate by district bar, dropout rate trend line, out-of-school youth by district bar
3. **School Capacity tab** — DataTable showing student-teacher ratio and student-classroom ratio per barangay, calculated from seed data

Key imports: `services/education_service.py` functions.

- [ ] **Step 2: Verify the view loads**

Run app, navigate to "Education", verify all 3 tabs render without errors.

- [ ] **Step 3: Commit**

```bash
git add ui/views/education_view.py
git commit -m "feat: add Education view with 3 tabs (statistics, overview, school capacity)"
```

---

### Task 15: Create Business Permits View

**Files:**
- Create: `ui/views/business_permit_view.py`

- [ ] **Step 1: Create the business permits view**

Create `ui/views/business_permit_view.py` with 3 tabs:

1. **Permits tab** — Full CRUD DataTable with type/status/barangay filters. Add/Edit/Delete dialog with all permit fields
2. **Permit Overview tab** — Charts: permits by type pie, revenue by type bar, active vs expired donut
3. **Expiring Permits tab** — DataTable showing permits expiring within 30/60/90 days (use `get_expiring_permits`)

Key imports: `services/business_permit_service.py` constants and functions.

- [ ] **Step 2: Verify the view loads**

Run app, navigate to "Business Permits", verify all 3 tabs render without errors.

- [ ] **Step 3: Commit**

```bash
git add ui/views/business_permit_view.py
git commit -m "feat: add Business Permits view with 3 tabs (permits, overview, expiring)"
```

---

## Phase 19: Cross-Department Sync + Notifications

### Task 16: Add Cross-Department Hooks to Service Save Functions

**Files:**
- Modify: `services/health_service.py`
- Modify: `services/social_welfare_service.py`
- Modify: `services/disaster_service.py`
- Modify: `services/education_service.py`
- Modify: `services/business_permit_service.py`

- [ ] **Step 1: Add hook to health_service.py**

In `save_health_statistics`, after the `return True, "Health statistics ..."` lines (both create and update paths), add before the return:

```python
            # Cross-department sync hook
            from services.cross_department_service import on_department_data_saved
            on_department_data_saved("health", barangay_id, year, user_id)
```

Add this in both the update path (after `log_action` for UPDATE) and the create path (after `log_action` for CREATE), before the `return True` line.

- [ ] **Step 2: Add hook to social_welfare_service.py**

Same pattern — add after both `log_action` calls in `save_social_welfare_data`:

```python
            from services.cross_department_service import on_department_data_saved
            on_department_data_saved("social_welfare", barangay_id, year, user_id)
```

- [ ] **Step 3: Add hooks to disaster_service.py**

In `save_disaster_risk_profile` (both paths):
```python
            from services.cross_department_service import on_department_data_saved
            on_department_data_saved("disaster", barangay_id, year, user_id)
```

In `save_disaster_incident` (both paths — use `date.today().year` for the year param since incidents don't have a year field directly):
```python
            from services.cross_department_service import on_department_data_saved
            from datetime import date as _date
            on_department_data_saved("disaster", barangay_id, _date.today().year, user_id)
```

- [ ] **Step 4: Add hook to education_service.py**

In `save_education_statistics` (both paths):
```python
            from services.cross_department_service import on_department_data_saved
            on_department_data_saved("education", barangay_id, year, user_id)
```

- [ ] **Step 5: Add hook to business_permit_service.py**

In `save_business_permit` (both paths — use `date.today().year` for year):
```python
            from services.cross_department_service import on_department_data_saved
            from datetime import date as _date
            on_department_data_saved("business_permits", barangay_id, _date.today().year, user_id)
```

- [ ] **Step 6: Commit**

```bash
git add services/health_service.py services/social_welfare_service.py services/disaster_service.py services/education_service.py services/business_permit_service.py
git commit -m "feat: add cross-department sync hooks to all department service save functions"
```

---

### Task 17: Add Cross-Department KPIs to Dashboard

**Files:**
- Modify: `ui/views/dashboard_view.py`

- [ ] **Step 1: Add import**

Add to the imports at top of `dashboard_view.py`:

```python
from services.cross_department_service import get_cross_department_kpis, get_cross_department_alerts
```

- [ ] **Step 2: Add cross-department alert card to stat cards**

In `_build_ui`, add a new card config to `card_configs` list:

```python
            ("cross_dept_alerts", "Dept. Alerts", "\U0001F6A8", "#D32F2F"),
```

- [ ] **Step 3: Add cross-department alert summary section**

After the compliance tracker section in `_build_ui`, add:

```python
        # Cross-department alerts
        alerts_card = ctk.CTkFrame(self, fg_color=CARD_BG, corner_radius=12)
        alerts_card.pack(fill="x", padx=PADDING_LARGE, pady=(0, PADDING_NORMAL))

        ctk.CTkLabel(
            alerts_card, text="Cross-Department Alerts",
            font=(FONT_FAMILY, 14, "bold"), text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=PADDING_NORMAL, pady=(PADDING_NORMAL, 5))

        self._alerts_frame = ctk.CTkScrollableFrame(alerts_card, fg_color="transparent", height=120)
        self._alerts_frame.pack(fill="x", padx=PADDING_NORMAL, pady=(0, PADDING_NORMAL))
```

- [ ] **Step 4: Update refresh method to populate cross-department data**

Add at the end of the `refresh` method:

```python
        # Cross-department KPIs
        try:
            kpis = get_cross_department_kpis()
            alert_count = kpis.get("active_alerts", 0)
            self._stat_cards["cross_dept_alerts"].set_value(str(alert_count))

            # Alert summary
            for widget in self._alerts_frame.winfo_children():
                widget.destroy()

            alerts = get_cross_department_alerts(unresolved_only=True, limit=10)
            if not alerts:
                ctk.CTkLabel(
                    self._alerts_frame, text="No active cross-department alerts.",
                    font=(FONT_FAMILY, FONT_SIZE_SMALL), text_color=TEXT_SECONDARY,
                ).pack(pady=10)
            else:
                for a in alerts:
                    row = ctk.CTkFrame(self._alerts_frame, fg_color="transparent")
                    row.pack(fill="x", pady=2)
                    sev_colors = {"critical": "#E53935", "warning": "#FB8C00", "info": "#1E88E5"}
                    color = sev_colors.get(a["severity"], TEXT_SECONDARY)
                    ctk.CTkLabel(
                        row, text=f"[{a['severity'].upper()}]",
                        font=(FONT_FAMILY, 10, "bold"), text_color=color,
                    ).pack(side="left", padx=(0, 5))
                    ctk.CTkLabel(
                        row, text=f"{a['barangay_name']}: {a['title']}",
                        font=(FONT_FAMILY, 10), text_color=TEXT_PRIMARY,
                    ).pack(side="left")
                    ctk.CTkLabel(
                        row, text=a["created_at"],
                        font=(FONT_FAMILY, 10), text_color=TEXT_SECONDARY,
                    ).pack(side="right")
        except Exception:
            pass
```

- [ ] **Step 5: Commit**

```bash
git add ui/views/dashboard_view.py
git commit -m "feat: add cross-department KPI card and alert summary to dashboard"
```

---

### Task 18: End-to-End Verification

**Files:** None (verification only)

- [ ] **Step 1: Fresh database test**

```bash
rm -f data/barangay_profiling.db
/c/laragon/bin/python/python-3.13/python.exe main.py
```

Verify: App launches, dashboard loads with cross-department alerts card.

- [ ] **Step 2: Navigate to each new view**

Navigate to: Health & Welfare, Disaster & Safety, Education, Business Permits. Verify all tabs load.

- [ ] **Step 3: Test CRUD operations**

In each view:
- Add a new record, verify it appears in the table
- Edit the record, verify changes saved
- Delete the record (where applicable)

- [ ] **Step 4: Test cross-department alert generation**

1. Find a barangay with high poverty (>20% poverty rate)
2. In Health & Welfare, add health statistics with dengue_cases >= 10 for that barangay
3. Check Notifications view — a cross-department alert should appear
4. Check Dashboard — alert should appear in the alerts summary

- [ ] **Step 5: Test permission guards**

Login as `viewer1` (password123). Verify Add/Edit/Delete buttons are hidden in all new views.

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "feat: complete milestone 3 phase 17-19 multi-department integration"
```

---

## Summary of Deliverables

| Phase | Tasks | Key Outputs |
|-------|-------|------------|
| 17 | Tasks 1-10 | 9 new models, 6 new services, seed data for all 182 barangays |
| 18 | Tasks 11-15 | 4 new sidebar views (Health, Disaster, Education, Business Permits) |
| 19 | Tasks 16-18 | Cross-department hooks, dashboard KPIs, alert generation, end-to-end verification |
