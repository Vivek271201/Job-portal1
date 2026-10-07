"""Load sample data into the database.

Usage:   python seed.py          (only if the database is empty)
         python seed.py --reset  (DROPS all tables first, then re-creates + seeds)
"""
import sys

from sqlalchemy import func, select

from database.connection import SessionLocal, engine
from database.models import Base, User
from services import file_service
from services.seed_data import SAMPLE_PASSWORD, seed


def main():
    if "--reset" in sys.argv:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    file_service.ensure_dirs()
    with SessionLocal() as db:
        if db.scalar(select(func.count()).select_from(User)):
            print("Database already contains users. Use `python seed.py --reset` to start over.")
            return
        counts = seed(db, file_service.UPLOAD_DIR)
    print("Sample data loaded:", counts)
    print(f"Login with any sample account, password: {SAMPLE_PASSWORD}")
    print("  Employer: hr@techvista.example.com\n  Seeker  : aarav.sharma@example.com")


if __name__ == "__main__":
    main()
