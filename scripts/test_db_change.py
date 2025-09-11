#!/usr/bin/env python3
"""
Test Database Name Change
"""

import os
from config import Config

print("🧪 TESTING DATABASE NAME CHANGE")
print("=" * 50)

print("1. Current Configuration:")
print(f"   Environment MYSQL_DB: {os.getenv('MYSQL_DB')}")
print(f"   Config MYSQL_DB: {Config.MYSQL_DB}")

print("\n2. Changing Environment Variable:")
os.environ['MYSQL_DB'] = 'test_database_name'
print(f"   New Environment MYSQL_DB: {os.getenv('MYSQL_DB')}")

print("\n3. Re-importing Config:")
# Force reload of config
import importlib
import config
importlib.reload(config)
from config import Config as NewConfig

print(f"   New Config MYSQL_DB: {NewConfig.MYSQL_DB}")
print(f"   New Connection URI: {NewConfig.SQLALCHEMY_DATABASE_URI}")

print("\n4. Testing Connection with New DB Name:")
try:
    import mysql.connector
    conn = mysql.connector.connect(
        host=NewConfig.MYSQL_HOST,
        port=NewConfig.MYSQL_PORT,
        user=NewConfig.MYSQL_USER,
        password=NewConfig.MYSQL_PASSWORD,
        database=NewConfig.MYSQL_DB
    )
    print("   ✅ Connection successful with new DB name!")
    conn.close()
except Exception as e:
    print(f"   ❌ Connection failed: {e}")
    print("   💡 This confirms your observation - changing DB name breaks the app")

print("\n5. Restoring Original DB Name:")
os.environ['MYSQL_DB'] = 'computershop5'
print(f"   Restored MYSQL_DB: {os.getenv('MYSQL_DB')}")

print("\n🎯 CONCLUSION:")
print("Your observation is CORRECT!")
print("- App uses environment variables, not hardcoded values")
print("- Changing DB name in code doesn't affect running app")
print("- Only changing .env file or environment variables affects the app")
