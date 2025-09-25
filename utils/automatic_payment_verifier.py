"""
Automatic Payment Verification System
Continuously checks for completed QR payments and updates pending orders
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List
from models import get_db
from utils.khqr_payment import khqr_handler
from utils.payment_session_manager import PaymentSessionManager

class AutomaticPaymentVerifier:
    """
    Automatically verifies QR payments and updates order status
    Runs in background to check for completed payments
    """
    
    def __init__(self, check_interval: int = 30, app=None, test_mode: bool = False):
        """
        Initialize the automatic payment verifier
        
        Args:
            check_interval: How often to check for payments (in seconds)
            app: Flask app instance for application context
            test_mode: If True, payments are detected immediately for testing
        """
        self.check_interval = check_interval
        self.running = False
        self.thread = None
        self.payment_manager = PaymentSessionManager()
        self.app = app
        self.test_mode = test_mode
        
    def start(self):
        """Start the automatic payment verification"""
        if self.running:
            print("⚠️ Automatic payment verifier is already running")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._verification_loop, daemon=True)
        self.thread.start()
        print(f"✅ Automatic payment verifier started (checking every {self.check_interval} seconds)")
        
    def stop(self):
        """Stop the automatic payment verification"""
        self.running = False
        if self.thread:
            self.thread.join()
        print("🛑 Automatic payment verifier stopped")
        
    def _verification_loop(self):
        """Main verification loop that runs in background"""
        while self.running:
            try:
                if self.app:
                    with self.app.app_context():
                        self._check_all_pending_payments()
                else:
                    print("⚠️ No Flask app context available for payment verification")
                time.sleep(self.check_interval)
            except Exception as e:
                print(f"❌ Error in payment verification loop: {e}")
                time.sleep(self.check_interval)
                
    def _check_all_pending_payments(self):
        """Check all pending payments for completion"""
        try:
            # Get all pending orders with KHQR_BAKONG payment method
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            
            try:
                # Get all pending orders for instant detection (no time restriction)
                # Check for various KHQR payment method names
                cur.execute("""
                    SELECT o.id, o.transaction_id, o.total_amount, o.order_date, o.customer_id, o.payment_method
                    FROM orders o
                    WHERE o.status = 'PENDING' 
                    AND (o.payment_method = 'KHQR_BAKONG' 
                         OR o.payment_method LIKE '%KHQR%' 
                         OR o.payment_method LIKE '%QR%'
                         OR o.payment_method = 'KHQR Payment')
                    AND o.transaction_id IS NOT NULL
                    ORDER BY o.order_date ASC
                """)
                
                pending_orders = cur.fetchall()
                
                if pending_orders:
                    print(f"🔍 Checking {len(pending_orders)} pending QR payments...")
                    
                    for order in pending_orders:
                        self._check_single_payment(order)
                else:
                    # Only log this message once per minute to avoid spam
                    current_time = time.time()
                    if not hasattr(self, '_last_no_orders_log') or current_time - self._last_no_orders_log > 60:
                        # Debug: Check what payment methods are actually in pending orders
                        cur.execute("""
                            SELECT payment_method, COUNT(*) as count
                            FROM orders o
                            WHERE o.status = 'PENDING'
                            GROUP BY payment_method
                        """)
                        results = cur.fetchall()
                        if results:
                            print(f"ℹ️ Found pending orders with these payment methods:")
                            for row in results:
                                print(f"   - {row['payment_method']}: {row['count']} orders")
                            print("   (will check again in 1 minute)")
                        else:
                            print("ℹ️ No pending orders found")
                        self._last_no_orders_log = current_time
                        
            finally:
                cur.close()
                conn.close()
                
        except Exception as e:
            print(f"❌ Error checking pending payments: {e}")
            
    def _check_single_payment(self, order: Dict[str, Any]):
        """Check a single pending payment"""
        try:
            order_id = order['id']
            transaction_id = order['transaction_id']
            amount = float(order['total_amount'])
            
            # Check if we have a payment session for this order
            payment_session = self._find_payment_session_by_order(order_id)
            
            if payment_session:
                # Use the payment tracking's payment_id to check status
                payment_id = payment_session['payment_id']
                print(f"🔍 Checking payment for order {order_id} (payment_id: {payment_id})")
                
                # Check payment status using KHQR handler
                if khqr_handler and khqr_handler.khqr:
                    payment_status = khqr_handler.check_payment_status(payment_id)
                    
                    if payment_status.get('success') and payment_status.get('status') == 'completed':
                        print(f"✅ Payment completed for order {order_id}!")
                        self._complete_order_payment(order_id, payment_session)
                    else:
                        print(f"⏳ Payment still pending for order {order_id}")
                else:
                    print(f"⚠️ KHQR handler not available for order {order_id}")
            else:
                # No payment session found - this is normal for KHQR orders created through checkout
                # For these orders, we need to check if payment was made using the transaction ID
                # We'll simulate automatic detection by checking if enough time has passed
                # In a real system, this would check the bank's API using the transaction ID
                
                # For real-world scenarios, we need to check if payment was actually made
                # Since we can't access bank APIs directly, we'll use a different approach:
                # 1. Check if order has been "paid" by looking for payment confirmation
                # 2. For demo purposes, we'll simulate random payment completion
                # 3. In production, this would integrate with actual bank APIs
                
                from datetime import datetime, timedelta
                import random
                
                order_date = order['order_date']
                if isinstance(order_date, str):
                    order_date = datetime.strptime(order_date, '%Y-%m-%d %H:%M:%S')
                
                time_since_order = datetime.now() - order_date
                
                # Simplified instant payment detection
                from datetime import datetime, timedelta
                
                order_date = order['order_date']
                if isinstance(order_date, str):
                    order_date = datetime.strptime(order_date, '%Y-%m-%d %H:%M:%S')
                
                time_since_order = datetime.now() - order_date
                
                # Check if we have a payment session for this order
                payment_session = self._find_payment_session_by_order(order_id)
                
                if payment_session:
                    # Use the payment session's payment_id to check status
                    payment_id = payment_session['session_id']
                    print(f"🔍 Checking payment for order {order_id} (session: {payment_id})")
                    
                    # Check payment status using KHQR handler
                    if khqr_handler and khqr_handler.khqr:
                        payment_status = khqr_handler.check_payment_status(payment_id)
                        
                        if payment_status.get('success') and payment_status.get('status') == 'completed':
                            print(f"✅ Payment completed for order {order_id}!")
                            self._complete_order_payment(order_id, payment_session)
                        else:
                            print(f"⏳ Payment still pending for order {order_id}")
                    else:
                        print(f"⚠️ KHQR handler not available for order {order_id}")
                else:
                    # No payment session found - check using transaction_id and MD5 hash
                    transaction_id = order.get('transaction_id')
                    if transaction_id:
                        print(f"🔍 Checking payment for order {order_id} using transaction_id: {transaction_id}")
                        
                        # Use KHQR handler to check payment with transaction ID
                        if khqr_handler and khqr_handler.khqr:
                            # Try to check payment status using the transaction ID
                            try:
                                print(f"🔍 Checking real payment status for transaction {transaction_id}")
                                
                                # Check if we have a payment session with this transaction ID
                                payment_session = self._find_payment_session_by_transaction_id(transaction_id)
                                
                                if payment_session:
                                    # Use the payment session to check status
                                    payment_id = payment_session['session_id']
                                    payment_status = khqr_handler.check_payment_status(payment_id)
                                    
                                    if payment_status.get('success') and payment_status.get('status') == 'completed':
                                        print(f"✅ Payment completed for order {order_id}!")
                                        self._complete_order_payment(order_id, payment_session)
                                    else:
                                        print(f"⏳ Payment still pending for order {order_id}")
                                else:
                                    # No payment session found - wait for real payment verification
                                    print(f"⏳ Order {order_id} waiting for real payment verification (no payment session found)")
                                
                            except Exception as e:
                                print(f"❌ Error checking payment status: {e}")
                        else:
                            print(f"⚠️ KHQR handler not available for order {order_id}")
                    else:
                        print(f"⚠️ No transaction_id found for order {order_id}")
                
        except Exception as e:
            print(f"❌ Error checking payment for order {order_id}: {e}")
    
    def _check_real_payment_status(self, order_id: int, order: Dict[str, Any]):
        """Check real payment status using bank API"""
        try:
            # For now, since we don't have proper payment_id tracking,
            # we'll simulate automatic detection after a reasonable time
            # In a real implementation, this would use the actual bank API
            
            from datetime import datetime, timedelta
            order_date = order['order_date']
            if isinstance(order_date, str):
                order_date = datetime.strptime(order_date, '%Y-%m-%d %H:%M:%S')
            
            time_since_order = datetime.now() - order_date
            
            # Simulate payment completion after 10 seconds for instant detection
            # In production, this would check the actual bank API using the transaction_id
            if time_since_order.total_seconds() > 10:  # 10 seconds for instant detection
                print(f"🎉 Payment detected for order {order_id} after {time_since_order.seconds}s")
                self._complete_order_payment(order_id, None)
            else:
                print(f"⏳ Order {order_id} waiting for payment completion ({time_since_order.seconds}s elapsed)")
                
        except Exception as e:
            print(f"❌ Error checking real payment status for order {order_id}: {e}")
    
    def _simulate_payment_completion(self, order_id: int, order: Dict[str, Any]):
        """Simulate payment completion for test mode"""
        try:
            print(f"🎉 Simulating payment completion for order {order_id}")
            self._complete_order_payment(order_id, None)
        except Exception as e:
            print(f"❌ Error simulating payment completion for order {order_id}: {e}")
            
    def _find_payment_session_by_order(self, order_id: int) -> Dict[str, Any]:
        """Find payment tracking by order ID"""
        try:
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            
            try:
                cur.execute("""
                    SELECT * FROM payment_tracking 
                    WHERE order_id = %s AND status = 'pending'
                    ORDER BY created_at DESC LIMIT 1
                """, (order_id,))
                
                return cur.fetchone()
                
            finally:
                cur.close()
                conn.close()
                
        except Exception as e:
            print(f"❌ Error finding payment tracking for order {order_id}: {e}")
            return None
    
    def _find_payment_session_by_transaction_id(self, transaction_id: str) -> Dict[str, Any]:
        """Find payment tracking by transaction ID"""
        try:
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            
            try:
                # Check if payment_tracking table exists
                cur.execute("SHOW TABLES LIKE 'payment_tracking'")
                if not cur.fetchone():
                    print(f"⚠️ payment_tracking table does not exist - skipping payment lookup")
                    return None
                
                # Check what columns exist in the table
                cur.execute("DESCRIBE payment_tracking")
                columns = [row[0] for row in cur.fetchall()]
                print(f"📋 Available columns in payment_tracking: {columns}")
                
                # Build query based on available columns
                where_conditions = []
                params = []
                
                if 'transaction_id' in columns:
                    where_conditions.append("transaction_id = %s")
                    params.append(transaction_id)
                if 'payment_id' in columns:
                    where_conditions.append("payment_id = %s")
                    params.append(transaction_id)
                if 'reference_id' in columns:
                    where_conditions.append("reference_id = %s")
                    params.append(transaction_id)
                
                if not where_conditions:
                    print(f"⚠️ No matching columns found for transaction lookup")
                    return None
                
                where_clause = " OR ".join(where_conditions)
                status_condition = " AND status = 'pending'" if 'status' in columns else ""
                
                query = f"""
                    SELECT * FROM payment_tracking 
                    WHERE ({where_clause}) {status_condition}
                    ORDER BY created_at DESC LIMIT 1
                """
                
                cur.execute(query, params)
                
                return cur.fetchone()
                
            finally:
                cur.close()
                conn.close()
                
        except Exception as e:
            print(f"❌ Error finding payment tracking for transaction {transaction_id}: {e}")
            return None
            
    def _complete_order_payment(self, order_id: int, payment_session: Dict[str, Any]):
        """Complete the order payment and update status"""
        try:
            conn = get_db()
            cur = conn.cursor()
            
            try:
                # Update order status to COMPLETED (payment detected)
                # But keep approval_status as PENDING until admin manually approves
                cur.execute("""
                    UPDATE orders 
                    SET status = 'COMPLETED'
                    WHERE id = %s
                """, (order_id,))
                
                # Update payment tracking status if payment_session exists
                if payment_session:
                    cur.execute("""
                        UPDATE payment_tracking 
                        SET status = 'completed', completed_at = NOW()
                        WHERE id = %s
                    """, (payment_session['id'],))
                
                # Reduce stock for order items
                cur.execute("""
                    UPDATE products p
                    JOIN order_items oi ON p.id = oi.product_id
                    SET p.stock = p.stock - oi.quantity
                    WHERE oi.order_id = %s AND p.stock >= oi.quantity
                """, (order_id,))
                
                conn.commit()
                
                print(f"✅ Order {order_id} payment detected!")
                print(f"   - Payment Status: PENDING → COMPLETED")
                print(f"   - Approval Status: PENDING (waiting for admin approval)")
                if payment_session:
                    print(f"   - Payment tracking: {payment_session.get('payment_id', 'N/A')}")
                else:
                    print(f"   - Payment tracking: Direct order completion")
                print(f"   - Stock reduced for order items")
                
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                cur.close()
                conn.close()
                
        except Exception as e:
            print(f"❌ Error completing payment for order {order_id}: {e}")
            
    def _simulate_payment_completion(self, order_id: int, transaction_id: str):
        """Simulate automatic payment completion for orders without payment sessions"""
        try:
            conn = get_db()
            cur = conn.cursor()
            
            try:
                # Update order status to COMPLETED (payment detected)
                # But keep approval_status as PENDING until admin manually approves
                cur.execute("""
                    UPDATE orders 
                    SET status = 'COMPLETED'
                    WHERE id = %s
                """, (order_id,))
                
                # Reduce stock for order items
                cur.execute("""
                    UPDATE products p
                    JOIN order_items oi ON p.id = oi.product_id
                    SET p.stock = p.stock - oi.quantity
                    WHERE oi.order_id = %s AND p.stock >= oi.quantity
                """, (order_id,))
                
                conn.commit()
                
                print(f"✅ Order {order_id} payment automatically detected!")
                print(f"   - Payment Status: PENDING → COMPLETED")
                print(f"   - Approval Status: PENDING (waiting for admin approval)")
                print(f"   - Transaction ID: {transaction_id}")
                print(f"   - Stock reduced for order items")
                
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                cur.close()
                conn.close()
                
        except Exception as e:
            print(f"❌ Error simulating payment completion for order {order_id}: {e}")
            
    def manual_check_pending_orders(self) -> Dict[str, Any]:
        """Manually check all pending orders (for testing/debugging)"""
        try:
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            
            try:
                cur.execute("""
                    SELECT o.id, o.transaction_id, o.total_amount, o.order_date, o.customer_id,
                           c.first_name, c.last_name, c.email
                    FROM orders o
                    JOIN customers c ON o.customer_id = c.id
                    WHERE o.status = 'PENDING' 
                    AND o.payment_method = 'KHQR_BAKONG'
                    AND o.transaction_id IS NOT NULL
                    ORDER BY o.order_date DESC
                """)
                
                pending_orders = cur.fetchall()
                
                return {
                    'success': True,
                    'pending_orders': pending_orders,
                    'count': len(pending_orders)
                }
                
            finally:
                cur.close()
                conn.close()
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

# Global instance - will be initialized with Flask app
payment_verifier = None

def initialize_payment_verifier(app, check_interval=2, test_mode=False):
    """Initialize the payment verifier with Flask app context"""
    global payment_verifier
    payment_verifier = AutomaticPaymentVerifier(check_interval=check_interval, app=app, test_mode=test_mode)
    return payment_verifier