
"""
Script to create the email_logs table.
"""
import sys
import os

# Add parent directory to path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from extensions import db
from models.email_log import EmailLog # Import to register with SQLAlchemy

app = create_app()

def main():
    print("Creating email_logs table...")
    with app.app_context():
        # Create table if not exists
        db.create_all() # This is safe, it only creates missing tables
        print("Table email_logs checked/created.")

if __name__ == '__main__':
    main()
