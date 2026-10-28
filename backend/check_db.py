import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
db_uri = os.getenv('DATABASE_URL') or os.getenv('SQLALCHEMY_DATABASE_URI') or "mysql+pymysql://root:root@localhost:3306/aikrofy"
engine = create_engine(db_uri)

with engine.connect() as conn:
    result = conn.execute(text("SELECT id, company_id, contact_phone, channel FROM conversations ORDER BY id DESC LIMIT 5"))
    for row in result:
        print(row)
