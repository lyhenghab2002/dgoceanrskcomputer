#!/usr/bin/env python3
"""
Railway KHQR Test - Run this on Railway to diagnose the issue
"""

import os
import sys
import traceback
from datetime import datetime

def railway_khqr_diagnostic():
    print("🚂 RAILWAY KHQR DIAGNOSTIC")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print(f"Python: {sys.version}")
    print(f"Platform: {sys.platform}")
    print()
    
    # Check environment variables
    print("🔧 Environment Variables:")
    jwt_token = os.getenv('KHQR_JWT_TOKEN')
    if jwt_token:
        print(f"✅ KHQR_JWT_TOKEN: {jwt_token[:50]}...")
    else:
        print("❌ KHQR_JWT_TOKEN: NOT SET")
        print("💡 Set this in Railway Variables tab")
    print()
    
    # Test import
    print("📦 Library Import Test:")
    try:
        from bakong_khqr import KHQR
        print("✅ bakong_khqr imported successfully")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        print("💡 Library not installed on Railway")
        return False
    except Exception as e:
        print(f"❌ Unexpected import error: {e}")
        print(f"Error type: {type(e).__name__}")
        traceback.print_exc()
        return False
    
    # Test JWT token
    print("\n🔑 JWT Token Test:")
    if not jwt_token:
        print("❌ No JWT token available")
        return False
    
    try:
        # Decode JWT to check if it's valid
        import base64
        import json
        
        # Split JWT token
        parts = jwt_token.split('.')
        if len(parts) != 3:
            print("❌ Invalid JWT format")
            return False
        
        # Decode payload
        payload = parts[1]
        # Add padding if needed
        payload += '=' * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        payload_data = json.loads(decoded)
        
        print(f"✅ JWT payload decoded successfully")
        print(f"   User ID: {payload_data.get('data', {}).get('id', 'N/A')}")
        print(f"   Issued at: {payload_data.get('iat', 'N/A')}")
        print(f"   Expires at: {payload_data.get('exp', 'N/A')}")
        
        # Check expiration
        import time
        current_time = int(time.time())
        exp_time = payload_data.get('exp', 0)
        if current_time < exp_time:
            print(f"✅ JWT token is valid (expires in {(exp_time - current_time) // 86400} days)")
        else:
            print(f"❌ JWT token is EXPIRED")
            return False
            
    except Exception as e:
        print(f"❌ JWT token validation failed: {e}")
        traceback.print_exc()
        return False
    
    # Test KHQR initialization
    print("\n🚀 KHQR Initialization Test:")
    try:
        khqr = KHQR(jwt_token)
        print("✅ KHQR instance created successfully")
        
        # Test available methods
        methods = [method for method in dir(khqr) if not method.startswith('_')]
        print(f"✅ Available methods: {methods}")
        
        return True
        
    except Exception as e:
        print(f"❌ KHQR initialization failed: {e}")
        print(f"Error type: {type(e).__name__}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = railway_khqr_diagnostic()
    print("\n" + "=" * 60)
    if success:
        print("🎉 DIAGNOSTIC PASSED - KHQR should work on Railway!")
    else:
        print("💥 DIAGNOSTIC FAILED - Check the errors above")
        print("\n🔧 SOLUTIONS:")
        print("1. Set KHQR_JWT_TOKEN environment variable in Railway")
        print("2. Check if bakong-khqr is in requirements.txt")
        print("3. Redeploy the application")
        print("4. Check Railway build logs for installation errors")
