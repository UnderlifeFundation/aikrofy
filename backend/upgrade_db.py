"""
Database Upgrade Script - Adds new columns to existing tables and creates new tables.
Idempotent and safe to run multiple times.
"""
import os
import logging
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("database_upgrade")

# Load env variables
load_dotenv()
db_uri = os.getenv('DATABASE_URL') or os.getenv('SQLALCHEMY_DATABASE_URI') or "mysql+pymysql://root:root@localhost:3306/aikrofy"

def upgrade_database():
    logger.info("Connecting to database...")
    engine = create_engine(db_uri)
    
    # 1. Inspect existing columns in 'customers'
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('customers')]
    logger.info(f"Existing columns in 'customers': {columns}")
    
    # 2. Add columns to 'customers' if they do not exist
    with engine.begin() as conn:
        # Check and create funnel_stage_id
        if 'funnel_stage_id' not in columns:
            logger.info("Altering 'customers' table to add 'funnel_stage_id'...")
            # We first create the funnel_stages table structure if not exists so constraint is valid
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS `funnel_stages` (
                    `id` INT AUTO_INCREMENT,
                    `company_id` INT NOT NULL,
                    `name` VARCHAR(100) NOT NULL,
                    `sort_order` INT NOT NULL DEFAULT 0,
                    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
                    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (`id`),
                    KEY `idx_company_id` (`company_id`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """))
            conn.execute(text("""
                ALTER TABLE `customers` 
                ADD COLUMN `funnel_stage_id` INT NULL,
                ADD CONSTRAINT `fk_customers_funnel_stage` 
                FOREIGN KEY (`funnel_stage_id`) REFERENCES `funnel_stages` (`id`) ON DELETE SET NULL;
            """))
            logger.info("Column 'funnel_stage_id' added with foreign key constraint.")
        else:
            logger.info("Column 'funnel_stage_id' already exists.")

        # Check and create lead_score
        if 'lead_score' not in columns:
            logger.info("Altering 'customers' table to add 'lead_score'...")
            conn.execute(text("ALTER TABLE `customers` ADD COLUMN `lead_score` INT NOT NULL DEFAULT 0;"))
            logger.info("Column 'lead_score' added successfully.")
        else:
            logger.info("Column 'lead_score' already exists.")

    # 3. Create all other new tables via SQLAlchemy metadata
    logger.info("Creating any other missing tables using SQLAlchemy models...")
    from app import create_app
    from extensions import db
    import models  # Import package to register all models in metadata
    
    app = create_app()
    with app.app_context():
        # This will register and create funnel_stages, contact_attributions, tenant_scoring_configs, etc.
        db.metadata.create_all(bind=engine)
        logger.info("All model tables verified/created.")

if __name__ == '__main__':
    upgrade_database()
