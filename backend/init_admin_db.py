from app import create_app
from extensions import db
from models.subscription import Plan, Subscription
from models.platform_config import PlatformConfig

def init_db():
    app = create_app()
    with app.app_context():
        print("Creating new tables...")
        # This will only create tables that don't exist
        db.create_all()
        print("Tables created successfully.")
        
        # Initialize platform config if missing
        PlatformConfig.get_config()
        print("Platform config initialized.")

if __name__ == '__main__':
    init_db()
