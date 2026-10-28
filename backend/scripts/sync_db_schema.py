#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
  Aikrofy — Universal Dynamic Database & RAG Synchronizer
  Single Source of Truth: Automatically inspects all 34+ SQLAlchemy models,
  creates missing tables, adds missing columns dynamically, and verifies seeds & RAG.
═══════════════════════════════════════════════════════════════════════════════
"""
import os
import sys
import time
import logging

# Ensure backend root is in sys.path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("db_sync")

def sync_database_schema(verbose: bool = True):
    """
    Inspects all SQLAlchemy models and automatically synchronizes
    MySQL tables and columns to prevent 1054 Unknown Column errors.
    """
    start_time = time.time()
    if verbose:
        print("=" * 70)
        print("  🔄 Aikrofy — Universal Dynamic Database & Schema Synchronizer")
        print("=" * 70)

    try:
        from app import create_app
        from extensions import db
        from database import engine
        from sqlalchemy import text, inspect
        import models  # Imports all 34+ models to register them in metadata
    except Exception as e:
        logger.error(f"❌ Failed to load Flask app context or models: {e}")
        return False

    app = create_app()

    with app.app_context():
        # 1. Ensure all standard SQLAlchemy tables exist
        logger.info("[1/5] Verifying and creating missing SQLAlchemy tables...")
        try:
            db.metadata.create_all(bind=engine)
            logger.info("  ✓ Standard SQLAlchemy tables verified.")
        except Exception as e:
            logger.warning(f"  ⚠️ Warning creating tables: {e}")

        # 2. Ensure Microservice External Tables exist
        logger.info("[2/5] Verifying external microservice tables (WhatsApp / Security)...")
        with engine.connect() as conn:
            # Bailey Sessions (Node.js WhatsApp microservice)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS `bailey_sessions` (
                    `pk_id` varchar(255) NOT NULL,
                    `session_id` varchar(255) NOT NULL,
                    `data` json DEFAULT NULL,
                    PRIMARY KEY (`pk_id`),
                    KEY `session_id_idx` (`session_id`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """))

            # User IP logs
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS `user_ip_logs` (
                    `id` INT AUTO_INCREMENT PRIMARY KEY,
                    `user_id` INT NULL,
                    `company_id` INT NULL,
                    `ip_address` VARCHAR(64) NOT NULL,
                    `city` VARCHAR(100) NULL,
                    `region` VARCHAR(100) NULL,
                    `country` VARCHAR(100) NULL,
                    `country_code` VARCHAR(10) NULL,
                    `latitude` DOUBLE NULL,
                    `longitude` DOUBLE NULL,
                    `isp` VARCHAR(255) NULL,
                    `user_agent` TEXT NULL,
                    `endpoint` VARCHAR(255) NULL,
                    `request_count` INT NOT NULL DEFAULT 1,
                    `first_seen_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    `last_seen_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX `ix_user_ip_logs_user_id` (`user_id`),
                    INDEX `ix_user_ip_logs_company_id` (`company_id`),
                    INDEX `ix_user_ip_logs_ip` (`ip_address`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """))

            # User Devices
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS `user_devices` (
                    `id` INT AUTO_INCREMENT PRIMARY KEY,
                    `user_id` INT NULL,
                    `company_id` INT NULL,
                    `device_id` VARCHAR(100) NOT NULL,
                    `device_name` VARCHAR(255) NULL,
                    `device_type` VARCHAR(50) NOT NULL DEFAULT 'desktop',
                    `network_ip` VARCHAR(64) NOT NULL,
                    `isp` VARCHAR(255) NULL,
                    `gps_lat` FLOAT NULL,
                    `gps_lng` FLOAT NULL,
                    `has_hardware_gps` BOOLEAN NOT NULL DEFAULT FALSE,
                    `city` VARCHAR(100) NULL,
                    `country` VARCHAR(100) NULL,
                    `country_code` VARCHAR(10) NULL,
                    `user_agent` TEXT NULL,
                    `request_count` INT NOT NULL DEFAULT 1,
                    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
                    `first_seen_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    `last_seen_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX `idx_device_id` (`device_id`),
                    INDEX `idx_network_ip` (`network_ip`),
                    INDEX `idx_user_id` (`user_id`),
                    INDEX `idx_company_id` (`company_id`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """))

            # Blocked IPs
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS `blocked_ips` (
                    `id` INT AUTO_INCREMENT PRIMARY KEY,
                    `ip_address` VARCHAR(64) NOT NULL UNIQUE,
                    `reason` VARCHAR(255) NULL DEFAULT 'Bloqueo por Super Admin',
                    `blocked_by` INT NULL,
                    `blocked_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    `is_active` TINYINT(1) NOT NULL DEFAULT 1,
                    INDEX `ix_blocked_ips_ip` (`ip_address`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """))
            conn.commit()
            logger.info("  ✓ External microservice tables verified.")

        # 3. Dynamic Column Inspection & Auto-Migration
        logger.info("[3/5] Inspecting all model columns and applying missing columns...")
        inspector = inspect(engine)
        db_tables = inspector.get_table_names()
        columns_added_count = 0

        with engine.connect() as conn:
            for table_name, table in db.metadata.tables.items():
                if table_name not in db_tables:
                    continue

                try:
                    existing_cols = {c['name'].lower(): c for c in inspector.get_columns(table_name)}
                except Exception as e:
                    logger.warning(f"  Could not inspect table '{table_name}': {e}")
                    continue

                for col in table.columns:
                    col_name_lower = col.name.lower()
                    if col_name_lower not in existing_cols:
                        # Compute MySQL datatype
                        try:
                            col_type = col.type.compile(engine.dialect)
                        except Exception:
                            col_type = str(col.type)

                        # Determine default or nullable clause
                        default_clause = ""
                        if col.default is not None and hasattr(col.default, 'arg') and not callable(col.default.arg):
                            val = col.default.arg
                            if isinstance(val, bool):
                                default_clause = f" DEFAULT {1 if val else 0}"
                            elif isinstance(val, (int, float)):
                                default_clause = f" DEFAULT {val}"
                            elif isinstance(val, str):
                                default_clause = f" DEFAULT '{val}'"

                        alter_sql = f"ALTER TABLE `{table_name}` ADD COLUMN `{col.name}` {col_type} NULL{default_clause};"
                        try:
                            conn.execute(text(alter_sql))
                            conn.commit()
                            columns_added_count += 1
                            logger.info(f"  [+] Added missing column `{table_name}`.`{col.name}` ({col_type})")
                        except Exception as alter_err:
                            if "Duplicate column" in str(alter_err) or "already exists" in str(alter_err):
                                pass
                            else:
                                logger.warning(f"  ⚠️ Could not add column `{table_name}`.`{col.name}`: {alter_err}")

        logger.info(f"  ✓ Column inspection finished. ({columns_added_count} missing columns added)")

        # 4. Essential Seed Data Verification
        logger.info("[4/5] Verifying essential seed data (Plans & Platform Config & Beta Access)...")
        with engine.connect() as conn:
            try:
                conn.execute(text("UPDATE `users` SET `is_beta_approved` = 1 WHERE `is_beta_approved` IS NULL OR `company_id` IS NOT NULL;"))
                conn.commit()
                logger.info("  ✓ Verified and ensured beta approval for all active corporate users.")
            except Exception as e:
                logger.warning(f"  Note verifying is_beta_approved: {e}")

            # 4b. Ensure company ownership back-fill (idempotent)
            #     The is_company_owner flag must be True for the first registered user
            #     of each company (the root account). We do this every deploy to
            #     ensure correctness even if the column was just added.
            try:
                rows = conn.execute(text("""
                    SELECT MIN(id) AS uid
                    FROM   users
                    WHERE  role = 'admin'
                      AND  company_id IS NOT NULL
                    GROUP  BY company_id
                """)).fetchall()
                owner_ids = [row[0] for row in rows if row[0] is not None]
                if owner_ids:
                    # Unset any incorrectly set flags first (safety)
                    conn.execute(text("UPDATE `users` SET `is_company_owner` = FALSE WHERE `company_id` IS NOT NULL AND `role` = 'admin'"))
                    # Re-set only the true owners
                    for uid in owner_ids:
                        conn.execute(text("UPDATE `users` SET `is_company_owner` = TRUE WHERE id = :id"), {'id': uid})
                    conn.commit()
                    logger.info(f"  ✓ Company ownership back-fill verified. ({len(owner_ids)} owners marked).")
            except Exception as e:
                logger.warning(f"  Note during ownership back-fill: {e}")

        try:
            from seed_plans import seed_plans
            seed_plans()
        except Exception as seed_err:
            logger.warning(f"  ⚠️ Seed plans note: {seed_err}")

        # 5. Verify RAG Global Handbooks (BOS-AI)
        logger.info("[5/5] Checking BOS-AI Handbooks in Knowledge Base (RAG)...")
        try:
            from scripts.import_bos_ai import import_bos_ai_handbooks
            import_bos_ai_handbooks()
        except Exception as rag_err:
            logger.warning(f"  ⚠️ BOS-AI RAG check note: {rag_err}")

    elapsed = round(time.time() - start_time, 2)
    if verbose:
        print("=" * 70)
        print(f"  ✅ Database & RAG Sync Completed Successfully in {elapsed}s!")
        print("=" * 70)
    return True

if __name__ == '__main__':
    success = sync_database_schema(verbose=True)
    sys.exit(0 if success else 1)
