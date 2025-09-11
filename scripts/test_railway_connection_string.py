#!/usr/bin/env python3
import mysql.connector
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get credentials from environment variables
host = os.getenv('MYSQL_HOST', 'shuttle.proxy.rlwy.net')
user = os.getenv('MYSQL_USER', 'root')
password = os.getenv('MYSQL_PASSWORD', 'YEQSqCUDYMKHVEqVtTRkCmoYkssrmasc')
database = os.getenv('MYSQL_DATABASE', 'railway')
port = int(os.getenv('MYSQL_PORT', '40319'))

print("=== Testing Railway Connection String Format ===")
print(f"Host: {host}")
print(f"User: {user}")
print(f"Password: {password[:5]}...{password[-5:]}")
print(f"Database: {database}")
print(f"Port: {port}")
print("=" * 50)

# Test with Railway's recommended connection format
try:
    # Railway often uses this format
    conn = mysql.connector.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        ssl_disabled=True,  # Railway sometimes requires this
        use_pure=True,
        autocommit=True
    )
    print("✅ SUCCESS with ssl_disabled=True!")
    
    # Test a simple query
    cursor = conn.cursor()
    cursor.execute("SELECT 1 as test")
    result = cursor.fetchone()
    print(f"✅ Query test: {result}")
    
    cursor.close()
    conn.close()
    print("✅ Connection closed successfully!")
    
except Exception as e:
    print(f"❌ FAILED: {e}")
    print(f"Error type: {type(e).__name__}")
    
    # Try with different SSL settings
    print("\n--- Trying with SSL enabled ---")
    try:
        conn = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            ssl_verify_cert=False,
            ssl_verify_identity=False,
            use_pure=True,
            autocommit=True
        )
        print("✅ SUCCESS with SSL settings!")
        
        cursor = conn.cursor()
        cursor.execute("SELECT 1 as test")
        result = cursor.fetchone()
        print(f"✅ Query test: {result}")
        
        cursor.close()
        conn.close()
        print("✅ Connection closed successfully!")
        
    except Exception as e2:
        print(f"❌ FAILED: {e2}")
        print(f"Error type: {type(e2).__name__}")
