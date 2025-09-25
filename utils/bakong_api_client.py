"""
Bakong Open API Client
Direct integration with Bakong Open API for payment processing and verification
Based on official Bakong API documentation
"""

import requests
import json
import hashlib
import hmac
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import os
from urllib.parse import urljoin

class BakongAPIClient:
    """
    Official Bakong Open API client for payment processing
    Implements direct API integration with proper authentication
    """
    
    def __init__(self, environment: str = 'sandbox'):
        """
        Initialize Bakong API client
        
        Args:
            environment: 'sandbox' or 'production'
        """
        self.environment = environment
        self.base_url = self._get_base_url()
        
        # Try to get official Bakong API credentials first
        self.api_key = os.getenv('BAKONG_API_KEY', '')
        self.api_secret = os.getenv('BAKONG_API_SECRET', '')
        self.merchant_id = os.getenv('BAKONG_MERCHANT_ID', '')
        self.merchant_account = os.getenv('BAKONG_MERCHANT_ACCOUNT', '')
        
        # If official credentials not available, use legacy JWT token approach
        if not all([self.api_key, self.api_secret, self.merchant_id, self.merchant_account]):
            print("⚠️ Official Bakong API credentials not found. Using legacy JWT token approach.")
            self.jwt_token = os.getenv('KHQR_JWT_TOKEN', "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjp7ImlkIjoiOTU5YjgzZWI2NjRhNDBlMyJ9LCJpYXQiOjE3NTIyNDI0OTQsImV4cCI6MTc2MDAxODQ5NH0.KEw_Z4nHQt-g4tUnE-cl6AJ9HSgSCKKDI_k5JI6tHS8")
            if not self.jwt_token:
                raise ValueError("Missing Bakong credentials. Please set either official API credentials or KHQR_JWT_TOKEN.")
            self.use_legacy = True
        else:
            self.use_legacy = False
            print("✅ Using official Bakong API credentials")
    
    def _get_base_url(self) -> str:
        """Get the appropriate base URL based on environment"""
        if self.environment == 'production':
            return 'https://api.bakong.nbc.gov.kh'
        else:
            return 'https://api-sandbox.bakong.nbc.gov.kh'
    
    def _generate_signature(self, method: str, endpoint: str, body: str = '', timestamp: str = '') -> str:
        """
        Generate HMAC signature for API authentication
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            body: Request body (for POST requests)
            timestamp: Request timestamp
            
        Returns:
            HMAC signature string
        """
        # Create signature string
        signature_string = f"{method.upper()}{endpoint}{body}{timestamp}"
        
        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            signature_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _get_headers(self, method: str, endpoint: str, body: str = '') -> Dict[str, str]:
        """
        Generate request headers with proper authentication
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            body: Request body
            
        Returns:
            Headers dictionary
        """
        timestamp = str(int(time.time() * 1000))  # Milliseconds timestamp
        signature = self._generate_signature(method, endpoint, body, timestamp)
        
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
            'X-Bakong-Signature': signature,
            'X-Bakong-Timestamp': timestamp,
            'X-Bakong-Merchant-ID': self.merchant_id,
            'User-Agent': 'ComputerShop/1.0'
        }
    
    def create_payment_request(self, amount: float, currency: str = 'USD', 
                             reference_id: str = None, description: str = '') -> Dict[str, Any]:
        """
        Create a payment request using Bakong API or legacy approach
        
        Args:
            amount: Payment amount
            currency: Currency code (USD, KHR)
            reference_id: Unique reference ID
            description: Payment description
            
        Returns:
            Payment request response
        """
        if not reference_id:
            reference_id = f"PAY_{uuid.uuid4().hex[:12].upper()}"
        
        # If using legacy approach, delegate to legacy system
        if self.use_legacy:
            return self._create_legacy_payment_qr(amount, currency, reference_id, description)
        
        # Use official Bakong API
        endpoint = '/api/v1/payments'
        payload = {
            'merchant_id': self.merchant_id,
            'merchant_account': self.merchant_account,
            'amount': amount,
            'currency': currency,
            'reference_id': reference_id,
            'description': description,
            'callback_url': f"{os.getenv('BASE_URL', 'http://localhost:5000')}/api/bakong/callback",
            'redirect_url': f"{os.getenv('BASE_URL', 'http://localhost:5000')}/payment/success",
            'expires_at': (datetime.now() + timedelta(minutes=15)).isoformat()
        }
        
        body = json.dumps(payload)
        headers = self._get_headers('POST', endpoint, body)
        
        try:
            response = requests.post(
                urljoin(self.base_url, endpoint),
                headers=headers,
                data=body,
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'API request failed: {str(e)}'
            }
    
    def _create_legacy_payment_qr(self, amount: float, currency: str, reference_id: str, description: str) -> Dict[str, Any]:
        """
        Create payment QR using legacy bakong_khqr library approach
        
        Args:
            amount: Payment amount
            currency: Currency code
            reference_id: Reference ID
            description: Payment description
            
        Returns:
            Payment response
        """
        try:
            # Import legacy KHQR library
            from bakong_khqr import KHQR
            
            # Initialize with JWT token
            khqr = KHQR(self.jwt_token)
            
            # Generate unique bill number
            bill_number = f"BILL_{uuid.uuid4().hex[:8].upper()}"
            
            # Create QR code using legacy method
            qr_data = khqr.create_qr(
                bank_account="kong_dalin1@aclb",
                merchant_name="DALIN KONG",
                merchant_city="Phnom Penh",
                amount=amount,
                currency=currency,
                store_label="shop",
                phone_number="015433830",
                bill_number=bill_number,
                terminal_label="POS-02"
            )
            
            # Generate MD5 hash for verification
            md5_hash = khqr.generate_md5(qr_data)
            
            # Generate QR code image
            qr_code_image = self._generate_qr_code_image(qr_data)
            
            # Create payment ID
            payment_id = str(uuid.uuid4())
            
            return {
                'success': True,
                'payment_id': payment_id,
                'qr_data': qr_data,
                'qr_code': qr_code_image,
                'md5_hash': md5_hash,
                'amount': amount,
                'currency': currency,
                'reference_id': reference_id,
                'bill_number': bill_number,
                'expires_at': (datetime.now() + timedelta(minutes=15)).isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Legacy payment creation failed: {str(e)}'
            }
    
    def _generate_qr_code_image(self, qr_data: str) -> str:
        """
        Generate QR code image from QR data
        
        Args:
            qr_data: QR code data string
            
        Returns:
            Base64 encoded QR code image
        """
        try:
            from PIL import Image, ImageDraw
            import qrcode
            import io
            import base64
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            # Create image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            return img_str
            
        except Exception as e:
            print(f"Error generating QR code image: {e}")
            return None
    
    def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """
        Get payment status from Bakong API
        
        Args:
            payment_id: Payment ID to check
            
        Returns:
            Payment status response
        """
        endpoint = f'/api/v1/payments/{payment_id}'
        headers = self._get_headers('GET', endpoint)
        
        try:
            response = requests.get(
                urljoin(self.base_url, endpoint),
                headers=headers,
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'API request failed: {str(e)}'
            }
    
    def verify_payment(self, payment_id: str, transaction_id: str = None) -> Dict[str, Any]:
        """
        Verify payment completion using Bakong API
        
        Args:
            payment_id: Payment ID
            transaction_id: Optional transaction ID for verification
            
        Returns:
            Payment verification response
        """
        endpoint = f'/api/v1/payments/{payment_id}/verify'
        payload = {
            'merchant_id': self.merchant_id,
            'payment_id': payment_id
        }
        
        if transaction_id:
            payload['transaction_id'] = transaction_id
        
        body = json.dumps(payload)
        headers = self._get_headers('POST', endpoint, body)
        
        try:
            response = requests.post(
                urljoin(self.base_url, endpoint),
                headers=headers,
                data=body,
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'API request failed: {str(e)}'
            }
    
    def create_qr_code(self, amount: float, currency: str = 'USD', 
                      reference_id: str = None, description: str = '') -> Dict[str, Any]:
        """
        Create QR code for payment using Bakong API
        
        Args:
            amount: Payment amount
            currency: Currency code
            reference_id: Unique reference ID
            description: Payment description
            
        Returns:
            QR code response with image data
        """
        if not reference_id:
            reference_id = f"QR_{uuid.uuid4().hex[:12].upper()}"
        
        endpoint = '/api/v1/qr-codes'
        payload = {
            'merchant_id': self.merchant_id,
            'merchant_account': self.merchant_account,
            'amount': amount,
            'currency': currency,
            'reference_id': reference_id,
            'description': description,
            'expires_at': (datetime.now() + timedelta(minutes=15)).isoformat()
        }
        
        body = json.dumps(payload)
        headers = self._get_headers('POST', endpoint, body)
        
        try:
            response = requests.post(
                urljoin(self.base_url, endpoint),
                headers=headers,
                data=body,
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'API request failed: {str(e)}'
            }
    
    def get_transaction_history(self, start_date: str = None, end_date: str = None, 
                              limit: int = 100) -> Dict[str, Any]:
        """
        Get transaction history from Bakong API
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            limit: Maximum number of transactions
            
        Returns:
            Transaction history response
        """
        endpoint = '/api/v1/transactions'
        params = {
            'merchant_id': self.merchant_id,
            'limit': limit
        }
        
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        
        # Build query string
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        full_endpoint = f"{endpoint}?{query_string}"
        
        headers = self._get_headers('GET', full_endpoint)
        
        try:
            response = requests.get(
                urljoin(self.base_url, full_endpoint),
                headers=headers,
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'API request failed: {str(e)}'
            }
    
    def cancel_payment(self, payment_id: str, reason: str = '') -> Dict[str, Any]:
        """
        Cancel a payment using Bakong API
        
        Args:
            payment_id: Payment ID to cancel
            reason: Cancellation reason
            
        Returns:
            Cancellation response
        """
        endpoint = f'/api/v1/payments/{payment_id}/cancel'
        payload = {
            'merchant_id': self.merchant_id,
            'payment_id': payment_id,
            'reason': reason
        }
        
        body = json.dumps(payload)
        headers = self._get_headers('POST', endpoint, body)
        
        try:
            response = requests.post(
                urljoin(self.base_url, endpoint),
                headers=headers,
                data=body,
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'API request failed: {str(e)}'
            }
    
    def validate_webhook_signature(self, payload: str, signature: str, timestamp: str) -> bool:
        """
        Validate webhook signature from Bakong
        
        Args:
            payload: Webhook payload
            signature: Webhook signature
            timestamp: Webhook timestamp
            
        Returns:
            True if signature is valid
        """
        expected_signature = self._generate_signature('POST', '/api/bakong/callback', payload, timestamp)
        return hmac.compare_digest(signature, expected_signature)


# Global instance
bakong_client = None

def get_bakong_client() -> BakongAPIClient:
    """Get or create Bakong API client instance"""
    global bakong_client
    if bakong_client is None:
        environment = os.getenv('BAKONG_ENVIRONMENT', 'sandbox')
        bakong_client = BakongAPIClient(environment)
    return bakong_client
