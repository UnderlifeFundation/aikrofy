"""
PymAI - Master VPS Local Database Setup and Adjustment Script
Initializes tables, creates WhatsApp session tables, injects beta trial columns,
and seeds default subscription plans. Fully idempotent.

Run on the VPS:
  python setup_vps_local_db.py
"""
import logging
from sqlalchemy import text
from app import create_app
from extensions import db

# Import all models to ensure they are registered with SQLAlchemy metadata
from models.user import User, UserRole
from models.company import Company
from models.agent import Agent
from models.conversation import Conversation, Message
from models.subscription import Plan, Subscription
from models.email_log import EmailLog
from models.payment_gateway import PaymentGatewayConfig, PaymentTransaction
from models.purchased_number import PurchasedNumber

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("vps-db-setup")

def run_db_setup():
    app = create_app()
    with app.app_context():
        logger.info("Connecting to target database...")
        from database import engine
        
        # 1. Create all base SQLAlchemy tables
        logger.info("Step 1/4: Creating base SQLAlchemy tables from models...")
        db.metadata.create_all(bind=engine)
        logger.info("SQLAlchemy base tables verified/created.")
        
        # 2. Create Node.js WhatsApp sessions table (bailey_sessions)
        logger.info("Step 2/4: Ensuring bailey_sessions table exists for api-whatsapp microservice...")
        create_bailey_sql = text("""
        CREATE TABLE IF NOT EXISTS `bailey_sessions` (
            `pk_id` varchar(255) NOT NULL,
            `session_id` varchar(255) NOT NULL,
            `data` json DEFAULT NULL,
            PRIMARY KEY (`pk_id`),
            KEY `session_id_idx` (`session_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)
        db.session.execute(create_bailey_sql)
        db.session.commit()
        logger.info("bailey_sessions table verified/created.")
        
        # 3. Add beta trial columns to companies table if they don't exist
        logger.info("Step 3/4: Inspecting companies table schema for beta trial columns...")
        result = db.session.execute(text("SHOW COLUMNS FROM companies"))
        columns = [row[0] for row in result.fetchall()]
        
        alterations = []
        if 'trial_activated' not in columns:
            alterations.append("ADD COLUMN trial_activated TINYINT(1) NOT NULL DEFAULT 0")
        if 'feedback_submitted' not in columns:
            alterations.append("ADD COLUMN feedback_submitted TINYINT(1) NOT NULL DEFAULT 0")
        if 'beta_feedback' not in columns:
            alterations.append("ADD COLUMN beta_feedback JSON DEFAULT NULL")
            
        if alterations:
            sql = f"ALTER TABLE companies {', '.join(alterations)};"
            logger.info(f"Executing schema adjustments: {sql}")
            db.session.execute(text(sql))
            db.session.commit()
            logger.info("Beta trial columns successfully added to companies table!")
        else:
            logger.info("companies table already has beta trial columns. No schema changes needed.")
            
        # 4. Seed subscription plans
        logger.info("Step 4/4: Seeding subscription plans (Jab, Uppercut, Knockout)...")
        from seed_plans import seed_plans
        try:
            # We call the function from seed_plans directly to avoid duplication
            seed_plans()
            logger.info("Subscription plans seeded successfully.")
        except Exception as seed_err:
            logger.error(f"Failed to seed subscription plans: {seed_err}")
            
        logger.info("🚀 Database setup and adjustment completed successfully!")

if __name__ == '__main__':
    run_db_setup()
