"""
Migration: Add accuracy, speed, heading to users and user_devices.
"""
from database import engine
from sqlalchemy import text

def run_migration():
    print("Running migration: Uber-precision GPS fields...")
    with engine.connect() as conn:
        cols = [
            ("users", "last_gps_accuracy", "FLOAT NULL"),
            ("users", "last_gps_speed", "FLOAT NULL"),
            ("users", "last_gps_heading", "FLOAT NULL"),
            ("user_devices", "gps_accuracy", "FLOAT NULL"),
            ("user_devices", "gps_speed", "FLOAT NULL"),
            ("user_devices", "gps_heading", "FLOAT NULL")
        ]
        for tbl, col_name, col_type in cols:
            try:
                conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN {col_name} {col_type};"))
                print(f"Added {col_name} to {tbl}")
            except Exception as e:
                if "Duplicate column" in str(e) or "already exists" in str(e):
                    pass
                else:
                    print(f"Note on {tbl}.{col_name}: {e}")

        conn.commit()
        print("Uber-precision GPS migration applied successfully!")

if __name__ == "__main__":
    run_migration()
