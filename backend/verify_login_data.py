import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

# Database Configuration from .env
MYSQL_HOST = os.getenv('MYSQL_HOST', '127.0.0.1')
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'aikrofy')

def get_connection():
    return pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        cursorclass=pymysql.cursors.DictCursor
    )

def main():
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            # Check user
            cursor.execute("SELECT id, name, email, role, is_active FROM users WHERE email=%s", ('jonnathan.ypg@gmail.com',))
            user = cursor.fetchone()
            
            if user:
                print(f"User Found: {user['name']} | Email: {user['email']} | Role: {user['role']} | Active: {user['is_active']}")
            else:
                print("Error: User 'jonnathan.ypg@gmail.com' NOT FOUND!")
            
            # Check Companies
            cursor.execute("SELECT id, name FROM companies")
            companies = cursor.fetchall()
            print(f"Total Companies: {len(companies)}")
            for c in companies:
                print(f"  - Company ID: {c['id']} | Name: {c['name']}")
                
    except Exception as e:
        print(f"Error connecting to database: {e}")
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()

if __name__ == '__main__':
    main()
