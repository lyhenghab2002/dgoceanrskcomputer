# Bakong API Integration Setup Guide

This guide explains how to set up the official Bakong API integration for your computer shop.

## 🚀 What's New

We've implemented a **complete Bakong API integration** that replaces the third-party library with direct API calls to Bakong's official endpoints.

### ✅ Features Implemented:

1. **Official Bakong API Client** (`utils/bakong_api_client.py`)
   - Direct HTTP calls to Bakong API endpoints
   - Proper HMAC-SHA256 authentication
   - Support for sandbox and production environments

2. **Enhanced Payment Handler** (`utils/bakong_payment_handler.py`)
   - QR code generation using Bakong API
   - Real-time payment verification
   - Payment cancellation support
   - Transaction history retrieval

3. **Webhook Support** (`utils/bakong_webhook.py`)
   - Real-time payment notifications
   - Signature validation for security
   - Automatic order status updates

4. **Backward Compatibility**
   - Falls back to legacy library if Bakong API fails
   - Gradual migration support

## 🔧 Setup Instructions

### 1. Get Bakong API Credentials

To use the official Bakong API, you need to register as a merchant:

1. **Visit Bakong Website**: Go to the official Bakong website
2. **Register as Merchant**: Apply for merchant account
3. **Get Credentials**: You'll receive:
   - API Key
   - API Secret
   - Merchant ID
   - Merchant Account Number

### 2. Set Environment Variables

Create a `.env` file in your project root with these variables:

```bash
# Bakong API Credentials
BAKONG_API_KEY=your_actual_api_key
BAKONG_API_SECRET=your_actual_api_secret
BAKONG_MERCHANT_ID=your_actual_merchant_id
BAKONG_MERCHANT_ACCOUNT=your_actual_account_number

# Environment (sandbox or production)
BAKONG_ENVIRONMENT=sandbox

# Base URL for callbacks
BASE_URL=http://localhost:5000

# Legacy fallback (optional)
KHQR_JWT_TOKEN=your_legacy_token
```

### 3. Install Required Dependencies

```bash
pip install requests pillow
```

### 4. Configure Webhook URL

In your Bakong merchant dashboard, set the webhook URL to:
```
https://yourdomain.com/api/bakong/callback
```

## 📋 API Endpoints

### Payment Processing

- **Create Payment**: `POST /api/khqr/create-payment`
- **Check Status**: `GET /api/khqr/check-payment/{payment_id}`
- **Verify Payment**: `POST /api/khqr/verify-payment`
- **Cancel Payment**: `POST /api/khqr/cancel-payment`

### Webhooks

- **Payment Callback**: `POST /api/bakong/callback`

## 🔒 Security Features

1. **HMAC-SHA256 Authentication**: All API calls are signed
2. **Webhook Signature Validation**: Prevents unauthorized webhooks
3. **Environment Separation**: Sandbox vs Production
4. **Error Handling**: Comprehensive error management

## 🧪 Testing

### Sandbox Environment

1. Set `BAKONG_ENVIRONMENT=sandbox`
2. Use sandbox API credentials
3. Test with small amounts
4. Verify webhook notifications

### Production Environment

1. Set `BAKONG_ENVIRONMENT=production`
2. Use production API credentials
3. Test thoroughly before going live
4. Monitor webhook logs

## 📊 Monitoring

The system logs all API interactions:

- ✅ Successful API calls
- ⚠️ API failures with fallback
- ❌ Authentication errors
- 🔄 Webhook processing

## 🔄 Migration from Legacy

The new system is **backward compatible**:

1. **Primary**: Uses official Bakong API
2. **Fallback**: Uses legacy `bakong_khqr` library if API fails
3. **Gradual**: You can migrate gradually

## 🆘 Troubleshooting

### Common Issues

1. **API Key Invalid**: Check your credentials
2. **Webhook Not Working**: Verify callback URL
3. **Payment Not Verified**: Check webhook processing
4. **Fallback to Legacy**: Check API connectivity

### Debug Mode

Set environment variable for detailed logging:
```bash
BAKONG_DEBUG=true
```

## 📞 Support

- **Bakong Support**: Contact Bakong for API issues
- **Documentation**: Refer to official Bakong API docs
- **Logs**: Check application logs for errors

## 🎯 Next Steps

1. **Get Credentials**: Register with Bakong
2. **Set Environment**: Configure your `.env` file
3. **Test Sandbox**: Verify everything works
4. **Go Live**: Switch to production
5. **Monitor**: Watch for any issues

---

**Note**: This implementation follows the official Bakong API documentation and provides a robust, secure payment processing system for your computer shop.
