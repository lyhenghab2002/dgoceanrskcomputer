#!/usr/bin/env python3
"""
Deployment script for Computer Shop E-commerce System
This script helps prepare the application for deployment
"""

import os
import sys
import subprocess
from pathlib import Path

def check_requirements():
    """Check if all required files exist"""
    required_files = [
        'app.py',
        'requirements.txt',
        'Procfile',
        'config.py',
        'models.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing required files: {', '.join(missing_files)}")
        return False
    
    print("✅ All required files present")
    return True

def check_environment():
    """Check environment configuration"""
    env_file = '.env'
    if not os.path.exists(env_file):
        print("⚠️  .env file not found. Please create one from env.example")
        return False
    
    print("✅ Environment file found")
    return True

def install_dependencies():
    """Install Python dependencies"""
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                      check=True, capture_output=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def create_directories():
    """Create necessary directories"""
    directories = [
        'static/uploads',
        'static/uploads/products',
        'static/uploads/payment_screenshots',
        'logs'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✅ Directories created")

def main():
    """Main deployment preparation"""
    print("🚀 Preparing Computer Shop E-commerce for deployment...")
    print("=" * 50)
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Check environment
    check_environment()
    
    # Create directories
    create_directories()
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    print("=" * 50)
    print("✅ Deployment preparation complete!")
    print("\nNext steps:")
    print("1. Configure your .env file with production settings")
    print("2. Set up your database")
    print("3. Deploy to your chosen platform")
    print("4. Run database migrations if needed")

if __name__ == "__main__":
    main()
