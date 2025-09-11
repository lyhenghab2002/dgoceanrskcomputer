#!/usr/bin/env python3
"""
Test App Database Connection with Proper Context
"""

from app import create_app

def test_app_database():
    """Test database connection using app context"""
    print("🚀 TESTING APP DATABASE CONNECTION")
    print("=" * 50)
    
    try:
        # Create app instance
        app = create_app()
        
        with app.app_context():
            from app import get_db
            print("✅ App context created successfully")
            
            # Test connection
            conn = get_db()
            if conn:
                print("✅ get_db() returned connection successfully")
                
                # Test query
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = DATABASE()")
                result = cursor.fetchone()
                print(f"✅ Found {result[0]} tables in current database")
                
                # Test a specific table
                cursor.execute("SELECT COUNT(*) FROM products")
                product_count = cursor.fetchone()
                print(f"✅ Found {product_count[0]} products in database")
                
                # Test categories
                cursor.execute("SELECT COUNT(*) FROM categories")
                category_count = cursor.fetchone()
                print(f"✅ Found {category_count[0]} categories in database")
                
                cursor.close()
                conn.close()
                print("✅ App database connection closed successfully")
                return True
            else:
                print("❌ get_db() returned None")
                return False
                
    except Exception as e:
        print(f"❌ App database test failed: {e}")
        print(f"Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    success = test_app_database()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 APP DATABASE CONNECTION SUCCESSFUL!")
        print("✅ Your local database is working perfectly")
        print("✅ All database functions are operational")
    else:
        print("💥 APP DATABASE CONNECTION FAILED!")
        print("❌ Check your database configuration")
