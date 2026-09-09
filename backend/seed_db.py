"""Initialize materials.db and insert the default material catalog.

Usage:
    python seed_db.py

Safe to run repeatedly - existing material IDs are left untouched.
"""

from app.db import init_db, SessionLocal
from app.seed_data import seed

if __name__ == "__main__":
    init_db()
    db = SessionLocal()
    try:
        inserted = seed(db)
    finally:
        db.close()
    print(f"Database ready. Inserted {inserted} new material(s).")
