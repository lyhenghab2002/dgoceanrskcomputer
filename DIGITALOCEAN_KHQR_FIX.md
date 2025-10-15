# DigitalOcean Ubuntu Server KHQR Fix Guide

## Problem
KHQR payment system works locally but fails on DigitalOcean Ubuntu VPS/droplet.

## Root Causes Identified
1. Missing environment variables on Ubuntu server
2. Python package installation issues on server
3. Network connectivity to Bakong API
4. SSL/HTTPS configuration issues
5. Virtual environment not activated
6. Missing system dependencies

## Step-by-Step Fix

### 1. SSH into Your DigitalOcean Ubuntu Server

```bash
ssh root@your-server-ip
# or
ssh username@your-server-ip
```

### 2. Set Environment Variables on Ubuntu Server

Create or edit your environment file:

```bash
# Navigate to your app directory
cd /path/to/your/app

# Create .env file
nano .env
```

Add these variables to your `.env` file:

```env
# KHQR Configuration
KHQR_JWT_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjp7ImlkIjoiOTU5YjgzZWI2NjRhNDBlMyJ9LCJpYXQiOjE3NjA0NjAxMDEsImV4cCI6MTc2ODIzNjEwMX0.tL1hT8aLC-Oca_KW8ZCCl6NK4xI62CsaC1_dLawi668

# Bakong API Configuration (if using official API)
BAKONG_API_KEY=your_api_key_here
BAKONG_API_SECRET=your_api_secret_here
BAKONG_MERCHANT_ID=your_merchant_id_here
BAKONG_MERCHANT_ACCOUNT=your_merchant_account_here
BAKONG_ENVIRONMENT=sandbox

# Application Configuration
BASE_URL=https://your-app-domain.ondigitalocean.app
FLASK_ENV=production
FLASK_DEBUG=False
```

### 3. Install System Dependencies

```bash
# Update package list
sudo apt update

# Install Python and pip
sudo apt install -y python3 python3-pip python3-venv

# Install system dependencies for image processing
sudo apt install -y libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1

# Install MySQL client libraries
sudo apt install -y default-libmysqlclient-dev pkg-config

# Install other dependencies
sudo apt install -y build-essential libssl-dev libffi-dev python3-dev
```

### 4. Set Up Virtual Environment

```bash
# Navigate to your app directory
cd /path/to/your/app

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### 5. Install Python Packages

```bash
# Make sure you're in the virtual environment
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Specifically install bakong-khqr if it fails
pip install bakong-khqr

# Install additional packages that might be missing
pip install qrcode[pil] Pillow requests
```

### 6. Create Server-Side Debug Script

Create a script to test KHQR on the server:

```python
# scripts/server_khqr_test.py
#!/usr/bin/env python3
"""
Server-side KHQR test for DigitalOcean deployment
"""

import os
import sys
import traceback
from datetime import datetime

def test_server_khqr():
    print("🔍 DigitalOcean Server KHQR Test")
    print("=" * 50)
    print(f"🕐 Test started at: {datetime.now()}")
    print(f"🌍 Platform: {sys.platform}")
    print(f"🐍 Python version: {sys.version}")
    print(f"📁 Current directory: {os.getcwd()}")
    
    # Test 1: Environment Variables
    print("\n1. Testing Environment Variables...")
    jwt_token = os.getenv('KHQR_JWT_TOKEN')
    if jwt_token:
        print(f"✅ KHQR_JWT_TOKEN: {jwt_token[:50]}...")
    else:
        print("❌ KHQR_JWT_TOKEN: NOT SET")
        return False
    
    # Test 2: Package Installation
    print("\n2. Testing Package Installation...")
    try:
        import pkg_resources
        installed_packages = [d.project_name for d in pkg_resources.working_set]
        if 'bakong-khqr' in installed_packages:
            print("✅ bakong-khqr is installed")
        else:
            print("❌ bakong-khqr is NOT installed")
            return False
    except Exception as e:
        print(f"❌ Error checking packages: {e}")
        return False
    
    # Test 3: Library Import
    print("\n3. Testing Library Import...")
    try:
        from bakong_khqr import KHQR
        print("✅ bakong-khqr library imported successfully")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    # Test 4: KHQR Initialization
    print("\n4. Testing KHQR Initialization...")
    try:
        khqr = KHQR(jwt_token)
        print("✅ KHQR instance created successfully")
    except Exception as e:
        print(f"❌ KHQR initialization failed: {e}")
        print(f"Error type: {type(e).__name__}")
        traceback.print_exc()
        return False
    
    # Test 5: Network Connectivity
    print("\n5. Testing Network Connectivity...")
    try:
        import requests
        # Test connection to Bakong API
        response = requests.get('https://api-sandbox.bakong.nbc.gov.kh', timeout=10)
        print(f"✅ Network connectivity OK - Status: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Network connectivity issue: {e}")
        print("💡 This might be normal if Bakong API is not accessible")
    
    print("\n" + "=" * 50)
    print("🎉 Server KHQR test completed!")
    return True

if __name__ == "__main__":
    success = test_server_khqr()
    if success:
        print("✅ KHQR should work on this server")
    else:
        print("❌ KHQR has issues on this server")
```

### 4. Update Your App Configuration

Add error handling and fallback mechanisms in your KHQR implementation:

```python
# In utils/khqr_payment.py - Add this at the top
import logging
import os

# Set up logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_server_environment():
    """Check if we're running on a server and log environment details"""
    logger.info(f"🌍 Running on platform: {os.name}")
    logger.info(f"🔧 KHQR_JWT_TOKEN set: {bool(os.getenv('KHQR_JWT_TOKEN'))}")
    logger.info(f"🔧 BAKONG_API_KEY set: {bool(os.getenv('BAKONG_API_KEY'))}")
    
    # Check if we're in production
    flask_env = os.getenv('FLASK_ENV', 'development')
    logger.info(f"🔧 Flask environment: {flask_env}")
    
    return flask_env == 'production'
```

### 5. Deploy and Test

1. **Test KHQR on Server:**
   ```bash
   # SSH into your server
   ssh root@your-server-ip
   
   # Navigate to your app directory
   cd /path/to/your/app
   
   # Activate virtual environment
   source venv/bin/activate
   
   # Run the debug script
   python scripts/server_khqr_test.py
   
   # Or test directly
   python -c "from bakong_khqr import KHQR; print('KHQR import successful')"
   ```

2. **Start Your Application:**
   ```bash
   # Make sure virtual environment is activated
   source venv/bin/activate
   
   # Start with Gunicorn
   gunicorn --bind 0.0.0.0:5000 app:app
   
   # Or start with Flask (for testing)
   python app.py
   ```

### 6. Common Issues and Solutions

#### Issue: "ModuleNotFoundError: No module named 'bakong_khqr'"
**Solution:**
- Ensure `bakong-khqr` is in requirements.txt
- Check build logs for installation errors
- Try adding explicit version: `bakong-khqr==1.0.0`

#### Issue: "KHQR_JWT_TOKEN not set"
**Solution:**
- Double-check environment variables in DigitalOcean dashboard
- Ensure variable names match exactly (case-sensitive)
- Redeploy after adding variables

#### Issue: "Network timeout" or "Connection refused"
**Solution:**
- Check if your server can reach external APIs
- Verify firewall settings
- Test with curl: `curl -I https://api-sandbox.bakong.nbc.gov.kh`

#### Issue: "SSL certificate verification failed"
**Solution:**
- Add SSL verification bypass for development:
  ```python
  import ssl
  ssl._create_default_https_context = ssl._create_unverified_context
  ```

### 7. Production Checklist

- [ ] Environment variables set in DigitalOcean
- [ ] requirements.txt updated
- [ ] Debug script created and tested
- [ ] Error handling added to KHQR code
- [ ] SSL/HTTPS properly configured
- [ ] Network connectivity verified
- [ ] Logs monitored for errors

### 8. Monitoring and Debugging

1. **Check DigitalOcean App Logs:**
   - Go to your app → Runtime Logs
   - Look for KHQR-related errors

2. **Add Logging to Your App:**
   ```python
   import logging
   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger(__name__)
   
   # In your KHQR functions
   logger.info("Creating KHQR payment...")
   ```

3. **Test Endpoints:**
   - Use your app's API endpoints to test KHQR
   - Monitor response times and errors

## Quick Fix Commands

If you need to quickly test on your server:

```bash
# SSH into your DigitalOcean droplet (if using VPS)
ssh root@your-server-ip

# Or use DigitalOcean App Platform console
# Navigate to your app → Console

# Test Python environment
python3 --version
pip3 list | grep bakong

# Test KHQR
python3 -c "from bakong_khqr import KHQR; print('KHQR import successful')"

# Check environment variables
echo $KHQR_JWT_TOKEN
```

## Expected Results

After implementing these fixes:
- ✅ KHQR library imports successfully
- ✅ Environment variables are properly set
- ✅ Network connectivity to Bakong API works
- ✅ QR codes generate without errors
- ✅ Payment verification functions correctly

---

**Need Help?** If issues persist, check the DigitalOcean App Platform logs and share the specific error messages for further assistance.
