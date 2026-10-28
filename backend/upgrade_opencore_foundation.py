"""
Database Upgrade Script - Fundación Underlife Open-Core Initiative
Adds business_category, courtesy_credits_granted, courtesy_credits_expires_at
to the 'companies' table safely and idempotently.

Copyright © 2026 FUNDACIÓN UNDERLIFE & WEBLIFETECH (Jonnathan Peña).
"""
import os
import logging
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("upgrade_foundation_opencore")

load_dotenv()
db_uri = os.getenv('DATABASE_URL') or os.getenv('SQLALCHEMY_DATABASE_URI') or "mysql+pymysql://root:root@localhost:3306/aikrofy"

def upgrade_companies_schema():
    logger.info("Connecting to database for Open-Core migration...")
    try:
        engine = create_engine(db_uri)
        inspector = inspect(engine)
        
        tables = inspector.get_table_names()
        if 'companies' not in tables:
            logger.warning("Table 'companies' not found in database. Skipping migration.")
            return

        columns = [col['name'] for col in inspector.get_columns('companies')]
        logger.info(f"Current columns in 'companies': {len(columns)} found.")

        with engine.begin() as conn:
            # 1. business_category
            if 'business_category' not in columns:
                logger.info("Adding 'business_category' column to 'companies'...")
                conn.execute(text("ALTER TABLE companies ADD COLUMN business_category VARCHAR(50) DEFAULT 'emprendimiento'"))
                logger.info("Successfully added 'business_category'.")
            else:
                logger.info("Column 'business_category' already exists.")

            # 2. courtesy_credits_granted
            if 'courtesy_credits_granted' not in columns:
                logger.info("Adding 'courtesy_credits_granted' column to 'companies'...")
                conn.execute(text("ALTER TABLE companies ADD COLUMN courtesy_credits_granted INT DEFAULT 0"))
                logger.info("Successfully added 'courtesy_credits_granted'.")
            else:
                logger.info("Column 'courtesy_credits_granted' already exists.")

            # 3. courtesy_credits_expires_at
            if 'courtesy_credits_expires_at' not in columns:
                logger.info("Adding 'courtesy_credits_expires_at' column to 'companies'...")
                conn.execute(text("ALTER TABLE companies ADD COLUMN courtesy_credits_expires_at DATETIME NULL"))
                logger.info("Successfully added 'courtesy_credits_expires_at'.")
            else:
                logger.info("Column 'courtesy_credits_expires_at' already exists.")

        logger.info("Open-Core database migration completed successfully!")
    except Exception as e:
        logger.error(f"Error executing migration: {e}")

if __name__ == "__main__":
    upgrade_companies_schema()
