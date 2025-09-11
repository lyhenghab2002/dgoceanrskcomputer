#!/usr/bin/env python3
import mysql.connector
import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=== Testing Railway Internal vs External Connections ===")
print("=" * 60)

# Test both internal and external URLs
test_configs = [
    {
        "name": "External (Public) URL",
        "host": "shuttle.proxy.rlwy.net",
        "port": 40319,
        "description": "This is the public URL that should work from anywhere"
    },
    {
        "name": "Internal URL", 
        "host": "mysql.railway.internal",
        "port": 3306,
        "description": "This is the internal URL (only works from within Railway)"
    }
]

for config in test_configs:
    print(f"\n--- Testing: {config['name']} ---")
    print(f"Description: {config['description']}")
    print(f"Host: {config['host']}")
    print(f"Port: {config['port']}")
    print("-" * 40)
    
    # Test with mysql-connector
    try:
        conn = mysql.connector.connect(
            host=config['host'],
            user='root',
            password='YEQSqCUDYMKHVEqVtTRkCmoYkssrmasc',
            database='railway',
            port=config['port'],
            use_pure=True,
            ssl_disabled=True,
            autocommit=True,
            connect_timeout=30
        )
        print("✅ SUCCESS with mysql-connector!")
        
        cursor = conn.cursor()
        cursor.execute("SELECT 1 as test, NOW() as current_time")
        result = cursor.fetchone()
        print(f"✅ Query test: {result}")
        
        cursor.close()
        conn.close()
        print("✅ Connection closed successfully!")
        
    except Exception as e:
        print(f"❌ FAILED with mysql-connector: {e}")
        
        # Try with PyMySQL
        try:
            conn = pymysql.connect(
                host=config['host'],
                user='root',
                password='YEQSqCUDYMKHVEqVtTRkCmoYkssrmasc',
                database='railway',
                port=config['port'],
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=30
            )
            print("✅ SUCCESS with PyMySQL!")
            
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 as test, NOW() as current_time")
                result = cursor.fetchone()
                print(f"✅ Query test: {result}")
            
            conn.close()
            print("✅ Connection closed successfully!")
            
        except Exception as e2:
            print(f"❌ FAILED with PyMySQL: {e2}")

print("\n" + "=" * 60)
print("SUMMARY:")
print("- If external URL fails but internal URL works: IP restriction issue")
print("- If both fail: Credentials or service issue")
print("- If external URL works: Your app should work!")
print("=" * 60)
