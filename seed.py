import json
import os
import sys
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, SessionLocal
from app.models import Profile
from uuid6 import uuid7

def seed():
    from app import models
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_file = os.path.join(os.path.dirname(__file__), "seed_profiles.json")
        with open(seed_file, "r") as f:
            data = json.load(f)
        profiles = data.get("profiles", [])
        print(f"Found {len(profiles)} profiles to seed...")
        inserted = 0
        skipped = 0
        for p in profiles:
            name = p.get("name", "").strip()
            if not name:
                skipped += 1
                continue
            existing = db.query(Profile).filter(Profile.name == name).first()
            if existing:
                skipped += 1
                continue
            profile = Profile(
                id=str(uuid7()),
                name=name,
                gender=p.get("gender", ""),
                gender_probability=float(p.get("gender_probability", 0)),
                age=int(p.get("age", 0)),
                age_group=p.get("age_group", ""),
                country_id=p.get("country_id", ""),
                country_name=p.get("country_name", ""),
                country_probability=float(p.get("country_probability", 0)),
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            db.add(profile)
            inserted += 1
            if inserted % 100 == 0:
                db.commit()
                print(f"Inserted {inserted} so far...")
        db.commit()
        print(f"Done! Inserted: {inserted}, Skipped: {skipped}")
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed()