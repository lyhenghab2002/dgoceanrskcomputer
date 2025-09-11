#!/usr/bin/env python3
import mysql.connector
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get credentials from environment variables or use Railway defaults
host = os.getenv('MYSQL_HOST', 'shuttle.proxy.rlwy.net')
user = os.getenv('MYSQL_USER', 'root')
password = os.getenv('MYSQL_PASSWORD', 'YEQSqCUDYMKHVEqVtTRkCmoYkssrmasc')
database = os.getenv('MYSQL_DATABASE', 'railway')  # Note: Railway uses MYSQL_DATABASE, not MYSQL_DB
port = int(os.getenv('MYSQL_PORT', '40319'))

print("=== Testing Exact Railway Connection ===")
print(f"Host: {host}")
print(f"User: {user}")
print(f"Password: {password[:5]}...{password[-5:]}")
print(f"Database: {database}")
print(f"Port: {port}")
print("=" * 50)

# Test different connection methods
connection_methods = [
    {
        "name": "Basic connection",
        "params": {
            "host": host,
            "user": user,
            "password": password,
            "database": database,
            "port": port,
            "use_pure": True
        }
    },
    {
        "name": "With autocommit",
        "params": {
            "host": host,
            "user": user,
            "password": password,
            "database": database,
            "port": port,
            "use_pure": True,
            "autocommit": True
        }
    },
    {
        "name": "With timeout",
        "params": {
            "host": host,
            "user": user,
            "password": password,
            "database": database,
            "port": port,
            "use_pure": True,
            "connect_timeout": 60
        }
    },
    {
        "name": "With native password",
        "params": {
            "host": host,
            "user": user,
            "password": password,
            "database": database,
            "port": port,
            "use_pure": True,
            "auth_plugin": "mysql_native_password"
        }
    },
    {
        "name": "All parameters combined",
        "params": {
            "host": host,
            "user": user,
            "password": password,
            "database": database,
            "port": port,
            "use_pure": True,
            "autocommit": True,
            "connect_timeout": 60,
            "auth_plugin": "mysql_native_password"
        }
    },
    {
        "name": "Without auth_plugin",
        "params": {
            "host": host,
            "user": user,
            "password": password,
            "database": database,
            "port": port,
            "use_pure": True,
            "autocommit": True,
            "connect_timeout": 60
        }
    },
    {
        "name": "With caching_sha2_password",
        "params": {
            "host": host,
            "user": user,
            "password": password,
            "database": database,
            "port": port,
            "use_pure": True,
            "autocommit": True,
            "connect_timeout": 60,
            "auth_plugin": "caching_sha2_password"
        }
    }
]

for method in connection_methods:
    print(f"\n--- Testing: {method['name']} ---")
    try:
        conn = mysql.connector.connect(**method['params'])
        print("✅ SUCCESS!")
        
        # Test a simple query
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        print(f"✅ Query test: {result}")
        
        cursor.close()
        conn.close()
        print("✅ Connection closed successfully!")
        break  # Stop on first success
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        print(f"Error type: {type(e).__name__}")
