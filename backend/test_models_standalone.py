
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config import get_config
from models.user import User

config = get_config()
engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

try:
    user = session.query(User).first()
    print(f"Found user: {user.email}")
except Exception as e:
    print(f"Error: {e}")
finally:
    session.close()
