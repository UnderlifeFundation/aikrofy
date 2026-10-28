#!/usr/bin/env python3
"""
IP Tracking & Geolocation Telemetry — Database Upgrade Script
Applies schema changes for user_ip_logs, blocked_ips, and IP geolocation columns.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    print("=" * 60)
    print("  Aikrofy — IP Tracking & Security Geolocation DB Upgrade")
    print("=" * 60)

    from database import engine
    from sqlalchemy import text, inspect

    insp = inspect(engine)
    existing_tables = insp.get_table_names()

    with engine.connect() as conn:
        # 1. user_ip_logs table
        if 'user_ip_logs' not in existing_tables:
            print("\n[1/4] Creating table 'user_ip_logs'...")
            conn.execute(text("""
                CREATE TABLE user_ip_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NULL,
                    company_id INT NULL,
                    ip_address VARCHAR(64) NOT NULL,
                    city VARCHAR(100) NULL,
                    region VARCHAR(100) NULL,
                    country VARCHAR(100) NULL,
                    country_code VARCHAR(10) NULL,
                    latitude DOUBLE NULL,
                    longitude DOUBLE NULL,
                    isp VARCHAR(255) NULL,
                    user_agent TEXT NULL,
                    endpoint VARCHAR(255) NULL,
                    request_count INT NOT NULL DEFAULT 1,
                    first_seen_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    last_seen_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX ix_user_ip_logs_user_id (user_id),
                    INDEX ix_user_ip_logs_company_id (company_id),
                    INDEX ix_user_ip_logs_ip (ip_address)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """))
            print("  ✓ 'user_ip_logs' created successfully.")
        else:
            print("  - Table 'user_ip_logs' already exists.")

        # 2. blocked_ips table
        if 'blocked_ips' not in existing_tables:
            print("\n[2/4] Creating table 'blocked_ips'...")
            conn.execute(text("""
                CREATE TABLE blocked_ips (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    ip_address VARCHAR(64) NOT NULL UNIQUE,
                    reason VARCHAR(255) NULL DEFAULT 'Bloqueo por Super Admin',
                    blocked_by INT NULL,
                    blocked_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    is_active TINYINT(1) NOT NULL DEFAULT 1,
                    INDEX ix_blocked_ips_ip (ip_address)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """))
            print("  ✓ 'blocked_ips' created successfully.")
        else:
            print("  - Table 'blocked_ips' already exists.")

        # 3. Add IP columns to users table
        print("\n[3/4] Updating 'users' table columns...")
        user_cols = [col['name'] for col in insp.get_columns('users')]
        cols_to_add_users = [
            ("last_ip", "VARCHAR(64) NULL"),
            ("last_ip_lat", "DOUBLE NULL"),
            ("last_ip_lng", "DOUBLE NULL"),
            ("last_ip_city", "VARCHAR(100) NULL"),
            ("last_ip_country", "VARCHAR(100) NULL"),
            ("last_ip_country_code", "VARCHAR(10) NULL"),
            ("last_ip_isp", "VARCHAR(255) NULL"),
            ("last_ip_updated_at", "DATETIME NULL"),
        ]
        for col_name, col_type in cols_to_add_users:
            if col_name not in user_cols:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
                print(f"  + Added column 'users.{col_name}'")

        # 4. Add IP columns to companies & beta_leads table
        print("\n[4/4] Updating 'companies' & 'beta_leads' table columns...")
        company_cols = [col['name'] for col in insp.get_columns('companies')]
        cols_to_add_comp = [
            ("last_ip", "VARCHAR(64) NULL"),
            ("last_ip_lat", "DOUBLE NULL"),
            ("last_ip_lng", "DOUBLE NULL"),
            ("last_ip_city", "VARCHAR(100) NULL"),
            ("last_ip_country", "VARCHAR(100) NULL"),
            ("last_ip_isp", "VARCHAR(255) NULL"),
            ("last_ip_updated_at", "DATETIME NULL"),
        ]
        for col_name, col_type in cols_to_add_comp:
            if col_name not in company_cols:
                conn.execute(text(f"ALTER TABLE companies ADD COLUMN {col_name} {col_type}"))
                print(f"  + Added column 'companies.{col_name}'")

        beta_cols = [col['name'] for col in insp.get_columns('beta_leads')]
        cols_to_add_beta = [
            ("submission_ip", "VARCHAR(64) NULL"),
            ("ip_lat", "DOUBLE NULL"),
            ("ip_lng", "DOUBLE NULL"),
            ("ip_city", "VARCHAR(100) NULL"),
            ("ip_country", "VARCHAR(100) NULL"),
        ]
        for col_name, col_type in cols_to_add_beta:
            if col_name not in beta_cols:
                conn.execute(text(f"ALTER TABLE beta_leads ADD COLUMN {col_name} {col_type}"))
                print(f"  + Added column 'beta_leads.{col_name}'")

        conn.commit()

    print("\n" + "=" * 60)
    print("  ✓ Database Upgrade for IP Geolocation & Security Finished!")
    print("=" * 60)

if __name__ == '__main__':
    main()
