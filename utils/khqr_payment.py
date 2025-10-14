"""
KHQR Payment Integration
Uses the official Bakong API for dynamic QR code generation and payment verificationwhy auto te 
"""

import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Import the new Bakong API handler
from utils.bakong_payment_handler import get_bakong_handler

# Legacy support for old bakong_khqr library
try:
    from bakong_khqr import KHQR
    LEGACY_KHQR_AVAILABLE = True
except ImportError:
    LEGACY_KHQR_AVAILABLE = False
    print("⚠️ Legacy bakong_khqr library not installed. Using official Bakong API.")


class KHQRPaymentHandler:
    """
    Enhanced KHQR payment handler using the official Bakong API
    Supports dynamic QR generation and real payment verification
    """
    
    def __init__(self):
        # Initialize payment tracking
        self.active_payments = {}
        
        # Use the new Bakong API handler
        self.bakong_handler = get_bakong_handler()
        
        # Legacy merchant information (for fallback)
        self.merchant_config = {
            'merchant_name': 'DALIN KONG',
            'merchant_city': 'Phnom Penh',
            'bank_account': 'kong_dalin1@aclb',
            'phone_number': '015433830',
            'store_label': 'shop',
            'terminal_label': 'POS-02'
        }
        
        # Check if Bakong API credentials are configured
        import os
        self.bakong_configured = all([
            os.getenv('BAKONG_API_KEY'),
            os.getenv('BAKONG_API_SECRET'),
            os.getenv('BAKONG_MERCHANT_ID'),
            os.getenv('BAKONG_MERCHANT_ACCOUNT')
        ])
        
        if not self.bakong_configured:
            print("⚠️ Bakong API credentials not configured. Using legacy system.")
            print("💡 Set BAKONG_API_KEY, BAKONG_API_SECRET, BAKONG_MERCHANT_ID, BAKONG_MERCHANT_ACCOUNT environment variables")

        # Legacy KHQR support (fallback)
        if not LEGACY_KHQR_AVAILABLE:
            self.khqr = None
            print("⚠️ Legacy KHQR library not available. Using official Bakong API.")
            return

        # Initialize legacy KHQR as fallback
        try:
            import os
            jwt_token = os.getenv('KHQR_JWT_TOKEN', "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjp7ImlkIjoiOTU5YjgzZWI2NjRhNDBlMyJ9LCJpYXQiOjE3NjA0NjAxMDEsImV4cCI6MTc2ODIzNjEwMX0.tL1hT8aLC-Oca_KW8ZCCl6NK4xI62CsaC1_dLawi668")
            
            print(f"🔧 Initializing legacy KHQR as fallback...")
            self.khqr = KHQR(jwt_token)
            print("✅ Legacy KHQR initialized as fallback")
        except Exception as e:
            self.khqr = None
            print(f"❌ Legacy KHQR fallback failed: {e}")
            print("💡 Using official Bakong API only")

        
    def create_payment_qr(self, amount: float, currency: str = "USD", 
                         reference_id: Optional[str] = None, order_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Create a dynamic KHQR payment QR code using official Bakong API
        
        Args:
            amount: Payment amount
            currency: Currency (USD or KHR)
            reference_id: Optional reference ID
            order_id: Optional order ID to associate with this payment
            
        Returns:
            Dictionary containing QR data and payment information
        """
        # Try official Bakong API first
        try:
            result = self.bakong_handler.create_payment_qr(
                amount=amount,
                currency=currency,
                reference_id=reference_id,
                order_id=order_id
            )
            
            if result.get('success', False):
                print("✅ Payment QR created using official Bakong API")
                
                # Generate MD5 hash for the QR data (Bakong API doesn't provide this)
                qr_data = result.get('qr_data', '')
                if qr_data and hasattr(self.khqr, 'generate_md5'):
                    try:
                        md5_hash = self.khqr.generate_md5(qr_data)
                        print(f"✅ MD5 hash generated: {md5_hash}")
                    except Exception as e:
                        print(f"⚠️ Error generating MD5 hash: {e}")
                        md5_hash = ''
                else:
                    print("⚠️ No QR data or generate_md5 method not available")
                    md5_hash = ''
                
                # Store payment locally for tracking
                payment_id = result.get('payment_id')
                if payment_id:
                    # Store in memory
                    self.active_payments[payment_id] = {
                        'payment_id': payment_id,
                        'amount': amount,
                        'currency': currency,
                        'reference_id': reference_id,
                        'order_id': order_id,
                        'qr_data': qr_data,
                        'qr_code': result.get('qr_code', ''),
                        'md5_hash': md5_hash,
                        'status': 'pending',
                        'created_at': datetime.now(),
                        'expires_at': datetime.now() + timedelta(minutes=15)
                    }
                    
                    # Store in database for persistence
                    self._store_payment_in_db(payment_id, order_id, qr_data, md5_hash, amount, currency)
                    
                    print(f"💾 Payment {payment_id} stored locally and in database for tracking")
                
                # Add MD5 hash to the result
                result['md5_hash'] = md5_hash
                return result
            else:
                print(f"⚠️ Bakong API failed: {result.get('error', 'Unknown error')}")
                # Fall back to legacy method
                
        except Exception as e:
            print(f"⚠️ Bakong API error: {e}")
            # Fall back to legacy method
        
        # Fallback to legacy KHQR library
        if not LEGACY_KHQR_AVAILABLE or self.khqr is None:
            return {
                'success': False,
                'error': 'Both Bakong API and legacy KHQR library not available'
            }

        if reference_id is None:
            reference_id = f"TRX{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Generate unique bill number
        bill_number = f"BILL_{uuid.uuid4().hex[:8].upper()}"

        try:
            import time
            start_time = time.time()
            print(f"🔧 Creating KHQR payment: {amount} {currency}")

            # Create QR code exactly like your working script
            qr_start = time.time()
            qr_data = self.khqr.create_qr(
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
            qr_time = time.time() - qr_start
            print(f"✅ QR created successfully - Length: {len(qr_data)} (took {qr_time:.2f}s)")

            # Generate MD5 hash for payment verification
            md5_start = time.time()
            md5_hash = self.khqr.generate_md5(qr_data)
            md5_time = time.time() - md5_start
            print(f"✅ MD5 hash: {md5_hash} (took {md5_time:.2f}s)")
            
            # Create payment record
            payment_id = str(uuid.uuid4())
            payment_data = {
                'payment_id': payment_id,
                'qr_data': qr_data,
                'md5_hash': md5_hash,
                'amount': amount,
                'currency': currency,
                'reference_id': reference_id,
                'bill_number': bill_number,
                'status': 'pending',
                'created_at': datetime.now(),
                'expires_at': datetime.now() + timedelta(minutes=15),
                'order_id': order_id  # Include order_id in payment data
            }
            
            # Store payment for tracking
            self.active_payments[payment_id] = payment_data
            
            # Create payment session in database for cancellation support
            if order_id:
                try:
                    from utils.bakong_payment import PaymentSession
                    session_id = PaymentSession.create_session(
                        cart_items=[],  # Empty for now, will be populated by cart
                        customer_info={},  # Empty for now, will be populated by cart
                        total_amount=amount,
                        order_id=order_id
                    )
                    payment_data['session_id'] = session_id
                    print(f"✅ Payment session created: {session_id} for order: {order_id}")
                except Exception as e:
                    print(f"⚠️ Warning: Could not create payment session: {e}")
            
            # Generate QR code image from QR data
            img_start = time.time()
            qr_code_image = self.generate_qr_code_image(qr_data)
            img_time = time.time() - img_start
            print(f"✅ QR image generated (took {img_time:.2f}s)")
            
            total_time = time.time() - start_time
            print(f"✅ Total KHQR payment creation time: {total_time:.2f}s")
            
            return {
                'success': True,
                'payment_id': payment_id,
                'qr_data': qr_data,
                'qr_code': qr_code_image,  # Base64 encoded QR code image
                'md5_hash': md5_hash,
                'amount': amount,
                'currency': currency,
                'reference_id': reference_id,
                'bill_number': bill_number,
                'expires_at': payment_data['expires_at'].isoformat(),
                'order_id': order_id,  # Include order_id in return value
                'session_id': payment_data.get('session_id')  # Include session_id for cancellation
            }
            
        except Exception as e:
            print(f"❌ KHQR creation failed: {e}")

            # Fallback: Create a test QR code for debugging
            if self.test_mode:
                print("🔄 Falling back to test QR code...")
                qr_data = f"FALLBACK_QR_AMOUNT_{amount}_{currency}_MERCHANT_DALIN_KONG_ACCOUNT_kong_dalin1@aclb_REF_{reference_id}"
                md5_hash = f"fallback_hash_{uuid.uuid4().hex[:16]}"

                # Create payment record with fallback data
                payment_id = str(uuid.uuid4())
                payment_data = {
                    'payment_id': payment_id,
                    'qr_data': qr_data,
                    'md5_hash': md5_hash,
                    'amount': amount,
                    'currency': currency,
                    'reference_id': reference_id,
                    'bill_number': bill_number,
                    'status': 'pending',
                    'created_at': datetime.now(),
                    'expires_at': datetime.now() + timedelta(minutes=15),
                    'fallback_mode': True
                }

                self.active_payments[payment_id] = payment_data

                print(f"✅ Fallback QR created for testing")
                
                # Generate QR code image for fallback
                qr_code_image = self.generate_qr_code_image(qr_data)
                
                return {
                    'success': True,
                    'payment_id': payment_id,
                    'qr_data': qr_data,
                    'qr_code': qr_code_image,  # Base64 encoded QR code image
                    'md5_hash': md5_hash,
                    'amount': amount,
                    'currency': currency,
                    'reference_id': reference_id,
                    'bill_number': bill_number,
                    'expires_at': payment_data['expires_at'].isoformat(),
                    'fallback_mode': True
                }

            return {
                'success': False,
                'error': f"Failed to create QR payment: {str(e)}"
            }
    
    def generate_qr_code_image(self, qr_data: str) -> str:
        """
        Generate a QR code image from QR data string
        
        Args:
            qr_data: QR data string to encode
            
        Returns:
            Base64 encoded PNG image string
        """
        try:
            import qrcode
            import io
            import base64
            
            # Create QR code with optimized settings for faster generation
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=4,  # Reduced from 8 to 4 for faster generation
                border=1,    # Reduced from 2 to 1 for smaller image
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            # Create QR code image
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64
            img_buffer = io.BytesIO()
            qr_img.save(img_buffer, format='PNG', optimize=True)
            img_buffer.seek(0)
            qr_base64 = base64.b64encode(img_buffer.getvalue()).decode()
            
            return qr_base64
            
        except ImportError:
            print("⚠️ qrcode library not available, cannot generate QR image")
            return None
        except Exception as e:
            print(f"❌ Error generating QR code image: {e}")
            return None

    def regenerate_qr_with_same_hash(self, amount: float, currency: str = "USD", 
                                   transaction_id: str = None, order_id: int = None) -> Dict[str, Any]:
        """
        Regenerate QR code using the same MD5 hash for cancelled payments
        
        Args:
            amount: Payment amount
            currency: Currency (USD or KHR)
            transaction_id: Existing transaction ID (MD5 hash) to reuse
            order_id: Order ID for reference
            
        Returns:
            Dictionary containing QR data and payment information
        """
        if not LEGACY_KHQR_AVAILABLE or self.khqr is None:
            return {
                'success': False,
                'error': 'KHQR library not available or not initialized'
            }

        if not transaction_id:
            return {
                'success': False,
                'error': 'Transaction ID is required for QR regeneration'
            }

        try:
            print(f"🔄 Regenerating QR with same hash: {transaction_id} for order {order_id}")

            # Generate unique bill number for the new QR
            bill_number = f"BILL_{uuid.uuid4().hex[:8].upper()}"

            # Create QR code with the same merchant details but new bill number
            qr_data = self.khqr.create_qr(
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

            print(f"✅ QR regenerated successfully - Length: {len(qr_data)}")

            # Use the same MD5 hash as the original payment
            md5_hash = transaction_id
            print(f"✅ Using existing MD5 hash: {md5_hash}")
            
            # Create new payment record with same hash
            payment_id = str(uuid.uuid4())
            payment_data = {
                'payment_id': payment_id,
                'qr_data': qr_data,
                'md5_hash': md5_hash,
                'amount': amount,
                'currency': currency,
                'reference_id': f"REGEN_{order_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'bill_number': bill_number,
                'status': 'pending',
                'created_at': datetime.now(),
                'expires_at': datetime.now() + timedelta(minutes=15),
                'order_id': order_id,
                'is_regenerated': True  # Flag to indicate this is a regenerated QR
            }
            
            # Store payment for tracking
            self.active_payments[payment_id] = payment_data
            
            # Generate QR code image from QR data
            qr_code_image = self.generate_qr_code_image(qr_data)
            
            return {
                'success': True,
                'payment_id': payment_id,
                'qr_data': qr_data,
                'qr_code': qr_code_image,  # Base64 encoded QR code image
                'md5_hash': md5_hash,
                'amount': amount,
                'currency': currency,
                'reference_id': payment_data['reference_id'],
                'bill_number': bill_number,
                'expires_at': payment_data['expires_at'].isoformat(),
                'order_id': order_id,
                'is_regenerated': True
            }
            
        except Exception as e:
            print(f"❌ QR regeneration failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """
        Check if a payment has been completed using legacy KHQR system

        Args:
            payment_id: Payment ID to check

        Returns:
            Payment status information
        """
        # Since we're using legacy system, skip Bakong API and go directly to legacy
        if not LEGACY_KHQR_AVAILABLE or self.khqr is None:
            return {
                'success': False,
                'error': 'Legacy KHQR library not available'
            }

        # Find payment by payment_id in active_payments
        payment_data = None
        for pid, data in self.active_payments.items():
            if pid == payment_id:
                payment_data = data
                break
        
        if not payment_data:
            return {
                'success': False,
                'error': 'Payment not found'
            }
        
        # Check if payment has expired
        if datetime.now() > payment_data['expires_at']:
            payment_data['status'] = 'expired'
            return {
                'success': True,
                'status': 'expired',
                'message': 'Payment has expired'
            }
        
        try:
            # Check how long the payment has been active
            time_since_creation = datetime.now() - payment_data['created_at']
            print(f"⏰ Payment age: {time_since_creation.total_seconds()} seconds")

            # Don't check payment status immediately - give it at least 10 seconds
            if time_since_creation.total_seconds() < 10:
                print(f"⏳ Payment too new ({time_since_creation.total_seconds()}s), keeping as pending")
                return {
                    'success': True,
                    'status': 'pending',
                    'payment_id': payment_id,
                    'message': 'Payment created, waiting for customer to scan QR code'
                }

            # Check if we have MD5 hash for real bank API verification
            if 'md5_hash' in payment_data and payment_data['md5_hash']:
                print(f"🔍 Checking payment with MD5 hash: {payment_data['md5_hash']}")
                try:
                    # Use KHQR API to check payment status with real bank API
                    payment_status = self.khqr.check_payment(payment_data['md5_hash'])
                    print(f"📊 KHQR API response: {payment_status}")
                    is_paid = payment_status == "PAID"
                    
                    if is_paid:
                        print("✅ Real payment confirmed by bank API!")
                    else:
                        print("⏳ Payment not yet confirmed by bank API")
                        
                except Exception as api_error:
                    print(f"❌ KHQR API error: {api_error}")
                    is_paid = False
            else:
                print("⚠️ No MD5 hash available - cannot verify payment with bank API")
                is_paid = False
            
            if is_paid:
                payment_data['status'] = 'completed'
                payment_data['completed_at'] = datetime.now()
                print(f"✅ Payment {payment_id} marked as completed!")

                # Handle order completion - check if this is for an existing order or needs new order creation
                order_id = None
                reference_id = payment_data.get('reference_id', '')
                
                # Check if reference_id indicates an existing order (format: ORDER_123)
                if reference_id.startswith('ORDER_'):
                    try:
                        existing_order_id = int(reference_id.replace('ORDER_', ''))
                        print(f"🔄 Found existing order ID {existing_order_id} in reference, updating to completed...")
                        
                        # Update existing order status and reduce stock
                        order_id = self.update_existing_order_to_completed(existing_order_id, payment_data)
                        print(f"✅ Updated existing order {existing_order_id} to completed")
                        
                    except (ValueError, Exception) as e:
                        print(f"❌ Error updating existing order: {e}")
                        # Fallback to creating new order
                        print(f"🔄 Falling back to creating new order...")
                        order_id = self.create_order_from_payment(payment_data)
                else:
                    # No existing order reference, create new order (for standalone KHQR payments)
                    print(f"🔄 No existing order reference, creating new order...")
                    order_id = self.create_order_from_payment(payment_data)
                
                print(f"📦 Final order ID: {order_id}")

                result = {
                    'success': True,
                    'status': 'completed',
                    'payment_id': payment_id,
                    'amount': payment_data['amount'],
                    'currency': payment_data['currency'],
                    'reference_id': payment_data['reference_id'],
                    'completed_at': payment_data['completed_at'].isoformat()
                }

                if order_id:
                    result['order_id'] = order_id
                    result['invoice_url'] = f'/invoice/{order_id}'
                    print(f"🧾 Invoice URL: /invoice/{order_id}")
                else:
                    print(f"❌ No order available - invoice URL not available")

                print(f"📤 Returning payment result: {result}")
                return result
            else:
                print(f"⏳ Payment {payment_id} still pending...")
                return {
                    'success': True,
                    'status': 'pending',
                    'payment_id': payment_id
                }


        except Exception as e:
            print(f"❌ Error checking payment status: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to check payment status: {str(e)}"
            }
    
    def get_payment_info(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """Get payment information by ID"""
        return self.active_payments.get(payment_id)

    def update_existing_order_to_completed(self, order_id: int, payment_data: Dict[str, Any] = None) -> Optional[int]:
        """Update an existing pending order payment confirmation - order remains Pending until staff approval"""
        try:
            from models import get_db
            
            print(f"🔄 Updating order {order_id} to completed and reducing stock...")
            
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            
            try:
                # Verify order exists and is pending
                cur.execute("SELECT id, status FROM orders WHERE id = %s", (order_id,))
                order = cur.fetchone()
                
                if not order:
                    print(f"❌ Order {order_id} not found")
                    return None
                
                if order['status'] != 'PENDING':
                    print(f"⚠️ Order {order_id} is already {order['status']}, not updating")
                    return order_id  # Return the order ID anyway since it exists
                
                # Update order status to 'COMPLETED' since payment is confirmed
                # But keep approval_status as 'Pending Approval' for staff to manually approve
                # Also update transaction_id with the payment's MD5 hash if available
                md5_hash = None
                if payment_data:
                    md5_hash = payment_data.get('md5_hash')
                
                if md5_hash:
                    cur.execute("UPDATE orders SET status = 'COMPLETED', transaction_id = %s WHERE id = %s", (md5_hash, order_id))
                    print(f"✅ Order {order_id} payment confirmed, status set to COMPLETED, transaction_id updated to {md5_hash}")
                else:
                    cur.execute("UPDATE orders SET status = 'COMPLETED' WHERE id = %s", (order_id,))
                    print(f"✅ Order {order_id} payment confirmed, status set to COMPLETED")
                
                # Get order items to reduce stock
                cur.execute("""
                    SELECT product_id, quantity 
                    FROM order_items 
                    WHERE order_id = %s
                """, (order_id,))
                
                order_items = cur.fetchall()
                print(f"📦 Found {len(order_items)} items to reduce stock for")
                
                # Stock is already reduced when order was placed at checkout
                # No need to reduce stock again here
                print(f"✅ Order {order_id} payment confirmed, status set to COMPLETED, approval_status remains Pending Approval")
                print(f"📦 Stock already reduced at checkout for {len(order_items)} items")
                
                conn.commit()
                return order_id
                
            except Exception as e:
                conn.rollback()
                print(f"❌ Error updating order {order_id}: {e}")
                raise e
            finally:
                cur.close()
                conn.close()
                
        except Exception as e:
            print(f"❌ Error in update_existing_order_to_completed: {str(e)}")
            return None

    def create_order_from_payment(self, payment_data: Dict[str, Any]) -> Optional[int]:
        """Create an order from completed payment data"""
        try:
            print(f"🔄 Starting order creation for payment: {payment_data['payment_id']}")

            from models import Order, Customer, get_db

            # Try to get Flask session
            try:
                from flask import session
                has_session = True
                print(f"🔍 Flask session available: {dict(session) if session else 'Empty'}")
            except:
                has_session = False
                print(f"⚠️ Flask session not available - creating guest customer")

            # Get current user from session if available
            if has_session and 'user_id' in session:
                customer_id = session['user_id']
                print(f"🔍 Using logged-in customer: {customer_id}")
            else:
                # Create a guest customer for KHQR payments
                customer_email = f"khqr_{payment_data['payment_id'][:8]}@guest.com"
                print(f"🔍 Creating guest customer with email: {customer_email}")

                try:
                    customer = Customer.get_by_email(customer_email)
                    if not customer:
                        print(f"🔍 Customer not found, creating new one...")
                        customer_id = Customer.create(
                            first_name="KHQR",
                            last_name="Guest",
                            email=customer_email,
                            password="defaultpassword123",
                            phone="",
                            address=""
                        )
                        print(f"✅ Created new customer: {customer_id}")
                    else:
                        customer_id = customer['id']
                        print(f"🔍 Found existing customer: {customer_id}")
                except Exception as customer_error:
                    print(f"❌ Error with customer operations: {customer_error}")
                    # Fallback: use a default customer ID if it exists
                    try:
                        customers = Customer.get_all()
                        if customers:
                            customer_id = customers[0]['id']
                            print(f"🔄 Using fallback customer: {customer_id}")
                        else:
                            print(f"❌ No customers found in database")
                            return None
                    except Exception as fallback_error:
                        print(f"❌ Fallback customer lookup failed: {fallback_error}")
                        return None

            # Find a product with available stock
            print(f"🔄 Looking for products with stock...")
            from models import Product

            products = Product.get_all()
            if not products:
                print(f"❌ No products found in database")
                return None

            # Find a product with stock > 0
            available_product = None
            for product in products:
                stock = product.get('stock', 0)
                print(f"🔍 Product {product['id']} - {product['name']}: Stock = {stock}")
                if stock > 0:
                    available_product = product
                    break

            if not available_product:
                print(f"❌ No products with stock found")
                return None

            print(f"✅ Using product: {available_product['id']} - {available_product['name']} (Stock: {available_product.get('stock', 0)})")

            # Create order items with the available product
            order_items = [{
                'product_id': available_product['id'],
                'quantity': 1,
                'price': float(payment_data['amount'])
            }]
            print(f"📦 Order items: {order_items}")

            print(f"🔄 Creating order with stock validation...")
            order_id = Order.create(
                customer_id=customer_id,
                order_date=payment_data.get('completed_at', datetime.now()),
                status='PENDING',
                items=order_items,
                payment_method='KHQR Payment',
                transaction_id=payment_data.get('md5_hash')
            )

            print(f"✅ Order {order_id} created successfully for KHQR payment {payment_data['payment_id']}")

            # Don't clear cart immediately - only clear after payment confirmation
            # self.clear_customer_cart(customer_id)

            return order_id

        except Exception as e:
            print(f"❌ Error creating order from payment: {str(e)}")
            import traceback
            print(f"❌ Full traceback: {traceback.format_exc()}")
            return None

    def confirm_payment_and_clear_cart(self, order_id: int, customer_id: int):
        """Confirm payment and clear customer's cart after successful payment"""
        try:
            print(f"🎉 Confirming payment for order {order_id} and clearing cart for customer {customer_id}")
            
            # Update order status to confirmed if needed
            from models import get_db
            conn = get_db()
            cur = conn.cursor()
            
            try:
                # Update order status to confirmed
                cur.execute("""
                    UPDATE orders
                    SET status = 'Confirmed', updated_at = NOW()
                    WHERE id = %s AND customer_id = %s
                """, (order_id, customer_id))
                
                conn.commit()
                print(f"✅ Order {order_id} confirmed")
                
                # Clear pending orders for this customer (clean up any failed attempts)
                cur.execute("""
                    DELETE oi FROM order_items oi
                    JOIN orders o ON oi.order_id = o.id
                    WHERE o.customer_id = %s AND o.status = 'PENDING'
                """, (customer_id,))

                cur.execute("""
                    DELETE FROM orders
                    WHERE customer_id = %s AND status = 'PENDING'
                """, (customer_id,))
                
                conn.commit()
                print(f"✅ Pending orders cleaned up for customer {customer_id}")
                
            finally:
                cur.close()
                conn.close()
                
        except Exception as e:
            print(f"❌ Error confirming payment and clearing cart: {str(e)}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
    
    def cleanup_expired_payments(self):
        """Remove expired payments from memory"""
        now = datetime.now()
        expired_payments = [
            pid for pid, payment in self.active_payments.items()
            if payment['expires_at'] < now
        ]
        
        for pid in expired_payments:
            del self.active_payments[pid]
            
        return len(expired_payments)
    
    def _store_payment_in_db(self, payment_id: str, order_id: int, qr_data: str, 
                            md5_hash: str, amount: float, currency: str):
        """Store payment information in database for persistence"""
        try:
            from models import get_db
            conn = get_db()
            cur = conn.cursor()
            
            cur.execute("""
                INSERT INTO payment_tracking 
                (order_id, payment_id, md5_hash, qr_data, amount, currency, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'pending')
                ON DUPLICATE KEY UPDATE
                md5_hash = VALUES(md5_hash),
                qr_data = VALUES(qr_data),
                amount = VALUES(amount),
                currency = VALUES(currency),
                status = VALUES(status)
            """, (order_id, payment_id, md5_hash, qr_data, amount, currency))
            
            conn.commit()
            cur.close()
            conn.close()
            print(f"💾 Payment {payment_id} stored in database")
            
        except Exception as e:
            print(f"❌ Error storing payment in database: {e}")
    
    def _get_payment_from_db(self, order_id: int):
        """Retrieve payment information from database"""
        try:
            from models import get_db
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            
            cur.execute("""
                SELECT payment_id, md5_hash, qr_data, amount, currency, status, 
                       created_at, completed_at
                FROM payment_tracking 
                WHERE order_id = %s 
                ORDER BY created_at DESC 
                LIMIT 1
            """, (order_id,))
            
            result = cur.fetchone()
            cur.close()
            conn.close()
            
            return result
            
        except Exception as e:
            print(f"❌ Error retrieving payment from database: {e}")
            return None


# Global instance - Production mode (real payments)
khqr_handler = KHQRPaymentHandler()
