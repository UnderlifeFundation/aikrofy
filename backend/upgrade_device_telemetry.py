"""
Migration: Add user_devices table and device telemetry columns to users & companies.
"""
from database import engine
from sqlalchemy import text

def run_migration():
    print("Running migration: Device Telemetry & Physical Hardware Identification...")
    with engine.connect() as conn:
        # 1. Create user_devices table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_devices (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NULL,
                company_id INT NULL,
                device_id VARCHAR(100) NOT NULL,
                device_name VARCHAR(255) NULL,
                device_type VARCHAR(50) NOT NULL DEFAULT 'desktop',
                network_ip VARCHAR(64) NOT NULL,
                isp VARCHAR(255) NULL,
                gps_lat FLOAT NULL,
                gps_lng FLOAT NULL,
                has_hardware_gps BOOLEAN NOT NULL DEFAULT FALSE,
                city VARCHAR(100) NULL,
                country VARCHAR(100) NULL,
                country_code VARCHAR(10) NULL,
                user_agent TEXT NULL,
                request_count INT NOT NULL DEFAULT 1,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                first_seen_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_seen_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_device_id (device_id),
                INDEX idx_network_ip (network_ip),
                INDEX idx_user_id (user_id),
                INDEX idx_company_id (company_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """))
        
        # 2. Add device columns to users
        user_cols = [
            ("last_device_id", "VARCHAR(100) NULL"),
            ("last_device_name", "VARCHAR(255) NULL"),
            ("last_device_type", "VARCHAR(50) NULL"),
            ("last_gps_lat", "FLOAT NULL"),
            ("last_gps_lng", "FLOAT NULL"),
            ("has_hardware_gps", "BOOLEAN DEFAULT FALSE")
        ]
        for col_name, col_type in user_cols:
            try:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type};"))
                print(f"Added {col_name} to users")
            except Exception as e:
                if "Duplicate column" in str(e) or "already exists" in str(e):
                    pass
                else:
                    print(f"Note on users.{col_name}: {e}")

        conn.commit()
        print("Device telemetry migration applied successfully!")

if __name__ == "__main__":
    run_migration()
