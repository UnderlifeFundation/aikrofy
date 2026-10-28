import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

conn = pymysql.connect(
    host=os.getenv('MYSQL_HOST'),
    user=os.getenv('MYSQL_USER'),
    password=os.getenv('MYSQL_PASSWORD'),
    database=os.getenv('MYSQL_DATABASE'),
    port=int(os.getenv('MYSQL_PORT', 3306))
)

try:
    with conn.cursor() as cursor:
        cursor.execute("SELECT id, name, external_plan_token FROM plans")
        rows = cursor.fetchall()
        for row in rows:
            print(f"ID: {row[0]}, Name: {row[1]}, Token: {row[2]}")
finally:
    conn.close()
