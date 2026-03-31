import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db import init_db
from ui.app import App
from utils.logger import setup_logging


def main():
    setup_logging()
    init_db()

    from services.system_service import auto_backup_on_startup, auto_generate_reports
    auto_backup_on_startup()
    auto_generate_reports()

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
