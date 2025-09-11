# Railway KHQR Setup Guide

## Issue
The KHQR payment system is failing on Railway with the error:
```
ERROR:app:❌ KHQR payment creation failed: KHQR library not available or not initialized
```

## Solutions

### Option 1: Set Environment Variable (Recommended)
1. Go to your Railway project dashboard
2. Navigate to the "Variables" tab
3. Add a new environment variable:
   - **Key**: `KHQR_JWT_TOKEN`
   - **Value**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjp7ImlkIjoiOTU5YjgzZWI2NjRhNDBlMyJ9LCJpYXQiOjE3NTIyNDI0OTQsImV4cCI6MTc2MDAxODQ5NH0.KEw_Z4nHQt-g4tUnE-cl6AJ9HSgSCKKDI_k5JI6tHS8`
4. Redeploy your application

### Option 2: Update JWT Token
If the current JWT token has expired:
1. Get a new JWT token from your KHQR provider
2. Update the environment variable `KHQR_JWT_TOKEN` with the new token
3. Redeploy your application

### Option 3: Disable KHQR (Fallback)
If you want to disable KHQR payments temporarily:
1. The app will automatically fall back to Cash and Pay on Delivery
2. Users will see a message: "KHQR payment temporarily unavailable. Please use Cash or Pay on Delivery instead."

## What's Fixed
- ✅ Better error handling for KHQR initialization failures
- ✅ Graceful fallback to alternative payment methods
- ✅ Environment variable support for JWT token
- ✅ Improved logging for debugging

## Testing
After deployment, test the checkout process:
1. Try KHQR payment - should show fallback message if not working
2. Try Cash payment - should work normally
3. Try Pay on Delivery - should work normally

The app will continue to function normally even if KHQR is not available.
