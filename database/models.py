from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, Date, DateTime,
    ForeignKey, UniqueConstraint, create_engine, Index
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# ── Departments ───────────────────────────────────────────────

class Department(TimestampMixin, Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, unique=True)
    level = Column(String(20), nullable=False, default="city")  # city / district / barangay
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=True)
    barangay_id = Column(Integer, ForeignKey("barangays.id"), nullable=True)

    users = relationship("User", back_populates="department")


# ── Users & Auth ──────────────────────────────────────────────

class User(TimestampMixin, Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default="viewer")
    is_active = Column(Boolean, default=True, nullable=False)
    must_change_password = Column(Boolean, default=False, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)

    department = relationship("Department", back_populates="users")
    audit_logs = relationship("AuditLog", back_populates="user")


class Submission(TimestampMixin, Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    submitted_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    table_name = Column(String(50), nullable=False)
    barangay_id = Column(Integer, ForeignKey("barangays.id"), nullable=True)
    year = Column(Integer, nullable=True)
    record_data = Column(Text, nullable=False)  # JSON
    status = Column(String(20), nullable=False, default="pending")  # draft/pending/approved/rejected
    review_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    submitter = relationship("User", foreign_keys=[submitted_by])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    barangay = relationship("Barangay")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(20), nullable=False)
    table_name = Column(String(50), nullable=False)
    record_id = Column(Integer, nullable=True)
    old_values = Column(Text, nullable=True)
    new_values = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="audit_logs")


# ── Geography ─────────────────────────────────────────────────

class District(Base):
    __tablename__ = "districts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)

    barangays = relationship("Barangay", back_populates="district")


class Barangay(TimestampMixin, Base):
    __tablename__ = "barangays"

    id = Column(Integer, primary_key=True, autoincrement=True)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
    name = Column(String(100), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    area_sqkm = Column(Float, nullable=True)
    classification = Column(String(20), nullable=True)

    district = relationship("District", back_populates="barangays")
    population_records = relationship("PopulationRecord", back_populates="barangay")
    resident_categories = relationship("ResidentCategory", back_populates="barangay")
    income_data = relationship("IncomeData", back_populates="barangay")
    businesses = relationship("Business", back_populates="barangay")
    utilities = relationship("Utility", back_populates="barangay")
    land_types = relationship("LandType", back_populates="barangay")
    waste_management = relationship("WasteManagement", back_populates="barangay")
    food_sources = relationship("FoodSource", back_populates="barangay")
    government_facilities = relationship("GovernmentFacility", back_populates="barangay")
    religious_demographics = relationship("ReligiousDemographic", back_populates="barangay")
    crime_incidents = relationship("CrimeIncident", back_populates="barangay")
    traffic_incidents = relationship("TrafficIncident", back_populates="barangay")
    health_statistics = relationship("HealthStatistics", back_populates="barangay")
    social_welfare_data = relationship("SocialWelfareData", back_populates="barangay")
    disaster_risk_profiles = relationship("DisasterRiskProfile", back_populates="barangay")
    disaster_incidents = relationship("DisasterIncident", back_populates="barangay")
    emergency_resources = relationship("EmergencyResource", back_populates="barangay")
    education_statistics = relationship("EducationStatistics", back_populates="barangay")
    business_permits = relationship("BusinessPermit", back_populates="barangay")


# ── Population & Demographics ─────────────────────────────────

class PopulationRecord(TimestampMixin, Base):
    __tablename__ = "population_records"
    __table_args__ = (UniqueConstraint("barangay_id", "year", name="uq_population_barangay_year"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    barangay_id = Column(Integer, ForeignKey("barangays.id"), nullable=False)
    year = Column(Integer, nullable=False)
    total_population = Column(Integer, nullable=True)
    male_count = Column(Integer, nullable=True)
    female_count = Column(Integer, nullable=True)
    registered_voters = Column(Integer, nullable=True)
    non_registered_residents = Column(Integer, nullable=True)
    foreign_residents = Column(Integer, nullable=True)
    household_count = Column(Integer, nullable=True)

    barangay = relationship("Barangay", back_populates="population_records")
    age_demographics = relationship("AgeDemographic", back_populates="population_record", cascade="all, delete-orphan")


class AgeDemographic(TimestampMixin, Base):
    __tablename__ = "age_demographics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    population_record_id = Column(Integer, ForeignKey("population_records.id"), nullable=False)
    age_group = Column(String(20), nullable=False)
    male_count = Column(Integer, nullable=True)
    female_count = Column(Integer, nullable=True)

    population_record = relationship("PopulationRecord", back_populates="age_demographics")


# ── Resident Categories ───────────────────────────────────────

class ResidentCategory(TimestampMixin, Base):
    __tablename__ = "resident_categories"
    __table_args__ = (UniqueConstraint("barangay_id", "year", name="uq_resident_barangay_year"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    barangay_id = Column(Integer, ForeignKey("barangays.id"), nullable=False)
    year = Column(Integer, nullable=False)
    renters_count = Column(Integer, nullable=True)
    homeowners_count = Column(Integer, nullable=True)
    squatters_count = Column(Integer, nullable=True)
    informal_settlers_count = Column(Integer, nullable=True)

    barangay = relationship("Barangay", back_populates="resident_categories")


# ── Economic Data ─────────────────────────────────────────────

class IncomeData(TimestampMixin, Base):
    __tablename__ = "income_data"
    __table_args__ = (UniqueConstraint("barangay_id", "year", name="uq_income_barangay_year"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    barangay_id = Column(Integer, ForeignKey("barangays.id"), nullable=False)
    year = Column(Integer, nullable=False)
    average_household_income = Column(Float, nullable=True)
    below_poverty_count = Column(Integer, nullable=True)
    low_income_count = Column(Integer, nullable=True)
    middle_income_count = Column(Integer, nullable=True)
    high_income_count = Column(Integer, nullable=True)

    barangay = relationship("Barangay", back_populates="income_data")


class Business(TimestampMixin, Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    barangay_id = Column(Integer, ForeignKey("barangays.id"), nullable=False)
    name = Column(String(200), nullable=False)
    type = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    registered_date = Column(Date, nullable=True)

    barangay = relationship("Barangay", back_populates="businesses")


# ── Infrastructure & Utilities ────────────────────────────────

class Utility(TimestampMixin, Base):
    __tablename__ = "utilities"
    __table_args__ = (UniqueConstraint("barangay_id", "year", name="uq_utility_barangay_year"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    barangay_id = Column(Integer, ForeignKey("barangays.id"), nullable=False)
    year = Column(Integer, nullable=False)
    water_source = Column(String(100), nullable=True)
    water_coverage_pct = Column(Float, nullable=True)
    power_provider = Column(String(100), nullable=True)
    power_coverage_pct = Column(Float, nullable=True)
    internet_coverage_pct = Column(Float, nullable=True)

    barangay = relationship("Barangay", back_populates="utilities")


class LandType(TimestampMixin, Base):
    __tablename__ = "land_types"

    id = Column(Integer, primary_key=True, autoincrement=True)
    barangay_id = Column(Integer, ForeignKey("barangays.id"), nullable=False)
    type = Column(String(50), nullable=False)
    area_sqkm = Column(Float, nullable=True)
    percentage = Column(Float, nullable=True)

    barangay = relationship("Barangay", back_populates="land_types")


class WasteManagement(TimestampMixin, Base):
    __tablename__ = "waste_management"
    __table_args__ = (UniqueConstraint("barangay_id", "year", name="uq_waste_barangay_year"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    barangay_id = Column(Integer, ForeignKey("barangays.id"), nullable=False)
    year = Column(Integer, nullable=False)
    collection_frequency = Column(String(50), nullable=True)
    disposal_method = Column(String(100), nullable=True)
    coverage_pct = Column(Float, nullable=True)

    barangay = relationship("Barangay", back_populates="waste_management")


# ── Community ─────────────────────────────────────────────────

class FoodSource(TimestampMixin, Base):
    __tablename__ = "food_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    barangay_id = Column(Integer, ForeignKey("barangays.id"), nullable=False)
    type = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)

    barangay = relationship("Barangay", back_populates="food_sources")


class GovernmentFacility(TimestampMixin, Base):
    __tablename__ = "government_facilities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    barangay_id = Column(Integer, ForeignKey("barangays.id"), nullable=False)
    agency_name = Column(String(200), nullable=False)
    facility_type = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)

    barangay = relationship("Barangay", back_populates="government_facilities")


class ReligiousDemographic(TimestampMixin, Base):
    __tablename__ = "religious_demographics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    barangay_id = Column(Integer, ForeignKey("barangays.id"), nullable=False)
    year = Column(Integer, nullable=False)
    religion = Column(String(100), nullable=False)
    count = Column(Integer, nullable=True)
    percentage = Column(Float, nullable=True)

    barangay = relationship("Barangay", back_populates="religious_demographics")


# ── Crime & Safety ────────────────────────────────────────────

class CrimeIncident(TimestampMixin, Base):
    __tablename__ = "crime_incidents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    barangay_id = Column(Integer, ForeignKey("barangays.id"), nullable=False)
    crime_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False, default="low")
    date_occurred = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, default="reported")
    description = Column(Text, nullable=True)

    barangay = relationship("Barangay", back_populates="crime_incidents")


class TrafficIncident(TimestampMixin, Base):
    __tablename__ = "traffic_incidents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    barangay_id = Column(Integer, ForeignKey("barangays.id"), nullable=False)
    incident_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False, default="low")
    date_occurred = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, default="reported")
    description = Column(Text, nullable=True)

    barangay = relationship("Barangay", back_populates="traffic_incidents")


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


# ── Notifications ────────────────────────────────────────────

class Notification(TimestampMixin, Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=True)
    severity = Column(String(20), nullable=False, default="info")  # info/warning/error
    is_read = Column(Boolean, default=False, nullable=False)

    user = relationship("User")


# ── Retry Queue ──────────────────────────────────────────────

class RetryQueue(TimestampMixin, Base):
    __tablename__ = "retry_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    operation = Column(String(100), nullable=False)
    table_name = Column(String(50), nullable=False)
    data = Column(Text, nullable=True)  # JSON
    error_message = Column(Text, nullable=True)
    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)
    status = Column(String(20), nullable=False, default="pending")  # pending/completed/failed


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


# ── Data Collection Scheduling ──────────────────────────────

class DataCollectionSchedule(TimestampMixin, Base):
    __tablename__ = "data_collection_schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False, unique=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, default="upcoming")
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
    health_submitted = Column(Boolean, default=False, nullable=False)
    social_welfare_submitted = Column(Boolean, default=False, nullable=False)
    disaster_submitted = Column(Boolean, default=False, nullable=False)
    education_submitted = Column(Boolean, default=False, nullable=False)
    business_permits_submitted = Column(Boolean, default=False, nullable=False)
    is_complete = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    barangay = relationship("Barangay")
