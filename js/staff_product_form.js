// Product Form JavaScript
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('product-form');
    const mode = '{{ mode }}' || 'create'; // 'create' or 'edit'
    
    // Debug: Log the mode
    console.log('Initial mode:', mode);
    
    // Form validation
    function validateForm() {
        let isValid = true;
        
        // Clear previous errors
        document.querySelectorAll('.error-message').forEach(error => {
            error.classList.remove('show');
        });
        document.querySelectorAll('.form-input, .form-textarea, .form-select').forEach(input => {
            input.classList.remove('error');
        });
        
        // Required fields validation
        const requiredFields = [
            { id: 'product-name', message: 'Product name is required' },
            { id: 'product-description', message: 'Description is required' },
            { id: 'product-price', message: 'Selling price is required' },
            { id: 'product-stock', message: 'Stock quantity is required' },
            { id: 'product-category', message: 'Category is required' }
        ];
        
        requiredFields.forEach(field => {
            const input = document.getElementById(field.id);
            const errorElement = document.getElementById(field.id.replace('product-', '') + '-error');
            
            if (!input.value.trim()) {
                isValid = false;
                input.classList.add('error');
                if (errorElement) {
                    errorElement.textContent = field.message;
                    errorElement.classList.add('show');
                }
            }
        });
        
        // Price validation
        const priceInput = document.getElementById('product-price');
        if (priceInput.value && parseFloat(priceInput.value) < 0) {
            isValid = false;
            priceInput.classList.add('error');
            const errorElement = document.getElementById('price-error');
            if (errorElement) {
                errorElement.textContent = 'Price must be greater than or equal to 0';
                errorElement.classList.add('show');
            }
        }
        
        // Stock validation
        const stockInput = document.getElementById('product-stock');
        if (stockInput.value && parseInt(stockInput.value) < 0) {
            isValid = false;
            stockInput.classList.add('error');
            const errorElement = document.getElementById('stock-error');
            if (errorElement) {
                errorElement.textContent = 'Stock must be greater than or equal to 0';
                errorElement.classList.add('show');
            }
        }
        
        return isValid;
    }
    
    // Real-time validation
    function setupRealTimeValidation() {
        const inputs = document.querySelectorAll('.form-input, .form-textarea, .form-select');
        
        inputs.forEach(input => {
            input.addEventListener('blur', function() {
                validateField(this);
            });
            
            input.addEventListener('input', function() {
                // Remove error state on input
                this.classList.remove('error');
                const errorElement = document.getElementById(this.id.replace('product-', '') + '-error');
                if (errorElement) {
                    errorElement.classList.remove('show');
                }
            });
        });
    }
    
    function validateField(input) {
        const fieldId = input.id;
        const errorElement = document.getElementById(fieldId.replace('product-', '') + '-error');
        
        // Required field validation
        if (input.hasAttribute('required') && !input.value.trim()) {
            input.classList.add('error');
            if (errorElement) {
                errorElement.textContent = `${input.previousElementSibling.textContent.replace(' *', '')} is required`;
                errorElement.classList.add('show');
            }
            return false;
        }
        
        // Price validation
        if (fieldId === 'product-price' && input.value) {
            const price = parseFloat(input.value);
            if (isNaN(price) || price < 0) {
                input.classList.add('error');
                if (errorElement) {
                    errorElement.textContent = 'Please enter a valid price (≥ 0)';
                    errorElement.classList.add('show');
                }
                return false;
            }
        }
        
        // Stock validation
        if (fieldId === 'product-stock' && input.value) {
            const stock = parseInt(input.value);
            if (isNaN(stock) || stock < 0) {
                input.classList.add('error');
                if (errorElement) {
                    errorElement.textContent = 'Please enter a valid stock quantity (≥ 0)';
                    errorElement.classList.add('show');
                }
                return false;
            }
        }
        
        // Success state
        input.classList.remove('error');
        if (errorElement) {
            errorElement.classList.remove('show');
        }
        return true;
    }
    
    // Image preview functionality for multiple files
    function setupImagePreview() {
        const imageInput = document.querySelector('input[name="product_images"]');
        const previewContainer = document.getElementById('image-preview-container');
        
        if (imageInput) {
            imageInput.addEventListener('change', function(e) {
                const files = Array.from(e.target.files);
                
                // Clear existing previews (except for edit mode current images)
                const existingPreviews = previewContainer.querySelectorAll('.preview-item:not([data-current])');
                existingPreviews.forEach(preview => preview.remove());
                
                // Limit to 3 files
                const filesToProcess = files.slice(0, 3);
                
                filesToProcess.forEach((file, index) => {
                    if (file.type.startsWith('image/')) {
                        const reader = new FileReader();
                        reader.onload = function(e) {
                            const previewItem = document.createElement('div');
                            previewItem.className = 'preview-item';
                            previewItem.innerHTML = `
                                <img src="${e.target.result}" alt="Preview ${index + 1}">
                                <span class="preview-label">Image ${index + 1}</span>
                                <button type="button" class="remove-btn" onclick="removePreview(this)">×</button>
                            `;
                            previewContainer.appendChild(previewItem);
                        };
                        reader.readAsDataURL(file);
                    }
                });
                
                // Show warning if more than 3 files selected
                if (files.length > 3) {
                    showMessage('Only the first 3 images will be uploaded.', 'warning');
                }
            });
            
            // Drag and drop functionality
            const uploadLabel = document.querySelector('.image-upload-label');
            
            uploadLabel.addEventListener('dragover', function(e) {
                e.preventDefault();
                uploadLabel.classList.add('dragover');
            });
            
            uploadLabel.addEventListener('dragleave', function(e) {
                e.preventDefault();
                uploadLabel.classList.remove('dragover');
            });
            
            uploadLabel.addEventListener('drop', function(e) {
                e.preventDefault();
                uploadLabel.classList.remove('dragover');
                
                const files = Array.from(e.dataTransfer.files);
                const imageFiles = files.filter(file => file.type.startsWith('image/'));
                
                if (imageFiles.length > 0) {
                    // Create a new FileList with the dropped files
                    const dt = new DataTransfer();
                    imageFiles.forEach(file => dt.items.add(file));
                    imageInput.files = dt.files;
                    
                    // Trigger change event
                    imageInput.dispatchEvent(new Event('change'));
                }
            });
        }
    }
    
    // Remove preview function
    window.removePreview = function(button) {
        const previewItem = button.closest('.preview-item');
        if (previewItem) {
            previewItem.remove();
        }
    };
    
    // Form submission
    function setupFormSubmission() {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            console.log('Form submitted, validating...');
            
            if (!validateForm()) {
                console.log('Form validation failed');
                showNotification('Please correct the errors in the form.', 'error');
                return;
            }
            
            console.log('Form validation passed, proceeding with submission...');
            
            const submitBtn = form.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            
            // Show loading state
            submitBtn.classList.add('loading');
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
            submitBtn.disabled = true;
            
            try {
                const formData = new FormData(form);
                
                // Handle multiple image files
                const imageInput = document.querySelector('input[name="product_images"]');
                if (imageInput && imageInput.files.length > 0) {
                    const files = Array.from(imageInput.files);
                    const maxFiles = Math.min(files.length, 3); // Limit to 3 files
                    
                    // Add each image file with proper names that match the API
                    for (let i = 0; i < maxFiles; i++) {
                        const file = files[i];
                        if (i === 0) {
                            formData.append('photo', file);
                        } else if (i === 1) {
                            formData.append('photo_back', file);
                        } else if (i === 2) {
                            formData.append('photo_left_rear', file);
                        }
                    }
                }
                
                const productIdElement = document.getElementById('product-id');
                const productId = productIdElement ? productIdElement.value : null;
                
                // Determine mode more robustly
                const actualMode = productIdElement ? 'edit' : 'create';
                
                // Debug: Log mode and productId
                console.log('Template mode:', mode);
                console.log('Actual mode:', actualMode);
                console.log('ProductId:', productId);
                
                const url = actualMode === 'create' 
                    ? '/api/staff/products/create' 
                    : `/staff/inventory/${productId}/update`;
                
                console.log('Submitting to URL:', url);
                
                const method = 'POST';
                
                const response = await fetch(url, {
                    method: method,
                    body: formData,
                    credentials: 'same-origin'
                });
                
                // Debug: Log response details
                console.log('Response status:', response.status);
                console.log('Response headers:', response.headers);
                
                const responseText = await response.text();
                console.log('Response text:', responseText);
                
                let result;
                try {
                    result = JSON.parse(responseText);
                } catch (e) {
                    console.error('Failed to parse JSON:', e);
                    console.error('Response was:', responseText);
                    showNotification('Server returned invalid response. Please check console for details.', 'error');
                    return;
                }
                
                if (result.success) {
                    // Debug: Log the result
                    console.log('Success result:', result);
                    
                    // Show success message
                    showNotification('Product ' + (actualMode === 'create' ? 'created' : 'updated') + ' successfully!', 'success');
                    
                    // Redirect to product details or inventory
                    setTimeout(() => {
                        if (actualMode === 'create') {
                            // For create mode, redirect to inventory list
                            console.log('Redirecting to inventory list...');
                            window.location.href = '/auth/staff/inventory';
                        } else {
                            // For edit mode, redirect to product details
                            console.log('Redirecting to product details...');
                            window.location.href = `/staff/inventory/${productId}`;
                        }
                    }, 1500);
                } else {
                    showNotification('Error: ' + (result.error || 'Something went wrong'), 'error');
                }
            } catch (error) {
                console.error('Form submission error:', error);
                showNotification('Error: Failed to ' + (mode === 'create' ? 'create' : 'update') + ' product', 'error');
            } finally {
                // Reset button state
                submitBtn.classList.remove('loading');
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            }
        });
    }
    
    // Notification system
    function showNotification(message, type = 'info') {
        // Remove existing notifications
        const existingNotifications = document.querySelectorAll('.notification');
        existingNotifications.forEach(notification => notification.remove());
        
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
                <span>${message}</span>
            </div>
        `;
        
        // Add styles
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#d4edda' : type === 'error' ? '#f8d7da' : '#d1ecf1'};
            color: ${type === 'success' ? '#155724' : type === 'error' ? '#721c24' : '#0c5460'};
            border: 1px solid ${type === 'success' ? '#c3e6cb' : type === 'error' ? '#f5c6cb' : '#bee5eb'};
            border-radius: 8px;
            padding: 15px 20px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 1000;
            max-width: 400px;
            animation: slideIn 0.3s ease;
        `;
        
        document.body.appendChild(notification);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }
    
    // Initialize everything
    setupRealTimeValidation();
    setupImagePreview();
    setupFormSubmission();
    
    // Add CSS for animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
        
        .notification-content {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .preview-overlay {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,123,255,0.8);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.9rem;
        }
    `;
    document.head.appendChild(style);
});
