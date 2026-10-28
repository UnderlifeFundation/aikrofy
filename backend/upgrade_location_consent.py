"""
Migration: Add location_consent column to users and user_devices tables.
Allows persistent storage of user's Uber-style location sharing choice.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine
from sqlalchemy import text

def run_migration():
    print("Running migration: Location Consent persistence...")
    with engine.connect() as conn:
        # Add location_consent to users
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN location_consent VARCHAR(50) DEFAULT 'unknown' NULL;"))
            print("Added location_consent to users table")
        except Exception as e:
            if "Duplicate column" in str(e) or "already exists" in str(e):
                print("Column users.location_consent already exists")
            else:
                print(f"Note on users.location_consent: {e}")

        # Add location_consent to user_devices
        try:
            conn.execute(text("ALTER TABLE user_devices ADD COLUMN location_consent VARCHAR(50) DEFAULT 'unknown' NULL;"))
            print("Added location_consent to user_devices table")
        except Exception as e:
            if "Duplicate column" in str(e) or "already exists" in str(e):
                print("Column user_devices.location_consent already exists")
            else:
                print(f"Note on user_devices.location_consent: {e}")

        conn.commit()
        print("Location consent migration completed successfully!")

if __name__ == "__main__":
    run_migration()
