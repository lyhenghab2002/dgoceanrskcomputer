#!/usr/bin/env python3
"""
Test Local Database Connection
This script tests the database connection using your current configuration
"""

import os
import sys
from datetime import datetime

def test_database_connection():
    """Test database connection with current configuration"""
    print("🔍 LOCAL DATABASE CONNECTION TEST")
    print("=" * 50)
    print(f"Test started at: {datetime.now()}")
    print()
    
    # Import configuration
    try:
        from config import Config
        print("✅ Configuration imported successfully")
    except Exception as e:
        print(f"❌ Failed to import configuration: {e}")
        return False
    
    # Display current database settings
    print("\n📊 DATABASE CONFIGURATION:")
    print(f"Host: {Config.MYSQL_HOST}")
    print(f"Port: {Config.MYSQL_PORT}")
    print(f"Database: {Config.MYSQL_DB}")
    print(f"User: {Config.MYSQL_USER}")
    print(f"Password: {'*' * len(Config.MYSQL_PASSWORD) if Config.MYSQL_PASSWORD else 'None'}")
    print(f"Connection URI: {Config.SQLALCHEMY_DATABASE_URI}")
    print()
    
    # Test 1: Try mysql-connector-python
    print("🔌 TESTING MYSQL-CONNECTOR-PYTHON:")
    try:
        import mysql.connector
        print("✅ mysql-connector-python imported successfully")
        
        # Test connection
        conn = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB
        )
        
        if conn.is_connected():
            print("✅ Database connection successful!")
            
            # Test query
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"✅ MySQL Version: {version[0]}")
            
            # Test table access
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"✅ Found {len(tables)} tables in database")
            
            # Show some tables
            if tables:
                print("📋 Sample tables:")
                for table in tables[:5]:  # Show first 5 tables
                    print(f"  - {table[0]}")
                if len(tables) > 5:
                    print(f"  ... and {len(tables) - 5} more")
            
            cursor.close()
            conn.close()
            print("✅ Connection closed successfully")
            return True
        else:
            print("❌ Database connection failed")
            return False
            
    except ImportError as e:
        print(f"❌ mysql-connector-python not installed: {e}")
        print("💡 Install with: pip install mysql-connector-python")
        return False
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print(f"Error type: {type(e).__name__}")
        return False
    
    # Test 2: Try PyMySQL (alternative)
    print("\n🔌 TESTING PYMYSQL:")
    try:
        import pymysql
        print("✅ PyMySQL imported successfully")
        
        # Test connection
        conn = pymysql.connect(
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB
        )
        
        print("✅ PyMySQL connection successful!")
        
        # Test query
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        print(f"✅ MySQL Version: {version[0]}")
        
        cursor.close()
        conn.close()
        print("✅ PyMySQL connection closed successfully")
        return True
        
    except ImportError as e:
        print(f"❌ PyMySQL not installed: {e}")
        print("💡 Install with: pip install PyMySQL")
    except Exception as e:
        print(f"❌ PyMySQL connection failed: {e}")
        print(f"Error type: {type(e).__name__}")
    
    return False

def test_app_database_functions():
    """Test database functions from your app"""
    print("\n🚀 TESTING APP DATABASE FUNCTIONS:")
    print("=" * 50)
    
    try:
        # Import your app's database function
        from app import get_db
        print("✅ get_db function imported successfully")
        
        # Test connection
        conn = get_db()
        if conn:
            print("✅ get_db() returned connection successfully")
            
            # Test query
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = DATABASE()")
            result = cursor.fetchone()
            print(f"✅ Found {result[0]} tables in current database")
            
            cursor.close()
            conn.close()
            print("✅ App database connection closed successfully")
            return True
        else:
            print("❌ get_db() returned None")
            return False
            
    except Exception as e:
        print(f"❌ App database function test failed: {e}")
        print(f"Error type: {type(e).__name__}")
        return False

def check_environment():
    """Check environment variables"""
    print("\n🌍 ENVIRONMENT CHECK:")
    print("=" * 50)
    
    # Check if .env file exists
    if os.path.exists('.env'):
        print("✅ .env file found")
    else:
        print("⚠️ .env file not found")
    
    # Check important environment variables
    env_vars = [
        'MYSQL_HOST',
        'MYSQL_USER', 
        'MYSQL_PASSWORD',
        'MYSQL_DB',
        'MYSQL_PORT',
        'MYSQL_URL'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            if 'PASSWORD' in var:
                print(f"✅ {var}: {'*' * 10}")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: Not set")

if __name__ == "__main__":
    print("🚀 LOCAL DATABASE CONNECTION TESTER")
    print("=" * 60)
    
    # Check environment
    check_environment()
    
    # Test database connection
    db_success = test_database_connection()
    
    # Test app functions
    app_success = test_app_database_functions()
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS:")
    print(f"Database Connection: {'✅ SUCCESS' if db_success else '❌ FAILED'}")
    print(f"App Functions: {'✅ SUCCESS' if app_success else '❌ FAILED'}")
    
    if db_success and app_success:
        print("\n🎉 ALL TESTS PASSED - Database is working perfectly!")
    elif db_success:
        print("\n⚠️ Database works but app functions have issues")
    else:
        print("\n💥 Database connection failed - Check your configuration")
        print("\n🔧 TROUBLESHOOTING:")
        print("1. Make sure MySQL server is running")
        print("2. Check database credentials in .env file")
        print("3. Verify database exists")
        print("4. Check firewall/network settings")
    
    print(f"\n🕐 Test completed at: {datetime.now()}")
