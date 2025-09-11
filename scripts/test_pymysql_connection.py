#!/usr/bin/env python3
import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get credentials
host = os.getenv('MYSQL_HOST', 'shuttle.proxy.rlwy.net')
user = os.getenv('MYSQL_USER', 'root')
password = os.getenv('MYSQL_PASSWORD', 'YEQSqCUDYMKHVEqVtTRkCmoYkssrmasc')
database = os.getenv('MYSQL_DATABASE', 'railway')
port = int(os.getenv('MYSQL_PORT', '40319'))

print("=== Testing with PyMySQL (Alternative to mysql-connector) ===")
print(f"Host: {host}")
print(f"User: {user}")
print(f"Password: {password[:5]}...{password[-5:]}")
print(f"Database: {database}")
print(f"Port: {port}")
print("=" * 50)

try:
    # Test with PyMySQL
    conn = pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        port=port,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    print("✅ SUCCESS with PyMySQL!")
    
    # Test a simple query
    with conn.cursor() as cursor:
        cursor.execute("SELECT 1 as test, NOW() as current_time")
        result = cursor.fetchone()
        print(f"✅ Query test: {result}")
    
    conn.close()
    print("✅ Connection closed successfully!")
    
except Exception as e:
    print(f"❌ FAILED with PyMySQL: {e}")
    print(f"Error type: {type(e).__name__}")
    
    # Try with different parameters
    print("\n--- Trying with different PyMySQL parameters ---")
    try:
        conn = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=60,
            read_timeout=60,
            write_timeout=60
        )
        print("✅ SUCCESS with PyMySQL (with timeouts)!")
        
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 as test, NOW() as current_time")
            result = cursor.fetchone()
            print(f"✅ Query test: {result}")
        
        conn.close()
        print("✅ Connection closed successfully!")
        
    except Exception as e2:
        print(f"❌ FAILED with PyMySQL (with timeouts): {e2}")
        print(f"Error type: {type(e2).__name__}")
