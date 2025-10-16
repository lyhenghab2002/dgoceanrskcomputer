/**
 * KHQR Payment Handler
 * Handles KHQR payment flow with QR code generation and payment verification
 */

class KHQRPayment {
    constructor() {
        this.currentPayment = null;
        this.statusCheckInterval = null;
        this.successCallback = null;
        this.errorCallback = null;
        this.suppressOwnModal = false; // Flag to suppress internal modal when used from cart
        
        // Handle page refresh detection
        this.handlePageRefresh();
        
        console.log('🔥 KHQR Payment system initialized');
    }

    /**
     * Handle page refresh detection for QR payments
     */
    handlePageRefresh() {
        // Check if there's a pending QR payment session in localStorage
        const pendingPayment = localStorage.getItem('khqr_pending_payment');
        if (pendingPayment) {
            try {
                const paymentData = JSON.parse(pendingPayment);
                // Check if the payment session is still valid (not too old)
                const now = Date.now();
                const paymentTime = paymentData.timestamp || 0;
                const timeDiff = now - paymentTime;
                
                // If payment is less than 30 minutes old, show the popup
                if (timeDiff < 30 * 60 * 1000) {
                    console.log('🔄 Detected page refresh during QR payment, showing popup');
                    this.showPageRefreshPopup(paymentData);
                } else {
                    // Clear old payment data
                    localStorage.removeItem('khqr_pending_payment');
                }
            } catch (error) {
                console.error('❌ Error parsing pending payment data:', error);
                localStorage.removeItem('khqr_pending_payment');
            }
        }
    }

    /**
     * Show popup for page refresh during QR payment
     */
    showPageRefreshPopup(paymentData) {
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                title: 'Payment Interrupted',
                text: 'You refreshed the page during QR payment. The order is now pending and you can pay later using the same QR code.',
                icon: 'info',
                showCancelButton: true,
                confirmButtonText: 'View Invoice',
                confirmButtonColor: '#28a745',
                cancelButtonText: 'Continue Shopping',
                cancelButtonColor: '#6c757d'
            }).then((result_modal) => {
                if (result_modal.isConfirmed && paymentData.order_id) {
                    // Redirect to invoice page for the pending order
                    console.log('Redirecting to invoice:', `/invoice/${paymentData.order_id}`);
                    window.location.href = `/invoice/${paymentData.order_id}`;
                } else {
                    // Continue shopping - redirect to homepage
                    window.location.href = '/';
                }
                // Clear the pending payment data
                localStorage.removeItem('khqr_pending_payment');
            });
        }
    }

    /**
     * Set success callback function
     */
    setSuccessCallback(callback) {
        this.successCallback = callback;
    }

    /**
     * Set error callback function
     */
    setErrorCallback(callback) {
        this.errorCallback = callback;
    }

    /**
     * Set flag to suppress internal modal (for cart integration)
     */
    setSuppressOwnModal(suppress) {
        this.suppressOwnModal = suppress;
    }

    /**
     * Check if test button should be shown (for development)
     */
    shouldShowTestButton() {
        // Show test button if URL contains ?test=true or if in development
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('test') === 'true' || window.location.hostname === 'localhost';
    }

    /**
     * Start KHQR payment process
     */
    async startPayment(amount, currency = 'USD', referenceId = null, orderId = null) {
        try {
            console.log(`🔄 Starting KHQR payment: ${amount} ${currency}, Order ID: ${orderId}`);
            
            // Show loading indicator
            this.showLoadingIndicator();
            
            // Create payment with timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
            
            const response = await fetch('/api/khqr/create-payment', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    amount: amount,
                    currency: currency,
                    reference_id: referenceId || `KHQR_${Date.now()}`,
                    order_id: orderId
                }),
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);

            const result = await response.json();

            if (!result.success) {
                // Check if KHQR is temporarily unavailable
                if (response.status === 503 && result.fallback_available) {
                    throw new Error('KHQR payment temporarily unavailable. Please use Cash or Pay on Delivery instead.');
                }
                throw new Error(result.error || 'Failed to create payment');
            }

            console.log('✅ KHQR payment created:', result);

            // Store current payment info
            this.currentPayment = result;

            // Store payment data in localStorage for page refresh detection
            const paymentData = {
                ...result,
                timestamp: Date.now()
            };
            localStorage.setItem('khqr_pending_payment', JSON.stringify(paymentData));

            // Show payment modal
            this.showPaymentModal(result);

            // Start checking payment status after 10 seconds
            setTimeout(() => {
                this.startStatusChecking();
            }, 10000);

        } catch (error) {
            console.error('❌ Error starting KHQR payment:', error);
            
            // Handle timeout specifically
            if (error.name === 'AbortError') {
                this.onPaymentError('Payment generation timed out. Please try again or use a different payment method.');
            } else {
                this.onPaymentError(error.message);
            }
        }
    }

    /**
     * Show loading indicator while generating QR code
     */
    showLoadingIndicator() {
        // Remove existing modal if any
        const existingModal = document.getElementById('khqr-payment-modal');
        if (existingModal) {
            existingModal.remove();
        }

        // Create loading modal
        const modal = document.createElement('div');
        modal.id = 'khqr-payment-modal';
        modal.className = 'modal fade show';
        modal.style.display = 'block';
        modal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">🔄 Generating KHQR Payment</h5>
                    </div>
                    <div class="modal-body text-center">
                        <div class="spinner-border text-primary mb-3" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <p>Please wait while we generate your payment QR code...</p>
                        <p class="text-muted small">This may take a few seconds</p>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
    }

    /**
     * Show payment modal with QR code
     */
    showPaymentModal(paymentData) {
        // Remove existing modal if any
        const existingModal = document.getElementById('khqr-payment-modal');
        if (existingModal) {
            existingModal.remove();
        }

        // Create modal HTML
        const modalHTML = `
            <div id="khqr-payment-modal" style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.8);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 10000;
                font-family: Arial, sans-serif;
            ">
                <div style="
                    background: white;
                    padding: 30px;
                    border-radius: 15px;
                    text-align: center;
                    max-width: 400px;
                    width: 90%;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                ">
                    <h2 style="margin: 0 0 20px 0; color: #2c5aa0;">KHQR Payment</h2>
                    
                    <div style="margin: 20px 0;">
                        <div style="font-size: 24px; font-weight: bold; color: #333;">
                            ${paymentData.currency} ${paymentData.amount}
                        </div>
                        <div style="font-size: 14px; color: #666; margin-top: 5px;">
                            Reference: ${paymentData.reference_id}
                        </div>
                    </div>

                    <div id="khqr-qr-container" style="margin: 20px 0;">
                        <!-- QR code will be inserted here -->
                    </div>

                    <div id="khqr-status" style="
                        margin: 20px 0;
                        padding: 10px;
                        background-color: #fff3cd;
                        border: 1px solid #ffeaa7;
                        border-radius: 5px;
                        color: #856404;
                    ">
                        ⏳ Waiting for payment...
                    </div>

                    <div style="margin-top: 20px;">
                        ${this.shouldShowTestButton() ? `
                        <button onclick="window.khqrPayment.testPayment()" style="
                            background-color: #ffc107;
                            color: #212529;
                            border: none;
                            padding: 10px 20px;
                            border-radius: 5px;
                            cursor: pointer;
                            font-size: 14px;
                            margin-right: 10px;
                        ">🧪 Test Payment</button>
                        ` : ''}
                        <button onclick="window.khqrPayment.cancelPayment()" style="
                            background-color: #6c757d;
                            color: white;
                            border: none;
                            padding: 10px 20px;
                            border-radius: 5px;
                            cursor: pointer;
                            font-size: 14px;
                        ">Cancel Payment</button>
                    </div>

                    <div style="margin-top: 15px; font-size: 12px; color: #666;">
                        <strong>Compatible Apps:</strong><br>
                        ACLEDA Mobile • ABA Mobile • Wing Bank • Pi Pay
                    </div>
                </div>
            </div>
        `;

        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalHTML);

        // Generate QR code
        this.generateQRCode(paymentData.qr_data);
    }

    /**
     * Generate QR code using QRCode.js library
     */
    generateQRCode(qrData) {
        const container = document.getElementById('khqr-qr-container');
        if (!container) return;

        // Clear container
        container.innerHTML = '';

        // Check if QRCode library is available
        if (typeof QRCode !== 'undefined') {
            // Use QRCode.js library if available
            new QRCode(container, {
                text: qrData,
                width: 200,
                height: 200,
                colorDark: "#000000",
                colorLight: "#ffffff",
                correctLevel: QRCode.CorrectLevel.M
            });
        } else {
            // Fallback: Use online QR code generator
            const qrImg = document.createElement('img');
            qrImg.src = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(qrData)}`;
            qrImg.style.width = '200px';
            qrImg.style.height = '200px';
            qrImg.style.border = '1px solid #ddd';
            container.appendChild(qrImg);
        }

        // Add scan instruction
        const instruction = document.createElement('div');
        instruction.style.marginTop = '10px';
        instruction.style.fontSize = '14px';
        instruction.style.color = '#666';
        instruction.innerHTML = '📱 Scan QR code to pay';
        container.appendChild(instruction);
    }

    /**
     * Start checking payment status
     */
    startStatusChecking() {
        if (!this.currentPayment) return;

        console.log('🔍 Starting payment status checking...');

        this.statusCheckInterval = setInterval(async () => {
            await this.checkPaymentStatus();
        }, 3000); // Check every 3 seconds
    }

    /**
     * Check payment status
     */
    async checkPaymentStatus() {
        if (!this.currentPayment) return;

        try {
            console.log(`🔍 Checking payment status for: ${this.currentPayment.payment_id}`);
            
            const response = await fetch(`/api/khqr/check-payment/${this.currentPayment.payment_id}`);
            const result = await response.json();

            if (!result.success) {
                console.error('❌ Error checking payment status:', result.error);
                return;
            }

            console.log('📊 Payment status:', result.status);

            if (result.status === 'completed') {
                console.log('🎉 Payment completed!');
                this.onPaymentSuccess(result);
            } else if (result.status === 'failed') {
                console.log('❌ Payment failed');
                this.onPaymentError('Payment failed');
            } else if (result.status === 'expired') {
                console.log('⏰ Payment expired');
                this.onPaymentError('Payment session expired');
            }
            // If status is 'pending', continue checking

        } catch (error) {
            console.error('❌ Error checking payment status:', error);
        }
    }

    /**
     * Handle successful payment
     */
    onPaymentSuccess(result) {
        console.log('🎉 Payment success handler called with result:', result);

        // Stop status checking
        if (this.statusCheckInterval) {
            clearInterval(this.statusCheckInterval);
            this.statusCheckInterval = null;
        }

        // Update status display (if still visible)
        const statusElement = document.getElementById('khqr-status');
        if (statusElement) {
            statusElement.style.backgroundColor = '#d4edda';
            statusElement.style.borderColor = '#c3e6cb';
            statusElement.style.color = '#155724';
            statusElement.innerHTML = '✅ Payment Successful!';
        }

        // Confirm payment and clear cart if we have an order ID
        if (result.order_id) {
            this.confirmPaymentAndClearCart(result.order_id);
        }

        // Close the QR modal immediately and show a popup
        this.closeModal();
        this.showSuccessPopup(result);

        // Call success callback
        if (this.successCallback) {
            console.log('📞 Calling success callback with result:', result);
            this.successCallback(result);
        } else {
            console.log('⚠️ No success callback defined');
        }

        // Reset current payment
        this.currentPayment = null;
        
        // Clear pending payment data from localStorage
        localStorage.removeItem('khqr_pending_payment');
    }

    /**
     * Show success popup (uses SweetAlert if available, otherwise a built-in fallback)
     */
    showSuccessPopup(result) {
        const hasInvoice = !!(result && (result.invoice_url || result.order_id));

        // Prefer SweetAlert if present
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                title: 'Payment Successful',
                text: 'Thank you! Your KHQR payment was received.',
                icon: 'success',
                confirmButtonText: hasInvoice ? 'View Invoice' : 'OK',
                confirmButtonColor: '#28a745',
                showCancelButton: hasInvoice,
                cancelButtonText: 'Close',
                cancelButtonColor: '#6c757d'
            }).then((res) => {
                if (res.isConfirmed && hasInvoice) {
                    const invoiceUrl = result.invoice_url || `/invoice/${result.order_id}`;
                    window.location.href = invoiceUrl;
                }
            });
            return;
        }

        // Fallback lightweight popup
        const overlay = document.createElement('div');
        overlay.style.position = 'fixed';
        overlay.style.inset = '0';
        overlay.style.background = 'rgba(0,0,0,0.4)';
        overlay.style.display = 'flex';
        overlay.style.alignItems = 'center';
        overlay.style.justifyContent = 'center';
        overlay.style.zIndex = '10000';

        const box = document.createElement('div');
        box.style.background = '#fff';
        box.style.borderRadius = '12px';
        box.style.padding = '22px 20px';
        box.style.width = 'min(90%, 380px)';
        box.style.textAlign = 'center';
        box.style.boxShadow = '0 10px 30px rgba(0,0,0,0.25)';

        const icon = document.createElement('div');
        icon.style.width = '72px';
        icon.style.height = '72px';
        icon.style.margin = '0 auto 12px';
        icon.style.borderRadius = '50%';
        icon.style.background = '#10b981';
        icon.style.display = 'flex';
        icon.style.alignItems = 'center';
        icon.style.justifyContent = 'center';
        icon.style.color = '#fff';
        icon.style.fontSize = '36px';
        icon.textContent = '✓';

        const title = document.createElement('div');
        title.textContent = 'Payment Successful';
        title.style.fontSize = '18px';
        title.style.fontWeight = '700';
        title.style.color = '#111827';
        title.style.margin = '0 0 6px 0';

        const text = document.createElement('div');
        text.textContent = 'Thank you! Your KHQR payment was received.';
        text.style.fontSize = '14px';
        text.style.color = '#4b5563';
        text.style.margin = '0 0 16px 0';

        const btn = document.createElement('button');
        btn.textContent = hasInvoice ? 'View Invoice' : 'Close';
        btn.style.background = '#22c55e';
        btn.style.color = '#fff';
        btn.style.border = 'none';
        btn.style.padding = '10px 16px';
        btn.style.borderRadius = '8px';
        btn.style.cursor = 'pointer';
        btn.onclick = () => {
            if (hasInvoice) {
                const url = result.invoice_url || `/invoice/${result.order_id}`;
                window.location.href = url;
            }
            overlay.remove();
        };

        box.appendChild(icon);
        box.appendChild(title);
        box.appendChild(text);
        box.appendChild(btn);
        overlay.appendChild(box);
        document.body.appendChild(overlay);

        // Auto-dismiss after 2.5s if no invoice link
        if (!hasInvoice) {
            setTimeout(() => overlay.remove(), 2500);
        }
    }

    /**
     * Handle payment error
     */
    onPaymentError(errorMessage) {
        // Stop status checking
        if (this.statusCheckInterval) {
            clearInterval(this.statusCheckInterval);
            this.statusCheckInterval = null;
        }

        // Update status display
        const statusElement = document.getElementById('khqr-status');
        if (statusElement) {
            statusElement.style.backgroundColor = '#f8d7da';
            statusElement.style.borderColor = '#f5c6cb';
            statusElement.style.color = '#721c24';
            statusElement.innerHTML = `❌ ${errorMessage}`;
        }

        // Handle expired payments with popup similar to cancellation
        if (errorMessage.includes('expired') || errorMessage.includes('timeout')) {
            this.handlePaymentExpired();
        } else {
            // Call error callback for other errors
            if (this.errorCallback) {
                this.errorCallback(errorMessage);
            }
        }

        console.error('❌ KHQR Payment error:', errorMessage);
    }

    /**
     * Handle payment expired/timeout with popup similar to cancellation
     */
    handlePaymentExpired() {
        // Close the payment modal first
        this.closeModal();
        
        // Show popup similar to cash/delivery with invoice option
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                title: 'Payment Timeout',
                text: 'Your payment session has expired. The order is now pending and you can pay later using the same QR code.',
                icon: 'warning',
                showCancelButton: true,
                confirmButtonText: 'View Invoice',
                confirmButtonColor: '#28a745',
                cancelButtonText: 'Continue Shopping',
                cancelButtonColor: '#6c757d'
            }).then((result_modal) => {
                if (result_modal.isConfirmed && this.currentPayment && this.currentPayment.order_id) {
                    // Redirect to invoice page for the pending order
                    console.log('Redirecting to invoice:', `/invoice/${this.currentPayment.order_id}`);
                    window.location.href = `/invoice/${this.currentPayment.order_id}`;
                } else {
                    // Continue shopping - redirect to homepage
                    window.location.href = '/';
                }
            });
        }
        
        // Reset payment state
        this.currentPayment = null;
    }

    /**
     * Test payment - simulate successful payment
     */
    async testPayment() {
        console.log('🧪 Testing KHQR payment...');

        try {
            // Stop any existing status checking
            if (this.statusCheckInterval) {
                clearInterval(this.statusCheckInterval);
                this.statusCheckInterval = null;
            }

            // Create test order via API
            const response = await fetch('/api/khqr/test-order', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    amount: this.currentPayment ? this.currentPayment.amount : 0.01
                })
            });

            const result = await response.json();
            console.log('🧪 Test order API response:', result);

            if (result.success) {
                // Simulate successful payment
                const testResult = {
                    success: true,
                    status: 'completed',
                    payment_id: this.currentPayment ? this.currentPayment.payment_id : 'TEST_' + Date.now(),
                    order_id: result.order_id,
                    amount: result.amount,
                    currency: result.currency,
                    reference_id: result.reference_id,
                    completed_at: new Date().toISOString(),
                    invoice_url: result.invoice_url
                };

                console.log('🧪 Simulating payment success with result:', testResult);
                
                // Confirm payment and clear cart for test payment
                await this.confirmPaymentAndClearCart(result.order_id);
                
                this.onPaymentSuccess(testResult);
            } else {
                console.error('❌ Test order creation failed:', result.error);
                this.onPaymentError(`Test failed: ${result.error}`);
            }

        } catch (error) {
            console.error('❌ Error in test payment:', error);
            this.onPaymentError(`Test error: ${error.message}`);
        }
    }

    /**
     * Cancel the current payment
     */
    async cancelPayment() {
        try {
            console.log('❌ Payment cancelled by user');
            
            // Stop status checking
            if (this.statusCheckInterval) {
                clearInterval(this.statusCheckInterval);
                this.statusCheckInterval = null;
            }

            // If we have a payment session, call the cancellation API
            if (this.currentPayment && this.currentPayment.session_id) {
                try {
                    console.log('🔄 Calling payment cancellation API...');
                    const response = await fetch(`/api/payment/cancel/${this.currentPayment.session_id}`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        }
                    });

                    const result = await response.json();
                    if (result.success) {
                        console.log('✅ Payment cancelled successfully, cart items restored');
                        
                        // Update cart display if the function exists
                        if (typeof updateCart === 'function') {
                            updateCart();
                        }
                        
                        // Show popup similar to cash/delivery with invoice option
                        if (typeof Swal !== 'undefined') {
                            Swal.fire({
                                title: 'Payment Cancelled',
                                text: 'Your payment has been cancelled. The order is now pending and you can pay later using the same QR code.',
                                icon: 'info',
                                showCancelButton: true,
                                confirmButtonText: 'View Invoice',
                                confirmButtonColor: '#28a745',
                                cancelButtonText: 'Continue Shopping',
                                cancelButtonColor: '#6c757d'
                            }).then((result_modal) => {
                                if (result_modal.isConfirmed && result.order_id) {
                                    // Redirect to invoice page for the pending order
                                    console.log('Redirecting to invoice:', `/invoice/${result.order_id}`);
                                    window.location.href = `/invoice/${result.order_id}`;
                                } else {
                                    // Continue shopping - redirect to homepage
                                    window.location.href = '/';
                                }
                            });
                        }
                    } else {
                        console.warn('⚠️ Payment cancellation API returned error:', result.error);
                    }
                } catch (apiError) {
                    console.error('❌ Error calling payment cancellation API:', apiError);
                }
            }
            
            // Reset payment state
            this.currentPayment = null;
            
            // Close modal
            this.closeModal();
            
            console.log('✅ Payment cancelled, cart items preserved');
            
        } catch (error) {
            console.error('❌ Error cancelling payment:', error);
            this.closeModal();
        }
    }

    /**
     * Confirm payment and clear cart
     */
    async confirmPaymentAndClearCart(orderId) {
        try {
            console.log('🎉 Confirming payment and clearing cart for order:', orderId);
            
            const response = await fetch('/api/khqr/confirm-payment', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    order_id: orderId
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            if (!result.success) {
                throw new Error(result.error || 'Failed to confirm payment');
            }

            console.log('✅ Payment confirmed and cart cleared successfully');
            
            // Update cart display if the function exists
            if (typeof updateCart === 'function') {
                updateCart();
            }

            // Show success message only if not suppressed
            if (!this.suppressOwnModal && typeof Swal !== 'undefined') {
                Swal.fire({
                    title: 'Payment Confirmed',
                    text: 'Your payment has been confirmed and cart has been cleared.',
                    icon: 'success',
                    confirmButtonText: 'OK'
                });
            }

        } catch (error) {
            console.error('❌ Error confirming payment and clearing cart:', error);
            // Show error message to user
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    title: 'Error',
                    text: 'Failed to confirm payment. Please contact support.',
                    icon: 'error',
                    confirmButtonText: 'OK'
                });
            }
        }
    }

    /**
     * Close payment modal
     */
    closeModal() {
        const modal = document.getElementById('khqr-payment-modal');
        if (modal) {
            modal.remove();
        }
        
        // Clear pending payment data from localStorage when modal is closed
        localStorage.removeItem('khqr_pending_payment');
    }
}

// Create global instance
window.khqrPayment = new KHQRPayment();

console.log('🚀 KHQR Payment JavaScript loaded successfully');
