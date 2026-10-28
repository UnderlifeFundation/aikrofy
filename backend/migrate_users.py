import os
import pymysql
import bcrypt
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
            # 1. Update existing user (ID 1)
            print("Updating User ID 1 to yosue.jpg@gmail.com...")
            update_sql = "UPDATE users SET email=%s, name=%s WHERE id=1"
            cursor.execute(update_sql, ('yosue.jpg@gmail.com', 'Yosue'))
            
            # 2. Create Super Admin user
            admin_email = os.getenv('SUPER_ADMIN_EMAIL', 'admin@aikrofy.local')
            password = os.getenv('SUPER_ADMIN_PASSWORD', 'changeme_admin_123')
            print(f"Creating Super Admin user {admin_email}...")
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            insert_sql = """
                INSERT INTO users (email, password_hash, name, role, company_id, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
            """
            cursor.execute(insert_sql, (admin_email, hashed, 'SuperAdmin', 'super_admin', None, 1))
            
            conn.commit()
            print("User migration completed successfully.")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()

if __name__ == '__main__':
    main()
