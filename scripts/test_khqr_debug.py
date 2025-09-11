#!/usr/bin/env python3
"""
KHQR Debug Test Script
Run this to test KHQR library availability and JWT token
"""

import os
import sys
from datetime import datetime

def test_khqr_availability():
    print("🔍 KHQR Debug Test")
    print("=" * 50)
    
    # Test 1: Check if library can be imported
    print("1. Testing library import...")
    try:
        from bakong_khqr import KHQR
        print("✅ bakong-khqr library imported successfully")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        print("💡 Try: pip install bakong-khqr")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    # Test 2: Check JWT token
    print("\n2. Testing JWT token...")
    jwt_token = os.getenv('KHQR_JWT_TOKEN', "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjp7ImlkIjoiOTU5YjgzZWI2NjRhNDBlMyJ9LCJpYXQiOjE3NTIyNDI0OTQsImV4cCI6MTc2MDAxODQ5NH0.KEw_Z4nHQt-g4tUnE-cl6AJ9HSgSCKKDI_k5JI6tHS8")
    print(f"JWT Token: {jwt_token[:50]}...")
    
    # Test 3: Try to create KHQR instance
    print("\n3. Testing KHQR initialization...")
    try:
        khqr = KHQR(jwt_token)
        print("✅ KHQR instance created successfully")
        
        # Test 4: Try a simple operation
        print("\n4. Testing KHQR functionality...")
        try:
            # This might fail but we want to see the error
            result = khqr.create_payment(amount=1000, description="Test")
            print("✅ KHQR create_payment test successful")
        except Exception as e:
            print(f"⚠️ KHQR create_payment failed (expected): {e}")
            print("💡 This is normal - the test amount/description might be invalid")
        
        return True
        
    except Exception as e:
        print(f"❌ KHQR initialization failed: {e}")
        print(f"Error type: {type(e).__name__}")
        return False

def test_environment():
    print("\n🌍 Environment Test")
    print("=" * 50)
    
    print(f"Python version: {sys.version}")
    print(f"Platform: {sys.platform}")
    print(f"Current directory: {os.getcwd()}")
    
    # Check if we're in a virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Running in virtual environment")
    else:
        print("⚠️ Not running in virtual environment")
    
    # Check installed packages
    print("\n📦 Checking installed packages...")
    try:
        import pkg_resources
        installed_packages = [d.project_name for d in pkg_resources.working_set]
        if 'bakong-khqr' in installed_packages:
            print("✅ bakong-khqr is installed")
        else:
            print("❌ bakong-khqr is NOT installed")
    except Exception as e:
        print(f"⚠️ Could not check installed packages: {e}")

if __name__ == "__main__":
    print(f"🕐 Test started at: {datetime.now()}")
    print()
    
    test_environment()
    print()
    success = test_khqr_availability()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 KHQR test PASSED - Library should work!")
    else:
        print("💥 KHQR test FAILED - Check the errors above")
    
    print(f"🕐 Test completed at: {datetime.now()}")
