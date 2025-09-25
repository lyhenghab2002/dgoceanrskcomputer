#!/usr/bin/env python3
"""
Installation script for screenshot fraud detection system
"""

import subprocess
import sys
import os

def install_requirements():
    """Install required Python packages"""
    print("📦 Installing required packages...")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ All packages installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing packages: {e}")
        return False

def create_database_table():
    """Create the order_screenshots table"""
    print("🗄️ Creating database table...")
    
    try:
        from models import get_db
        
        conn = get_db()
        cur = conn.cursor()
        
        # Read and execute the SQL script
        with open('scripts/create_screenshot_tracking_table.sql', 'r') as f:
            sql_script = f.read()
        
        cur.execute(sql_script)
        conn.commit()
        cur.close()
        conn.close()
        
        print("✅ Database table created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error creating database table: {e}")
        return False

def create_directories():
    """Create necessary directories"""
    print("📁 Creating directories...")
    
    directories = [
        'uploads/screenshots',
        'uploads/payment_screenshots',
        'static/uploads/screenshots',
        'static/uploads/payment_screenshots'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"   ✅ Created: {directory}")
    
    print("✅ All directories created!")

def main():
    """Main installation function"""
    print("🚀 Installing Screenshot Fraud Detection System")
    print("=" * 50)
    
    # Step 1: Install packages
    if not install_requirements():
        print("❌ Installation failed at package installation step")
        return False
    
    # Step 2: Create directories
    create_directories()
    
    # Step 3: Create database table
    if not create_database_table():
        print("❌ Installation failed at database table creation step")
        return False
    
    print("\n🎉 Installation completed successfully!")
    print("\n📋 Next steps:")
    print("1. Test the system with: python test_fraud_detection.py")
    print("2. Upload a payment screenshot to test fraud detection")
    print("3. Check the logs for fraud detection results")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
