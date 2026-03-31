import json
import logging
from config import SEED_DATA_PATH, DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_FULLNAME
from database.db import get_session
from database.models import User, District, Barangay, PopulationRecord

logger = logging.getLogger(__name__)


def seed_if_empty():
    session = get_session()
    try:
        if session.query(District).count() > 0:
            # Check if real data has been seeded (population records exist)
            if session.query(PopulationRecord).count() == 0:
                logger.info("Database has barangays but no population data. Seeding real data...")
                session.close()
                _seed_real_data()
                return
            logger.info("Database already seeded. Skipping.")
            return

        _seed_districts_and_barangays(session)
        _seed_default_admin(session)
        session.commit()
        logger.info("Database seeded successfully.")
        session.close()

        # Now seed real data
        _seed_real_data()

    except Exception as e:
        session.rollback()
        logger.error(f"Seed failed: {e}")
        raise
    finally:
        try:
            session.close()
        except Exception:
            pass


def _seed_districts_and_barangays(session):
    with open(SEED_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    for district_data in data["districts"]:
        district = District(name=district_data["name"])
        session.add(district)
        session.flush()

        for brgy_entry in district_data["barangays"]:
            # Support both old format (string) and new format (dict with name/lat/lon)
            if isinstance(brgy_entry, str):
                name, lat, lon = brgy_entry, None, None
            else:
                name = brgy_entry["name"]
                lat = brgy_entry.get("lat")
                lon = brgy_entry.get("lon")

            barangay = Barangay(
                district_id=district.id,
                name=name,
                latitude=lat,
                longitude=lon,
            )
            session.add(barangay)

    session.flush()
    total = session.query(Barangay).count()
    logger.info(f"Seeded {session.query(District).count()} districts and {total} barangays.")


def _seed_default_admin(session):
    from auth.auth_manager import AuthManager
    auth = AuthManager()

    existing = session.query(User).filter_by(username=DEFAULT_ADMIN_USERNAME).first()
    if existing:
        return

    admin = User(
        username=DEFAULT_ADMIN_USERNAME,
        password_hash=auth.hash_password(DEFAULT_ADMIN_PASSWORD),
        full_name=DEFAULT_ADMIN_FULLNAME,
        role="admin",
        is_active=True,
        must_change_password=True,
    )
    session.add(admin)
    logger.info("Default admin user created.")


def _seed_real_data():
    """Seed real Davao City data (population, income, utilities, etc.) on first run."""
    try:
        from database.real_data import seed_real_data
        logger.info("Seeding real Davao City data (this may take a moment)...")
        seed_real_data(skip_init=True)
        logger.info("Real data seeding complete.")
    except Exception as e:
        logger.error(f"Real data seeding failed: {e}")
        logger.info("The app will still work — you can enter data manually or run: python -m database.real_data")
