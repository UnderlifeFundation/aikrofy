"""
Migration: Add CRM tables and columns
- Creates 'notes' table
- Adds 'customer_id' column to 'conversations' table
"""
from app import create_app
from extensions import db
from sqlalchemy import text
import logging

# Import all models
from models import *
from models.note import Note

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    app = create_app()
    with app.app_context():
        # 1. Create any missing tables (notes, etc.)
        logger.info("Creating missing tables (notes)...")
        db.create_all()
        logger.info("Done.")

        # 2. Add customer_id to conversations if missing
        logger.info("Checking conversations.customer_id column...")
        try:
            result = db.session.execute(text(
                "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_NAME = 'conversations' AND COLUMN_NAME = 'customer_id'"
            ))
            if result.fetchone() is None:
                logger.info("Adding customer_id to conversations...")
                db.session.execute(text(
                    "ALTER TABLE conversations ADD COLUMN customer_id INT NULL, "
                    "ADD INDEX idx_conv_customer_id (customer_id), "
                    "ADD CONSTRAINT fk_conv_customer FOREIGN KEY (customer_id) REFERENCES customers(id)"
                ))
                db.session.commit()
                logger.info("customer_id added successfully.")
            else:
                logger.info("customer_id already exists. Skipping.")
        except Exception as e:
            logger.error(f"Error adding customer_id: {e}")
            db.session.rollback()

        logger.info("Migration complete!")

if __name__ == '__main__':
    migrate()
