"""
Bakong Payment Handler
Uses the official Bakong API client for payment processing and verification
"""

import uuid
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import os
import base64
import io

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from utils.bakong_api_client import get_bakong_client

class BakongPaymentHandler:
    """
    Payment handler using official Bakong API
    Provides QR generation, payment verification, and transaction management
    """
    
    def __init__(self):
        """Initialize Bakong payment handler"""
        self.client = get_bakong_client()
        self.active_payments = {}  # Local payment tracking
    
    def create_payment_qr(self, amount: float, currency: str = "USD", 
                         reference_id: Optional[str] = None, order_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Create a payment QR code using Bakong API or legacy approach
        
        Args:
            amount: Payment amount
            currency: Currency (USD or KHR)
            reference_id: Optional reference ID
            order_id: Optional order ID to associate with this payment
            
        Returns:
            Dictionary containing QR data and payment information
        """
        try:
            # Generate reference ID if not provided
            if not reference_id:
                reference_id = f"ORDER_{order_id}_{int(time.time())}" if order_id else f"PAY_{uuid.uuid4().hex[:12].upper()}"
            
            # Create payment request using Bakong API
            description = f"Payment for Order #{order_id}" if order_id else "Computer Shop Payment"
            
            api_response = self.client.create_payment_request(
                amount=amount,
                currency=currency,
                reference_id=reference_id,
                description=description
            )
            
            if not api_response.get('success', True):  # Assume success if no error field
                return {
                    'success': False,
                    'error': api_response.get('error', 'Failed to create payment request')
                }
            
            # Extract payment information
            payment_id = api_response.get('payment_id', str(uuid.uuid4()))
            qr_data = api_response.get('qr_data', '')
            qr_code_url = api_response.get('qr_code_url', '')
            qr_code_image = api_response.get('qr_code', '')  # Base64 encoded image
            
            # Store payment for tracking
            payment_data = {
                'payment_id': payment_id,
                'amount': amount,
                'currency': currency,
                'reference_id': reference_id,
                'order_id': order_id,
                'qr_data': qr_data,
                'qr_code_url': qr_code_url,
                'status': 'pending',
                'created_at': datetime.now(),
                'expires_at': datetime.now() + timedelta(minutes=15),
                'api_response': api_response
            }
            
            self.active_payments[payment_id] = payment_data
            
            return {
                'success': True,
                'payment_id': payment_id,
                'qr_data': qr_data,
                'qr_code': qr_code_image,  # Base64 encoded image
                'qr_code_url': qr_code_url,
                'amount': amount,
                'currency': currency,
                'reference_id': reference_id,
                'expires_at': payment_data['expires_at'].isoformat(),
                'order_id': order_id
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to create payment QR: {str(e)}'
            }
    
    def check_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """
        Check payment status using Bakong API
        
        Args:
            payment_id: Payment ID to check
            
        Returns:
            Payment status information
        """
        try:
            # Check if payment exists locally
            if payment_id not in self.active_payments:
                return {
                    'success': False,
                    'error': 'Payment not found'
                }
            
            payment_data = self.active_payments[payment_id]
            
            # Check if payment has expired
            if datetime.now() > payment_data['expires_at']:
                payment_data['status'] = 'expired'
                return {
                    'success': True,
                    'status': 'expired',
                    'message': 'Payment has expired'
                }
            
            # Check payment status using Bakong API
            api_response = self.client.get_payment_status(payment_id)
            
            if not api_response.get('success', True):
                return {
                    'success': False,
                    'error': api_response.get('error', 'Failed to check payment status')
                }
            
            # Update payment status based on API response
            api_status = api_response.get('status', 'pending')
            
            if api_status == 'completed' or api_status == 'paid':
                payment_data['status'] = 'completed'
                payment_data['completed_at'] = datetime.now()
                
                # Update order if this is for an existing order
                if payment_data.get('order_id'):
                    self._update_order_payment_status(payment_data['order_id'], 'completed')
                
                return {
                    'success': True,
                    'status': 'completed',
                    'payment_id': payment_id,
                    'amount': payment_data['amount'],
                    'currency': payment_data['currency'],
                    'completed_at': payment_data['completed_at'].isoformat(),
                    'order_id': payment_data.get('order_id')
                }
            else:
                return {
                    'success': True,
                    'status': 'pending',
                    'payment_id': payment_id,
                    'message': 'Payment is still pending'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to check payment status: {str(e)}'
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
        try:
            # Use Bakong API to verify payment
            api_response = self.client.verify_payment(payment_id, transaction_id)
            
            if not api_response.get('success', True):
                return {
                    'success': False,
                    'error': api_response.get('error', 'Payment verification failed')
                }
            
            # Update local payment status
            if payment_id in self.active_payments:
                payment_data = self.active_payments[payment_id]
                payment_data['status'] = 'verified'
                payment_data['verified_at'] = datetime.now()
                
                # Update order if this is for an existing order
                if payment_data.get('order_id'):
                    self._update_order_payment_status(payment_data['order_id'], 'verified')
            
            return {
                'success': True,
                'status': 'verified',
                'payment_id': payment_id,
                'verified_at': datetime.now().isoformat(),
                'transaction_id': transaction_id
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Payment verification failed: {str(e)}'
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
        try:
            # Cancel payment using Bakong API
            api_response = self.client.cancel_payment(payment_id, reason)
            
            if not api_response.get('success', True):
                return {
                    'success': False,
                    'error': api_response.get('error', 'Failed to cancel payment')
                }
            
            # Update local payment status
            if payment_id in self.active_payments:
                payment_data = self.active_payments[payment_id]
                payment_data['status'] = 'cancelled'
                payment_data['cancelled_at'] = datetime.now()
                payment_data['cancellation_reason'] = reason
            
            return {
                'success': True,
                'status': 'cancelled',
                'payment_id': payment_id,
                'cancelled_at': datetime.now().isoformat(),
                'reason': reason
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to cancel payment: {str(e)}'
            }
    
    def get_payment_info(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get payment information
        
        Args:
            payment_id: Payment ID
            
        Returns:
            Payment information or None if not found
        """
        return self.active_payments.get(payment_id)
    
    def _generate_qr_code_image(self, qr_data: str) -> str:
        """
        Generate QR code image from QR data
        
        Args:
            qr_data: QR code data string
            
        Returns:
            Base64 encoded QR code image
        """
        try:
            if not PIL_AVAILABLE:
                print("PIL not available, returning None for QR code image")
                return None
                
            # For now, return a placeholder
            # In a real implementation, you would generate the actual QR code
            # using a QR code library like qrcode
            
            # Create a simple placeholder image
            from PIL import Image, ImageDraw, ImageFont
            
            # Create a simple QR code placeholder
            img = Image.new('RGB', (200, 200), color='white')
            draw = ImageDraw.Draw(img)
            
            # Draw a simple pattern
            for i in range(0, 200, 20):
                for j in range(0, 200, 20):
                    if (i + j) % 40 == 0:
                        draw.rectangle([i, j, i+15, j+15], fill='black')
            
            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            return img_str
            
        except Exception as e:
            print(f"Error generating QR code image: {e}")
            return None
    
    def _update_order_payment_status(self, order_id: int, status: str):
        """
        Update order payment status in database
        
        Args:
            order_id: Order ID
            status: Payment status
        """
        try:
            from models import get_db
            
            conn = get_db()
            cur = conn.cursor()
            
            # Update order status
            cur.execute("""
                UPDATE orders 
                SET payment_verification_status = %s, 
                    payment_verified_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (status, order_id))
            
            conn.commit()
            cur.close()
            conn.close()
            
        except Exception as e:
            print(f"Error updating order payment status: {e}")
    
    def handle_webhook(self, payload: Dict[str, Any], signature: str, timestamp: str) -> Dict[str, Any]:
        """
        Handle Bakong webhook notifications
        
        Args:
            payload: Webhook payload
            signature: Webhook signature
            timestamp: Webhook timestamp
            
        Returns:
            Webhook handling response
        """
        try:
            # Validate webhook signature
            if not self.client.validate_webhook_signature(
                json.dumps(payload), signature, timestamp
            ):
                return {
                    'success': False,
                    'error': 'Invalid webhook signature'
                }
            
            # Process webhook payload
            event_type = payload.get('event_type')
            payment_id = payload.get('payment_id')
            
            if event_type == 'payment.completed':
                # Payment completed
                if payment_id in self.active_payments:
                    payment_data = self.active_payments[payment_id]
                    payment_data['status'] = 'completed'
                    payment_data['completed_at'] = datetime.now()
                    
                    # Update order if this is for an existing order
                    if payment_data.get('order_id'):
                        self._update_order_payment_status(payment_data['order_id'], 'completed')
            
            elif event_type == 'payment.failed':
                # Payment failed
                if payment_id in self.active_payments:
                    payment_data = self.active_payments[payment_id]
                    payment_data['status'] = 'failed'
                    payment_data['failed_at'] = datetime.now()
                    payment_data['failure_reason'] = payload.get('reason', 'Unknown')
            
            return {
                'success': True,
                'message': 'Webhook processed successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Webhook processing failed: {str(e)}'
            }


# Global instance
bakong_handler = None

def get_bakong_handler() -> BakongPaymentHandler:
    """Get or create Bakong payment handler instance"""
    global bakong_handler
    if bakong_handler is None:
        bakong_handler = BakongPaymentHandler()
    return bakong_handler

