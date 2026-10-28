from app import create_app
from extensions import db
import logging
from sqlalchemy import text

# Import all models to ensure they are registered with SQLAlchemy
from models.email_log import EmailLog
from models.payment_gateway import PaymentGatewayConfig, PaymentTransaction
from models.purchased_number import PurchasedNumber
from models.whatsapp_template import WhatsAppTemplate
from models.media_asset import CompanyMediaAsset


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_missing_tables():
    app = create_app()
    with app.app_context():
        # Create all tables known to SQLAlchemy metadata (like email_logs)
        from database import engine
        logger.info("Creating missing SQLAlchemy tables...")
        db.metadata.create_all(bind=engine)
        logger.info("SQLAlchemy tables verified/created.")
        
        # Create external tables strictly needed by whatsapp node microservice
        logger.info("Ensuring bailey_sessions table exists for WhatsApp Node Service...")
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
        logger.info("bailey_sessions verified/created.")

if __name__ == '__main__':
    create_missing_tables()
