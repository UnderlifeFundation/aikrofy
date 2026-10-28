import os
import sys

# Add backend to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_db():
    app = create_app()
    with app.app_context():
        logger.info("Starting database update...")
        
        # Add is_demo column
        try:
            db.session.execute(text("ALTER TABLE companies ADD COLUMN is_demo BOOLEAN DEFAULT FALSE;"))
            db.session.commit()
            logger.info("Column 'is_demo' added successfully.")
        except Exception as e:
            db.session.rollback()
            logger.warning(f"Failed to add 'is_demo' column (it might already exist): {e}")

        # Add demo_expires_at column
        try:
            db.session.execute(text("ALTER TABLE companies ADD COLUMN demo_expires_at DATETIME NULL;"))
            db.session.commit()
            logger.info("Column 'demo_expires_at' added successfully.")
        except Exception as e:
            db.session.rollback()
            logger.warning(f"Failed to add 'demo_expires_at' column (it might already exist): {e}")
            
        logger.info("Database update completed.")

if __name__ == '__main__':
    update_db()
