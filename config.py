import os

APP_NAME = "Davao City Barangay Profiling System"
APP_VERSION = "1.0.0"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "barangay_profiling.db")
SEED_DATA_PATH = os.path.join(BASE_DIR, "data", "davao_barangays.json")
LOG_PATH = os.path.join(BASE_DIR, "data", "app.log")

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"
DEFAULT_ADMIN_FULLNAME = "System Administrator"

BCRYPT_ROUNDS = 12
MIN_PASSWORD_LENGTH = 8

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800
WINDOW_MIN_WIDTH = 1024
WINDOW_MIN_HEIGHT = 600

BACKUP_DIR = os.path.join(BASE_DIR, "data", "backups")
MAX_BACKUPS = 10
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT = 3

DASHBOARD_REFRESH_SECONDS = 60
ANOMALY_CHECK_INTERVAL = 5
