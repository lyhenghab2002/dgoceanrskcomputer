#!/usr/bin/env python3
"""
Check Database Configuration
"""

import os
from config import Config

print("🔍 DATABASE CONFIGURATION CHECK")
print("=" * 50)

print("📋 Environment Variables:")
print(f"MYSQL_DB: {os.getenv('MYSQL_DB')}")
print(f"MYSQL_HOST: {os.getenv('MYSQL_HOST')}")
print(f"MYSQL_USER: {os.getenv('MYSQL_USER')}")
print(f"MYSQL_PASSWORD: {'*' * 10 if os.getenv('MYSQL_PASSWORD') else 'None'}")
print(f"MYSQL_PORT: {os.getenv('MYSQL_PORT')}")
print(f"MYSQL_URL: {os.getenv('MYSQL_URL')}")

print("\n📋 Config Class Values:")
print(f"Config.MYSQL_DB: {Config.MYSQL_DB}")
print(f"Config.MYSQL_HOST: {Config.MYSQL_HOST}")
print(f"Config.MYSQL_USER: {Config.MYSQL_USER}")
print(f"Config.MYSQL_PASSWORD: {'*' * 10 if Config.MYSQL_PASSWORD else 'None'}")
print(f"Config.MYSQL_PORT: {Config.MYSQL_PORT}")
print(f"Config.SQLALCHEMY_DATABASE_URI: {Config.SQLALCHEMY_DATABASE_URI}")

print("\n🔍 Analysis:")
if os.getenv('MYSQL_DB'):
    print("✅ Using environment variable for database name")
else:
    print("⚠️ Using default fallback value for database name")
    print(f"   Default: {Config.MYSQL_DB}")

print("\n💡 This explains why changing DB name doesn't affect the app:")
print("   - No environment variables are set")
print("   - App uses hardcoded defaults from config.py")
print("   - Default DB name is 'computershop5'")
