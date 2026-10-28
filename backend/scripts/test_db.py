import pymysql
import os
import sys

# Try to load environment from various locations
def get_env_val(key, default=None):
    return os.environ.get(key, default)

def test_connection():
    # Attempt to read from .env if possible
    try:
        from dotenv import load_dotenv
        # Check current dir and parent dir for .env
        for p in ['.env', '../.env', 'backend/.env']:
            if os.path.exists(p):
                load_dotenv(p)
                break
    except ImportError:
        pass

    host = get_env_val('MYSQL_HOST', '127.0.0.1')
    port = int(get_env_val('MYSQL_PORT', 3306))
    user = get_env_val('MYSQL_USER', 'root')
    password = get_env_val('MYSQL_PASSWORD', '')
    db_name = get_env_val('MYSQL_DATABASE', 'aikrofy')

    print(f"--- PymAI Database Connectivity Probe ---")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"User: {user}")
    print(f"DB:   {db_name}")
    print("-" * 40)
    
    try:
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=db_name,
            connect_timeout=10
        )
        print("\n✅ CONNECTION SUCCESSFUL!")
        print("Your VPS can reach the remote database.")
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            result = cursor.fetchone()
            print(f"Verified Database Name: {result[0]}")
            
        connection.close()
    except pymysql.err.OperationalError as e:
        code, msg = e.args
        print(f"\n❌ CONNECTION FAILED (Code: {code})")
        if code == 2003:
            print("💡 DIAGNOSIS: Connection Timeout/Refused.")
            print("🛑 CAUSE: The remote server is not responding to your VPS.")
            print("🛠 ACTION: Ensure the VPS IP (109.205.180.23) is whitelisted in Hostinger's Remote MySQL panel.")
        elif code == 1045:
            print("💡 DIAGNOSIS: Access Denied.")
            print("🛠 ACTION: Check your DB_USER and DB_PASSWORD.")
        else:
            print(f"Detail: {msg}")
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")

if __name__ == "__main__":
    test_connection()
