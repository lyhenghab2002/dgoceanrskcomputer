#!/usr/bin/env python3
"""
Test Environment Variable Reloading
"""

import os
from dotenv import load_dotenv

print("🧪 TESTING ENVIRONMENT VARIABLE RELOADING")
print("=" * 60)

print("1. Initial Environment Variables:")
print(f"   MYSQL_DB: {os.getenv('MYSQL_DB')}")

print("\n2. Loading .env file:")
load_dotenv()
print(f"   MYSQL_DB after load_dotenv(): {os.getenv('MYSQL_DB')}")

print("\n3. Simulating .env file change:")
print("   (In real scenario, you would edit .env file)")
print("   Let's change the environment variable directly:")

# Simulate changing the .env file
os.environ['MYSQL_DB'] = 'new_database_name'
print(f"   MYSQL_DB after change: {os.getenv('MYSQL_DB')}")

print("\n4. Reloading .env file:")
load_dotenv(override=True)  # This forces reload
print(f"   MYSQL_DB after reload: {os.getenv('MYSQL_DB')}")

print("\n5. Testing with config.py:")
from config import Config
print(f"   Config.MYSQL_DB: {Config.MYSQL_DB}")

print("\n🎯 KEY POINTS:")
print("✅ Environment variables are loaded ONCE when the app starts")
print("✅ Changing .env file doesn't affect running app")
print("✅ You need to RESTART the app to see .env changes")
print("✅ load_dotenv(override=True) can force reload in new processes")

print("\n💡 TO SEE .ENV CHANGES:")
print("1. Stop your running app (Ctrl+C)")
print("2. Edit .env file")
print("3. Start app again (python app.py)")
print("4. Changes will be visible")
