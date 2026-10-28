import os
import pymysql
import bcrypt
from dotenv import load_dotenv

load_dotenv()

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
    conn = get_connection()
    try:
        target_email = os.getenv('ADMIN_EMAIL', 'admin@aikrofy.local')
        new_password = os.getenv('NEW_ADMIN_PASSWORD', 'changeme_admin_123')
        hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        with conn.cursor() as cursor:
            # Check if user exists
            cursor.execute("SELECT id FROM users WHERE email=%s", (target_email,))
            user = cursor.fetchone()
            if not user:
                print("Error: User not found!")
                return
                
            cursor.execute(
                "UPDATE users SET password_hash=%s WHERE email=%s",
                (hashed, target_email)
            )
        conn.commit()
        print(f"Success: Password updated for '{target_email}'")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    main()
