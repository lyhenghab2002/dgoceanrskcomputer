"""
Bakong Webhook Handler
Handles real-time payment notifications from Bakong API
"""

import json
import hmac
import hashlib
from datetime import datetime
from typing import Dict, Any
from flask import request, jsonify
import os

from utils.bakong_payment_handler import get_bakong_handler

def handle_bakong_webhook():
    """
    Handle Bakong webhook notifications
    This function should be called from a Flask route
    """
    try:
        # Get webhook data
        payload = request.get_json()
        signature = request.headers.get('X-Bakong-Signature', '')
        timestamp = request.headers.get('X-Bakong-Timestamp', '')
        
        if not all([payload, signature, timestamp]):
            return jsonify({
                'success': False,
                'error': 'Missing required webhook headers'
            }), 400
        
        # Process webhook using Bakong handler
        handler = get_bakong_handler()
        result = handler.handle_webhook(payload, signature, timestamp)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Webhook processing failed: {str(e)}'
        }), 500

def validate_webhook_signature(payload: str, signature: str, timestamp: str) -> bool:
    """
    Validate Bakong webhook signature
    
    Args:
        payload: Raw webhook payload
        signature: Webhook signature from headers
        timestamp: Webhook timestamp from headers
        
    Returns:
        True if signature is valid
    """
    try:
        api_secret = os.getenv('BAKONG_API_SECRET', '')
        if not api_secret:
            return False
        
        # Create signature string
        signature_string = f"POST/api/bakong/callback{payload}{timestamp}"
        
        # Generate expected signature
        expected_signature = hmac.new(
            api_secret.encode('utf-8'),
            signature_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(signature, expected_signature)
        
    except Exception as e:
        print(f"Error validating webhook signature: {e}")
        return False
