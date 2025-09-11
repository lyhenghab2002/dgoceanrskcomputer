#!/usr/bin/env python3
import mysql.connector
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Use the exact MYSQL_PUBLIC_URL from Railway
mysql_public_url = os.getenv('MYSQL_PUBLIC_URL', 'mysql://root:YEQSqCUDYMKHVEqVtTRkCmoYkssrmasc@shuttle.proxy.rlwy.net:40319/railway')

print("=== Testing Railway MYSQL_PUBLIC_URL ===")
print(f"Connection URL: {mysql_public_url}")
print("=" * 50)

# Parse the URL
import re
match = re.match(r'mysql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', mysql_public_url)
if match:
    user, password, host, port, database = match.groups()
    port = int(port)
    
    print(f"Parsed - Host: {host}")
    print(f"Parsed - User: {user}")
    print(f"Parsed - Password: {password[:5]}...{password[-5:]}")
    print(f"Parsed - Database: {database}")
    print(f"Parsed - Port: {port}")
    print("=" * 50)
    
    # Test connection methods
    connection_methods = [
        {
            "name": "Basic connection with public URL",
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
            "name": "With SSL disabled",
            "params": {
                "host": host,
                "user": user,
                "password": password,
                "database": database,
                "port": port,
                "use_pure": True,
                "ssl_disabled": True
            }
        },
        {
            "name": "With autocommit and SSL disabled",
            "params": {
                "host": host,
                "user": user,
                "password": password,
                "database": database,
                "port": port,
                "use_pure": True,
                "ssl_disabled": True,
                "autocommit": True
            }
        },
        {
            "name": "With timeout and SSL disabled",
            "params": {
                "host": host,
                "user": user,
                "password": password,
                "database": database,
                "port": port,
                "use_pure": True,
                "ssl_disabled": True,
                "autocommit": True,
                "connect_timeout": 60
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
            cursor.execute("SELECT 1 as test, NOW() as current_time")
            result = cursor.fetchone()
            print(f"✅ Query test: {result}")
            
            cursor.close()
            conn.close()
            print("✅ Connection closed successfully!")
            break  # Stop on first success
            
        except Exception as e:
            print(f"❌ FAILED: {e}")
            print(f"Error type: {type(e).__name__}")
else:
    print("❌ Failed to parse MYSQL_PUBLIC_URL")
