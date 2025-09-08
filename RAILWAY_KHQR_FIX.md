# 🚂 Railway KHQR Fix Guide

## Current Issue
```
ERROR:app:❌ KHQR payment creation failed: KHQR library not available or not initialized
```

## 🔧 Step-by-Step Fix

### 1. Set Environment Variable
1. Go to your Railway project dashboard
2. Click on your project
3. Go to **Variables** tab
4. Click **+ New Variable**
5. Add:
   - **Key**: `KHQR_JWT_TOKEN`
   - **Value**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjp7ImlkIjoiOTU5YjgzZWI2NjRhNDBlMyJ9LCJpYXQiOjE3NTIyNDI0OTQsImV4cCI6MTc2MDAxODQ5NH0.KEw_Z4nHQt-g4tUnE-cl6AJ9HSgSCKKDI_k5JI6tHS8`
6. Click **Add**

### 2. Verify Requirements
Make sure `bakong-khqr` is in your `requirements.txt`:
```
bakong-khqr
```

### 3. Redeploy
1. Go to **Deployments** tab
2. Click **Deploy** or trigger a new deployment
3. Wait for deployment to complete

### 4. Test the Fix
1. Go to your live site
2. Try to create an order with KHQR payment
3. Check Railway logs for:
   - `✅ KHQR initialized successfully` (success)
   - `❌ KHQR library not available` (still failing)

## 🔍 Debug Steps (if still failing)

### Run Diagnostic Script
Add this to your app temporarily to debug:

```python
# Add this to app.py temporarily
@app.route('/debug/khqr')
def debug_khqr():
    from railway_khqr_test import railway_khqr_diagnostic
    import io
    import sys
    
    # Capture output
    old_stdout = sys.stdout
    sys.stdout = buffer = io.StringIO()
    
    try:
        success = railway_khqr_diagnostic()
        output = buffer.getvalue()
        return f"<pre>{output}</pre>"
    finally:
        sys.stdout = old_stdout
```

Then visit: `https://your-app.railway.app/debug/khqr`

### Check Railway Logs
1. Go to **Deployments** tab
2. Click on latest deployment
3. Check **Build Logs** for:
   - `Installing bakong-khqr...`
   - Any import errors
4. Check **Runtime Logs** for:
   - `🔧 Attempting to initialize KHQR with token: ...`
   - `❌ Import error` or `❌ Failed to initialize`

## 🎯 Expected Results

### Success (Fixed)
```
INFO:app:✅ KHQR initialized successfully
INFO:app:🔧 Attempting to initialize KHQR with token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Still Failing
```
ERROR:app:❌ KHQR payment creation failed: KHQR library not available or not initialized
```

## 🚨 Alternative Solutions

### If Environment Variable Doesn't Work
The JWT token is already hardcoded in your code as a fallback, so this should work even without the environment variable.

### If Library Installation Fails
1. Check Railway build logs for `bakong-khqr` installation errors
2. Try updating `requirements.txt` with specific version:
   ```
   bakong-khqr==1.0.0
   ```

### If Still Failing
The app works perfectly with Cash and Pay on Delivery. KHQR is optional - users can still complete orders without it.

## 📞 Support
If none of these steps work, the issue might be:
1. Railway's Python environment compatibility
2. Network restrictions on Railway
3. Library dependencies not available on Railway

The app is fully functional without KHQR - it's just an additional payment option.
