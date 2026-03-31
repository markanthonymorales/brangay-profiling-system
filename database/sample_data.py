"""
Sample data seeder for testing.
Run: python -c "from database.sample_data import seed_sample_data; seed_sample_data()"
"""
import logging
import random
from datetime import date, timedelta
from database.db import get_session, init_db
from database.models import Barangay, District
from services.population_service import save_population_record
from services.resident_service import save_resident_category
from services.economic_service import save_income_record, save_business
from services.infrastructure_service import save_utility_record, save_waste_record, save_land_type
from services.community_service import save_food_source, save_government_facility, save_religious_demographic
from services.crime_service import save_crime_incident, save_traffic_incident, CRIME_TYPES, TRAFFIC_TYPES, SEVERITY_LEVELS
from services.user_service import create_user

logger = logging.getLogger(__name__)

BUSINESS_NAMES = [
    "Sari-Sari Store", "Eatery", "Hardware Store", "Pharmacy",
    "Internet Cafe", "Laundry Shop", "Barbershop", "Bakery",
    "Carinderia", "Water Refilling Station", "Vulcanizing Shop",
    "Rice Dealer", "Fish Vendor", "Clothing Store", "Auto Repair Shop",
]

BUSINESS_TYPES = ["retail", "food", "services", "manufacturing", "agriculture", "other"]
FOOD_TYPES = ["market", "farm", "fishing", "imported"]
RELIGIONS = ["Catholic", "Islam", "Iglesia ni Cristo", "Protestant", "Seventh-Day Adventist", "Buddhist", "Others"]
AGENCIES = ["PNP", "BFP", "DSWD", "DOH", "DepEd", "DILG", "DOLE"]
FACILITY_TYPES = ["police station", "fire station", "health center", "school", "barangay hall"]
WATER_SOURCES = ["DCWD", "Deep Well", "Spring", "Level III"]
POWER_PROVIDERS = ["DLPC", "DECORP", "Solar"]
WASTE_FREQ = ["daily", "weekly", "bi-weekly"]
WASTE_METHODS = ["landfill", "recycling", "composting", "mixed"]


def seed_sample_data():
    init_db()
    session = get_session()

    try:
        # Create test users
        create_user("encoder1", "password123", "Juan Dela Cruz", "encoder", 1)
        create_user("encoder2", "password123", "Maria Santos", "encoder", 1)
        create_user("viewer1", "password123", "Pedro Reyes", "viewer", 1)
        logger.info("Test users created.")

        # Get sample barangays (30 barangays across all districts)
        districts = session.query(District).all()
        sample_barangays = []
        for d in districts:
            brgys = session.query(Barangay).filter_by(district_id=d.id).limit(10).all()
            sample_barangays.extend(brgys)

        session.close()

        for brgy in sample_barangays:
            _seed_barangay_data(brgy.id, brgy.name)

        logger.info(f"Sample data seeded for {len(sample_barangays)} barangays.")
        print(f"Sample data seeded for {len(sample_barangays)} barangays across {len(districts)} districts.")
        print("Test accounts: encoder1/password123, encoder2/password123, viewer1/password123")

    except Exception as e:
        logger.error(f"Sample data seed failed: {e}")
        raise


def _seed_barangay_data(barangay_id: int, name: str):
    user_id = 1  # admin

    # Population data for 2024, 2025, 2026
    base_pop = random.randint(5000, 50000)
    for year in [2024, 2025, 2026]:
        pop = base_pop + random.randint(-500, 2000) * (year - 2023)
        male = int(pop * random.uniform(0.48, 0.52))
        female = pop - male
        save_population_record(barangay_id, year, {
            "total_population": pop,
            "male_count": male,
            "female_count": female,
            "registered_voters": int(pop * random.uniform(0.4, 0.7)),
            "non_registered_residents": int(pop * random.uniform(0.1, 0.3)),
            "foreign_residents": random.randint(0, 50),
            "household_count": int(pop / random.uniform(3.5, 5.5)),
        }, user_id)

    # Resident categories
    for year in [2025, 2026]:
        households = int(base_pop / 4)
        save_resident_category(barangay_id, year, {
            "renters_count": int(households * random.uniform(0.15, 0.4)),
            "homeowners_count": int(households * random.uniform(0.4, 0.7)),
            "squatters_count": int(households * random.uniform(0, 0.1)),
            "informal_settlers_count": int(households * random.uniform(0, 0.08)),
        }, user_id)

    # Income data
    for year in [2025, 2026]:
        avg_income = random.uniform(8000, 45000)
        total_hh = int(base_pop / 4)
        save_income_record(barangay_id, year, {
            "average_household_income": round(avg_income, 2),
            "below_poverty_count": int(total_hh * random.uniform(0.05, 0.3)),
            "low_income_count": int(total_hh * random.uniform(0.15, 0.35)),
            "middle_income_count": int(total_hh * random.uniform(0.25, 0.45)),
            "high_income_count": int(total_hh * random.uniform(0.05, 0.2)),
        }, user_id)

    # Businesses (2-6 per barangay)
    for _ in range(random.randint(2, 6)):
        save_business(barangay_id, {
            "name": random.choice(BUSINESS_NAMES) + f" #{random.randint(1, 99)}",
            "type": random.choice(BUSINESS_TYPES),
            "is_active": random.random() > 0.15,
            "registered_date": date(random.randint(2018, 2026), random.randint(1, 12), random.randint(1, 28)),
        }, user_id)

    # Utilities
    for year in [2025, 2026]:
        save_utility_record(barangay_id, year, {
            "water_source": random.choice(WATER_SOURCES),
            "water_coverage_pct": round(random.uniform(40, 100), 1),
            "power_provider": random.choice(POWER_PROVIDERS),
            "power_coverage_pct": round(random.uniform(60, 100), 1),
            "internet_coverage_pct": round(random.uniform(10, 90), 1),
        }, user_id)

    # Waste management
    save_waste_record(barangay_id, 2026, {
        "collection_frequency": random.choice(WASTE_FREQ),
        "disposal_method": random.choice(WASTE_METHODS),
        "coverage_pct": round(random.uniform(30, 95), 1),
    }, user_id)

    # Land types
    remaining = 100.0
    for lt in ["residential", "commercial", "agricultural", "industrial"]:
        pct = round(random.uniform(5, remaining - 10) if remaining > 20 else remaining, 1)
        remaining -= pct
        if pct > 0:
            save_land_type(barangay_id, {
                "type": lt, "area_sqkm": round(pct * 0.05, 3), "percentage": pct,
            }, user_id)

    # Food sources
    for _ in range(random.randint(1, 3)):
        save_food_source(barangay_id, {
            "type": random.choice(FOOD_TYPES),
            "description": f"Local {random.choice(FOOD_TYPES)} area serving the community",
        }, user_id)

    # Government facilities
    for _ in range(random.randint(1, 3)):
        save_government_facility(barangay_id, {
            "agency_name": random.choice(AGENCIES),
            "facility_type": random.choice(FACILITY_TYPES),
            "address": f"Purok {random.randint(1, 15)}, {name}",
        }, user_id)

    # Religious demographics
    total_pop = base_pop
    remaining_pop = total_pop
    for religion in random.sample(RELIGIONS, random.randint(2, 5)):
        count = int(remaining_pop * random.uniform(0.1, 0.6))
        remaining_pop -= count
        if count > 0:
            save_religious_demographic(barangay_id, {
                "year": 2026,
                "religion": religion,
                "count": count,
                "percentage": round((count / total_pop) * 100, 1),
            }, user_id)

    # Crime incidents (3-15 per barangay over 6 months)
    for _ in range(random.randint(3, 15)):
        month = random.randint(1, 6)
        day = random.randint(1, 28)
        save_crime_incident(barangay_id, {
            "crime_type": random.choice(CRIME_TYPES),
            "severity": random.choice(SEVERITY_LEVELS),
            "date_occurred": date(2026, month, day),
            "status": random.choice(["reported", "under_investigation", "resolved"]),
            "description": f"Incident report #{random.randint(1000, 9999)}",
        }, user_id)

    # Traffic incidents (1-5 per barangay)
    for _ in range(random.randint(1, 5)):
        month = random.randint(1, 6)
        day = random.randint(1, 28)
        save_traffic_incident(barangay_id, {
            "incident_type": random.choice(TRAFFIC_TYPES),
            "severity": random.choice(SEVERITY_LEVELS),
            "date_occurred": date(2026, month, day),
            "status": random.choice(["reported", "under_investigation", "resolved"]),
            "description": f"Traffic report #{random.randint(1000, 9999)}",
        }, user_id)


if __name__ == "__main__":
    from utils.logger import setup_logging
    setup_logging()
    seed_sample_data()
