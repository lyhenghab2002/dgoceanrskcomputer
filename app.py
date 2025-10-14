from flask import Flask, jsonify, request, redirect, url_for, render_template, session, flash, get_flashed_messages, make_response
from auth import auth_bp

app = Flask(__name__)

# Auth blueprint will be registered later with /auth prefix

from flask_mysqldb import MySQL
from config import Config
from datetime import datetime, timedelta
from models import Product, Customer, Order, Supplier, Report, db, Category, PreOrder, Notification, generate_slug, PreOrderPayment, get_db, Color, Warranty
import os
import json
import hashlib
from werkzeug.utils import secure_filename
from utils.bakong_payment import BakongQRGenerator, PaymentSession
from utils.screenshot_fraud_detector import screenshot_detector
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
import base64


# QR Code Cache for faster generation
qr_cache = {}

def pregenerate_common_qr_codes():
    """Pre-generate QR codes for common amounts to improve speed"""
    import qrcode
    import io
    import base64
    
    common_amounts = [1, 5, 10, 20, 50, 100, 200, 500, 1000]
    currency = "USD"
    description = "Payment"
    
    for amount in common_amounts:
        cache_key = f"{amount}_{currency}_{description}"
        if cache_key not in qr_cache:
            # Generate QR code with optimized parameters
            qr_data = f"KHQR:amount={amount}:currency={currency}:desc={description}"
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=8,
                border=2,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            img_buffer = io.BytesIO()
            qr_img.save(img_buffer, format='PNG', optimize=True)
            img_buffer.seek(0)
            qr_base64 = base64.b64encode(img_buffer.getvalue()).decode()
            
            qr_cache[cache_key] = qr_base64
    
    app.logger.info(f"Pre-generated {len(common_amounts)} common QR codes")

# Initialize extensions without circular imports
mysql = MySQL()

def create_app():
    app = Flask(__name__, static_folder='static')
    app.config.from_object(Config)
    app.config['UPLOAD_FOLDER'] = 'static/uploads/products'
    app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
    app.secret_key = Config.SECRET_KEY
    
    # Configure logging
    import logging
    logging.basicConfig(level=logging.INFO)
    app.logger = logging.getLogger(__name__)
    
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize extensions with app
    mysql.init_app(app)
    from models import db
    db.init_app(app)
    
    # Pre-generate common QR codes for faster payment processing
    try:
        pregenerate_common_qr_codes()
    except Exception as e:
        app.logger.warning(f"Could not pre-generate QR codes: {e}")

    def allowed_file(filename):
        app.logger.info(f"allowed_file called with: {filename}, type: {type(filename)}")
        if not filename:
            return False
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

    # Template filters
    @app.template_filter('slugify')
    def slugify_filter(text):
        """Template filter to generate URL slugs"""
        return generate_slug(text)

    # Public Routes
    @app.route('/login')
    def login_redirect():
        return redirect(url_for('auth.login'))
    
    @app.route('/admin')
    def admin_login():
        # Check if user is already logged in as staff/admin
        if session.get('user_id') and session.get('role') in ['staff', 'admin', 'super_admin', 'manager', 'sales', 'clerk', 'cashier']:
            # Redirect to appropriate staff dashboard based on role
            if session.get('role') in ['admin', 'super_admin']:
                return redirect(url_for('auth.staff_dashboard'))
            else:
                return redirect(url_for('auth.staff_dashboard'))
        
        return render_template('admin_login.html')
    
    @app.route('/admin/login', methods=['POST'])
    def admin_login_post():
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash('Username and password are required', 'error')
            return redirect(url_for('admin_login'))
        
        # Simple rate limiting - check if too many failed attempts
        failed_attempts = session.get('admin_login_failed', 0)
        if failed_attempts >= 5:
            flash('Too many failed login attempts. Please wait before trying again.', 'error')
            return redirect(url_for('admin_login'))
        
        try:
            from models import User
            user = User.get_by_username(username)
            
            if not user:
                # Increment failed attempts
                session['admin_login_failed'] = failed_attempts + 1
                flash('Invalid username or password', 'error')
                return redirect(url_for('admin_login'))
            
            # Check if user has staff/admin role
            if user.get('role') not in ['staff', 'admin', 'super_admin', 'manager', 'sales', 'clerk', 'cashier']:
                # Increment failed attempts
                session['admin_login_failed'] = failed_attempts + 1
                flash('Access denied. Insufficient privileges.', 'error')
                return redirect(url_for('admin_login'))
            
            # Check if user is active
            if not user.get('is_active', True):
                # Increment failed attempts
                session['admin_login_failed'] = failed_attempts + 1
                flash('Account is deactivated. Please contact administrator.', 'error')
                return redirect(url_for('admin_login'))
            
                        # Verify password
            from werkzeug.security import check_password_hash
            if not check_password_hash(user.get('password'), password):
                # Check if user is super admin
                if user.get('role') == 'super_admin':
                    # Super admin gets link to reset their own password
                    session['admin_login_failed'] = failed_attempts + 1
                    # Store super admin info for password reset
                    session['super_admin_reset_user_id'] = user.get('id')
                    session['super_admin_reset_username'] = user.get('username')
                    flash('Invalid password. Click "Reset Your Password" below to change your password.', 'super-admin-reset')
                    return redirect(url_for('admin_login'))
                else:
                    # Regular staff users need to contact super admin
                    session['admin_login_failed'] = failed_attempts + 1
                    flash('Invalid password. Contact Super Admin for assistance.', 'error')
                    return redirect(url_for('admin_login'))
            
            # Reset failed attempts on successful login
            session.pop('admin_login_failed', None)
            
            # Check if user needs to change password
            if user.get('force_password_change'):
                # Store user info in temporary session variables for password change
                session['temp_user_id'] = user.get('id')
                session['temp_username'] = user.get('username')
                app.logger.info(f"User {username} needs to change password, redirecting to force password change")
                return redirect(url_for('auth.force_password_change'))
            
            # Set session
            session['user_id'] = user.get('id')
            session['username'] = user.get('username')
            session['role'] = user.get('role')
            session['full_name'] = user.get('full_name', user.get('username'))  # Fallback to username if no full_name
            
            # Update last login time
            User.update_last_login(user.get('id'))
            
            # Log successful login
            app.logger.info(f"Admin login successful for user: {username}, role: {user.get('role')}")
            
            # Redirect to appropriate dashboard
            return redirect(url_for('auth.staff_dashboard'))
            
        except Exception as e:
            app.logger.error(f"Admin login error: {str(e)}")
            flash('An error occurred during login. Please try again.', 'error')
            return redirect(url_for('admin_login'))
    
    @app.route('/admin/logout')
    def admin_logout():
        # Clear admin session
        session.pop('user_id', None)
        session.pop('username', None)
        session.pop('role', None)
        session.pop('full_name', None)
        
        flash('You have been logged out successfully.', 'success')
        return redirect(url_for('admin_login'))
    
    @app.route('/register')
    def register():
        products = Product.get_all()
        # Clear any existing flash messages to prevent duplicates
        get_flashed_messages()
        return render_template('Register.html', products=products)
    
    @app.route('/auth/register', methods=['POST'])
    def register_customer():
        """Register a new customer - OTP verification is optional"""
        # Clear any existing flash messages
        get_flashed_messages()
        app.logger.info("Starting registration process...")
        
        try:
            data = request.form
            first_name = data.get('first_name', '').strip()
            last_name = data.get('last_name', '').strip()
            email = data.get('email', '').strip().lower()
            password = data.get('password', '')
            phone = data.get('phone', '').strip()
            address = data.get('address', '').strip()
            
            app.logger.info(f"Registration attempt: {first_name} {last_name} - {email}")
            
            # Basic validation
            if not all([first_name, last_name, email, password]):
                app.logger.warning("Registration failed: Missing required fields")
                flash('Please fill in all required fields', 'error')
                return redirect(url_for('register'))
            
            if not email or '@' not in email:
                app.logger.warning("Registration failed: Invalid email format")
                flash('Please enter a valid email address', 'error')
                return redirect(url_for('register'))
            
            if len(password) < 6:
                app.logger.warning("Registration failed: Password too short")
                flash('Password must be at least 6 characters long', 'error')
                return redirect(url_for('register'))
            
            from models import Customer
            
            # Check if email already exists
            existing_customer = Customer.get_by_email(email)
            if existing_customer:
                app.logger.warning(f"Registration failed: Email {email} already exists")
                flash('An account with this email already exists', 'error')
                return redirect(url_for('register'))
            
            # Create customer account (OTP verification not required)
            app.logger.info("Attempting to create customer account...")
            customer_id = Customer.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=password,
                phone=phone,
                address=address
            )
            app.logger.info(f"Customer.create returned: {customer_id}")
            
            if customer_id:
                # Set OTP as not enabled initially (user can verify later) - do this separately
                try:
                    conn = get_db()
                    cur = conn.cursor()
                    cur.execute("""
                        UPDATE customers 
                        SET otp_enabled = FALSE 
                        WHERE id = %s
                    """, (customer_id,))
                    conn.commit()
                    cur.close()
                    conn.close()
                except Exception as db_error:
                    app.logger.error(f"Database error after account creation: {str(db_error)}")
                    # Continue even if OTP setting fails
                
                app.logger.info("Account created successfully, redirecting to login...")
                return redirect(url_for('auth.login') + '?registered=success')
            else:
                flash('Failed to create account. Please try again.', 'error')
                return redirect(url_for('register'))
                
        except Exception as e:
            app.logger.error(f"Registration error: {str(e)}")
            app.logger.info("Setting error message...")
            flash('An error occurred during registration. Please try again.', 'error')
            return redirect(url_for('register'))
    
    @app.route('/verify-email')
    def verify_email_page():
        """Show email verification page"""
        if 'username' not in session or session.get('role') != 'customer':
            flash('Please log in to verify your email', 'error')
            return redirect(url_for('login'))
        return render_template('verify_email.html')
    
    @app.route('/api/send-verification-otp', methods=['POST'])
    def send_verification_otp():
        """Send OTP for email verification"""
        if 'username' not in session or session.get('role') != 'customer':
            return jsonify({'success': False, 'error': 'Please log in'}), 401
        
        try:
            customer_id = session.get('user_id')
            if not customer_id:
                return jsonify({'success': False, 'error': 'Customer ID not found'}), 400
            
            from models import Customer
            customer = Customer.get_by_id(customer_id)
            if not customer:
                return jsonify({'success': False, 'error': 'Customer not found'}), 404
            
            # Check if already verified
            if customer.get('otp_enabled'):
                return jsonify({'success': False, 'error': 'Email already verified'}), 400
            
            # Generate and send OTP
            import random
            import string
            from datetime import datetime, timedelta
            
            otp_code = ''.join(random.choices(string.digits, k=6))
            expires_at = datetime.now() + timedelta(minutes=15)
            
            # Store OTP in database
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO customer_otp_verification 
                (customer_id, otp_code, email, expires_at) 
                VALUES (%s, %s, %s, %s)
            """, (customer_id, otp_code, customer['email'], expires_at))
            conn.commit()
            cur.close()
            
            # Send email using the email utility
            try:
                from utils.email_utils import EmailManager
                customer_name = f"{customer['first_name']} {customer['last_name']}"
                email_sent = EmailManager.send_registration_otp_email(
                    customer['email'], 
                    customer_name, 
                    otp_code
                )
                
                if email_sent:
                    app.logger.info(f"OTP email sent successfully to {customer['email']}")
                    return jsonify({
                        'success': True, 
                        'message': f'Verification code sent to {customer["email"]}'
                    })
                else:
                    app.logger.warning(f"Email sending failed, showing OTP in console: {otp_code}")
                    return jsonify({
                        'success': True, 
                        'message': f'Email service unavailable. Your code is: {otp_code}',
                        'otp_code': otp_code
                    })
            except Exception as email_error:
                app.logger.error(f"Email sending error: {str(email_error)}")
                app.logger.info(f"OTP for {customer['email']}: {otp_code}")
                return jsonify({
                    'success': True, 
                    'message': f'Email service unavailable. Your code is: {otp_code}',
                    'otp_code': otp_code
                })
            
        except Exception as e:
            app.logger.error(f"Error sending verification OTP: {str(e)}")
            return jsonify({'success': False, 'error': 'Failed to send verification code'}), 500
    
    @app.route('/api/verify-email-otp', methods=['POST'])
    def verify_email_otp():
        """Verify email with OTP code"""
        if 'username' not in session or session.get('role') != 'customer':
            return jsonify({'success': False, 'error': 'Please log in'}), 401
        
        try:
            data = request.get_json()
            otp_code = data.get('otp_code', '').strip()
            
            if not otp_code or len(otp_code) != 6:
                return jsonify({'success': False, 'error': 'Please enter a valid 6-digit code'}), 400
            
            customer_id = session.get('user_id')
            
            # Verify OTP
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                SELECT * FROM customer_otp_verification 
                WHERE customer_id = %s AND otp_code = %s AND used = FALSE AND expires_at > NOW()
                ORDER BY created_at DESC LIMIT 1
            """, (customer_id, otp_code))
            
            otp_record = cur.fetchone()
            
            if not otp_record:
                return jsonify({'success': False, 'error': 'Invalid or expired verification code'}), 400
            
            # Mark OTP as used
            cur.execute("""
                UPDATE customer_otp_verification 
                SET used = TRUE 
                WHERE id = %s
            """, (otp_record['id'],))
            
            # Enable OTP for customer
            cur.execute("""
                UPDATE customers 
                SET otp_enabled = TRUE 
                WHERE id = %s
            """, (customer_id,))
            
            conn.commit()
            cur.close()
            
            return jsonify({
                'success': True, 
                'message': 'Email verified successfully! Your account is now more secure.'
            })
            
        except Exception as e:
            app.logger.error(f"Error verifying OTP: {str(e)}")
            return jsonify({'success': False, 'error': 'Failed to verify code'}), 500
        
    @app.route('/')
    def show_dashboard():
        try:
            # Cache products for better performance
            products = Product.get_featured()
            return render_template('homepage.html', products=products)
        except Exception as e:
            # If database error, show a simple page
            return f"<h1>Computer Shop</h1><p>App is running but database connection failed: {str(e)}</p>"
    
    @app.route('/test')
    def test_route():
        return "<h1>Test Route Works!</h1><p>If you can see this, the app is running correctly.</p>"
    
    @app.route('/db-test')
    def db_test():
        try:
            # Test database connection with timeout
            import mysql.connector
            from config import Config
            
            conn = mysql.connector.connect(
                host=Config.MYSQL_HOST,
                user=Config.MYSQL_USER,
                password=Config.MYSQL_PASSWORD,
                database=Config.MYSQL_DB,
                port=Config.MYSQL_PORT,
                connection_timeout=10,  # 10 second timeout
                auth_plugin='mysql_native_password'
            )
            
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            return f"""
            <h1>Database Connection Test - SUCCESS!</h1>
            <p>✅ Connected to: {Config.MYSQL_HOST}</p>
            <p>✅ Database: {Config.MYSQL_DB}</p>
            <p>✅ User: {Config.MYSQL_USER}</p>
            <p>✅ Test query result: {result}</p>
            """
            
        except Exception as e:
            return f"""
            <h1>Database Connection Test - FAILED</h1>
            <p>❌ Error: {str(e)}</p>
            <p>Host: {Config.MYSQL_HOST}</p>
            <p>Port: {Config.MYSQL_PORT}</p>
            <p>Database: {Config.MYSQL_DB}</p>
            <p>User: {Config.MYSQL_USER}</p>
            """
        
    @app.route('/auth/staff/inventory')
    def staff_inventory():
        try:
            products = Product.get_all()
        except Exception as e:
            app.logger.error(f"Error fetching products: {e}")
            products = []
        brands = Product.get_distinct_brands()
        brand_filter = request.args.get('brand_filter')
        search_query = (request.args.get('q') or '').strip()
        category_filter = request.args.get('category_filter', '')

        if brand_filter and search_query:
            products = Product.get_by_brand(brand_filter)
        elif brand_filter:
            products = Product.get_by_brand(brand_filter)
        elif search_query:
            # Use search_query to filter products by name (not category)
            products = Product.search(search_query)
        else:
            products = Product.get_all()
        categories = Category.get_all()
        try:
            from models import Warranty
            warranties = Warranty.get_all()
        except Exception as e:
            app.logger.error(f"Error fetching warranties: {e}")
            warranties = []
        app.logger.info(f"Brands in app.py: {brands}")
        return render_template('staff_inventory.html', products=products, brands=brands, categories=categories, warranties=warranties)

    def get_product_sales_data(product_id):
        """Get sales overview data for a specific product"""
        try:
            conn = mysql.connection
            cur = conn.cursor()
            
            # Get total sold, total revenue, and average price
            cur.execute("""
                SELECT 
                    COALESCE(SUM(oi.quantity), 0) as total_sold,
                    COALESCE(SUM(oi.quantity * oi.price), 0) as total_revenue,
                    COALESCE(AVG(oi.price), 0) as average_price
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                WHERE oi.product_id = %s AND o.status = 'COMPLETED'
            """, (product_id,))
            totals = cur.fetchone()
            
            # Get this month's sales
            cur.execute("""
                SELECT COALESCE(SUM(oi.quantity), 0) as this_month_sold
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                WHERE oi.product_id = %s 
                AND o.status = 'COMPLETED'
                AND MONTH(o.order_date) = MONTH(CURRENT_DATE())
                AND YEAR(o.order_date) = YEAR(CURRENT_DATE())
            """, (product_id,))
            this_month = cur.fetchone()
            
            # Get last 30 days sales
            cur.execute("""
                SELECT COALESCE(SUM(oi.quantity), 0) as last_30_days_sold
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                WHERE oi.product_id = %s 
                AND o.status = 'COMPLETED'
                AND o.order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
            """, (product_id,))
            last_30_days = cur.fetchone()
            
            # Get best month
            cur.execute("""
                SELECT 
                    MONTH(o.order_date) as month,
                    YEAR(o.order_date) as year,
                    SUM(oi.quantity) as quantity_sold
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                WHERE oi.product_id = %s
                AND o.status = 'COMPLETED'
                GROUP BY YEAR(o.order_date), MONTH(o.order_date)
                ORDER BY quantity_sold DESC
                LIMIT 1
            """, (product_id,))
            best_month = cur.fetchone()
            
            cur.close()
            
            return {
                'total_sold': totals[0],
                'total_revenue': float(totals[1]),
                'average_price': float(totals[2]),
                'this_month_sold': this_month[0],
                'last_30_days_sold': last_30_days[0],
                'best_month': best_month
            }
        except Exception as e:
            app.logger.error(f"Error fetching sales data for product {product_id}: {e}")
            return {
                'total_sold': 0,
                'total_revenue': 0.0,
                'average_price': 0.0,
                'this_month_sold': 0,
                'last_30_days_sold': 0,
                'best_month': None
            }

    @app.route('/staff/inventory/<int:product_id>')
    def staff_product_details(product_id):
        """Staff product details page"""
        if 'user_id' not in session or session.get('role') not in ['staff', 'admin', 'super_admin']:
            return redirect(url_for('auth.login'))
        
        try:
            product = Product.get_by_id(product_id)
            if not product:
                return render_template('error.html', error='Product not found'), 404
            
            # Get sales data for this product
            sales_data = get_product_sales_data(product_id)
            
            return render_template('staff_product_details.html', 
                                 product=product, 
                                 sales_data=sales_data)
        except Exception as e:
            app.logger.error(f"Error fetching product {product_id}: {e}")
            return render_template('error.html', error='Internal server error'), 500

    @app.route('/products/all')
    def show_all_products():
        products = Product.get_all()
        return render_template('all_products.html', products=products)

    @app.route('/products/<int:product_id>', methods=['GET'])
    def view_product(product_id):
        if product_id <= 0:
            return render_template('error.html', error='Invalid product ID'), 400
        try:
            product = Product.get_by_id(product_id)
            if not product:
                return render_template('error.html', error='Product not found'), 404
            return render_template('product_detail.html', product=product)
        except Exception as e:
            app.logger.error(f"Error fetching product {product_id}: {e}")
            return render_template('error.html', error='Internal server error'), 500

    @app.route('/products/<string:product_slug>', methods=['GET'])
    def view_product_by_slug(product_slug):
        try:
            product = Product.get_by_slug(product_slug)
            if not product:
                return render_template('error.html', error='Product not found'), 404
            return render_template('product_detail.html', product=product)
        except Exception as e:
            app.logger.error(f"Error fetching product with slug {product_slug}: {e}")
            return render_template('error.html', error='Internal server error'), 500

    @app.route('/api/products/<int:product_id>', methods=['GET'])
    def api_get_product(product_id):
        try:
            product = Product.get_by_id(product_id)
            if not product:
                return jsonify({'success': False, 'error': 'Product not found'}), 404
            product_data = {
                'id': product['id'],
                'name': product['name'],
                'description': product['description'],
                'price': product['price'],
                'stock': product['stock'],
                'category_id': product['category_id'],
                'category_name': product.get('category_name'),
                'warranty_id': product.get('warranty_id'),
                'warranty_name': product.get('warranty_name'),
                'cpu': product.get('cpu'),
                'ram': product.get('ram'),
                'storage': product.get('storage'),
                'graphics': product.get('graphics'),
                'display': product.get('display'),
                'os': product.get('os'),
                'original_price': product.get('original_price'),
                'keyboard': product.get('keyboard'),
                'battery': product.get('battery'),
                'weight': product.get('weight'),
                'photo': product.get('photo'),
                'photo_front': product.get('photo'),
                'left_rear_view': product.get('left_rear_view'),
                'right_rear_view': product.get('right_rear_view'),
                'back_view': product.get('back_view'),
                'color': product.get('color')
            }
            return jsonify({'success': True, 'product': product_data})
        except Exception as e:
            app.logger.error(f"Error fetching product {product_id} via API: {e}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

    @app.route('/api/products/<int:product_id>/related', methods=['GET'])
    def api_get_related_products(product_id):
        """Get related products for a specific product"""
        try:
            limit = request.args.get('limit', 6, type=int)
            related_products = Product.get_related_products(product_id, limit)
            
            # Format the products for JSON response
            formatted_products = []
            for product in related_products:
                formatted_product = {
                    'id': product['id'],
                    'name': product['name'],
                    'price': float(product['price']),
                    'photo': product['photo'],
                    'description': product['description'],
                    'stock': product['stock'],
                    'category_name': product['category_name'],
                    'original_price': float(product['original_price']) if product['original_price'] else None,
                    'discount_percentage': float(product['discount_percentage']) if product['discount_percentage'] else 0,
                    'color': product['color']
                }
                formatted_products.append(formatted_product)
            
            return jsonify({'success': True, 'products': formatted_products})
        except Exception as e:
            app.logger.error(f"Error fetching related products for {product_id}: {e}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

    @app.route('/api/products/top-selling', methods=['GET'])
    def api_get_top_selling_products():
        """Get top selling products based on order history"""
        try:
            limit = request.args.get('limit', 5, type=int)
            
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            
            # Get top selling products based on order items quantity
            query = """
                SELECT p.id, p.name, p.price, p.photo, p.description, p.stock,
                       c.name as color, cat.name as category_name, p.original_price,
                       COALESCE(p.discount_percentage, 0) as discount_percentage,
                       COALESCE(SUM(oi.quantity), 0) as total_sold
                FROM products p
                LEFT JOIN colors c ON p.color_id = c.id
                LEFT JOIN categories cat ON p.category_id = cat.id
                LEFT JOIN order_items oi ON p.id = oi.product_id
                LEFT JOIN orders o ON oi.order_id = o.id
                WHERE (p.archived IS NULL OR p.archived = FALSE)
                AND p.stock > 0
                AND (o.status = 'COMPLETED' OR o.status IS NULL)
                GROUP BY p.id, p.name, p.price, p.photo, p.description, p.stock, c.name, cat.name, p.original_price, p.discount_percentage
                ORDER BY total_sold DESC, p.id DESC
                LIMIT %s
            """
            
            cur.execute(query, (limit,))
            products = cur.fetchall()
            cur.close()
            conn.close()
            
            # Format the products for JSON response
            formatted_products = []
            for i, product in enumerate(products, 1):
                formatted_product = {
                    'id': product['id'],
                    'name': product['name'],
                    'price': float(product['price']),
                    'photo': product['photo'],
                    'description': product['description'],
                    'stock': product['stock'],
                    'category_name': product['category_name'],
                    'original_price': float(product['original_price']) if product['original_price'] else None,
                    'discount_percentage': float(product['discount_percentage']) if product['discount_percentage'] else 0,
                    'rank': i,
                    'total_sold': int(product['total_sold'])
                }
                formatted_products.append(formatted_product)
            
            return jsonify({'success': True, 'products': formatted_products})
        except Exception as e:
            app.logger.error(f"Error fetching top selling products: {e}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

    def build_category_hierarchy(category_id):
        """Build dynamic category hierarchy for cascading dropdowns"""
        from models import get_db
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        
        try:
            # Get all categories with their hierarchy information
            cur.execute("""
                SELECT id, name, description, parent_id, sort_order
                FROM categories 
                WHERE is_active = TRUE
                ORDER BY parent_id, sort_order, name
            """)
            all_categories = cur.fetchall()
            
            # Build hierarchy tree
            hierarchy = {}
            for cat in all_categories:
                if cat['parent_id'] not in hierarchy:
                    hierarchy[cat['parent_id']] = []
                hierarchy[cat['parent_id']].append(cat)
            
            # Get all subcategories for the given category (including nested levels)
            def get_all_subcategories(parent_id, level=0):
                subcategories = []
                if parent_id in hierarchy:
                    for subcat in hierarchy[parent_id]:
                        subcat['level'] = level
                        subcategories.append(subcat)
                        # Recursively get sub-subcategories
                        subcategories.extend(get_all_subcategories(subcat['id'], level + 1))
                return subcategories
            
            return get_all_subcategories(category_id)
            
        finally:
            cur.close()
            conn.close()

    @app.route('/api/categories/<int:category_id>/subcategories', methods=['GET'])
    def api_get_subcategories(category_id):
        """API endpoint to get all subcategories for a parent category"""
        try:
            hierarchy = build_category_hierarchy(category_id)
            return jsonify({
                'success': True,
                'subcategories': hierarchy
            })
        except Exception as e:
            app.logger.error(f"Error fetching subcategories for category {category_id}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/navigation/categories', methods=['GET'])
    def api_get_navigation_categories():
        """API endpoint to get categories for navigation dropdowns"""
        try:
            from models import Category
            categories = Category.get_all_hierarchical()
            return jsonify({
                'success': True,
                'categories': categories
            })
        except Exception as e:
            app.logger.error(f"Error fetching navigation categories: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/products/category/<int:category_id>')
    def products_by_category(category_id):
        category = None
        products = []
        hierarchy = []
        
        try:
            categories = Category.get_all()
            category = next((c for c in categories if c['id'] == category_id), None)
            
            if category:
                # Build dynamic hierarchy for cascading dropdowns
                hierarchy = build_category_hierarchy(category_id)
                
                # Get all subcategory IDs (including nested levels)
                subcategory_ids = [cat['id'] for cat in hierarchy]
                
                # Always include the parent category ID in the search
                all_category_ids = [category_id] + subcategory_ids
                
                # Get filter parameters from URL
                min_price = request.args.get('min_price', type=float)
                max_price = request.args.get('max_price', type=float)
                sort_by = request.args.get('sort', type=str)
                
                if all_category_ids:
                    # Use filtering if parameters are provided
                    if min_price is not None or max_price is not None or sort_by:
                        products = Product.get_by_categories_with_price_range(all_category_ids, min_price, max_price, sort_by)
                        app.logger.info(f"Category {category_id} with filters (price: {min_price}-{max_price}, sort: {sort_by}) found {len(products)} products")
                    else:
                        # Get products from parent category and all subcategories
                        products = Product.get_by_categories(all_category_ids)
                else:
                    # Fallback: get products directly from the category
                    products = Product.get_by_category(category_id)
                    
        except Exception as e:
            app.logger.error(f"Error fetching products for category {category_id}: {e}")
            products = []
            
        return render_template('category_products.html', 
                             category=category, 
                             products=products, 
                             hierarchy=hierarchy)

    @app.route('/products/category/multi/<category_ids>')
    def products_by_multiple_categories(category_ids):
        category = None
        products = []
        hierarchy = []
        try:
            categories = Category.get_all()
            # Parse category_ids from comma-separated string to list of ints
            category_id_list = [int(cid) for cid in category_ids.split(',') if cid.isdigit()]
            # For display, pick the first category or None
            category = next((c for c in categories if c['id'] == category_id_list[0]), None) if category_id_list else None
            if category_id_list:
                products = Product.get_by_categories(category_id_list)
            # Build category hierarchy for the template
            hierarchy = build_category_hierarchy(categories)
        except Exception as e:
            products = []
            hierarchy = []
        return render_template('category_products.html', category=category, products=products, hierarchy=hierarchy)

    @app.route('/products/brand/<string:brand_name>')
    def products_by_brand(brand_name):
        products = []
        hierarchy = []
        brand_categories = []
        try:
            # Get filter parameters from URL
            min_price = request.args.get('min_price', type=float)
            max_price = request.args.get('max_price', type=float)
            sort_by = request.args.get('sort', type=str)
            category_filter = request.args.get('category', type=str)
            
            # Get available categories for this brand
            brand_categories = Product.get_categories_by_brand(brand_name)
            
            # Use filtering if parameters are provided
            if min_price is not None or max_price is not None or sort_by or category_filter:
                products = Product.get_by_brand_with_price_range(brand_name, min_price, max_price, sort_by, category_filter)
                app.logger.info(f"Brand '{brand_name}' with filters (price: {min_price}-{max_price}, sort: {sort_by}, category: {category_filter}) found {len(products)} products")
            else:
                products = Product.get_by_brand(brand_name)
                app.logger.info(f"Brand '{brand_name}' found {len(products)} products")
            
            # Build category hierarchy for the template (empty for brand pages)
            hierarchy = []
        except Exception as e:
            app.logger.error(f"Error fetching products for brand {brand_name}: {e}")
            products = []
            hierarchy = []
            brand_categories = []
        return render_template('category_products.html', brand=brand_name, products=products, hierarchy=hierarchy, brand_categories=brand_categories)


    @app.route('/about')
    def about():
        products = Product.get_all()
        return render_template('about.html', products=products)

    
    @app.route('/services')
    def services():
        products = Product.get_all()
        return render_template('services.html', products=products)
    
    @app.route('/privacy')
    def privacy():
        products = Product.get_all()
        return render_template('privacy.html', products=products)
    

    @app.route('/cart')
    def cart():
        return render_template('cart.html')

    @app.route('/api/cart/add', methods=['POST'])
    def add_to_cart():
        app.logger.info(f"🛒 ADD TO CART CALLED - Session: {dict(session)}")

        # Allow both logged-in and non-logged-in users to add to cart
        data = request.get_json()
        product_id = data.get('product_id')
        quantity = data.get('quantity', 1)

        app.logger.info(f"🛒 ADD TO CART - Product ID: {product_id}, Quantity: {quantity}")

        if not product_id:
            return jsonify({'success': False, 'error': 'Product ID is required'}), 400

        # Verify product exists and has stock
        product = Product.get_by_id(product_id)
        if not product:
            return jsonify({'success': False, 'error': 'Product not found'}), 404

        if product['stock'] < quantity:
            return jsonify({'success': False, 'error': f'Only {product["stock"]} items available in stock'}), 400

        try:
            # Initialize cart if it doesn't exist
            if 'cart' not in session:
                session['cart'] = []

            # Check if item already exists in cart
            existing_item = None
            for item in session['cart']:
                if item['product_id'] == product_id:
                    existing_item = item
                    break

            if existing_item:
                # Update quantity of existing item
                new_quantity = existing_item['quantity'] + quantity
                if product['stock'] < new_quantity:
                    return jsonify({'success': False, 'error': f'Only {product["stock"]} items available in stock'}), 400
                existing_item['quantity'] = new_quantity
                app.logger.info(f"🛒 Updated existing cart item quantity to {new_quantity}")
            else:
                # Add new item to cart
                session['cart'].append({
                    'product_id': product_id,
                    'name': product['name'],
                    'price': product['price'],
                    'quantity': quantity,
                    'photo': product.get('photo', ''),
                    'stock': product['stock']
                })
                app.logger.info(f"🛒 Added new item to cart")

            session.modified = True

            # Note: We don't sync with pending orders here because once an order is created,
            # it should remain independent of cart changes. Pending orders are locked in.

            app.logger.info(f"✅ ADD TO CART SUCCESS - Session cart: {session.get('cart', [])}")

            return jsonify({
                'success': True,
                'message': 'Item added to cart successfully',
                'cart_count': len(session['cart']),
                'cart_total_items': sum(item['quantity'] for item in session['cart'])
            })

        except Exception as e:
            app.logger.error(f"Error adding to cart: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/cart/checkout', methods=['POST'])
    def checkout_cart():
        """Process checkout for all items in cart with volume discounts"""
        app.logger.info(f"🛒 CHECKOUT CALLED - Session: {dict(session)}")

        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in to checkout'}), 401

        if 'cart' not in session or not session['cart']:
            return jsonify({'success': False, 'error': 'Cart is empty'}), 400

        try:
            # Get payment method from request data
            data = request.get_json() or {}
            payment_method = data.get('payment_method', 'Cash')  # Default to Cash instead of QR Payment
            otp_code = data.get('otp_code')  # OTP verification for checkout
            app.logger.info(f"💳 Payment method selected: {payment_method}")

            customer_id = session.get('user_id')
            if not customer_id:
                return jsonify({'success': False, 'error': 'Customer not found in session'}), 401

            # Check if customer needs OTP verification for checkout
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                SELECT otp_enabled FROM customers WHERE id = %s
            """, (customer_id,))
            customer = cur.fetchone()
            
            if customer and not customer.get('otp_enabled'):
                # Customer account is not verified, require verification
                cur.close()
                return jsonify({
                    'success': False, 
                    'error': 'Please verify your account to continue purchasing',
                    'requires_verification': True
                }), 400
            
            # If customer is verified (otp_enabled = 1), proceed with checkout without OTP requirement
            # OTP is only used for initial email verification, not for every purchase
            
            cur.close()

            conn = get_db()
            cur = conn.cursor(dictionary=True)

            try:
                # Validate all cart items and calculate total
                cart_items = []
                preorder_items = []
                subtotal = 0

                for cart_item in session['cart']:
                    if cart_item.get('type') == 'preorder':
                        preorder_items.append(cart_item)
                        # Add pre-order item price * quantity to subtotal
                        item_price = float(cart_item.get('price', 0))
                        item_quantity = int(cart_item.get('quantity', 1))
                        item_total = item_price * item_quantity
                        subtotal += item_total
                        continue

                    product = Product.get_by_id(cart_item['product_id'])
                    if not product:
                        return jsonify({'success': False, 'error': f'Product {cart_item["product_id"]} not found'}), 404

                    if product['stock'] < cart_item['quantity']:
                        return jsonify({'success': False, 'error': f'Only {product["stock"]} items available for {product["name"]}'}), 400

                    # Ensure all values are float for calculations
                    item_price = float(product['price'])
                    item_quantity = int(cart_item['quantity'])
                    item_total = item_quantity * item_price
                    subtotal += item_total

                    cart_items.append({
                        'product_id': cart_item['product_id'],
                        'product': product,
                        'quantity': item_quantity,
                        'price': item_price,
                        'item_total': item_total
                    })

                # Calculate volume discount
                volume_discount_amount = 0.0
                volume_discount_rule_id = None
                volume_discount_percentage = 0.0

                cur.execute("""
                    SELECT id, name, discount_percentage
                    FROM volume_discount_rules
                    WHERE minimum_amount <= %s AND is_active = TRUE
                    ORDER BY minimum_amount DESC
                    LIMIT 1
                """, (subtotal,))

                volume_rule = cur.fetchone()
                if volume_rule:
                    volume_discount_rule_id = volume_rule['id']
                    volume_discount_percentage = float(volume_rule['discount_percentage'])

                    # Calculate volume discount amount - ensure all values are float
                    volume_discount_amount = float(subtotal) * (volume_discount_percentage / 100.0)

                # Calculate final total - ensure all values are float
                final_total = float(subtotal) - float(volume_discount_amount)

                # Orders start as 'PENDING' but will be updated to 'COMPLETED' when payment is confirmed
                # Staff approval is still required for fulfillment
                initial_status = 'PENDING'
                
                # All orders start with 'Pending Approval' status
                # This will be updated when payment is confirmed
                approval_status = 'Pending Approval'
                
                # Generate transaction ID for QR payments only
                transaction_id = None
                if payment_method == 'KHQR_BAKONG':
                    import uuid
                    # Generate a unique transaction ID using UUID and MD5 hash
                    unique_id = str(uuid.uuid4())
                    transaction_id = hashlib.md5(unique_id.encode()).hexdigest()
                    app.logger.info(f"🔑 Generated transaction ID for KHQR payment: {transaction_id}")
                
                # Create order with appropriate initial status and approval status
                if transaction_id:
                    # QR payment with transaction ID
                    cur.execute("""
                        INSERT INTO orders (customer_id, order_date, total_amount, status, payment_method, approval_status, volume_discount_rule_id, volume_discount_percentage, volume_discount_amount, transaction_id)
                        VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (customer_id, final_total, initial_status, payment_method, approval_status, volume_discount_rule_id, volume_discount_percentage, volume_discount_amount, transaction_id))
                else:
                    # Non-QR payment without transaction ID
                    cur.execute("""
                        INSERT INTO orders (customer_id, order_date, total_amount, status, payment_method, approval_status, volume_discount_rule_id, volume_discount_percentage, volume_discount_amount)
                        VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s, %s)
                    """, (customer_id, final_total, initial_status, payment_method, approval_status, volume_discount_rule_id, volume_discount_percentage, volume_discount_amount))
                order_id = cur.lastrowid

                # Add all regular cart items to order
                for cart_item in cart_items:
                    product = cart_item['product']

                    # Calculate the selling price before discount for proper invoice display
                    # If there's a discount, calculate the original selling price
                    if product.get('discount_percentage') and product['discount_percentage'] > 0:
                        # Calculate selling price before discount: current_price / (1 - discount_percentage/100)
                        selling_price_before_discount = float(product['price']) / (1 - float(product['discount_percentage']) / 100)
                        original_price = round(selling_price_before_discount, 2)
                        discount_amount = round(selling_price_before_discount - float(product['price']), 2)
                        discount_percentage = product['discount_percentage']
                    else:
                        # No discount, use current price as original
                        original_price = product['price']
                        discount_amount = 0
                        discount_percentage = 0

                    # Get category name for denormalized data
                    cur.execute("SELECT name FROM categories WHERE id = %s", (product['category_id'],))
                    category_result = cur.fetchone()
                    category_name = category_result['name'] if category_result else 'Unknown'

                    cur.execute("""
                        INSERT INTO order_items (order_id, product_id, product_name, product_description, product_category, quantity, price, original_price, discount_percentage, discount_amount)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (order_id, cart_item['product_id'], product['name'], product.get('description', ''), category_name, cart_item['quantity'], cart_item['price'],
                          original_price, discount_percentage, discount_amount))

                    # Reduce stock immediately when order is placed
                    # This reserves the stock for the customer and prevents overselling
                    cur.execute("""
                        UPDATE products 
                        SET stock = stock - %s 
                        WHERE id = %s
                    """, (cart_item['quantity'], cart_item['product_id']))
                    
                    # Log inventory change
                    cur.execute("""
                        INSERT INTO inventory (product_id, changes, change_date) 
                        VALUES (%s, %s, NOW())
                    """, (cart_item['product_id'], -cart_item['quantity']))
                    
                    app.logger.info(f"Stock reduced for product {cart_item['product_id']} by {cart_item['quantity']}")

                # Process pre-order items separately
                for preorder_item in preorder_items:
                    preorder_id = preorder_item.get('preorder_id')
                    quantity = preorder_item.get('quantity', 1)

                    # Validate pre-order exists and belongs to customer
                    from models import PreOrder
                    preorder = PreOrder.get_by_id(preorder_id)
                    if not preorder:
                        return jsonify({'success': False, 'error': f'Pre-order {preorder_id} not found'}), 404

                    if preorder['customer_id'] != customer_id:
                        return jsonify({'success': False, 'error': 'Unauthorized access to pre-order'}), 403

                    # Get product and category info for denormalized data
                    cur.execute("SELECT p.name, p.description, c.name as category_name FROM products p JOIN categories c ON p.category_id = c.id WHERE p.id = %s", (preorder_item['product_id'],))
                    product_result = cur.fetchone()
                    product_name = product_result['name'] if product_result else 'Unknown Product'
                    product_description = product_result['description'] if product_result else ''
                    category_name = product_result['category_name'] if product_result else 'Unknown'

                    # Insert pre-order items into order_items with type 'preorder'
                    cur.execute("""
                        INSERT INTO order_items (order_id, product_id, product_name, product_description, product_category, quantity, price, original_price, discount_percentage, discount_amount, type)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'preorder')
                    """, (order_id, preorder_item['product_id'], product_name, product_description, category_name, quantity, preorder_item['price'], preorder_item['price'], 0, 0))

                    # Reduce stock for pre-order items if applicable (usually stock is 0)
                    cur.execute("""
                        UPDATE products
                        SET stock = stock - %s
                        WHERE id = %s
                    """, (quantity, preorder_item['product_id']))

                    # Log inventory change
                    cur.execute("""
                        INSERT INTO inventory (product_id, changes)
                        VALUES (%s, %s)
                    """, (preorder_item['product_id'], -quantity))

                # Keep order status as PENDING until payment is confirmed
                # Don't clear cart yet - only clear when payment is actually confirmed
                conn.commit()

                app.logger.info(f"✅ CHECKOUT SUCCESS - Order ID: {order_id}, Total: {final_total}, Volume Discount: {volume_discount_amount}, Order status: PENDING - awaiting payment confirmation")
                
                app.logger.info(f"✅ CHECKOUT SUCCESS - Order ID: {order_id}, Total: {final_total}, Volume Discount: {volume_discount_amount}, Order status updated to COMPLETED - awaiting staff approval")

                return jsonify({
                    'success': True,
                    'message': 'Order placed successfully',
                    'order_id': order_id,
                    'subtotal': subtotal,
                    'volume_discount_amount': volume_discount_amount,
                    'final_total': final_total
                })

            finally:
                cur.close()
                conn.close()

        except Exception as e:
            app.logger.error(f"Error during checkout: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/cart/remove', methods=['POST'])
    def remove_from_cart():
        # Allow both logged-in and non-logged-in users to remove from cart
        data = request.get_json()
        product_id = data.get('product_id')

        if not product_id:
            return jsonify({'success': False, 'error': 'Product ID is required'}), 400

        try:
            # Check if user is logged in
            if 'username' in session:
                # Logged-in user: remove from database
                customer_id = session.get('user_id')
                if not customer_id:
                    return jsonify({'success': False, 'error': 'Customer not found in session'}), 401

                conn = get_db()
                cur = conn.cursor(dictionary=True)

                try:
                    # Note: We don't modify pending orders here because once an order is created,
                    # it should remain independent of cart changes. Pending orders are locked in.
                    app.logger.info(f"🛒 REMOVE FROM CART (Logged-in) - Product ID: {product_id} - Pending orders not modified")

                finally:
                    cur.close()
                    conn.close()
            else:
                # Non-logged-in user: only remove from session cart
                app.logger.info(f"🛒 REMOVE FROM CART (Guest) - Product ID: {product_id}")

            # Remove from session cart for both logged-in and non-logged-in users
            if 'cart' in session:
                original_length = len(session['cart'])
                session['cart'] = [item for item in session['cart'] if item['product_id'] != product_id]
                session.modified = True
                app.logger.info(f"🛒 Session cart updated - Removed product {product_id}, items before: {original_length}, after: {len(session['cart'])}")

            return jsonify({'success': True, 'message': 'Item removed from cart'})

        except Exception as e:
            app.logger.error(f"Error removing from cart: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/cart/remove-preorder', methods=['POST'])
    def remove_preorder_from_cart():
        """Remove a pre-order item from cart"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        data = request.get_json()
        preorder_id = data.get('preorder_id')

        if not preorder_id:
            return jsonify({'success': False, 'error': 'Pre-order ID is required'}), 400

        if 'cart' not in session:
            session['cart'] = []

        # Remove pre-order item from cart
        session['cart'] = [item for item in session['cart'] if item.get('preorder_id') != preorder_id]
        session.modified = True

        return jsonify({'success': True, 'message': 'Pre-order item removed from cart'})

    @app.route('/api/cart/update', methods=['POST'])
    def update_cart_quantity():
        data = request.get_json()
        product_id = data.get('product_id')
        quantity = data.get('quantity', 1)

        if not product_id:
            return jsonify({'success': False, 'error': 'Product ID is required'}), 400

        if quantity <= 0:
            return jsonify({'success': False, 'error': 'Quantity must be greater than 0'}), 400

        if 'cart' not in session:
            session['cart'] = []

        # Update quantity for existing item in session cart
        for item in session['cart']:
            if item['product_id'] == product_id:
                item['quantity'] = quantity
                break

        session.modified = True
        
        # Note: We don't update pending orders here because once an order is created,
        # it should remain independent of cart changes. Pending orders are locked in.
        
        # Calculate total items for response
        cart_total_items = sum(item.get('quantity', 1) for item in session['cart'])
        
        return jsonify({
            'success': True, 
            'message': 'Cart updated',
            'cart_total_items': cart_total_items
        })

    # Note: Removed sync-pending endpoint because pending orders should be independent of cart changes

    @app.route('/api/payment/check-pending', methods=['POST'])
    def check_pending_payments():
        """Manual payment verification - no automatic checking needed"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401
            
        return jsonify({
            'success': True,
            'message': 'Manual verification mode - use "Mark as Paid" button to verify payments'
        })

    @app.route('/api/payment/stop-verifier', methods=['POST'])
    def stop_payment_verifier():
        """No automatic verifier to stop - manual mode only"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401
            
        return jsonify({
            'success': True, 
            'message': 'Manual verification mode - no automatic verifier running'
        })

    @app.route('/api/payment/toggle-test-mode', methods=['POST'])
    def toggle_test_mode():
        """No test mode needed - manual verification only"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401
            
        return jsonify({
            'success': True, 
            'message': 'Manual verification mode - no test mode needed',
            'test_mode': False
        })

    @app.route('/payment/verification')
    def payment_verification():
        """Payment verification page for customers to upload payment screenshots"""
        return render_template('payment_verification.html')

    @app.route('/api/payment/verify-upload', methods=['POST'])
    def verify_payment_upload():
        """Verify payment by uploading screenshot and comparing transaction IDs"""
        try:
            order_id = request.form.get('order_id')
            transaction_id = request.form.get('transaction_id', '').strip()
            payment_notes = request.form.get('payment_notes', '').strip()
            
            if not order_id:
                return jsonify({'success': False, 'error': 'Order ID is required'}), 400
            
            # Check if file was uploaded
            if 'payment_screenshot' not in request.files:
                return jsonify({'success': False, 'error': 'Payment screenshot is required'}), 400
            
            file = request.files['payment_screenshot']
            if file.filename == '':
                return jsonify({'success': False, 'error': 'No file selected'}), 400
            
            # Validate file type and size
            allowed_extensions = {'png', 'jpg', 'jpeg', 'pdf'}
            if not ('.' in file.filename and 
                   file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
                return jsonify({'success': False, 'error': 'Invalid file type. Please upload JPG, PNG, or PDF'}), 400
            
            # Check file size (10MB limit)
            file.seek(0, 2)  # Seek to end
            file_size = file.tell()
            file.seek(0)  # Reset to beginning
            if file_size > 10 * 1024 * 1024:  # 10MB
                return jsonify({'success': False, 'error': 'File too large. Maximum size is 10MB'}), 400
            
            # Check if order exists and is pending
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            
            cur.execute("""
                SELECT id, status, payment_method, transaction_id, total_amount, customer_id
                FROM orders 
                WHERE id = %s
            """, (order_id,))
            
            order = cur.fetchone()
            if not order:
                return jsonify({'success': False, 'error': f'Order #{order_id} not found'}), 404
            
            # Allow QR orders to upload screenshots even when completed
            if order['payment_method'] not in ['KHQR_BAKONG'] and order['status'] != 'PENDING':
                return jsonify({'success': False, 'error': f'Order #{order_id} is not pending. Current status: {order["status"]}'}), 400
            
            # Save uploaded file
            import os
            from werkzeug.utils import secure_filename
            
            # Create upload directory if it doesn't exist
            upload_dir = os.path.join(app.static_folder, 'uploads', 'payment_screenshots')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Generate unique filename
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"order_{order_id}_{timestamp}_{filename}"
            file_path = os.path.join(upload_dir, unique_filename)
            
            # Save file
            file.save(file_path)
            
            # Store relative path for database
            relative_path = f"uploads/payment_screenshots/{unique_filename}"
            
            # Update order with payment verification info
            cur.execute("""
                UPDATE orders 
                SET payment_screenshot_path = %s,
                    payment_verification_status = 'verified',
                    screenshot_uploaded_at = NOW(),
                    transaction_id = COALESCE(NULLIF(%s, ''), transaction_id)
                WHERE id = %s
            """, (relative_path, transaction_id, order_id))
            
            # Determine order status based on verification type
            if transaction_id and order['transaction_id'] and transaction_id == order['transaction_id']:
                # Transaction ID matches - automatic completion
                cur.execute("""
                    UPDATE orders 
                    SET status = 'COMPLETED',
                        approval_status = 'Pending Approval'
                    WHERE id = %s
                """, (order_id,))
                
                # Reduce stock
                cur.execute("""
                    UPDATE products p
                    JOIN order_items oi ON p.id = oi.product_id
                    SET p.stock = p.stock - oi.quantity
                    WHERE oi.order_id = %s AND p.stock >= oi.quantity
                """, (order_id,))
                
                order_status = 'COMPLETED'
            elif not transaction_id and order['payment_method'] == 'KHQR_BAKONG':
                # QR code upload - no transaction ID, but payment proof provided
                # Mark as verified and ready for admin approval
                cur.execute("""
                    UPDATE orders 
                    SET status = 'PENDING',
                        approval_status = 'Pending Approval',
                        payment_verification_status = 'verified'
                    WHERE id = %s
                """, (order_id,))
                
                order_status = 'PENDING (QR Payment Verified)'
            else:
                # Other payment methods or invoice uploads
                order_status = 'PENDING (Verified)'
            
            conn.commit()
            cur.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Payment verification uploaded successfully',
                'order_status': order_status,
                'order_id': order_id
            })
            
        except Exception as e:
            app.logger.error(f"Error in payment verification: {str(e)}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

    @app.route('/api/orders/search', methods=['POST'])
    def search_orders():
        """Search for orders by email or phone number"""
        try:
            data = request.get_json()
            email = data.get('email', '').strip()
            phone = data.get('phone', '').strip()
            
            if not email and not phone:
                return jsonify({'success': False, 'error': 'Email or phone number is required'}), 400
            
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            
            # Build search query
            query = """
                SELECT o.id, o.status, o.order_date, o.total_amount, o.payment_method, o.transaction_id,
                       c.first_name, c.last_name, c.email, c.phone
                FROM orders o
                JOIN customers c ON o.customer_id = c.id
                WHERE 1=1
            """
            params = []
            
            if email:
                query += " AND c.email = %s"
                params.append(email)
            
            if phone:
                query += " AND c.phone = %s"
                params.append(phone)
            
            query += " ORDER BY o.order_date DESC LIMIT 10"
            
            cur.execute(query, params)
            orders = cur.fetchall()
            
            cur.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'orders': orders
            })
            
        except Exception as e:
            app.logger.error(f"Error searching orders: {str(e)}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

    @app.route('/api/payment/extract-order-info', methods=['POST'])
    def extract_order_info():
        """Extract order ID and transaction ID from uploaded file"""
        try:
            if 'file' not in request.files:
                return jsonify({'success': False, 'error': 'No file uploaded'}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'success': False, 'error': 'No file selected'}), 400
            
            # Check file type
            allowed_extensions = {'png', 'jpg', 'jpeg', 'pdf', 'doc', 'docx'}
            if not ('.' in file.filename and
                   file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
                return jsonify({'success': False, 'error': 'Invalid file type. Supported: JPG, PNG, PDF, DOC, DOCX'}), 400
            
            # Save file temporarily
            import tempfile
            import os
            from werkzeug.utils import secure_filename
            
            filename = secure_filename(file.filename)
            temp_dir = tempfile.mkdtemp()
            temp_path = os.path.join(temp_dir, filename)
            file.save(temp_path)
            
            try:
                # Extract information using OCR and QR code reading
                order_id = None
                transaction_id = None
                
                # Try QR code extraction first
                try:
                    from utils.qr_recovery_system import QRRecoverySystem
                    qr_system = QRRecoverySystem()
                    
                    # Read QR code from image
                    qr_data = qr_system.read_qr_from_image(temp_path)
                    if qr_data:
                        order_info = qr_system.extract_order_info_from_qr(qr_data)
                        if order_info:
                            order_id = order_info.get('order_id')
                            # QR codes typically don't contain transaction ID, only order reference
                            # Transaction ID is generated by the bank when payment is made
                            transaction_id = None
                except Exception as e:
                    app.logger.warning(f"QR extraction failed: {str(e)}")
                
                # If QR extraction failed, try OCR for invoice text
                if not order_id or not transaction_id:
                    try:
                        # Use OCR to extract text from image
                        import pytesseract
                        from PIL import Image
                        
                        # Convert PDF to image if needed
                        if filename.lower().endswith('.pdf'):
                            import pdf2image
                            images = pdf2image.convert_from_path(temp_path)
                            if images:
                                image = images[0]
                            else:
                                return jsonify({'success': False, 'error': 'Could not process PDF'}), 400
                        else:
                            image = Image.open(temp_path)
                        
                        # Extract text using OCR
                        text = pytesseract.image_to_string(image)
                        
                        # Extract order ID and transaction ID using regex
                        import re
                        
                        # Look for order ID patterns
                        order_patterns = [
                            r'Order\s*#?\s*(\d+)',
                            r'Order\s*ID\s*:?\s*(\d+)',
                            r'Order\s*Number\s*:?\s*(\d+)',
                            r'#(\d+)',
                        ]
                        
                        for pattern in order_patterns:
                            match = re.search(pattern, text, re.IGNORECASE)
                            if match:
                                order_id = match.group(1)
                                break
                        
                        # Look for transaction ID patterns
                        transaction_patterns = [
                            r'Transaction\s*ID\s*:?\s*([A-Za-z0-9]+)',
                            r'Trans\s*ID\s*:?\s*([A-Za-z0-9]+)',
                            r'TXN\s*ID\s*:?\s*([A-Za-z0-9]+)',
                            r'Reference\s*:?\s*([A-Za-z0-9]+)',
                            r'Ref\s*:?\s*([A-Za-z0-9]+)',
                        ]
                        
                        for pattern in transaction_patterns:
                            match = re.search(pattern, text, re.IGNORECASE)
                            if match:
                                transaction_id = match.group(1)
                                break
                                
                    except Exception as e:
                        app.logger.warning(f"OCR extraction failed: {str(e)}")
                
                return jsonify({
                    'success': True,
                    'order_id': order_id,
                    'transaction_id': transaction_id,
                    'message': 'Information extracted successfully'
                })
                
            finally:
                # Clean up temporary file
                try:
                    os.remove(temp_path)
                    os.rmdir(temp_dir)
                except:
                    pass
                    
        except Exception as e:
            app.logger.error(f"Error extracting order info: {str(e)}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

    @app.route('/api/payment/verify-instantly', methods=['POST'])
    def verify_payment_instantly():
        """Instantly verify a specific order payment"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401
            
        try:
            data = request.get_json()
            order_id = data.get('order_id')
            
            if not order_id:
                return jsonify({'success': False, 'error': 'Order ID required'}), 400
            
            # Manual verification - no automatic verifier needed
            
            # Get the specific order
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            
            try:
                cur.execute("""
                    SELECT o.id, o.transaction_id, o.total_amount, o.order_date, o.customer_id, o.status
                    FROM orders o
                    WHERE o.id = %s AND o.status = 'PENDING' AND o.payment_method = 'KHQR_BAKONG'
                """, (order_id,))
                
                order = cur.fetchone()
                
                if not order:
                    return jsonify({'success': False, 'error': 'Order not found or not pending'}), 404
                
                # Manual verification - staff confirms customer has actually paid
                # This overrides the automatic system when staff knows payment was made
                
                # Update order status to COMPLETED (manual verification)
                cur.execute("""
                    UPDATE orders 
                    SET status = 'COMPLETED', 
                        approval_status = 'Approved',
                        approval_date = NOW(),
                        approved_by = %s
                    WHERE id = %s
                """, (session.get('user_id', 1), order_id))
                
                # Reduce stock for order items
                cur.execute("""
                    UPDATE products p
                    JOIN order_items oi ON p.id = oi.product_id
                    SET p.stock = p.stock - oi.quantity
                    WHERE oi.order_id = %s AND p.stock >= oi.quantity
                """, (order_id,))
                
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'status': 'completed',
                    'message': 'Order marked as paid and completed! (Manual verification)',
                    'order_id': order_id
                })
                    
            finally:
                cur.close()
                conn.close()
                
        except Exception as e:
            app.logger.error(f"Error verifying payment instantly: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/cart/update-preorder', methods=['POST'])
    def update_preorder_cart_quantity():
        """Update quantity of a pre-order item in cart"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        data = request.get_json()
        preorder_id = data.get('preorder_id')
        quantity = data.get('quantity', 1)

        if not preorder_id:
            return jsonify({'success': False, 'error': 'Pre-order ID is required'}), 400

        if quantity <= 0:
            return jsonify({'success': False, 'error': 'Quantity must be greater than 0'}), 400

        if 'cart' not in session:
            session['cart'] = []

        # Update quantity for existing pre-order item
        for item in session['cart']:
            if item.get('preorder_id') == preorder_id:
                item['quantity'] = quantity
                break

        session.modified = True
        return jsonify({'success': True, 'message': 'Pre-order cart updated'})

    @app.route('/api/cart/add-preorder', methods=['POST'])
    def add_preorder_to_cart():
        """Add a pre-order to cart for payment"""
        app.logger.info(f"🛒 ADD PREORDER TO CART - Session data: {dict(session)}")

        if 'username' not in session:
            app.logger.error("❌ No username in session for add preorder to cart")
            return jsonify({'success': False, 'error': 'Please log in to add items to cart'}), 401

        try:
            data = request.get_json()
            app.logger.info(f"📦 Received data: {data}")

            preorder_id = data.get('preorder_id')
            product_id = data.get('product_id')
            quantity = data.get('quantity', 1)
            price = data.get('price')

            app.logger.info(f"🔍 Parsed: preorder_id={preorder_id}, product_id={product_id}, quantity={quantity}, price={price}")

            if not all([preorder_id, product_id, quantity, price]):
                app.logger.error(f"❌ Missing required fields: preorder_id={preorder_id}, product_id={product_id}, quantity={quantity}, price={price}")
                return jsonify({'success': False, 'error': 'Missing required fields'}), 400

            # Verify the pre-order exists and belongs to the current user
            from models import PreOrder, Customer

            customer_id = session.get('user_id')
            customer = Customer.get_by_id(customer_id)
            if not customer:
                return jsonify({'success': False, 'error': 'Customer not found'}), 404

            preorder = PreOrder.get_by_id(preorder_id)
            if not preorder:
                return jsonify({'success': False, 'error': 'Pre-order not found'}), 404

            if preorder['customer_id'] != customer['id']:
                return jsonify({'success': False, 'error': 'Unauthorized access to pre-order'}), 403

            # Verify product exists
            product = Product.get_by_id(product_id)
            if not product:
                return jsonify({'success': False, 'error': 'Product not found'}), 404

            # Initialize cart if it doesn't exist
            if 'cart' not in session:
                session['cart'] = []
                app.logger.info("🛒 Initialized empty cart")

            app.logger.info(f"🛒 Current cart before adding: {session['cart']}")

            # Check if this product is already in cart (combine same products)
            existing_item = None
            for item in session['cart']:
                # Check for same product, regardless of whether it's a pre-order or regular item
                if item.get('product_id') == product_id and item.get('type') == 'preorder':
                    existing_item = item
                    break

            if existing_item:
                # Combine quantities if same product already in cart
                existing_item['quantity'] += int(quantity)
                app.logger.info(f"🔄 Combined quantities for existing product in cart: {existing_item}")
            else:
                # Add new pre-order item to cart
                cart_item = {
                    'product_id': product_id,
                    'preorder_id': preorder_id,
                    'name': product['name'],
                    'price': float(price),
                    'quantity': int(quantity),
                    'type': 'preorder'  # Mark as pre-order item
                }
                session['cart'].append(cart_item)
                app.logger.info(f"➕ Added new pre-order to cart: {cart_item}")

            session.modified = True
            app.logger.info(f"🛒 Final cart after adding: {session['cart']}")

            app.logger.info(f"✅ Pre-order {preorder_id} added to cart for customer {customer['id']}")

            return jsonify({
                'success': True,
                'message': 'Pre-order added to cart successfully'
            })

        except Exception as e:
            app.logger.error(f"Error adding pre-order to cart: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/cart/test-add-preorder/<int:preorder_id>', methods=['GET'])
    def test_add_preorder_to_cart(preorder_id):
        """Test endpoint to manually add a pre-order to cart"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        try:
            from models import PreOrder, Customer

            # Get the pre-order
            preorder = PreOrder.get_by_id(preorder_id)
            if not preorder:
                return jsonify({'success': False, 'error': 'Pre-order not found'}), 404

            # Get product info
            product = Product.get_by_id(preorder['product_id'])
            if not product:
                return jsonify({'success': False, 'error': 'Product not found'}), 404

            # Initialize cart if it doesn't exist
            if 'cart' not in session:
                session['cart'] = []

            # Add pre-order to cart
            cart_item = {
                'product_id': preorder['product_id'],
                'preorder_id': preorder_id,
                'name': product['name'],
                'price': float(preorder['expected_price']),
                'quantity': int(preorder['quantity']),
                'type': 'preorder'
            }
            session['cart'].append(cart_item)
            session.modified = True

            app.logger.info(f"🧪 TEST: Added pre-order {preorder_id} to cart manually")

            return jsonify({
                'success': True,
                'message': f'Pre-order {preorder_id} added to cart for testing',
                'cart_item': cart_item
            })

        except Exception as e:
            app.logger.error(f"Error in test add preorder: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/cart/clear', methods=['POST'])
    def clear_cart():
        # Allow both logged-in and non-logged-in users to clear cart
        # Clear session cart
        session['cart'] = []
        session.modified = True
        app.logger.info("🛒 Cart cleared for user")
        return jsonify({'success': True, 'message': 'Cart cleared'})



    @app.route('/api/cart/items', methods=['GET'])
    def get_cart_items():
        # Allow both logged-in and non-logged-in users to view cart
        # For non-logged-in users, only show session cart items
        # For logged-in users, show both session cart and any pending orders

        # Get cart items from pending order instead of session
        cart_items = []
        total_amount = 0
        total_items = 0

        try:
            conn = get_db()
            cur = conn.cursor(dictionary=True)

            try:
                # Use session cart for display since orders are now completed immediately
                session_cart = session.get('cart', [])
                for cart_item in session_cart:
                    # Skip pre-order items here - they'll be handled in the dedicated pre-order loop
                    if cart_item.get('type') == 'preorder':
                        continue
                        
                    # Get product details for regular items
                    cur.execute("""
                        SELECT name, price, photo FROM products WHERE id = %s
                    """, (cart_item['product_id'],))
                    product_data = cur.fetchone()

                    if product_data:
                        item = {
                            'id': cart_item['product_id'],
                            'name': product_data['name'],
                            'price': float(product_data['price']),
                            'quantity': cart_item['quantity'],
                            'photo': product_data.get('photo', ''),
                            'subtotal': float(product_data['price']) * cart_item['quantity']
                        }
                        cart_items.append(item)
                        total_amount += item['subtotal']
                        total_items += cart_item['quantity']

                # Also include session cart items (for pre-orders and mixed carts)
                if 'cart' in session:
                    for item in session['cart']:
                        if item.get('type') == 'preorder':
                            # Handle pre-order items from session
                            cart_item = {
                                'preorder_id': item.get('preorder_id'),
                                'name': item.get('name', 'Pre-order Item'),
                                'price': float(item.get('price', 0)),
                                'quantity': item.get('quantity', 1),
                                'type': 'preorder',
                                'subtotal': float(item.get('price', 0)) * item.get('quantity', 1)
                            }
                            cart_items.append(cart_item)
                            total_amount += cart_item['subtotal']
                            total_items += item['quantity']

            finally:
                cur.close()
                conn.close()

        except Exception as e:
            app.logger.error(f"Error loading cart items: {str(e)}")
            # Fallback to session cart if database fails
            if 'cart' not in session:
                session['cart'] = []

            for item in session['cart']:
                # Only process regular items if not already in pending order
                if item.get('type') != 'preorder':
                    product = Product.get_by_id(item['product_id'])
                    if product:
                        cart_item = {
                            'id': product['id'],
                            'name': product['name'],
                            'price': float(product['price']),
                            'quantity': item['quantity'],
                            'photo': product.get('photo', ''),
                            'subtotal': float(product['price']) * item['quantity']
                        }
                        cart_items.append(cart_item)
                        total_amount += cart_item['subtotal']
                        total_items += item['quantity']

        response_data = {
            'success': True,
            'cart_items': cart_items,
            'total_amount': total_amount,
            'total_items': total_items
        }

        app.logger.info(f"🛒 CART API RETURNING: {response_data}")
        return jsonify(response_data)

    @app.route('/api/cart/count', methods=['GET'])
    def get_cart_count():
        """Get cart count for both logged-in and non-logged-in users"""
        try:
            cart_items = session.get('cart', [])
            total_items = sum(item.get('quantity', 1) for item in cart_items)
            
            return jsonify({
                'success': True,
                'cart_count': len(cart_items),
                'total_items': total_items
            })
        except Exception as e:
            app.logger.error(f"Error getting cart count: {str(e)}")
            return jsonify({
                'success': False,
                'cart_count': 0,
                'total_items': 0
            })

    @app.route('/api/user/info', methods=['GET'])
    def get_user_info():
        """Get logged-in user information for checkout."""
        if 'username' not in session or 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not logged in'})

        try:
            # Get customer information by user_id
            customer = Customer.get_by_id(session['user_id'])

            if not customer:
                return jsonify({'success': False, 'error': 'Customer not found'})

            user_info = {
                'id': customer['id'],
                'first_name': customer['first_name'],
                'last_name': customer['last_name'],
                'email': customer['email'],
                'phone': customer.get('phone', ''),
                'address': customer.get('address', '')
            }

            return jsonify({
                'success': True,
                'user': user_info
            })

        except Exception as e:
            app.logger.error(f"Error getting user info: {str(e)}")
            return jsonify({'success': False, 'error': 'Failed to get user information'}), 500

    # Bakong Payment Endpoints
    @app.route('/api/payment/create-session', methods=['POST'])
    def create_payment_session():
        """Since orders are now created immediately when adding to cart, payment session just clears the cart."""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        try:
            # Clear cart since all orders are already completed
            session['cart'] = []
            session.modified = True

            return jsonify({
                'success': True,
                'message': 'Payment session created - all orders already completed',
                'session': {'id': 'dummy', 'status': 'completed'}
            })

        except Exception as e:
            app.logger.error(f"Error clearing cart: {str(e)}")
            return jsonify({'success': False, 'error': 'Failed to clear cart'}), 500

    @app.route('/api/payment/status/<session_id>', methods=['GET'])
    def get_payment_status(session_id):
        """Get payment status for a session."""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        try:
            payment_session = PaymentSession.get_session(session_id)

            if not payment_session:
                return jsonify({'success': False, 'error': 'Session not found'}), 404

            # Check if session is expired
            if PaymentSession.is_session_expired(session_id):
                PaymentSession.update_session_status(session_id, 'expired')
                return jsonify({
                    'success': True,
                    'status': 'expired',
                    'message': 'Payment session has expired'
                })

            # In a real implementation, this would check with Bakong API
            # For your ACLEDA Bank QR code, payment verification is manual
            # Customer scans QR → pays → shows confirmation → you confirm manually
            # Payment status remains 'pending' until you manually confirm

            return jsonify({
                'success': True,
                'status': payment_session['status'],
                'session': payment_session
            })

        except Exception as e:
            app.logger.error(f"Error checking payment status: {str(e)}")
            return jsonify({'success': False, 'error': 'Failed to check payment status'}), 500

    @app.route('/api/payment/cancel/<session_id>', methods=['POST'])
    def cancel_payment(session_id):
        """Cancel a payment session and restore order to pending status with cart items."""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        try:
            payment_session = PaymentSession.get_session(session_id)

            if not payment_session:
                return jsonify({'success': False, 'error': 'Session not found'}), 404

            if payment_session['status'] in ['completed', 'failed']:
                return jsonify({'success': False, 'error': 'Cannot cancel completed or failed payment'}), 400

            # Get order ID from payment session
            order_id = payment_session.get('order_id')
            if order_id:
                # Instead of cancelling the order, restore it to pending status
                # and restore cart items to the customer's cart
                conn = get_db()
                cur = conn.cursor(dictionary=True)
                
                try:
                    # Get order items to restore to cart
                    cur.execute("""
                        SELECT oi.product_id, oi.quantity, oi.price, p.name as product_name
                        FROM order_items oi
                        JOIN products p ON oi.product_id = p.id
                        WHERE oi.order_id = %s
                    """, (order_id,))
                    
                    order_items = cur.fetchall()
                    
                    # Restore items to customer's cart
                    restored_cart = []
                    for item in order_items:
                        restored_cart.append({
                            'product_id': item['product_id'],
                            'quantity': item['quantity'],
                            'price': float(item['price']),
                            'name': item['product_name']
                        })
                    
                    # Update session cart with restored items
                    session['cart'] = restored_cart
                    session.modified = True
                    
                    # Keep order as PENDING so customer can pay later with the same QR
                    # Don't mark as CANCELLED - let them complete payment later
                    app.logger.info(f"Order {order_id} payment cancelled, but order remains PENDING for later payment")
                    
                finally:
                    cur.close()
                    conn.close()

            # Keep payment session as pending so customer can complete payment later
            # Don't mark as cancelled - let them use the same QR later
            app.logger.info(f"Payment session {session_id} kept as pending for later completion")

            return jsonify({
                'success': True,
                'message': 'Payment cancelled. You can pay later using the same QR code. Items restored to cart.',
                'order_id': order_id,
                'cart_restored': True
            })

        except Exception as e:
            app.logger.error(f"Error cancelling payment: {str(e)}")
            return jsonify({'success': False, 'error': 'Failed to cancel payment'}), 500

    @app.route('/api/payment/confirm/<session_id>', methods=['POST'])
    def confirm_payment(session_id):
        """Confirm QR payment - order remains PENDING until staff approval"""
        app.logger.info(f"🔥 PAYMENT CONFIRMATION STARTED for session: {session_id}")

        if 'username' not in session:
            app.logger.error("❌ No username in session for payment confirmation")
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        try:
            # Get payment session
            payment_session = PaymentSession.get_session(session_id)
            if not payment_session:
                return jsonify({'success': False, 'error': 'Payment session not found'}), 404

            # Get the order ID from the payment session
            order_id = payment_session.get('order_id')
            if not order_id:
                return jsonify({'success': False, 'error': 'No order associated with this payment'}), 400

            conn = get_db()
            cur = conn.cursor(dictionary=True)

            try:
                # Verify order exists and is pending
                cur.execute("SELECT id, status FROM orders WHERE id = %s", (order_id,))
                order = cur.fetchone()
                
                if not order:
                    return jsonify({'success': False, 'error': 'Order not found'}), 404
                
                if order['status'] != 'PENDING':
                    return jsonify({'success': False, 'error': f'Order already {order["status"]}'}), 400

                # Update order status to 'COMPLETED' after payment confirmation
                # approval_status remains 'Pending Approval' for staff to manually approve
                cur.execute("UPDATE orders SET status = 'COMPLETED' WHERE id = %s", (order_id,))

                # Stock is already reduced when order was placed at checkout
                # No need to reduce stock again here
                app.logger.info(f"Order {order_id} status updated to COMPLETED - stock already reduced at checkout")

                # Update payment session status
                PaymentSession.update_session_status(session_id, 'completed')

                conn.commit()

                # Clear cart since payment is confirmed
                if 'cart' in session:
                    session['cart'] = []
                    session.modified = True
                session['cart'] = []
                if 'created_order_ids' in session:
                    session['created_order_ids'] = []
                session.modified = True

                app.logger.info(f"✅ Payment confirmed - Order {order_id} payment confirmed, status set to COMPLETED, approval_status remains Pending Approval, stock reduced")

                return jsonify({
                    'success': True,
                    'message': 'Payment confirmed successfully. Order is now completed and pending staff approval.',
                    'order_id': order_id
                })

            except Exception as e:
                conn.rollback()
                raise e
            finally:
                cur.close()
                conn.close()

        except Exception as e:
            app.logger.error(f"Error confirming payment: {str(e)}")
            return jsonify({'success': False, 'error': 'Failed to confirm payment'}), 500

    @app.route('/api/payment/cash', methods=['POST'])
    def process_cash_payment():
        """Process cash payment confirmation and update order status to completed."""
        app.logger.info("💵 CASH PAYMENT CONFIRMATION STARTED")

        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        try:
            # Get the order ID from the request body
            data = request.get_json()
            if not data or 'order_id' not in data:
                app.logger.error("❌ No order_id provided in request body")
                return jsonify({'success': False, 'error': 'Order ID is required'}), 400
            
            order_id = data['order_id']
            app.logger.info(f"💰 Processing cash payment for order {order_id}")

            # Update the order status to COMPLETED
            conn = mysql.connection
            cur = conn.cursor()
            
            # Check if order exists
            cur.execute("""
                SELECT id FROM orders WHERE id = %s
            """, (order_id,))
            
            if not cur.fetchone():
                return jsonify({'success': False, 'error': 'Order not found'}), 404
            
            # Always update cash payment to PENDING status (regardless of current status)
            cur.execute("""
                UPDATE orders 
                SET status = 'PENDING', approval_status = 'Pending Approval'
                WHERE id = %s
            """, (order_id,))
            
            conn.commit()
            cur.close()

            app.logger.info(f"💵 CASH PAYMENT CONFIRMED - Order {order_id} set to PENDING for admin approval")

            return jsonify({
                'success': True,
                'message': 'Payment confirmed - order pending admin approval',
                'order_id': order_id,  # Return the order ID for invoice redirect
                'payment_type': 'cash'  # Indicate this is a cash payment
            })

        except Exception as e:
            app.logger.error(f"Error processing cash payment: {str(e)}")
            return jsonify({'success': False, 'error': 'Failed to process payment'}), 500

    @app.route('/order-confirmation/<int:order_id>')
    def view_order_confirmation(order_id):
        """Display order confirmation page for payment method selection."""
        app.logger.info(f"🧾 Invoice requested for order_id: {order_id}")
        app.logger.info(f"👤 Session data: {dict(session)}")

        # Temporarily bypass auth check for debugging
        # if 'username' not in session:
        #     app.logger.warning("❌ No username in session, redirecting to login")
        #     return redirect(url_for('login'))

        try:
            # Get order details
            app.logger.info(f"🔍 Looking for order with ID: {order_id}")
            order = Order.get_by_id(order_id)
            app.logger.info(f"📋 Order found: {order}")

            if not order:
                app.logger.error(f"❌ Order {order_id} not found")
                flash('Order not found', 'error')
                return redirect(url_for('show_dashboard'))

            # Get customer details
            customer = Customer.get_by_id(order['customer_id'])
            if not customer:
                flash('Customer not found', 'error')
                return redirect(url_for('show_dashboard'))

            # Get detailed customer address from customer_addresses table
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            
            # Try to get detailed address first
            cur.execute("""
                SELECT house_number, street_name, street_number, village, sangkat, commune, khan,
                       province, country, building_name, floor_number, unit_number, 
                       landmark, delivery_notes
                FROM customer_addresses 
                WHERE customer_id = %s AND is_active = TRUE 
                ORDER BY is_default DESC, id DESC 
                LIMIT 1
            """, (order['customer_id'],))
            
            detailed_address = cur.fetchone()
            
            if detailed_address:
                # Check if street_name contains full address (common case)
                if detailed_address['street_name'] and detailed_address['street_name'].strip():
                    # Use street_name as the main address if it contains full address
                    customer_address = detailed_address['street_name'].strip()
                    
                    # Add province and country if they exist and aren't already in street_name
                    if detailed_address['province'] and detailed_address['province'] not in customer_address:
                        customer_address += f", {detailed_address['province']}"
                    if detailed_address['country'] and detailed_address['country'] not in customer_address:
                        customer_address += f", {detailed_address['country']}"
                else:
                    # Build complete address from atomic components
                    address_parts = []
                    if detailed_address['house_number']:
                        address_parts.append(detailed_address['house_number'])
                    if detailed_address['street_name']:
                        if detailed_address['street_number']:
                            address_parts.append(f"st{detailed_address['street_number']}")
                        address_parts.append(detailed_address['street_name'])
                    if detailed_address['village']:
                        address_parts.append(detailed_address['village'])
                    if detailed_address['sangkat']:
                        address_parts.append(detailed_address['sangkat'])
                    if detailed_address['commune']:
                        address_parts.append(detailed_address['commune'])
                    if detailed_address['khan']:
                        address_parts.append(detailed_address['khan'])
                    if detailed_address['province']:
                        address_parts.append(detailed_address['province'])
                    if detailed_address['country']:
                        address_parts.append(detailed_address['country'])
                    
                    # Add building details if available
                    building_parts = []
                    if detailed_address['building_name']:
                        building_parts.append(detailed_address['building_name'])
                    if detailed_address['floor_number']:
                        building_parts.append(f"Floor {detailed_address['floor_number']}")
                    if detailed_address['unit_number']:
                        building_parts.append(f"Unit {detailed_address['unit_number']}")
                    
                    if building_parts:
                        address_parts.extend(building_parts)
                    
                    customer_address = ', '.join(filter(None, address_parts))
            else:
                # Fallback to simple address from customers table
                customer_address = customer.get('address', 'N/A')
                app.logger.info(f"   No detailed address found, using simple address: {customer_address}")
            
            # Add the formatted address to the order object
            order['customer_address'] = customer_address if customer_address and customer_address.strip() else 'N/A'
            
            # Debug logging
            app.logger.info(f"🏠 ADDRESS DEBUG for customer {order['customer_id']}:")
            app.logger.info(f"   Detailed address query result: {detailed_address}")
            app.logger.info(f"   Built address: {customer_address}")
            app.logger.info(f"   Final address: {order['customer_address']}")
            
            # Add customer information to the order object
            order['first_name'] = customer.get('first_name', '')
            order['last_name'] = customer.get('last_name', '')
            order['email'] = customer.get('email', '')
            order['phone'] = customer.get('phone', '')
            
            cur.close()
            conn.close()

            # Get order items
            order_items = Order.get_order_items(order_id)
            app.logger.info(f"📦 Order items: {order_items}")

            # Calculate invoice summary with discount information
            invoice_summary = {
                'original_total': 0,
                'item_discount_total': 0,
                'volume_discount_amount': float(order.get('volume_discount_amount', 0)),
                'volume_discount_percentage': float(order.get('volume_discount_percentage', 0)),
                'volume_discount_rule_id': order.get('volume_discount_rule_id'),
                'total_discount': 0,
                'has_discounts': False,
                'has_volume_discount': False
            }

            # Calculate item-level discounts
            for item in order_items:
                item_original_total = float(item['quantity']) * float(item['original_price'])
                item_discount_total = float(item['quantity']) * float(item['discount_amount'])

                invoice_summary['original_total'] += item_original_total
                invoice_summary['item_discount_total'] += item_discount_total

                if item['has_discount']:
                    invoice_summary['has_discounts'] = True

            # Add volume discount information
            if invoice_summary['volume_discount_amount'] > 0:
                invoice_summary['has_volume_discount'] = True
                invoice_summary['has_discounts'] = True

                # Get volume discount rule name
                if invoice_summary['volume_discount_rule_id']:
                    conn = mysql.connection
                    cur = conn.cursor()
                    cur.execute("SELECT name FROM volume_discount_rules WHERE id = %s",
                              (invoice_summary['volume_discount_rule_id'],))
                    rule = cur.fetchone()
                    invoice_summary['volume_discount_rule_name'] = rule[0] if rule else 'Volume Discount'
                    cur.close()
                else:
                    invoice_summary['volume_discount_rule_name'] = 'Volume Discount'

            # Calculate total discount (item discounts + volume discount)
            invoice_summary['total_discount'] = invoice_summary['item_discount_total'] + invoice_summary['volume_discount_amount']

            # Calculate what the total would have been without volume discount
            invoice_summary['subtotal_before_volume_discount'] = float(order['total_amount']) + invoice_summary['volume_discount_amount']

            app.logger.info("✅ Rendering order confirmation template")
            return render_template('order_confirmation.html',
                                 order=order,
                                 customer=customer,
                                 order_items=order_items,
                                 invoice_summary=invoice_summary,
                                 detailed_address=detailed_address)

        except Exception as e:
            app.logger.error(f"💥 Error viewing invoice: {str(e)}")
            flash('Error loading invoice', 'error')
            return redirect(url_for('show_dashboard'))

    @app.route('/api/orders/<int:order_id>/update-address', methods=['POST'])
    def update_order_address(order_id):
        """Update order address information."""
        try:
            data = request.get_json()
            app.logger.info(f"📍 Updating address for order {order_id}: {data}")
            
            # Get database connection
            conn = get_db()
            cur = conn.cursor()
            
            # Update order table with basic info
            cur.execute("""
                UPDATE orders 
                SET first_name = %s, last_name = %s, phone = %s, email = %s
                WHERE id = %s
            """, (
                data.get('first_name'),
                data.get('last_name'), 
                data.get('phone'),
                data.get('email'),
                order_id
            ))
            
            # Update or insert detailed address
            cur.execute("""
                SELECT id FROM customer_addresses 
                WHERE customer_id = (SELECT customer_id FROM orders WHERE id = %s) 
                AND is_active = TRUE
                LIMIT 1
            """, (order_id,))
            
            existing_address = cur.fetchone()
            
            if existing_address:
                # Update existing address
                cur.execute("""
                    UPDATE customer_addresses 
                    SET house_number = %s, street_name = %s, village = %s, sangkat = %s,
                        commune = %s, khan = %s, province = %s, country = %s,
                        delivery_notes = %s
                    WHERE id = %s
                """, (
                    data.get('house_number'),
                    data.get('street_name'),
                    data.get('village'),
                    data.get('sangkat'),
                    data.get('commune'),
                    data.get('khan'),
                    data.get('province'),
                    data.get('country'),
                    data.get('delivery_notes'),
                    existing_address[0]
                ))
            else:
                # Insert new address
                cur.execute("""
                    INSERT INTO customer_addresses 
                    (customer_id, house_number, street_name, village, sangkat, commune, khan, 
                     province, country, delivery_notes, is_active, is_default, created_at)
                    VALUES (
                        (SELECT customer_id FROM orders WHERE id = %s),
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, TRUE, NOW()
                    )
                """, (
                    order_id,
                    data.get('house_number'),
                    data.get('street_name'),
                    data.get('village'),
                    data.get('sangkat'),
                    data.get('commune'),
                    data.get('khan'),
                    data.get('province'),
                    data.get('country'),
                    data.get('delivery_notes')
                ))
            
            conn.commit()
            cur.close()
            
            app.logger.info(f"✅ Address updated successfully for order {order_id}")
            return jsonify({'success': True, 'message': 'Address updated successfully'})
            
        except Exception as e:
            app.logger.error(f"💥 Error updating address for order {order_id}: {str(e)}")
            return jsonify({'success': False, 'error': 'Failed to update address'}), 500

    @app.route('/mixed-cart/summary/<int:order_id>/<int:preorder_id>')
    def view_mixed_cart_summary(order_id, preorder_id):
        """Display summary for mixed cart payment (both order and pre-order)."""
        app.logger.info(f"🧾 Mixed cart summary requested for order_id: {order_id}, preorder_id: {preorder_id}")

        if 'username' not in session:
            app.logger.warning("❌ No username in session, redirecting to login")
            return redirect(url_for('auth.login'))

        try:
            # Get order details
            order = Order.get_by_id(order_id)
            if not order:
                flash('Order not found', 'error')
                return redirect(url_for('show_dashboard'))

            # Get pre-order details
            preorder = PreOrder.get_by_id(preorder_id)
            if not preorder:
                flash('Pre-order not found', 'error')
                return redirect(url_for('show_dashboard'))

            # Get customer details (should be same for both)
            customer = Customer.get_by_id(order['customer_id'])
            if not customer:
                flash('Customer not found', 'error')
                return redirect(url_for('show_dashboard'))

            # Get order items
            order_items = Order.get_order_items(order_id)

            # Get payment history for pre-order
            payment_history = PreOrderPayment.get_by_preorder(preorder_id)
            latest_payment = payment_history[-1] if payment_history else None

            return render_template('mixed_cart_summary.html',
                                 order=order,
                                 preorder=preorder,
                                 customer=customer,
                                 order_items=order_items,
                                 payment_history=payment_history,
                                 latest_payment=latest_payment)

        except Exception as e:
            app.logger.error(f"Error displaying mixed cart summary: {str(e)}")
            flash('Error loading summary', 'error')
            return redirect(url_for('show_dashboard'))

    @app.route('/thank-you/<int:order_id>')
    def thank_you_page(order_id):
        """Thank you page after successful payment"""
        try:
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            
            # Get order details
            cur.execute("""
                SELECT o.*
                FROM orders o
                WHERE o.id = %s
            """, (order_id,))
            
            order = cur.fetchone()
            
            if not order:
                flash('Order not found', 'error')
                return redirect(url_for('show_dashboard'))
            
            # Get order items with product details
            cur.execute("""
                SELECT oi.*, p.name as product_name, p.photo as image_url,
                       p.discount_percentage,
                       CASE
                           WHEN p.discount_percentage IS NOT NULL AND p.discount_percentage > 0
                           THEN 1
                           ELSE 0
                       END as has_discount
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = %s
            """, (order_id,))
            
            order_items = cur.fetchall()
            
            # Calculate total
            total = sum(item['price'] * item['quantity'] for item in order_items)
            
            return render_template('thank_you.html', order=order, order_items=order_items, total=total)
            
        except Exception as e:
            app.logger.error(f"Error loading thank you page for order {order_id}: {str(e)}")
            flash('Error loading thank you page', 'error')
            return redirect(url_for('show_dashboard'))
        finally:
            try:
                if 'cur' in locals():
                    cur.close()
                if 'conn' in locals():
                    conn.close()
            except:
                pass

    @app.route('/api/orders/<int:order_id>/payment-status')
    def check_order_payment_status(order_id):
        """Check if order payment is verified"""
        try:
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            
            # Check if payment is verified
            cur.execute("""
                SELECT pt.payment_verification_status, pt.qr_code_data
                FROM payment_tracking pt
                WHERE pt.order_id = %s 
                ORDER BY pt.created_at DESC 
                LIMIT 1
            """, (order_id,))
            
            payment_data = cur.fetchone()
            
            if payment_data and payment_data['payment_verification_status'] == 'verified':
                return jsonify({
                    'success': True,
                    'payment_verified': True,
                    'status': 'completed'
                })
            else:
                return jsonify({
                    'success': True,
                    'payment_verified': False,
                    'status': 'pending'
                })
                
        except Exception as e:
            app.logger.error(f"Error checking payment status for order {order_id}: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Failed to check payment status'
            }), 500
        finally:
            try:
                if 'cur' in locals():
                    cur.close()
                if 'conn' in locals():
                    conn.close()
            except:
                pass

    @app.route('/invoice-pdf/<int:order_id>')
    def invoice_pdf(order_id):
        """Generate PDF invoice for order"""
        try:
            app.logger.info(f"📄 Starting PDF generation for order {order_id}")
            # Get order details
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            
            # Get order information
            cur.execute("""
                SELECT o.*, c.first_name, c.last_name, c.email, c.phone
                FROM orders o
                JOIN customers c ON o.customer_id = c.id
                WHERE o.id = %s
            """, (order_id,))
            
            order_data = cur.fetchone()
            if not order_data:
                app.logger.error(f"❌ Order {order_id} not found")
                return jsonify({'error': 'Order not found'}), 404
            
            app.logger.info(f"✅ Order {order_id} found: {order_data['first_name']} {order_data['last_name']}")
            
            # Get order items
            cur.execute("""
                SELECT oi.*, p.name as product_name, 
                       SUBSTRING_INDEX(TRIM(p.name), ' ', 1) as brand,
                       p.photo as image_url,
                       p.discount_percentage,
                       CASE
                           WHEN p.discount_percentage IS NOT NULL AND p.discount_percentage > 0
                           THEN 1
                           ELSE 0
                       END as has_discount
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = %s
            """, (order_id,))
            
            order_items = cur.fetchall()
            
            # Get delivery address
            cur.execute("""
                SELECT ca.* FROM customer_addresses ca
                WHERE ca.customer_id = %s AND ca.is_default = 1
                LIMIT 1
            """, (order_data['customer_id'],))
            
            address_data = cur.fetchone()
            delivery_address = None
            if address_data:
                address_parts = []
                if address_data['house_number']:
                    address_parts.append(address_data['house_number'])
                if address_data['street_name']:
                    address_parts.append(address_data['street_name'])
                if address_data['commune']:
                    address_parts.append(address_data['commune'])
                if address_data['province']:
                    address_parts.append(address_data['province'])
                if address_data['country']:
                    address_parts.append(address_data['country'])
                delivery_address = ', '.join(address_parts)
            
            # Payment information is already available in order_data
            
            # Company information
            company_info = {
                'name': 'RusseyKeo Computer',
                'address': 'Phnom Penh, Cambodia',
                'phone': '+855 12 345 678',
                'email': 'info@russeykeo.com',
                'website': 'www.russeykeo.com'
            }
            
            # Generate PDF using ReportLab
            app.logger.info(f"📄 Generating PDF for order {order_id}")
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
            
            # Styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=30,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#2563eb')
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=12,
                textColor=colors.HexColor('#2563eb')
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=6
            )
            
            # Build PDF content
            story = []
            
            # Title
            story.append(Paragraph("INVOICE", title_style))
            story.append(Spacer(1, 20))
            
            # Company and Invoice Info
            order_date = order_data['order_date']
            if isinstance(order_date, str):
                order_date = datetime.strptime(order_date, '%Y-%m-%d %H:%M:%S')
            
            company_data = [
                [company_info['name'], f"Invoice #: {order_data['id']}"],
                [company_info['address'], f"Date: {order_date.strftime('%B %d, %Y')}"],
                [f"Phone: {company_info['phone']}", f"Due Date: {(order_date + timedelta(days=30)).strftime('%B %d, %Y')}"],
                [f"Email: {company_info['email']}", f"Payment Method: {order_data['payment_method'].replace('_', ' ').title()}"],
                [f"Website: {company_info['website']}", f"Status: {order_data['status']}"]
            ]
            
            company_table = Table(company_data, colWidths=[3*inch, 3*inch])
            company_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            story.append(company_table)
            story.append(Spacer(1, 20))
            
            # Customer Information
            story.append(Paragraph("Bill To:", heading_style))
            customer_info = f"""
            <b>{order_data['first_name']} {order_data['last_name']}</b><br/>
            {order_data['email']}<br/>
            {order_data['phone']}<br/>
            """
            if delivery_address:
                customer_info += f"{delivery_address}<br/>"
            
            story.append(Paragraph(customer_info, normal_style))
            story.append(Spacer(1, 20))
            
            # Payment Status
            status_color = colors.green if order_data['status'] == 'COMPLETED' else colors.orange
            status_text = "✓ PAYMENT COMPLETED" if order_data['status'] == 'COMPLETED' else "⏳ PAYMENT PENDING"
            story.append(Paragraph(f"<b>Payment Status:</b> <font color='{status_color.hexval()}'>{status_text}</font>", normal_style))
            story.append(Spacer(1, 20))
            
            # Items Table
            story.append(Paragraph("Order Items:", heading_style))
            
            # Table data
            table_data = [['#', 'Description', 'Brand', 'Qty', 'Unit Price', 'Total']]
            
            for i, item in enumerate(order_items, 1):
                discount_text = f" ({item['discount_percentage']}% off)" if item['has_discount'] else ""
                table_data.append([
                    str(i),
                    f"{item['product_name']}{discount_text}",
                    item['brand'],
                    str(item['quantity']),
                    f"${item['price']:.2f}",
                    f"${item['price'] * item['quantity']:.2f}"
                ])
            
            # Create table
            items_table = Table(table_data, colWidths=[0.5*inch, 2.5*inch, 1*inch, 0.5*inch, 1*inch, 1*inch])
            items_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('ALIGN', (1, 1), (1, -1), 'LEFT'),  # Description left-aligned
            ]))
            
            story.append(items_table)
            story.append(Spacer(1, 20))
            
            # Totals
            subtotal = float(order_data['total_amount'] or 0)
            total = subtotal
            
            totals_data = [
                ['Subtotal:', f"${subtotal:.2f}"],
                ['Tax:', "$0.00"],
                ['Shipping:', "$0.00"],
                ['TOTAL:', f"${total:.2f}"]
            ]
            
            totals_table = Table(totals_data, colWidths=[2*inch, 1*inch])
            totals_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
                ('FONTSIZE', (0, -1), (-1, -1), 12),
            ]))
            
            story.append(totals_table)
            story.append(Spacer(1, 30))
            
            # Payment Information
            if order_data['payment_method'] == 'KHQR_BAKONG':
                story.append(Paragraph("Payment Information:", heading_style))
                story.append(Paragraph(f"<b>Payment Method:</b> KHQR Bakong", normal_style))
                story.append(Paragraph(f"<b>Amount:</b> ${float(order_data['total_amount'] or 0):.2f}", normal_style))
                story.append(Paragraph(f"<b>Status:</b> {order_data['status']}", normal_style))
                story.append(Spacer(1, 20))
            
            # Terms and Conditions
            story.append(Paragraph("Terms and Conditions:", heading_style))
            terms_text = """
            • Payment is due within 30 days of invoice date.<br/>
            • Late payments may incur a 1.5% monthly service charge.<br/>
            • All sales are final. Returns accepted within 7 days of delivery.<br/>
            • Warranty terms apply as per manufacturer specifications.<br/>
            • For support, contact us at {company_email} or {company_phone}.<br/>
            """.format(company_email=company_info['email'], company_phone=company_info['phone'])
            
            story.append(Paragraph(terms_text, normal_style))
            story.append(Spacer(1, 20))
            
            # Footer
            footer_text = f"""
            <b>{company_info['name']}</b><br/>
            {company_info['address']} | Phone: {company_info['phone']} | Email: {company_info['email']}<br/>
            Thank you for your business!<br/>
            <i>This invoice was generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</i>
            """
            story.append(Paragraph(footer_text, normal_style))
            
            # Build PDF
            app.logger.info(f"📄 Building PDF for order {order_id}")
            doc.build(story)
            pdf_bytes = buffer.getvalue()
            buffer.close()
            
            app.logger.info(f"✅ PDF generated successfully for order {order_id}, size: {len(pdf_bytes)} bytes")
            
            # Return PDF as response
            response = make_response(pdf_bytes)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'inline; filename="invoice_{order_id}.pdf"'
            
            return response
            
        except Exception as e:
            app.logger.error(f"❌ Error generating PDF invoice for order {order_id}: {str(e)}")
            return jsonify({'error': 'Failed to generate PDF invoice'}), 500
        finally:
            try:
                if 'cur' in locals():
                    cur.close()
                if 'conn' in locals():
                    conn.close()
            except:
                pass

    @app.route('/invoice/<int:order_id>')
    def view_invoice(order_id):
        """Display invoice page for payment processing (QR generation and verification)."""
        app.logger.info(f"🧾 Invoice payment processing requested for order_id: {order_id}")
        
        try:
            # Get order details
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            
            # Get order information
            cur.execute("""
                SELECT o.*, c.first_name, c.last_name, c.email, c.phone, c.address
                FROM orders o
                LEFT JOIN customers c ON o.customer_id = c.id
                WHERE o.id = %s
            """, (order_id,))
            
            order = cur.fetchone()
            
            if not order:
                flash('Order not found', 'error')
                return redirect(url_for('show_dashboard'))
            
            # Get order items
            cur.execute("""
                SELECT oi.*, p.name as product_name, 
                       SUBSTRING_INDEX(TRIM(p.name), ' ', 1) as brand, 
                       p.photo as image_url
                FROM order_items oi
                LEFT JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = %s
            """, (order_id,))
            
            order_items = cur.fetchall()
            
            # Process image URLs to make them absolute paths
            for item in order_items:
                if item['image_url']:
                    # If it's already a full URL, keep it as is
                    if item['image_url'].startswith('http'):
                        continue
                    # Otherwise, make it a static file path
                    item['image_url'] = f"/static/uploads/products/{item['image_url']}"
                else:
                    item['image_url'] = None
            
            # Get detailed customer address from customer_addresses table
            cur.execute("""
                SELECT house_number, street_name, street_number, village, sangkat, commune, khan,
                       province, country, building_name, floor_number, unit_number, 
                       landmark, delivery_notes
                FROM customer_addresses 
                WHERE customer_id = %s AND is_active = TRUE 
                ORDER BY is_default DESC, id DESC 
                LIMIT 1
            """, (order['customer_id'],))
            
            detailed_address = cur.fetchone()
            
            if detailed_address:
                # Check if street_name contains full address (common case)
                if detailed_address['street_name'] and detailed_address['street_name'].strip():
                    # Use street_name as the main address if it contains full address
                    customer_address = detailed_address['street_name'].strip()
                    
                    # Add province and country if they exist and aren't already in street_name
                    if detailed_address['province'] and detailed_address['province'] not in customer_address:
                        customer_address += f", {detailed_address['province']}"
                    if detailed_address['country'] and detailed_address['country'] not in customer_address:
                        customer_address += f", {detailed_address['country']}"
                else:
                    # Build complete address from atomic components
                    address_parts = []
                    if detailed_address['house_number']:
                        address_parts.append(detailed_address['house_number'])
                    if detailed_address['street_name']:
                        if detailed_address['street_number']:
                            address_parts.append(f"st{detailed_address['street_number']}")
                        address_parts.append(detailed_address['street_name'])
                    if detailed_address['village']:
                        address_parts.append(detailed_address['village'])
                    if detailed_address['sangkat']:
                        address_parts.append(detailed_address['sangkat'])
                    if detailed_address['commune']:
                        address_parts.append(detailed_address['commune'])
                    if detailed_address['khan']:
                        address_parts.append(detailed_address['khan'])
                    if detailed_address['province']:
                        address_parts.append(detailed_address['province'])
                    if detailed_address['country']:
                        address_parts.append(detailed_address['country'])
                    
                    # Add building details if available
                    building_parts = []
                    if detailed_address['building_name']:
                        building_parts.append(detailed_address['building_name'])
                    if detailed_address['floor_number']:
                        building_parts.append(f"Floor {detailed_address['floor_number']}")
                    if detailed_address['unit_number']:
                        building_parts.append(f"Unit {detailed_address['unit_number']}")
                    
                    if building_parts:
                        address_parts.append(", ".join(building_parts))
                    
                    # Add landmark if available
                    if detailed_address['landmark']:
                        address_parts.append(f"Near {detailed_address['landmark']}")
                    
                    customer_address = ", ".join(address_parts)
                
                # Add delivery notes if available
                if detailed_address['delivery_notes']:
                    customer_address += f"\n\nDelivery Notes: {detailed_address['delivery_notes']}"
            else:
                # Fallback to basic address from customers table
                customer_address = order.get('address', 'No address provided')
            
            cur.close()
            conn.close()
            
            # Calculate totals
            subtotal = sum(float(item['price']) * item['quantity'] for item in order_items)
            total = float(order['total_amount'])
            
            return render_template('invoice.html',
                                 order=order,
                                 order_items=order_items,
                                 subtotal=subtotal,
                                 total=total,
                                 customer_address=customer_address)
            
        except Exception as e:
            app.logger.error(f"Error loading invoice: {str(e)}")
            flash('Error loading invoice', 'error')
            return redirect(url_for('show_dashboard'))

    @app.route('/oldinvoice/<int:order_id>')
    def view_old_invoice(order_id):
        """Display old invoice page directly after cart checkout."""
        app.logger.info(f"🧾 Old invoice requested for order_id: {order_id}")
        app.logger.info(f"👤 Session data: {dict(session)}")

        try:
            # Get order details
            app.logger.info(f"🔍 Looking for order with ID: {order_id}")
            order = Order.get_by_id(order_id)
            app.logger.info(f"📋 Order found: {order}")

            if not order:
                app.logger.error(f"❌ Order {order_id} not found")
                flash('Order not found', 'error')
                return redirect(url_for('show_dashboard'))

            # Check if payment method needs to be updated from URL parameters
            payment_confirmed = request.args.get('payment_confirmed') == 'true'
            method = request.args.get('method')
            
            if payment_confirmed and method:
                # Map URL method to database method
                method_mapping = {
                    'cash': 'Cash',
                    'pay_on_delivery': 'Pay on Delivery', 
                    'khqr': 'KHQR_BAKONG'
                }
                
                db_method = method_mapping.get(method, method)
                
                # Update payment method in database if it's different
                if order.get('payment_method') != db_method:
                    conn = get_db()
                    cur = conn.cursor()
                    try:
                        cur.execute("""
                            UPDATE orders 
                            SET payment_method = %s
                            WHERE id = %s
                        """, (db_method, order_id))
                        conn.commit()
                        app.logger.info(f"✅ Updated payment method for order {order_id} to {db_method}")
                        
                        # Update the order object for display
                        order['payment_method'] = db_method
                    finally:
                        cur.close()
                        conn.close()

            # Get customer details
            customer = Customer.get_by_id(order['customer_id'])
            if not customer:
                flash('Customer not found', 'error')
                return redirect(url_for('show_dashboard'))

            # Get detailed customer address from customer_addresses table
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            
            # Try to get detailed address first
            cur.execute("""
                SELECT house_number, street_name, street_number, village, sangkat, commune, khan,
                       province, country, building_name, floor_number, unit_number, 
                       landmark, delivery_notes
                FROM customer_addresses 
                WHERE customer_id = %s AND is_active = TRUE 
                ORDER BY is_default DESC, id DESC 
                LIMIT 1
            """, (order['customer_id'],))
            
            detailed_address = cur.fetchone()
            
            if detailed_address:
                # Check if street_name contains full address (common case)
                if detailed_address['street_name'] and detailed_address['street_name'].strip():
                    # Use street_name as the main address if it contains full address
                    customer_address = detailed_address['street_name'].strip()
                    
                    # Add province and country if they exist and aren't already in street_name
                    if detailed_address['province'] and detailed_address['province'] not in customer_address:
                        customer_address += f", {detailed_address['province']}"
                    if detailed_address['country'] and detailed_address['country'] not in customer_address:
                        customer_address += f", {detailed_address['country']}"
                else:
                    # Build complete address from atomic components
                    address_parts = []
                    if detailed_address['house_number']:
                        address_parts.append(detailed_address['house_number'])
                    if detailed_address['street_name']:
                        if detailed_address['street_number']:
                            address_parts.append(f"st{detailed_address['street_number']}")
                        address_parts.append(detailed_address['street_name'])
                    if detailed_address['village']:
                        address_parts.append(detailed_address['village'])
                    if detailed_address['sangkat']:
                        address_parts.append(detailed_address['sangkat'])
                    if detailed_address['commune']:
                        address_parts.append(detailed_address['commune'])
                    if detailed_address['khan']:
                        address_parts.append(detailed_address['khan'])
                    if detailed_address['province']:
                        address_parts.append(detailed_address['province'])
                    if detailed_address['country']:
                        address_parts.append(detailed_address['country'])
                    
                    # Add building details if available
                    building_parts = []
                    if detailed_address['building_name']:
                        building_parts.append(detailed_address['building_name'])
                    if detailed_address['floor_number']:
                        building_parts.append(f"Floor {detailed_address['floor_number']}")
                    if detailed_address['unit_number']:
                        building_parts.append(f"Unit {detailed_address['unit_number']}")
                    
                    if building_parts:
                        address_parts.extend(building_parts)
                    
                    customer_address = ', '.join(filter(None, address_parts))
            else:
                # Fallback to simple address from customers table
                customer_address = customer.get('address', 'N/A')
                app.logger.info(f"   No detailed address found, using simple address: {customer_address}")
            
            # Add the formatted address to the order object
            order['customer_address'] = customer_address if customer_address and customer_address.strip() else 'N/A'
            
            # Debug logging
            app.logger.info(f"🏠 ADDRESS DEBUG for customer {order['customer_id']}:")
            app.logger.info(f"   Detailed address query result: {detailed_address}")
            app.logger.info(f"   Built address: {customer_address}")
            app.logger.info(f"   Final address: {order['customer_address']}")
            
            # Add customer information to the order object
            order['first_name'] = customer.get('first_name', '')
            order['last_name'] = customer.get('last_name', '')
            order['email'] = customer.get('email', '')
            order['phone'] = customer.get('phone', '')
            
            cur.close()
            conn.close()

            # Get order items
            order_items = Order.get_order_items(order_id)
            app.logger.info(f"📦 Order items: {order_items}")

            # Calculate invoice summary with discount information
            invoice_summary = {
                'original_total': 0,
                'item_discount_total': 0,
                'volume_discount_amount': float(order.get('volume_discount_amount', 0)),
                'volume_discount_percentage': float(order.get('volume_discount_percentage', 0)),
                'volume_discount_rule_id': order.get('volume_discount_rule_id'),
                'total_discount': 0,
                'has_discounts': False,
                'has_volume_discount': False
            }

            # Calculate item-level discounts
            for item in order_items:
                item_original_total = float(item['quantity']) * float(item['original_price'])
                item_discount_total = float(item['quantity']) * float(item['discount_amount'])

                invoice_summary['original_total'] += item_original_total
                invoice_summary['item_discount_total'] += item_discount_total

                if item['has_discount']:
                    invoice_summary['has_discounts'] = True

            # Add volume discount information
            if invoice_summary['volume_discount_amount'] > 0:
                invoice_summary['has_volume_discount'] = True
                invoice_summary['has_discounts'] = True

                # Get volume discount rule name
                if invoice_summary['volume_discount_rule_id']:
                    conn = mysql.connection
                    cur = conn.cursor()
                    cur.execute("SELECT name FROM volume_discount_rules WHERE id = %s",
                              (invoice_summary['volume_discount_rule_id'],))
                    rule = cur.fetchone()
                    invoice_summary['volume_discount_rule_name'] = rule[0] if rule else 'Volume Discount'
                    cur.close()
                else:
                    invoice_summary['volume_discount_rule_name'] = 'Volume Discount'

            # Calculate total discount (item discounts + volume discount)
            invoice_summary['total_discount'] = invoice_summary['item_discount_total'] + invoice_summary['volume_discount_amount']

            # Calculate what the total would have been without volume discount
            invoice_summary['subtotal_before_volume_discount'] = float(order['total_amount']) + invoice_summary['volume_discount_amount']

            app.logger.info("✅ Rendering old invoice template")
            return render_template('oldnvoice.html',
                                 order=order,
                                 customer=customer,
                                 order_items=order_items,
                                 invoice_summary=invoice_summary,
                                 detailed_address=detailed_address)

        except Exception as e:
            app.logger.error(f"💥 Error viewing old invoice: {str(e)}")
            flash('Error loading invoice', 'error')
            return redirect(url_for('show_dashboard'))

    @app.route('/preorder/invoice/<int:preorder_id>')
    def view_preorder_invoice(preorder_id):
        """Display invoice for pre-order payment."""
        app.logger.info(f"🧾 Pre-order invoice requested for preorder_id: {preorder_id}")
        app.logger.info(f"👤 Session data: {dict(session)}")

        if 'username' not in session:
            app.logger.warning("❌ No username in session, redirecting to login")
            return redirect(url_for('auth.login'))

        try:
            from models import PreOrder, Customer, PreOrderPayment

            # Get pre-order details
            app.logger.info(f"🔍 Looking for pre-order with ID: {preorder_id}")
            preorder = PreOrder.get_by_id(preorder_id)
            app.logger.info(f"📋 Pre-order found: {preorder}")

            if not preorder:
                app.logger.error(f"❌ Pre-order {preorder_id} not found")
                flash('Pre-order not found', 'error')
                return redirect(url_for('show_dashboard'))

            # Verify ownership (customers can only view their own pre-orders)
            if session.get('role') == 'customer' and preorder['customer_id'] != session.get('user_id'):
                app.logger.warning(f"❌ Customer {session.get('user_id')} trying to access pre-order {preorder_id} owned by {preorder['customer_id']}")
                flash('Access denied', 'error')
                return redirect(url_for('show_dashboard'))

            # Get customer details
            customer = Customer.get_by_id(preorder['customer_id'])
            if not customer:
                flash('Customer not found', 'error')
                return redirect(url_for('show_dashboard'))

            # Get payment history for this pre-order
            payment_history = PreOrderPayment.get_by_preorder(preorder_id)
            app.logger.info(f"💳 Payment history: {payment_history}")

            # Get the latest payment (most recent)
            latest_payment = payment_history[-1] if payment_history else None

            app.logger.info("✅ Rendering pre-order invoice template")
            return render_template('preorder_invoice.html',
                                 preorder=preorder,
                                 customer=customer,
                                 payment_history=payment_history,
                                 latest_payment=latest_payment)

        except Exception as e:
            app.logger.error(f"Error displaying invoice: {str(e)}")
            flash('Error loading invoice', 'error')
            return redirect(url_for('show_dashboard'))

    @app.route('/api/payment/cleanup', methods=['POST'])
    def cleanup_expired_sessions():
        """Clean up expired payment sessions."""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        try:
            PaymentSession.cleanup_expired_sessions()
            return jsonify({
                'success': True,
                'message': 'Expired sessions cleaned up'
            })
        except Exception as e:
            app.logger.error(f"Error cleaning up sessions: {str(e)}")
            return jsonify({'success': False, 'error': 'Failed to cleanup sessions'}), 500

    # Pre-order API Endpoints
    @app.route('/api/preorders/create', methods=['POST'])
    def create_preorder():
        """Create a new pre-order"""
        app.logger.info(f"🔥 PREORDER CREATE STARTED - Session: {dict(session)}")

        if 'username' not in session:
            app.logger.error("❌ No username in session for preorder creation")
            return jsonify({'success': False, 'error': 'Please log in to place pre-orders'}), 401

        try:
            data = request.get_json()
            app.logger.info(f"📦 Preorder data received: {data}")

            product_id = data.get('product_id')
            quantity = data.get('quantity', 1)
            deposit_percentage = data.get('deposit_percentage', 0)  # 0, 25, 50, 100
            payment_method = data.get('payment_method')  # 'Cash' or 'QR Payment'
            notes = data.get('notes', '')

            if not product_id:
                return jsonify({'success': False, 'error': 'Product ID is required'}), 400

            # Get product details
            product = Product.get_by_id(product_id)
            if not product:
                return jsonify({'success': False, 'error': 'Product not found'}), 404

            # Check if pre-orders are allowed for this product
            if not product.get('allow_preorder', True):
                return jsonify({'success': False, 'error': 'Pre-orders not available for this product'}), 400

            # Check if product is actually out of stock
            if product.get('stock_quantity', 0) > 0:
                return jsonify({'success': False, 'error': 'Product is currently in stock. Please add to cart instead.'}), 400

            # Get customer information
            from models import Customer

            # Check if user is a customer or staff (for testing)
            if session.get('role') not in ['customer', 'staff', 'admin', 'super_admin']:
                return jsonify({'success': False, 'error': 'Only customers and staff can place pre-orders'}), 403

            customer_id = session.get('user_id')
            if not customer_id:
                return jsonify({'success': False, 'error': 'Customer ID not found in session'}), 401

            customer = Customer.get_by_id(customer_id)
            if not customer:
                return jsonify({'success': False, 'error': 'Customer not found'}), 404

            # Calculate deposit amount
            expected_price = float(product['price'])
            deposit_amount = 0.00
            deposit_payment_method = None

            if deposit_percentage > 0:
                deposit_amount = (expected_price * quantity * deposit_percentage) / 100
                deposit_payment_method = payment_method

            # Create pre-order
            from models import PreOrder
            pre_order_id = PreOrder.create(
                customer_id=customer['id'],
                product_id=product_id,
                quantity=quantity,
                expected_price=expected_price,
                deposit_amount=deposit_amount,
                deposit_payment_method=deposit_payment_method,
                expected_availability_date=product.get('expected_restock_date'),
                notes=notes
            )

            app.logger.info(f"✅ Pre-order created: {pre_order_id} for customer {customer['id']}")

            response_data = {
                'success': True,
                'pre_order_id': pre_order_id,
                'message': 'Pre-order created successfully',
                'deposit_amount': deposit_amount,
                'expected_price': expected_price,
                'total_amount': expected_price * quantity
            }

            app.logger.info(f"🎉 PREORDER CREATE SUCCESS - Returning: {response_data}")
            return jsonify(response_data)

        except Exception as e:
            app.logger.error(f"Error creating pre-order: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/preorders/customer', methods=['GET'])
    def get_customer_preorders():
        """Get all pre-orders for the logged-in customer"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        try:
            from models import Customer, PreOrder

            # Check if user is a customer or staff (for testing)
            if session.get('role') not in ['customer', 'staff', 'admin', 'super_admin']:
                return jsonify({'success': False, 'error': 'Only customers and staff can view pre-orders'}), 403

            customer_id = session.get('user_id')
            if not customer_id:
                return jsonify({'success': False, 'error': 'Customer ID not found in session'}), 401

            customer = Customer.get_by_id(customer_id)
            if not customer:
                return jsonify({'success': False, 'error': 'Customer not found'}), 404

            status_filter = request.args.get('status')
            pre_orders = PreOrder.get_by_customer(customer['id'], status_filter)

            return jsonify({
                'success': True,
                'pre_orders': pre_orders
            })

        except Exception as e:
            app.logger.error(f"Error fetching customer pre-orders: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/preorders/status', methods=['GET'])
    def get_preorder_status():
        """Get pre-order status for multiple products (for button state management)"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        try:
            from models import Customer, PreOrder

            customer_id = session.get('user_id')
            if not customer_id:
                return jsonify({'success': False, 'error': 'Customer ID not found in session'}), 401

            customer = Customer.get_by_id(customer_id)
            if not customer:
                return jsonify({'success': False, 'error': 'Customer not found'}), 404

            # Get product IDs from query parameter (comma-separated)
            product_ids_param = request.args.get('product_ids', '')
            if not product_ids_param:
                return jsonify({'success': True, 'preorder_status': {}})

            try:
                product_ids = [int(pid.strip()) for pid in product_ids_param.split(',') if pid.strip()]
            except ValueError:
                return jsonify({'success': False, 'error': 'Invalid product IDs format'}), 400

            # Get active pre-orders for these products
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            try:
                if product_ids:
                    placeholders = ','.join(['%s'] * len(product_ids))
                    query = f"""
                        SELECT product_id, id as preorder_id, status, quantity, created_date
                        FROM pre_orders
                        WHERE customer_id = %s
                        AND product_id IN ({placeholders})
                        AND status IN ('pending', 'confirmed', 'partially_paid', 'ready_for_pickup')
                        ORDER BY created_date DESC
                    """
                    cur.execute(query, [customer['id']] + product_ids)
                    preorders = cur.fetchall()

                    # Create status map: product_id -> preorder info
                    preorder_status = {}
                    for preorder in preorders:
                        product_id = preorder['product_id']
                        # Only include the most recent active pre-order per product
                        if product_id not in preorder_status:
                            preorder_status[product_id] = {
                                'has_preorder': True,
                                'preorder_id': preorder['preorder_id'],
                                'status': preorder['status'],
                                'quantity': preorder['quantity'],
                                'created_date': preorder['created_date'].isoformat() if preorder['created_date'] else None
                            }

                    return jsonify({
                        'success': True,
                        'preorder_status': preorder_status
                    })
                else:
                    return jsonify({'success': True, 'preorder_status': {}})

            finally:
                cur.close()
                conn.close()

        except Exception as e:
            app.logger.error(f"Error getting pre-order status: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/preorders/<int:preorder_id>/cancel', methods=['DELETE'])
    def cancel_preorder_toggle(preorder_id):
        """Cancel a pre-order (toggle functionality)"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        try:
            from models import Customer, PreOrder

            customer_id = session.get('user_id')
            if not customer_id:
                return jsonify({'success': False, 'error': 'Customer ID not found in session'}), 401

            customer = Customer.get_by_id(customer_id)
            if not customer:
                return jsonify({'success': False, 'error': 'Customer not found'}), 404

            # Get pre-order details to verify ownership
            preorder = PreOrder.get_by_id(preorder_id)
            if not preorder:
                return jsonify({'success': False, 'error': 'Pre-order not found'}), 404

            # Verify ownership
            if preorder['customer_id'] != customer['id']:
                return jsonify({'success': False, 'error': 'Access denied'}), 403

            # Allow cancellation for all statuses

            # Cancel the pre-order using the proper method
            reason = 'Customer requested cancellation'
            refund_info = PreOrder.cancel_pre_order(preorder_id, reason)

            app.logger.info(f"✅ Pre-order {preorder_id} cancelled by customer {customer['id']}")
            return jsonify({
                'success': True,
                'message': 'Pre-order cancelled successfully',
                'product_id': preorder['product_id'],
                'refund_info': refund_info
            })

        except Exception as e:
            app.logger.error(f"Error cancelling pre-order: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/preorders/<int:pre_order_id>', methods=['GET'])
    def get_preorder_details(pre_order_id):
        """Get details of a specific pre-order"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        try:
            from models import PreOrder, Customer
            customer = Customer.get_by_id(session['user_id'])
            if not customer:
                return jsonify({'success': False, 'error': 'Customer not found'}), 404

            pre_order = PreOrder.get_by_id(pre_order_id)
            if not pre_order:
                return jsonify({'success': False, 'error': 'Pre-order not found'}), 404

            # Check if this pre-order belongs to the logged-in customer
            if pre_order['customer_id'] != customer['id']:
                return jsonify({'success': False, 'error': 'Access denied'}), 403

            return jsonify({
                'success': True,
                'pre_order': pre_order
            })

        except Exception as e:
            app.logger.error(f"Error fetching pre-order details: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/preorders/<int:pre_order_id>/cancel', methods=['POST'])
    def cancel_preorder(pre_order_id):
        """Cancel a pre-order"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        try:
            from models import PreOrder, Customer

            # Check if user is a customer or staff (for testing)
            if session.get('role') not in ['customer', 'staff', 'admin', 'super_admin']:
                return jsonify({'success': False, 'error': 'Only customers and staff can cancel pre-orders'}), 403

            customer_id = session.get('user_id')
            if not customer_id:
                return jsonify({'success': False, 'error': 'Customer ID not found in session'}), 401

            pre_order = PreOrder.get_by_id(pre_order_id)
            if not pre_order:
                return jsonify({'success': False, 'error': 'Pre-order not found'}), 404

            # Check if this pre-order belongs to the logged-in customer
            if pre_order['customer_id'] != customer_id:
                return jsonify({'success': False, 'error': 'Access denied'}), 403

            # Allow cancellation for all statuses

            data = request.get_json()
            reason = data.get('reason', 'Customer requested cancellation')

            refund_info = PreOrder.cancel_pre_order(pre_order_id, reason)

            return jsonify({
                'success': True,
                'message': 'Pre-order cancelled successfully',
                'refund_info': refund_info
            })

        except Exception as e:
            app.logger.error(f"Error cancelling pre-order: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/preorders/<int:pre_order_id>/deposit', methods=['POST'])
    def add_preorder_deposit(pre_order_id):
        """Add deposit payment to a pre-order"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        try:
            from models import PreOrder, Customer

            # Check if user is a customer or staff (for testing)
            if session.get('role') not in ['customer', 'staff', 'admin', 'super_admin']:
                return jsonify({'success': False, 'error': 'Only customers and staff can add deposits'}), 403

            customer_id = session.get('user_id')
            if not customer_id:
                return jsonify({'success': False, 'error': 'Customer ID not found in session'}), 401

            pre_order = PreOrder.get_by_id(pre_order_id)
            if not pre_order:
                return jsonify({'success': False, 'error': 'Pre-order not found'}), 404

            # Check if this pre-order belongs to the logged-in customer
            if pre_order['customer_id'] != customer_id:
                return jsonify({'success': False, 'error': 'Access denied'}), 403

            data = request.get_json()
            deposit_amount = data.get('deposit_amount')
            payment_method = data.get('payment_method')

            if not deposit_amount or deposit_amount <= 0:
                return jsonify({'success': False, 'error': 'Valid deposit amount is required'}), 400

            if not payment_method:
                return jsonify({'success': False, 'error': 'Payment method is required'}), 400

            new_total_deposit = PreOrder.add_deposit_payment(pre_order_id, deposit_amount, payment_method)

            return jsonify({
                'success': True,
                'message': 'Deposit payment added successfully',
                'new_total_deposit': new_total_deposit
            })

        except Exception as e:
            app.logger.error(f"Error adding deposit payment: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/preorder/payment/qr', methods=['POST'])
    def create_preorder_qr_payment():
        """Create QR payment session for pre-order"""
        app.logger.info("🔄 PREORDER QR PAYMENT STARTED")

        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        try:
            from models import Customer, PreOrder

            # Get customer
            customer = Customer.get_by_id(session['user_id'])
            if not customer:
                return jsonify({'success': False, 'error': 'Customer not found'}), 404

            data = request.get_json()
            pre_order_id = data.get('pre_order_id')
            payment_amount = float(data.get('payment_amount', 0))
            payment_type = data.get('payment_type', 'deposit')  # 'deposit' or 'full'

            if not pre_order_id:
                return jsonify({'success': False, 'error': 'Pre-order ID is required'}), 400

            if payment_amount <= 0:
                return jsonify({'success': False, 'error': 'Valid payment amount is required'}), 400

            # Get pre-order details
            pre_order = PreOrder.get_by_id(pre_order_id)
            if not pre_order:
                return jsonify({'success': False, 'error': 'Pre-order not found'}), 404

            # Verify ownership
            if pre_order['customer_id'] != customer['id']:
                return jsonify({'success': False, 'error': 'Access denied'}), 403

            # Verify payment amount doesn't exceed remaining balance
            total_price = float(pre_order['expected_price']) * pre_order['quantity']
            remaining_balance = total_price - float(pre_order['deposit_amount'] or 0)

            if payment_amount > remaining_balance:
                return jsonify({'success': False, 'error': f'Payment amount exceeds remaining balance of ${remaining_balance:.2f}'}), 400

            # Create payment session for pre-order
            session_id = PaymentSession.create_preorder_session(
                pre_order=pre_order,
                customer_info=customer,
                payment_amount=payment_amount,
                payment_type=payment_type
            )

            # Generate QR code
            qr_generator = BakongQRGenerator(use_static_qr=True)
            qr_data = qr_generator.generate_payment_qr(
                amount=payment_amount,
                currency="USD",
                reference_id=f"PREORDER_{pre_order_id}_{payment_type.upper()}"
            )

            # Update session with QR data
            PaymentSession.update_session_status(session_id, 'pending', {
                'qr_data': qr_data,
                'pre_order_id': pre_order_id,
                'payment_type': payment_type
            })

            # Get updated session
            payment_session = PaymentSession.get_session(session_id)

            app.logger.info(f"✅ Pre-order QR payment session created: {session_id}")
            return jsonify({
                'success': True,
                'session': payment_session
            })

        except Exception as e:
            app.logger.error(f"Error creating pre-order QR payment: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/preorder/<int:pre_order_id>/payments', methods=['GET'])
    def get_preorder_payments(pre_order_id):
        """Get payment history for a specific pre-order"""
        try:
            # Check if user is logged in
            if 'username' not in session:
                return jsonify({'success': False, 'error': 'Authentication required'}), 401

            from models import Customer, PreOrder, PreOrderPayment

            # Get customer
            customer = Customer.get_by_id(session['user_id'])
            if not customer:
                return jsonify({'success': False, 'error': 'Customer not found'}), 404

            # Get pre-order details to verify ownership
            preorder = PreOrder.get_by_id(pre_order_id)
            if not preorder or preorder['customer_id'] != customer['id']:
                return jsonify({'success': False, 'error': 'Pre-order not found or access denied'}), 404

            # Get payment history
            payments = PreOrderPayment.get_by_preorder(pre_order_id)
            total_paid = PreOrderPayment.get_total_paid(pre_order_id)

            # Calculate remaining balance
            total_price = preorder['expected_price'] * preorder['quantity']
            remaining_balance = total_price - total_paid

            return jsonify({
                'success': True,
                'payments': payments,
                'total_paid': total_paid,
                'total_price': total_price,
                'remaining_balance': max(0, remaining_balance),
                'payment_progress': (total_paid / total_price) * 100 if total_price > 0 else 0
            })

        except Exception as e:
            app.logger.error(f"Error getting pre-order payments: {str(e)}")
            return jsonify({'success': False, 'error': 'Failed to retrieve payment history'}), 500

    @app.route('/api/preorder/payment/confirm', methods=['POST'])
    def confirm_preorder_payment():
        """Confirm pre-order payment completion"""
        app.logger.info("💳 PREORDER PAYMENT CONFIRMATION STARTED")

        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        try:
            data = request.get_json()
            session_id = data.get('session_id')

            if not session_id:
                return jsonify({'success': False, 'error': 'Session ID is required'}), 400

            # Get payment session
            payment_session = PaymentSession.get_session(session_id)
            if not payment_session:
                return jsonify({'success': False, 'error': 'Payment session not found'}), 404

            # Verify session belongs to current user
            customer = Customer.get_by_id(session['user_id'])
            if payment_session['customer_info']['id'] != customer['id']:
                return jsonify({'success': False, 'error': 'Access denied'}), 403

            # Get pre-order details
            pre_order_id = payment_session.get('pre_order_id')
            payment_amount = payment_session['payment_amount']
            payment_type = payment_session.get('payment_type', 'deposit')

            # Add payment to pre-order
            if payment_type == 'deposit':
                PreOrder.add_deposit_payment(pre_order_id, payment_amount, 'QR Payment')
            else:  # full payment
                PreOrder.add_deposit_payment(pre_order_id, payment_amount, 'QR Payment')

            # Update pre-order status based on payment
            pre_order = PreOrder.get_by_id(pre_order_id)
            total_price = float(pre_order['expected_price']) * pre_order['quantity']
            total_paid = float(pre_order['deposit_amount'] or 0)

            if total_paid >= total_price:
                # Full payment received
                PreOrder.update_status(pre_order_id, 'confirmed', 'Full payment received via QR code')
            else:
                # Partial payment
                PreOrder.update_status(pre_order_id, 'partially_paid', f'Partial payment of ${payment_amount:.2f} received via QR code')

            # Mark session as processed
            PaymentSession.update_session_status(session_id, 'processed', {
                'pre_order_id': pre_order_id,
                'payment_amount': payment_amount,
                'payment_type': payment_type
            })

            app.logger.info(f"✅ Pre-order payment confirmed: {pre_order_id}, Amount: ${payment_amount}")
            return jsonify({
                'success': True,
                'pre_order_id': pre_order_id,
                'payment_amount': payment_amount,
                'message': 'Payment confirmed successfully'
            })

        except Exception as e:
            app.logger.error(f"Error confirming pre-order payment: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/customer/preorders')
    def customer_preorders():
        """Customer pre-orders dashboard"""
        app.logger.info(f"🔍 Pre-orders route accessed. Session data: {dict(session)}")

        # Check session authentication
        if 'username' not in session or 'user_id' not in session:
            app.logger.warning(f"❌ Authentication failed. Username in session: {'username' in session}, User_id in session: {'user_id' in session}")
            flash('Please log in to view your pre-orders', 'error')
            return redirect(url_for('auth.login'))

        # Check user role
        user_role = session.get('role')
        app.logger.info(f"👤 User role: {user_role}")
        if user_role not in ['customer', 'staff', 'admin', 'super_admin']:
            app.logger.warning(f"❌ Access denied. User role '{user_role}' not authorized")
            flash('Access denied. Customer account required.', 'error')
            return redirect(url_for('show_dashboard'))

        try:
            from models import Customer, PreOrder, Order

            # Get user_id from session
            user_id = session['user_id']
            user_role = session.get('role')
            app.logger.info(f"🔍 Looking up customer with user_id: {user_id}, role: {user_role}")

            # Handle different user types
            if user_role == 'customer':
                # For customers, look up in customers table
                customer = Customer.get_by_id(user_id)
                app.logger.info(f"👤 Customer lookup result: {customer}")

                if not customer:
                    app.logger.error(f"❌ Customer not found for user_id: {user_id}")
                    flash('Customer not found', 'error')
                    return redirect(url_for('show_dashboard'))

                customer_id = customer['id']

            elif user_role in ['staff', 'admin', 'super_admin']:
                # For staff, create a mock customer object for testing
                # In production, you might want to restrict this or handle differently
                app.logger.info(f"🔧 Staff user accessing pre-orders for testing")

                # Get the first customer for testing purposes
                all_customers = Customer.get_all()
                if not all_customers:
                    flash('No customers found in system', 'error')
                    return redirect(url_for('show_dashboard'))

                customer = all_customers[0]  # Use first customer for staff testing
                customer_id = customer['id']
                app.logger.info(f"🔧 Using customer {customer_id} for staff testing")

            else:
                app.logger.error(f"❌ Unknown user role: {user_role}")
                flash('Invalid user role', 'error')
                return redirect(url_for('show_dashboard'))

            # Get customer's confirmed pre-orders only
            app.logger.info(f"📦 Fetching confirmed pre-orders for customer_id: {customer_id}")
            pre_orders = PreOrder.get_by_customer(customer_id, status='confirmed')
            app.logger.info(f"📦 Found {len(pre_orders) if pre_orders else 0} confirmed pre-orders")

            # Disable completed orders to prevent navigation conflicts
            app.logger.info(f"🚫 Completed orders disabled to prevent navigation conflicts")
            completed_orders = []

            app.logger.info("🎯 Successfully rendering customer_preorders.html")
            return render_template('customer_preorders.html',
                                 pre_orders=pre_orders,
                                 completed_orders=completed_orders,
                                 customer=customer)

        except Exception as e:
            app.logger.error(f"💥 Error loading customer pre-orders: {str(e)}")
            app.logger.error(f"💥 Exception type: {type(e)}")
            import traceback
            app.logger.error(f"💥 Traceback: {traceback.format_exc()}")
            flash('Error loading pre-orders', 'error')
            return redirect(url_for('show_dashboard'))

    @app.route('/debug/session')
    def debug_session():
        """Debug route to check session data"""
        return jsonify({
            'session_data': dict(session),
            'username_in_session': 'username' in session,
            'user_id_in_session': 'user_id' in session,
            'role_in_session': session.get('role'),
            'user_id_value': session.get('user_id')
        })

    @app.route('/api/customer/completed-orders')
    def get_customer_completed_orders():
        """API endpoint to get completed orders for the logged-in customer"""
        if 'username' not in session or 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Please log in to view orders'}), 401

        try:
            from models import Customer, Order

            # Get user info
            user_id = session['user_id']
            user_role = session.get('role')

            # Handle different user types (same logic as main route)
            if user_role == 'customer':
                customer = Customer.get_by_id(user_id)
                if not customer:
                    return jsonify({'success': False, 'error': 'Customer not found'}), 404
                customer_id = customer['id']
            elif user_role in ['staff', 'admin', 'super_admin']:
                # For staff testing, use first customer
                all_customers = Customer.get_all()
                if not all_customers:
                    return jsonify({'success': False, 'error': 'No customers found'}), 404
                customer_id = all_customers[0]['id']
            else:
                return jsonify({'success': False, 'error': 'Invalid user role'}), 403

            # Get completed orders safely
            completed_orders = Order.get_completed_orders_by_customer(customer_id)

            # Convert to JSON-safe format
            orders_data = []
            for order in completed_orders:
                order_data = {
                    'id': order['id'],
                    'order_date': str(order['order_date']) if order['order_date'] else 'Unknown',
                    'total_amount': float(order['total_amount']) if order['total_amount'] else 0.0,
                    'payment_method': order['payment_method'] or 'Unknown',
                    'approval_status': order.get('approval_status', 'Unknown'),
                    'transaction_id': order.get('transaction_id'),
                    'items': []
                }

                for item in order.get('items', []):
                    order_data['items'].append({
                        'product_id': item['product_id'],
                        'product_name': item['product_name'] or 'Unknown Product',
                        'product_photo': item['product_photo'] or 'default.jpg',
                        'quantity': int(item['quantity']) if item['quantity'] else 0,
                        'price': float(item['price']) if item['price'] else 0.0
                    })

                orders_data.append(order_data)

            return jsonify({
                'success': True,
                'completed_orders': orders_data,
                'count': len(orders_data)
            })

        except Exception as e:
            app.logger.error(f"Error fetching completed orders via API: {str(e)}")
            return jsonify({'success': False, 'error': 'Failed to load completed orders'}), 500

    # Completed orders API routes - now enabled
    @app.route('/api/orders/<int:order_id>/screenshot', methods=['GET'])
    def get_order_screenshot(order_id):
        """Get payment screenshot for an order"""
        try:
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            
            try:
                # Get order screenshot information
                cur.execute("""
                    SELECT payment_screenshot_path, screenshot_uploaded_at
                    FROM orders
                    WHERE id = %s
                """, (order_id,))
                
                order = cur.fetchone()
                
                if not order:
                    return jsonify({'success': False, 'error': 'Order not found'}), 404
                
                if not order['payment_screenshot_path']:
                    return jsonify({'success': False, 'error': 'No screenshot available for this order'}), 404
                
                # Check if the file actually exists on the server
                import os
                full_path = os.path.join(app.static_folder, order['payment_screenshot_path'])
                if not os.path.exists(full_path):
                    app.logger.warning(f"Screenshot file not found: {full_path}")
                    return jsonify({'success': False, 'error': 'Screenshot file not found on server'}), 404
                
                return jsonify({
                    'success': True,
                    'screenshot_path': order['payment_screenshot_path'],
                    'uploaded_at': order['screenshot_uploaded_at'].isoformat() if order['screenshot_uploaded_at'] else None
                })
                
            finally:
                cur.close()
                conn.close()
                
        except Exception as e:
            app.logger.error(f"Error fetching order screenshot: {str(e)}")
            return jsonify({'success': False, 'error': 'Failed to fetch screenshot'}), 500

    @app.route('/api/orders/<int:order_id>/reorder', methods=['POST'])
    def reorder_items(order_id):
        """Add all items from a completed order back to the cart"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in to reorder items'}), 401

        try:
            from models import Order, Customer

            # Get customer ID
            customer = Customer.get_by_id(session['user_id'])
            if not customer:
                return jsonify({'success': False, 'error': 'Customer not found'}), 404

            # Get order items
            order_items = Order.get_order_items(order_id)
            if not order_items:
                return jsonify({'success': False, 'error': 'Order not found or has no items'}), 404

            # Verify order belongs to customer
            order = Order.get_by_id(order_id)
            if not order or order['customer_id'] != customer['id']:
                return jsonify({'success': False, 'error': 'Order not found or access denied'}), 403

            # Initialize cart if it doesn't exist
            if 'cart' not in session:
                session['cart'] = []

            items_added = 0
            for item in order_items:
                # Check if item already exists in cart
                existing_item = None
                for cart_item in session['cart']:
                    if cart_item['product_id'] == item['product_id']:
                        existing_item = cart_item
                        break

                if existing_item:
                    existing_item['quantity'] += item['quantity']
                else:
                    session['cart'].append({
                        'product_id': item['product_id'],
                        'quantity': item['quantity']
                    })
                items_added += 1

            session.modified = True
            return jsonify({
                'success': True,
                'message': 'Items added to cart successfully',
                'items_added': items_added
            })

        except Exception as e:
            app.logger.error(f"Error reordering items: {str(e)}")
            return jsonify({'success': False, 'error': 'An error occurred while reordering items'}), 500

    @app.route('/api/orders/<int:order_id>/details')
    def get_order_details(order_id):
        """Get detailed information about a specific order"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in to view order details'}), 401

        try:
            from models import Order, Customer

            # Get customer ID
            customer = Customer.get_by_id(session['user_id'])
            if not customer:
                return jsonify({'success': False, 'error': 'Customer not found'}), 404

            # Get order details
            order = Order.get_by_id(order_id)
            if not order:
                return jsonify({'success': False, 'error': 'Order not found'}), 404

            # Verify order belongs to customer
            if order['customer_id'] != customer['id']:
                return jsonify({'success': False, 'error': 'Access denied'}), 403

            # Get order items
            order_items = Order.get_order_items(order_id)

            # Format the response
            order_data = {
                'id': order['id'],
                'order_date': order['order_date'].isoformat() if hasattr(order['order_date'], 'isoformat') else str(order['order_date']),
                'total_amount': float(order['total_amount']),
                'payment_method': order['payment_method'],
                'status': order['status'],
                'items': []
            }

            for item in order_items:
                order_data['items'].append({
                    'product_id': item['product_id'],
                    'product_name': item['product_name'],
                    'quantity': item['quantity'],
                    'price': float(item['price'])
                })

            return jsonify({'success': True, 'order': order_data})

        except Exception as e:
            app.logger.error(f"Error getting order details: {str(e)}")
            return jsonify({'success': False, 'error': 'An error occurred while loading order details'}), 500



    @app.route('/api/staff/preorders/<int:pre_order_id>/update-status', methods=['POST'])
    def update_preorder_status(pre_order_id):
        """Update pre-order status (staff only)"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        try:
            data = request.get_json()
            new_status = data.get('status')
            notes = data.get('notes')

            if not new_status:
                return jsonify({'success': False, 'error': 'Status is required'}), 400

            from models import PreOrder
            PreOrder.update_status(pre_order_id, new_status, notes)

            return jsonify({
                'success': True,
                'message': f'Pre-order status updated to {new_status}'
            })

        except Exception as e:
            app.logger.error(f"Error updating pre-order status: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/staff/preorders/<int:pre_order_id>/mark-ready', methods=['POST'])
    def mark_preorder_ready(pre_order_id):
        """Mark pre-order as ready for pickup (staff only)"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        try:
            from models import PreOrder
            PreOrder.mark_ready_for_pickup(pre_order_id)

            return jsonify({
                'success': True,
                'message': 'Pre-order marked as ready for pickup'
            })

        except Exception as e:
            app.logger.error(f"Error marking pre-order ready: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/staff/preorders/stats')
    def preorder_stats():
        """Get pre-order statistics for dashboard"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        try:
            from models import PreOrder
            stats = PreOrder.get_stats()
            return jsonify({
                'success': True,
                'stats': stats
            })

        except Exception as e:
            app.logger.error(f"Error getting pre-order stats: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/staff/preorders/recent')
    def recent_preorders():
        """Get recent pre-orders for dashboard table"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        try:
            from models import PreOrder
            # Get recent pre-orders (limit to 10 for dashboard)
            recent_preorders = PreOrder.get_recent_for_dashboard(limit=10)
            return jsonify({
                'success': True,
                'preorders': recent_preorders
            })

        except Exception as e:
            app.logger.error(f"Error getting recent pre-orders: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/staff/preorders')
    def api_staff_preorders():
        """AJAX API endpoint for staff pre-orders with pagination"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        try:
            from models import PreOrder

            # Get parameters
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('page_size', 10))
            status_filter = request.args.get('status')
            ajax = request.args.get('ajax')

            # If no status filter or empty string, show all statuses
            if not status_filter or status_filter == '':
                status_filter = None  # None means show all statuses

            # Get paginated pre-orders
            result = PreOrder.get_all_paginated(
                page=page,
                page_size=page_size,
                status=status_filter
            )

            return jsonify({
                'success': True,
                'preorders': result['pre_orders'],
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_count': result['total_count'],
                    'total_pages': result['total_pages']
                }
            })

        except Exception as e:
            app.logger.error(f"Error getting pre-orders via API: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/auth/staff/api/pre_order/<int:pre_order_id>/details', methods=['GET'])
    def staff_get_preorder_details(pre_order_id):
        """Get details of a specific pre-order (staff access)"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        try:
            from models import PreOrder

            pre_order = PreOrder.get_by_id(pre_order_id)
            if not pre_order:
                return jsonify({'success': False, 'error': 'Pre-order not found'}), 404

            return jsonify({
                'success': True,
                'pre_order': pre_order
            })

        except Exception as e:
            app.logger.error(f"Error fetching pre-order details: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/products/<int:product_id>/stock', methods=['GET'])
    def get_product_stock(product_id):
        """Get current stock level for a product"""
        try:
            from models import Product

            product = Product.get_by_id(product_id)
            if not product:
                return jsonify({'success': False, 'error': 'Product not found'}), 404

            return jsonify({
                'success': True,
                'stock': product.get('stock', 0),
                'product_name': product.get('name', '')
            })

        except Exception as e:
            app.logger.error(f"Error fetching product stock: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/orders/<int:order_id>/cancel-single-item', methods=['POST'])
    def cancel_single_order_item(order_id):
        """Cancel a specific item from a pending order"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        try:
            data = request.get_json()
            product_id = data.get('product_id')
            reason = data.get('reason', 'Out of stock')
            notes = data.get('notes', '')

            # Debug logging
            app.logger.info(f"Cancel item request - Order ID: {order_id}, Product ID: {product_id}, Reason: '{reason}', Notes: '{notes}'")

            if not product_id:
                return jsonify({'success': False, 'error': 'Product ID is required'}), 400

            conn = get_db()
            cur = conn.cursor(dictionary=True)

            try:
                # Check if order exists and is pending (only pending orders can be cancelled)
                cur.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
                order = cur.fetchone()

                if not order:
                    return jsonify({'success': False, 'error': 'Order not found'}), 404

                # Only allow cancellation for pending orders
                if order['status'].lower() != 'pending':
                    return jsonify({'success': False, 'error': f'Only pending orders can be cancelled. Current status: {order["status"].lower()}'}), 400

                # Check if item exists in order
                cur.execute("""
                    SELECT id, quantity, price FROM order_items
                    WHERE order_id = %s AND product_id = %s
                """, (order_id, product_id))
                order_item = cur.fetchone()

                if not order_item:
                    return jsonify({'success': False, 'error': 'Item not found in order'}), 404

                # Log the cancellation in the order_item_cancellations table
                staff_id = session.get('user_id', 1)  # Get actual staff ID from session

                try:
                    cur.execute("""
                        INSERT INTO order_item_cancellations
                        (order_id, order_item_id, product_id, cancelled_quantity, original_quantity, reason, cancelled_by_staff_id, notes, status, customer_notified)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (order_id, order_item['id'], product_id, order_item['quantity'], order_item['quantity'], reason, staff_id, notes, 'completed', True))
                    app.logger.info(f"Cancellation logged successfully with reason: {reason}")
                except Exception as log_error:
                    # If logging fails, continue with the cancellation but log the error
                    app.logger.error(f"Failed to log cancellation: {log_error}")
                    # Still proceed with the actual cancellation

                # Remove item from order
                cur.execute("""
                    DELETE FROM order_items
                    WHERE order_id = %s AND product_id = %s
                """, (order_id, product_id))

                # Check if order is now empty
                cur.execute("SELECT COUNT(*) as item_count FROM order_items WHERE order_id = %s", (order_id,))
                remaining_items = cur.fetchone()['item_count']

                if remaining_items == 0:
                    # Cancel the entire order if no items left
                    cur.execute("UPDATE orders SET status = 'CANCELLED' WHERE id = %s", (order_id,))

                conn.commit()

                # Create customer notification
                try:
                    from models import Notification

                    # Get product name for notification
                    cur.execute("SELECT name FROM products WHERE id = %s", (product_id,))
                    product_result = cur.fetchone()
                    product_name = product_result['name'] if product_result else f"Product ID {product_id}"

                    if remaining_items == 0:
                        notification_message = f"Your order #{order_id} has been cancelled due to {reason.lower()}."
                    else:
                        notification_message = f"Item '{product_name}' from your order #{order_id} has been cancelled due to {reason.lower()}."

                    Notification.create_notification(
                        customer_id=order['customer_id'],
                        message=notification_message,
                        notification_type='order_item_cancelled',
                        related_id=order_id
                    )
                    app.logger.info(f"Customer notification sent for order {order_id} item cancellation")
                except Exception as notification_error:
                    app.logger.error(f"Failed to send customer notification: {notification_error}")

                return jsonify({
                    'success': True,
                    'message': f'Item cancelled successfully. Customer has been notified.',
                    'order_cancelled': remaining_items == 0
                })

            finally:
                cur.close()
                conn.close()

        except Exception as e:
            app.logger.error(f"Error cancelling order item: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/staff/preorders/<int:pre_order_id>/confirm', methods=['POST'])
    def confirm_preorder(pre_order_id):
        """Confirm a pending pre-order (staff only)"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        try:
            from models import PreOrder

            # Get the pre-order
            preorder = PreOrder.get_by_id(pre_order_id)
            if not preorder:
                return jsonify({'success': False, 'error': 'Pre-order not found'}), 404

            # Check if it's pending
            if preorder['status'] != 'pending':
                return jsonify({'success': False, 'error': 'Only pending pre-orders can be confirmed'}), 400

            # Update status to confirmed
            PreOrder.update_status(pre_order_id, 'confirmed', f"Confirmed by staff: {session['username']}")

            return jsonify({
                'success': True,
                'message': 'Pre-order confirmed successfully'
            })

        except Exception as e:
            app.logger.error(f"Error confirming pre-order: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/staff/preorders/<int:pre_order_id>/complete', methods=['POST'])
    def complete_preorder(pre_order_id):
        """Complete a pre-order and notify customer"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        if session.get('role') not in ['staff', 'admin', 'super_admin']:
            return jsonify({'success': False, 'error': 'Insufficient permissions'}), 403

        try:
            from models import PreOrder, Notification, Product

            # Get the pre-order
            preorder = PreOrder.get_by_id(pre_order_id)
            if not preorder:
                return jsonify({'success': False, 'error': 'Pre-order not found'}), 404

            # Check if it's confirmed
            if preorder['status'] != 'confirmed':
                return jsonify({'success': False, 'error': 'Only confirmed pre-orders can be completed'}), 400

            # Check product stock
            product = Product.get_by_id(preorder['product_id'])
            if not product or product['stock'] <= 0:
                # Product is out of stock - notify admin and return error to staff
                app.logger.warning(f"🚨 STOCK ISSUE: Staff {session['username']} attempted to complete pre-order #{pre_order_id} for {preorder['product_name']} but product is out of stock (current stock: {product['stock'] if product else 0})")

                # Get customer details for admin notification
                customer = Customer.get_by_id(preorder['customer_id'])
                customer_name = f"{customer['first_name']} {customer['last_name']}" if customer else "Unknown Customer"

                # Create admin notification (you can implement this to show on admin dashboard)
                admin_message = f"Staff member {session['username']} attempted to complete pre-order #{pre_order_id} for {preorder['product_name']} (Customer: {customer_name}), but the product is currently out of stock."
                app.logger.error(f"📋 ADMIN ALERT: {admin_message}")

                return jsonify({
                    'success': False,
                    'error': f'Product "{preorder["product_name"]}" is currently out of stock (Stock: {product["stock"] if product else 0}). Admin has been notified.',
                    'stock_issue': True
                })

            # Product is in stock - proceed with completion
            # Update status to completed
            PreOrder.update_status(pre_order_id, 'completed', f"Completed by staff: {session['username']} - Product is ready for pickup")

            # Create notification for customer
            notification_message = f"Great news! Your pre-order #{pre_order_id} for {preorder['product_name']} is now ready for pickup. Please visit our store to collect your item."

            Notification.create_notification(
                customer_id=preorder['customer_id'],
                message=notification_message,
                notification_type='preorder_ready',
                related_id=pre_order_id
            )

            app.logger.info(f"✅ Pre-order {pre_order_id} completed and customer {preorder['customer_id']} notified")

            return jsonify({
                'success': True,
                'message': 'Pre-order completed and customer notified successfully'
            })

        except Exception as e:
            app.logger.error(f"Error completing pre-order: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/staff/preorders/<int:pre_order_id>/notify-stock-issue', methods=['POST'])
    def notify_stock_issue(pre_order_id):
        """Notify admin about stock issue for a pre-order"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        if session.get('role') not in ['staff', 'admin', 'super_admin']:
            return jsonify({'success': False, 'error': 'Insufficient permissions'}), 403

        try:
            from models import PreOrder, Customer

            # Get the pre-order details
            preorder = PreOrder.get_by_id(pre_order_id)
            if not preorder:
                return jsonify({'success': False, 'error': 'Pre-order not found'}), 404

            # Get customer details
            customer = Customer.get_by_id(preorder['customer_id'])
            if not customer:
                return jsonify({'success': False, 'error': 'Customer not found'}), 404

            # Log the stock issue for admin attention
            app.logger.warning(f"🚨 STOCK ISSUE: Staff {session['username']} attempted to complete pre-order #{pre_order_id} for {preorder['product_name']} but product is out of stock. Customer: {customer['first_name']} {customer['last_name']} ({customer['email']})")

            # You could also create a notification for admin users here
            # For now, we'll just log it and return success

            return jsonify({
                'success': True,
                'message': 'Admin has been notified about the stock issue'
            })

        except Exception as e:
            app.logger.error(f"Error notifying about stock issue: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/staff/preorders/<int:pre_order_id>/delete', methods=['DELETE'])
    def delete_preorder(pre_order_id):
        """Delete a pre-order (staff only, cancelled or pending status only)"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        try:
            from models import PreOrder

            # Delete the pre-order (validation is done in the model)
            PreOrder.delete_pre_order(pre_order_id)

            return jsonify({
                'success': True,
                'message': 'Pre-order deleted successfully'
            })

        except ValueError as e:
            # Handle validation errors (wrong status, not found, etc.)
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            app.logger.error(f"Error deleting pre-order: {str(e)}")
            return jsonify({'success': False, 'error': 'An unexpected error occurred'}), 500

    @app.route('/auth/staff/api/orders/<int:order_id>/confirm', methods=['POST'])
    def confirm_order(order_id):
        """Confirm a pending order (staff only)"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        try:
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            
            # Get order details
            cur.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
            order = cur.fetchone()
            
            if not order:
                return jsonify({'success': False, 'error': 'Order not found'}), 404
            
            # Check if order can be confirmed
            if order['status'] not in ['PENDING', 'COMPLETED']:
                return jsonify({'success': False, 'error': f'Order cannot be confirmed. Current status: {order["status"]}'}), 400
            
            # Update order status to confirmed
            cur.execute("UPDATE orders SET status = 'CONFIRMED', approval_status = 'Approved' WHERE id = %s", (order_id,))
            conn.commit()
            
            app.logger.info(f"Order {order_id} confirmed by staff: {session['username']}")
            
            return jsonify({
                'success': True,
                'message': f'Order #{order_id} confirmed successfully'
            })
            
        except Exception as e:
            app.logger.error(f"Error confirming order {order_id}: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()

    @app.route('/auth/staff/api/orders/<int:order_id>/reject', methods=['POST'])
    def reject_order(order_id):
        """Reject a pending order (staff only)"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        try:
            data = request.get_json() or {}
            reason = data.get('reason', 'No reason provided')
            
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            
            # Get order details
            cur.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
            order = cur.fetchone()
            
            if not order:
                return jsonify({'success': False, 'error': 'Order not found'}), 404
            
            # Check if order can be rejected
            if order['status'] not in ['PENDING', 'COMPLETED']:
                return jsonify({'success': False, 'error': f'Order cannot be rejected. Current status: {order["status"]}'}), 400
            
            # Update order status to rejected
            cur.execute("UPDATE orders SET status = 'REJECTED', approval_status = 'Rejected' WHERE id = %s", (order_id,))
            conn.commit()
            
            app.logger.info(f"Order {order_id} rejected by staff: {session['username']}, Reason: {reason}")
            
            return jsonify({
                'success': True,
                'message': f'Order #{order_id} rejected successfully'
            })
            
        except Exception as e:
            app.logger.error(f"Error rejecting order {order_id}: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()

    @app.route('/api/staff/orders/<int:order_id>/cancel', methods=['POST'])
    def cancel_order(order_id):
        """Cancel a completed order (staff only)"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401

        try:
            from models import Order, Notification

            data = request.get_json() or {}
            reason = data.get('reason', 'Out of stock')
            notes = data.get('notes', '')

            # Cancel the order with inventory restoration
            result = Order.cancel_order(order_id, reason, notes, session['username'])

            # Create web notification for customer
            order = Order.get_by_id(order_id)
            if order:
                notification_message = f"Your order #{order_id} has been cancelled due to {reason.lower()}. A full refund will be processed within 3-5 business days."
                Notification.create_notification(
                    customer_id=order['customer_id'],
                    message=notification_message,
                    notification_type='order_cancelled',
                    related_id=order_id
                )

            return jsonify({
                'success': True,
                'message': 'Order cancelled successfully. Customer has been notified.',
                'cancelled_items': result.get('cancelled_items', [])
            })

        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            app.logger.error(f"Error cancelling order {order_id}: {str(e)}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

    @app.route('/api/staff/orders/<int:order_id>/cancel-item', methods=['POST'])
    def cancel_order_item(order_id):
        """Cancel specific items from an order (staff only)"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401

        try:
            from models import Order, Notification

            data = request.get_json() or {}
            item_ids = data.get('item_ids', [])
            reason = data.get('reason', 'Out of stock')
            notes = data.get('notes', '')

            if not item_ids:
                return jsonify({'success': False, 'error': 'No items selected for cancellation'}), 400

            # Cancel specific items with inventory restoration
            result = Order.cancel_order_items(order_id, item_ids, reason, notes, session['username'])

            # Create web notification for customer
            order = Order.get_by_id(order_id)
            if order:
                if result.get('order_fully_cancelled'):
                    notification_message = f"Your order #{order_id} has been cancelled due to {reason.lower()}. A full refund will be processed within 3-5 business days."
                else:
                    cancelled_count = len(result.get('cancelled_items', []))
                    notification_message = f"Some items from your order #{order_id} have been cancelled due to {reason.lower()}. A partial refund will be processed within 3-5 business days."

                Notification.create_notification(
                    customer_id=order['customer_id'],
                    message=notification_message,
                    notification_type='order_cancelled',
                    related_id=order_id
                )

            return jsonify({
                'success': True,
                'message': 'Selected items cancelled successfully. Customer has been notified.',
                'cancelled_items': result.get('cancelled_items', []),
                'order_fully_cancelled': result.get('order_fully_cancelled', False)
            })

        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            app.logger.error(f"Error cancelling order items {order_id}: {str(e)}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

    @app.route('/api/customer/notifications')
    def get_customer_notifications():
        """Get notifications for logged-in customer"""
        if 'username' not in session or session.get('role') not in ['customer', 'staff', 'admin', 'super_admin']:
            return jsonify({'success': False, 'error': 'Customer or staff authentication required'}), 401

        try:
            from models import Notification

            customer_id = session.get('user_id')
            unread_only = request.args.get('unread_only', 'false').lower() == 'true'

            notifications = Notification.get_customer_notifications(customer_id, unread_only)

            # Format notifications for JSON response
            formatted_notifications = []
            for notification in notifications:
                formatted_notifications.append({
                    'id': notification['id'],
                    'message': notification['message'],
                    'type': notification['notification_type'],
                    'related_id': notification['related_id'],
                    'created_date': notification['created_date'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(notification['created_date'], 'strftime') else notification['created_date'],
                    'is_read': bool(notification['is_read'])
                })

            return jsonify({
                'success': True,
                'notifications': formatted_notifications
            })

        except Exception as e:
            app.logger.error(f"Error fetching customer notifications: {str(e)}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

    @app.route('/api/customer/notifications/<int:notification_id>/read', methods=['POST'])
    def mark_notification_read(notification_id):
        """Mark a notification as read"""
        if 'username' not in session or session.get('role') != 'customer':
            return jsonify({'success': False, 'error': 'Customer authentication required'}), 401

        try:
            from models import Notification

            customer_id = session.get('user_id')
            success = Notification.mark_as_read(notification_id, customer_id)

            if success:
                return jsonify({'success': True, 'message': 'Notification marked as read'})
            else:
                return jsonify({'success': False, 'error': 'Notification not found or access denied'}), 404

        except Exception as e:
            app.logger.error(f"Error marking notification as read: {str(e)}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

    @app.route('/api/customer/notifications/mark-all-read', methods=['POST'])
    def mark_all_notifications_read():
        """Mark all notifications as read for customer"""
        if 'username' not in session or session.get('role') != 'customer':
            return jsonify({'success': False, 'error': 'Customer authentication required'}), 401

        try:
            from models import Notification

            customer_id = session.get('user_id')
            count = Notification.mark_all_as_read(customer_id)

            return jsonify({
                'success': True,
                'message': f'{count} notifications marked as read'
            })

        except Exception as e:
            app.logger.error(f"Error marking all notifications as read: {str(e)}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

    @app.route('/api/customer/notifications/clear-all', methods=['POST'])
    def clear_all_notifications():
        """Clear all notifications for customer"""
        if 'username' not in session or session.get('role') != 'customer':
            return jsonify({'success': False, 'error': 'Customer authentication required'}), 401

        try:
            from models import Notification

            customer_id = session.get('user_id')
            count = Notification.clear_all_notifications(customer_id)

            return jsonify({
                'success': True,
                'message': f'{count} notifications cleared'
            })

        except Exception as e:
            app.logger.error(f"Error clearing all notifications: {str(e)}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

    @app.route('/api/customer/profile', methods=['GET'])
    def get_customer_profile():
        """Get customer profile information"""
        if 'username' not in session or session.get('role') != 'customer':
            return jsonify({'success': False, 'error': 'Customer authentication required'}), 401

        try:
            from models import Customer
            
            customer_id = session.get('user_id')
            customer = Customer.get_by_id(customer_id)
            
            if not customer:
                return jsonify({'success': False, 'error': 'Customer not found'}), 404

            return jsonify({
                'success': True,
                'customer': {
                    'id': customer['id'],
                    'first_name': customer['first_name'],
                    'last_name': customer['last_name'],
                    'email': customer['email'],
                    'phone': customer['phone'],
                    'address': customer['address'],
                    'otp_enabled': customer.get('otp_enabled', False)
                }
            })

        except Exception as e:
            app.logger.error(f"Error getting customer profile: {str(e)}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

    @app.route('/account')
    def customer_account():
        """Customer account dashboard page"""
        app.logger.info(f"Account page accessed by user: {session.get('username')}, role: {session.get('role')}")
        
        if 'username' not in session or session.get('role') != 'customer':
            app.logger.warning(f"Unauthorized access attempt - username: {session.get('username')}, role: {session.get('role')}")
            return redirect(url_for('auth.login'))
        
        try:
            from models import Customer, Order
            
            customer_id = session.get('user_id')
            app.logger.info(f"Customer ID: {customer_id}")
            
            customer = Customer.get_by_id(customer_id)
            
            if not customer:
                app.logger.error(f"Customer not found for ID: {customer_id}")
                flash('Customer not found', 'error')
                return redirect(url_for('show_dashboard'))
            
            app.logger.info(f"Customer found: {customer.get('first_name', 'Unknown')}")
            
            # Get default address from CustomerAddress table
            from models import CustomerAddress
            addresses = CustomerAddress.get_by_customer_id(customer_id)
            default_address = None
            
            # Find default address
            for addr in addresses:
                if addr['is_default']:
                    default_address = addr
                    break
            
            # If no default, use the first one
            if not default_address and addresses:
                default_address = addresses[0]
            
            # Add address fields to customer data for template
            if default_address:
                customer['house_number'] = default_address.get('house_number', '')
                customer['street_name'] = default_address.get('street_name', '')
                customer['village'] = default_address.get('village', '')
                customer['sangkat'] = default_address.get('sangkat', '')
                customer['commune'] = default_address.get('commune', '')
                customer['khan'] = default_address.get('khan', '')
                customer['province'] = default_address.get('province', '')
                customer['postal_code'] = default_address.get('postal_code', '')
                customer['country'] = default_address.get('country', 'Cambodia')
                customer['address_type'] = default_address.get('address_type', 'home')
                customer['building_name'] = default_address.get('building_name', '')
                customer['floor_number'] = default_address.get('floor_number', '')
                customer['unit_number'] = default_address.get('unit_number', '')
                customer['landmark'] = default_address.get('landmark', '')
                customer['delivery_notes'] = default_address.get('delivery_notes', '')
            else:
                # Set default empty values
                customer['house_number'] = ''
                customer['street_name'] = ''
                customer['village'] = ''
                customer['sangkat'] = ''
                customer['commune'] = ''
                customer['khan'] = ''
                customer['province'] = ''
                customer['postal_code'] = ''
                customer['country'] = 'Cambodia'
                customer['address_type'] = 'home'
                customer['building_name'] = ''
                customer['floor_number'] = ''
                customer['unit_number'] = ''
                customer['landmark'] = ''
                customer['delivery_notes'] = ''
            
            # Get all orders for the customer (for the main order history section)
            all_orders = []
            try:
                conn = get_db()
                cur = conn.cursor(dictionary=True)
                cur.execute("""
                    SELECT o.id, o.order_date as created_at, o.status, o.payment_method,
                           SUM(oi.quantity * oi.price) as total_amount
                    FROM orders o
                    JOIN order_items oi ON o.id = oi.order_id
                    WHERE o.customer_id = %s
                    GROUP BY o.id, o.order_date, o.status, o.payment_method
                    ORDER BY o.order_date DESC
                """, (customer_id,))
                all_orders = cur.fetchall()
                app.logger.info(f"Found {len(all_orders)} orders for customer {customer_id}")
            except Exception as e:
                app.logger.error(f"Error fetching orders: {str(e)}")
                all_orders = []
            
            # Get recent orders for dashboard widget (limit to 5)
            recent_orders = all_orders[:5] if all_orders else []
            
            app.logger.info("Rendering account template")
            return render_template('account.html', 
                                 customer=customer, 
                                 recent_orders=recent_orders,
                                 all_orders=all_orders)
            
        except Exception as e:
            app.logger.error(f"Error loading account page: {str(e)}")
            flash('Error loading account information', 'error')
            return redirect(url_for('show_dashboard'))

    @app.route('/account/delivery-addresses')
    def customer_delivery_addresses():
        """Customer delivery addresses management page"""
        app.logger.info(f"Delivery addresses page accessed by user: {session.get('username')}, role: {session.get('role')}")
        
        if 'username' not in session or session.get('role') != 'customer':
            app.logger.warning(f"Unauthorized access attempt - username: {session.get('username')}, role: {session.get('role')}")
            return redirect(url_for('auth.login'))
        
        try:
            from models import Customer, CustomerAddress
            
            customer_id = session.get('user_id')
            app.logger.info(f"Customer ID: {customer_id}")
            
            customer = Customer.get_by_id(customer_id)
            
            if not customer:
                app.logger.error(f"Customer not found for ID: {customer_id}")
                flash('Customer not found', 'error')
                return redirect(url_for('show_dashboard'))
            
            # Get all addresses for the customer
            addresses = CustomerAddress.get_by_customer_id(customer_id)
            app.logger.info(f"Found {len(addresses)} addresses for customer {customer_id}")
            
            return render_template('delivery_addresses.html', 
                                 customer=customer, 
                                 addresses=addresses)
            
        except Exception as e:
            app.logger.error(f"Error loading delivery addresses page: {str(e)}")
            flash('Error loading delivery addresses', 'error')
            return redirect(url_for('customer_account'))

    @app.route('/api/customer/profile/update', methods=['POST'])
    def update_customer_profile():
        """Update customer profile information"""
        if 'username' not in session or session.get('role') != 'customer':
            return jsonify({'success': False, 'error': 'Customer authentication required'}), 401

        try:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['first_name', 'last_name', 'email']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({'success': False, 'error': f'{field.replace("_", " ").title()} is required'}), 400

            from models import Customer
            
            customer_id = session.get('user_id')
            
            # Check if email is already taken by another customer
            existing_customer = Customer.get_by_email(data['email'])
            if existing_customer and existing_customer['id'] != customer_id:
                return jsonify({'success': False, 'error': 'Email is already taken by another customer'}), 400

            # Update customer profile (basic info only)
            update_data = {
                'first_name': data['first_name'].strip(),
                'last_name': data['last_name'].strip(),
                'email': data['email'].strip().lower(),
                'phone': data.get('phone', '').strip()
            }

            success = Customer.update(customer_id, **update_data)
            
            if success:
                # Update session username if name was changed
                if 'username' in session:
                    session['username'] = f"{update_data['first_name']} {update_data['last_name']}"
                
                # Handle address update/create
                from models import CustomerAddress
                
                # Prepare address data
                address_data = {
                    'house_number': data.get('house_number', '').strip(),
                    'street_name': data.get('street_name', '').strip(),
                    'village': data.get('village', '').strip(),
                    'sangkat': data.get('sangkat', '').strip(),
                    'commune': data.get('commune', '').strip(),
                    'khan': data.get('khan', '').strip(),
                    'province': data.get('province', '').strip(),
                    'postal_code': data.get('postal_code', '').strip(),
                    'country': data.get('country', 'Cambodia').strip(),
                    'building_name': data.get('building_name', '').strip(),
                    'floor_number': data.get('floor_number', '').strip(),
                    'unit_number': data.get('unit_number', '').strip(),
                    'landmark': data.get('landmark', '').strip(),
                    'delivery_notes': data.get('delivery_notes', '').strip()
                }
                
                address_type = data.get('address_type', 'home').strip()
                
                # Check if customer has any addresses
                existing_addresses = CustomerAddress.get_by_customer_id(customer_id)
                
                if existing_addresses:
                    # Update the first/default address
                    address_id = existing_addresses[0]['id']
                    CustomerAddress.update(address_id, address_data)
                else:
                    # Create new address as default
                    CustomerAddress.create(customer_id, address_data, address_type, is_default=True)
                
                return jsonify({
                    'success': True,
                    'message': 'Profile and address updated successfully'
                })
            else:
                return jsonify({'success': False, 'error': 'Failed to update profile'}), 500

        except Exception as e:
            app.logger.error(f"Error updating customer profile: {str(e)}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

    # =====================================================
    # CUSTOMER ADDRESS MANAGEMENT API ENDPOINTS
    # =====================================================

    @app.route('/api/customer/addresses', methods=['GET'])
    def get_customer_addresses():
        """Get all addresses for the logged-in customer"""
        if 'username' not in session or session.get('role') != 'customer':
            return jsonify({'success': False, 'error': 'Customer authentication required'}), 401

        try:
            customer_id = session.get('user_id')
            if not customer_id:
                return jsonify({'success': False, 'error': 'Customer ID not found'}), 400

            from models import CustomerAddress
            addresses = CustomerAddress.get_by_customer_id(customer_id)
            
            # Format addresses for display
            formatted_addresses = []
            for addr in addresses:
                formatted_addr = {
                    'id': addr['id'],
                    'address_type': addr['address_type'],
                    'is_default': addr['is_default'],
                    'house_number': addr['house_number'],
                    'street_name': addr['street_name'],
                    'street_number': addr['street_number'],
                    'village': addr['village'],
                    'sangkat': addr['sangkat'],
                    'commune': addr['commune'],
                    'khan': addr['khan'],
                    'province': addr['province'],
                    'postal_code': addr['postal_code'],
                    'country': addr['country'],
                    'building_name': addr['building_name'],
                    'floor_number': addr['floor_number'],
                    'unit_number': addr['unit_number'],
                    'landmark': addr['landmark'],
                    'delivery_notes': addr['delivery_notes'],
                    'formatted_display': CustomerAddress.format_display(addr),
                    'created_at': addr['created_at'].strftime('%Y-%m-%d %H:%M:%S') if addr['created_at'] else None
                }
                formatted_addresses.append(formatted_addr)

            return jsonify({
                'success': True,
                'addresses': formatted_addresses
            })

        except Exception as e:
            app.logger.error(f"Error getting customer addresses: {str(e)}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

    @app.route('/api/customer/addresses', methods=['POST'])
    def create_customer_address():
        """Create a new address for the logged-in customer"""
        app.logger.info(f"POST /api/customer/addresses called - Session: {dict(session)}")
        
        if 'username' not in session or session.get('role') != 'customer':
            app.logger.warning(f"Authentication failed - Username: {session.get('username')}, Role: {session.get('role')}")
            return jsonify({'success': False, 'error': 'Customer authentication required'}), 401

        try:
            customer_id = session.get('user_id')
            if not customer_id:
                return jsonify({'success': False, 'error': 'Customer ID not found'}), 400

            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400

            app.logger.info(f"Creating address for customer {customer_id} with data: {data}")

            # Validate required fields
            if not data.get('province'):
                return jsonify({'success': False, 'error': 'Province is required'}), 400

            from models import CustomerAddress
            
            # Set default values
            address_type = data.get('address_type', 'home')
            is_default = data.get('is_default', False)
            
            app.logger.info(f"Address type: {address_type}, is_default: {is_default}")
            
            # If this is being set as default, unset other defaults first
            if is_default:
                CustomerAddress.set_default(customer_id, None)  # This will unset all defaults
            
            address_id = CustomerAddress.create(customer_id, data, address_type, is_default)
            
            app.logger.info(f"Address created successfully with ID: {address_id}")
            
            return jsonify({
                'success': True,
                'address_id': address_id,
                'message': 'Address created successfully'
            })

        except Exception as e:
            app.logger.error(f"Error creating customer address: {str(e)}")
            app.logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            app.logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({'success': False, 'error': f'Internal server error: {str(e)}'}), 500

    @app.route('/api/customer/addresses/<int:address_id>', methods=['GET'])
    def get_customer_address(address_id):
        """Get a specific address for the logged-in customer"""
        if 'username' not in session or session.get('role') != 'customer':
            return jsonify({'success': False, 'error': 'Customer authentication required'}), 401

        try:
            customer_id = session.get('user_id')
            if not customer_id:
                return jsonify({'success': False, 'error': 'Customer ID not found'}), 400

            from models import CustomerAddress
            
            # Get the address and verify it belongs to this customer
            address = CustomerAddress.get_by_id(address_id)
            if not address or address['customer_id'] != customer_id:
                return jsonify({'success': False, 'error': 'Address not found or access denied'}), 404

            return jsonify({
                'success': True,
                'address': address
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/customer/addresses/<int:address_id>', methods=['PUT'])
    def update_customer_address(address_id):
        """Update an existing address for the logged-in customer"""
        if 'username' not in session or session.get('role') != 'customer':
            return jsonify({'success': False, 'error': 'Customer authentication required'}), 401

        try:
            customer_id = session.get('user_id')
            if not customer_id:
                return jsonify({'success': False, 'error': 'Customer ID not found'}), 400

            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400

            from models import CustomerAddress
            
            # Verify the address belongs to this customer
            address = CustomerAddress.get_by_id(address_id)
            if not address or address['customer_id'] != customer_id:
                return jsonify({'success': False, 'error': 'Address not found or access denied'}), 404

            success = CustomerAddress.update(address_id, data)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Address updated successfully'
                })
            else:
                return jsonify({'success': False, 'error': 'Failed to update address'}), 500

        except Exception as e:
            app.logger.error(f"Error updating customer address: {str(e)}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

    @app.route('/api/customer/addresses/<int:address_id>/set-default', methods=['POST'])
    def set_default_address(address_id):
        """Set an address as default for the logged-in customer"""
        if 'username' not in session or session.get('role') != 'customer':
            return jsonify({'success': False, 'error': 'Customer authentication required'}), 401

        try:
            customer_id = session.get('user_id')
            if not customer_id:
                return jsonify({'success': False, 'error': 'Customer ID not found'}), 400

            from models import CustomerAddress
            
            # Verify the address belongs to this customer
            address = CustomerAddress.get_by_id(address_id)
            if not address or address['customer_id'] != customer_id:
                return jsonify({'success': False, 'error': 'Address not found or access denied'}), 404

            success = CustomerAddress.set_default(customer_id, address_id)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Default address updated successfully'
                })
            else:
                return jsonify({'success': False, 'error': 'Failed to set default address'}), 500

        except Exception as e:
            app.logger.error(f"Error setting default address: {str(e)}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

    @app.route('/api/customer/addresses/<int:address_id>', methods=['DELETE'])
    def delete_customer_address(address_id):
        """Delete an address for the logged-in customer"""
        if 'username' not in session or session.get('role') != 'customer':
            return jsonify({'success': False, 'error': 'Customer authentication required'}), 401

        try:
            customer_id = session.get('user_id')
            if not customer_id:
                return jsonify({'success': False, 'error': 'Customer ID not found'}), 400

            from models import CustomerAddress
            
            # Verify the address belongs to this customer
            address = CustomerAddress.get_by_id(address_id)
            if not address or address['customer_id'] != customer_id:
                return jsonify({'success': False, 'error': 'Address not found or access denied'}), 404

            success = CustomerAddress.delete(address_id)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Address deleted successfully'
                })
            else:
                return jsonify({'success': False, 'error': 'Failed to delete address'}), 500

        except Exception as e:
            app.logger.error(f"Error deleting customer address: {str(e)}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

    @app.route('/api/customer/addresses/default', methods=['GET'])
    def get_default_address():
        """Get the default address for the logged-in customer"""
        if 'username' not in session or session.get('role') != 'customer':
            return jsonify({'success': False, 'error': 'Customer authentication required'}), 401

        try:
            customer_id = session.get('user_id')
            if not customer_id:
                return jsonify({'success': False, 'error': 'Customer ID not found'}), 400

            from models import CustomerAddress
            addresses = CustomerAddress.get_by_customer_id(customer_id)
            
            # Find default address
            default_address = None
            for addr in addresses:
                if addr['is_default']:
                    default_address = addr
                    break
            
            if not default_address and addresses:
                # If no default set, use the first one
                default_address = addresses[0]

            if default_address:
                formatted_addr = {
                    'id': default_address['id'],
                    'address_type': default_address['address_type'],
                    'is_default': default_address['is_default'],
                    'house_number': default_address['house_number'],
                    'street_name': default_address['street_name'],
                    'street_number': default_address['street_number'],
                    'village': default_address['village'],
                    'sangkat': default_address['sangkat'],
                    'commune': default_address['commune'],
                    'khan': default_address['khan'],
                    'province': default_address['province'],
                    'postal_code': default_address['postal_code'],
                    'country': default_address['country'],
                    'building_name': default_address['building_name'],
                    'floor_number': default_address['floor_number'],
                    'unit_number': default_address['unit_number'],
                    'landmark': default_address['landmark'],
                    'delivery_notes': default_address['delivery_notes'],
                    'formatted_display': CustomerAddress.format_display(default_address)
                }
                
                return jsonify({
                    'success': True,
                    'address': formatted_addr
                })
            else:
                return jsonify({
                    'success': True,
                    'address': None,
                    'message': 'No addresses found'
                })

        except Exception as e:
            app.logger.error(f"Error getting default address: {str(e)}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

    # =====================================================
    # PARTIAL ORDER CANCELLATION API ENDPOINTS
    # =====================================================

    @app.route('/api/staff/orders/<int:order_id>/items/<int:item_id>/cancel', methods=['POST'])
    def cancel_order_item_partial(order_id, item_id):
        """Cancel a specific item in an order (partial cancellation)"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401

        try:
            data = request.get_json()
            cancel_quantity = int(data.get('cancel_quantity', 1))
            reason = data.get('reason', 'out_of_stock')
            notes = data.get('notes', '')
            notify_customer = data.get('notify_customer', True)

            from models import PartialCancellation

            # Perform the partial cancellation
            result = PartialCancellation.cancel_order_item(
                order_id=order_id,
                item_id=item_id,
                cancel_quantity=cancel_quantity,
                reason=reason,
                staff_id=session.get('user_id'),
                notes=notes,
                notify_customer=notify_customer
            )

            if result['success']:
                return jsonify({
                    'success': True,
                    'message': f'Successfully cancelled {cancel_quantity} item(s)',
                    'refund_amount': result['refund_amount'],
                    'cancelled_quantity': result['cancelled_quantity'],
                    'product_name': result['product_name']
                })
            else:
                return jsonify({'success': False, 'error': result['error']}), 400

        except Exception as e:
            app.logger.error(f"Error cancelling order item: {str(e)}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

    @app.route('/api/staff/orders/<int:order_id>/cancellation-options', methods=['GET'])
    def get_order_cancellation_options(order_id):
        """Get cancellation options for an order"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401

        try:
            from models import PartialCancellation

            options = PartialCancellation.get_cancellation_options(order_id)
            return jsonify({
                'success': True,
                'order_id': order_id,
                'items': options['items'],
                'can_cancel_items': options['can_cancel'],
                'order_status': options['order_status']
            })

        except Exception as e:
            app.logger.error(f"Error getting cancellation options: {str(e)}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

    @app.route('/api/staff/orders/unified')
    def unified_orders():
        """Get recent orders for the customer order widget"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        try:
            from datetime import datetime, timedelta

            # Get recent orders (last 7 days, excluding cancelled)
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            
            # Get status filter from query parameters
            status_filter = request.args.get('status', 'all')
            
            # Build the query based on status filter
            if status_filter == 'all':
                status_condition = "o.status IN ('PENDING', 'COMPLETED', 'CONFIRMED')"
            elif status_filter == 'pending':
                status_condition = "o.status = 'PENDING'"
            elif status_filter == 'completed':
                status_condition = "o.status = 'COMPLETED'"
            else:
                status_condition = "o.status IN ('PENDING', 'COMPLETED', 'CONFIRMED')"

            cur.execute(f"""
                SELECT o.id, o.order_date, c.first_name, c.last_name, o.total_amount,
                       o.status, o.payment_method, o.approval_status, o.transaction_id
                FROM orders o
                JOIN customers c ON o.customer_id = c.id
                WHERE {status_condition}
                AND DATE(o.order_date) = CURDATE()
                ORDER BY o.order_date DESC
                LIMIT 50
            """)

            order_rows = cur.fetchall()
            orders_data = []
            orders_total = 0

            for row in order_rows:
                # Get order items to determine details
                cur.execute("""
                    SELECT p.name as product_name, oi.quantity
                    FROM order_items oi
                    JOIN products p ON oi.product_id = p.id
                    WHERE oi.order_id = %s
                """, (row['id'],))
                order_items = cur.fetchall()

                # Determine details based on number of items
                if len(order_items) == 1:
                    details = order_items[0]['product_name']  # Show product name for single item
                else:
                    details = 'Multiple items'

                order_data = {
                    'id': row['id'],
                    'date': row['order_date'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(row['order_date'], 'strftime') else str(row['order_date']),
                    'customer_name': f"{row['first_name']} {row['last_name']}",
                    'amount': float(row['total_amount']) if row['total_amount'] is not None else 0.0,
                    'status': row['status'],
                    'payment_method': row['payment_method'] if row['payment_method'] is not None else 'QR Payment',
                    'approval_status': row['approval_status'] if row['approval_status'] is not None else 'Pending Approval',
                    'type': 'order',
                    'details': details
                }
                orders_data.append(order_data)
                # Count all orders in total (not just completed)
                orders_total += order_data['amount']

            cur.close()

            # Sort orders by date descending (most recent first)
            orders_data.sort(key=lambda x: x['date'], reverse=True)

            return jsonify({
                'success': True,
                'orders': orders_data,
                'summary': {
                    'orders_count': len(orders_data),
                    'orders_total': orders_total
                }
            })

        except Exception as e:
            app.logger.error(f"Error getting unified orders: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/staff/orders/unified/all')
    def unified_orders_all():
        """Get completed orders for the customer order widget (excluding pending)"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        try:
            from datetime import datetime

            # Get all orders (excluding cancelled)
            conn = get_db()
            cur = conn.cursor(dictionary=True)

            cur.execute("""
                SELECT o.id, o.order_date, c.first_name, c.last_name, o.total_amount,
                       o.status, o.payment_method, o.approval_status, o.transaction_id
                FROM orders o
                JOIN customers c ON o.customer_id = c.id
                WHERE o.status = 'COMPLETED'
                ORDER BY o.order_date DESC
                LIMIT 20
            """)

            order_rows = cur.fetchall()
            orders_data = []
            orders_total = 0

            for row in order_rows:
                # Get order items to determine details
                cur.execute("""
                    SELECT p.name as product_name, oi.quantity
                    FROM order_items oi
                    JOIN products p ON oi.product_id = p.id
                    WHERE oi.order_id = %s
                """, (row['id'],))
                order_items = cur.fetchall()

                # Determine details based on number of items
                if len(order_items) == 1:
                    details = order_items[0]['product_name']  # Show product name for single item
                else:
                    details = 'Multiple items'

                order_data = {
                    'id': row['id'],
                    'date': row['order_date'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(row['order_date'], 'strftime') else str(row['order_date']),
                    'customer_name': f"{row['first_name']} {row['last_name']}",
                    'amount': float(row['total_amount']) if row['total_amount'] is not None else 0.0,
                    'status': row['status'],
                    'payment_method': row['payment_method'] if row['payment_method'] is not None else 'QR Payment',
                    'approval_status': row['approval_status'] if row['approval_status'] is not None else 'Pending Approval',
                    'type': 'order',
                    'details': details
                }
                orders_data.append(order_data)
                if row['status'] == 'COMPLETED':  # Only count completed orders in total
                    orders_total += order_data['amount']

            cur.close()

            # Sort orders by date descending (most recent first)
            orders_data.sort(key=lambda x: x['date'], reverse=True)

            return jsonify({
                'success': True,
                'orders': orders_data,
                'summary': {
                    'orders_count': len(orders_data),
                    'orders_total': orders_total
                }
            })

        except Exception as e:
            app.logger.error(f"Error getting unified orders: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/debug/preorders')
    def debug_preorders():
        """Debug endpoint to check pre-orders in database"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401
        
        try:
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            
            # Get all pre-orders with details
            cur.execute("""
                SELECT 
                    po.id, po.status, po.created_date, po.expected_price, po.quantity,
                    c.first_name, c.last_name, p.name as product_name
                FROM pre_orders po
                JOIN customers c ON po.customer_id = c.id
                JOIN products p ON po.product_id = p.id
                ORDER BY po.created_date DESC
                LIMIT 20
            """)
            
            preorders = cur.fetchall()
            cur.close()
            
            result = []
            for po in preorders:
                result.append({
                    'id': po['id'],
                    'status': po['status'],
                    'created_date': str(po['created_date']),
                    'expected_price': float(po['expected_price']) if po['expected_price'] else 0,
                    'quantity': po['quantity'],
                    'customer': f"{po['first_name']} {po['last_name']}",
                    'product': po['product_name']
                })
            
            return jsonify({
                'success': True,
                'total_preorders': len(result),
                'preorders': result
            })
            
        except Exception as e:
            app.logger.error(f"Error debugging pre-orders: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/test-invoice')
    def test_invoice():
        """Test invoice template with dummy data."""
        try:
            # Create dummy data for testing
            dummy_order = {
                'id': 999,
                'total_amount': 1249.00,
                'order_date': datetime.now()
            }

            dummy_customer = {
                'first_name': 'Test',
                'last_name': 'Customer',
                'email': 'test@example.com',
                'phone': '123-456-7890',
                'address': '123 Test Street'
            }

            dummy_items = [
                {
                    'product_name': 'MSI Katana 17',
                    'brand': 'MSI',
                    'quantity': 1,
                    'price': 1249.00
                }
            ]

            return render_template('order_confirmation.html',
                                 order=dummy_order,
                                 customer=dummy_customer,
                                 order_items=dummy_items)
        except Exception as e:
            return f"Error rendering invoice: {str(e)}"

    @app.route('/test-preorder-invoice')
    def test_preorder_invoice():
        """Test pre-order invoice template with dummy data."""
        try:
            # Create dummy data for testing
            dummy_preorder = {
                'id': 73,
                'product_name': 'MSI Katana 17 B13VFK-1427KH',
                'quantity': 1,
                'expected_price': 1249.00,
                'total_paid': 312.25,
                'status': 'confirmed'
            }

            dummy_customer = {
                'first_name': 'Test',
                'last_name': 'Customer',
                'email': 'test@example.com',
                'phone': '123-456-7890',
                'address': '123 Test Street'
            }

            dummy_payment = {
                'payment_amount': 312.25,
                'payment_type': 'deposit',
                'payment_method': 'Cash',
                'payment_date': datetime.now(),
                'payment_status': 'completed'
            }

            dummy_payment_history = [dummy_payment]

            return render_template('preorder_invoice.html',
                                 preorder=dummy_preorder,
                                 customer=dummy_customer,
                                 payment_history=dummy_payment_history,
                                 latest_payment=dummy_payment)
        except Exception as e:
            return f"Error rendering pre-order invoice: {str(e)}"



    @app.route('/test-qr')
    def test_qr():
        """Test QR code generation."""
        try:
            print("🔧 Testing QR code generation...")
            qr_generator = BakongQRGenerator(use_static_qr=True)
            qr_data = qr_generator.generate_payment_qr(
                amount=10.00,
                currency="USD",
                reference_id="TEST123"
            )
            print(f"✅ QR data generated: {bool(qr_data.get('qr_image_base64'))}")
            return f"""
            <h2>QR Test Results</h2>
            <p>Success: {bool(qr_data.get('qr_image_base64'))}</p>
            <p>Reference: {qr_data.get('reference_id')}</p>
            <p>Amount: ${qr_data.get('amount')}</p>
            {f'<img src="data:image/png;base64,{qr_data.get("qr_image_base64")}" style="max-width: 300px;">' if qr_data.get('qr_image_base64') else '<p>No QR image generated</p>'}
            """
        except Exception as e:
            print(f"❌ Error testing QR: {str(e)}")
            return f"<h2>Error:</h2><p>{str(e)}</p>"

    # Staff Suppliers Page Route
    @app.route('/auth/staff/suppliers')
    def staff_suppliers():
        try:
            suppliers = Supplier.get_all()
        except Exception as e:
            app.logger.error(f"Error fetching suppliers: {e}")
            suppliers = []
        return render_template('staff_suppliers.html', suppliers=suppliers)

    # Staff Supplier Search API Route
    @app.route('/auth/staff/suppliers/search')
    def staff_suppliers_search():
        query = (request.args.get('q') or '').strip()
        if not query:
            return jsonify({'success': False, 'suppliers': [], 'error': 'Empty search query'})
        try:
            suppliers = Supplier.search(query)
            return jsonify({'success': True, 'suppliers': suppliers})
        except Exception as e:
            app.logger.error(f"Error searching suppliers: {e}")
            return jsonify({'success': False, 'suppliers': [], 'error': str(e)})

    # Staff Supplier Update API Route
    @app.route('/auth/staff/suppliers/<int:supplier_id>', methods=['PUT'])
    def update_supplier(supplier_id):
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        try:
            name = data.get('name', '').strip()
            contact_person = data.get('contact_person', '').strip()
            phone = data.get('phone', '').strip()
            email = data.get('email', '').strip()
            address = data.get('address', '').strip()

            if not name:
                return jsonify({'success': False, 'error': 'Name is required'}), 400

            updated = Supplier.update(supplier_id, name, contact_person, phone, email, address)
            if updated:
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'error': 'Update failed'}), 500
        except Exception as e:
            app.logger.error(f"Error updating supplier: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    # Staff Supplier Create API Route
    @app.route('/auth/staff/suppliers', methods=['POST'])
    def create_supplier():
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        try:
            name = data.get('name', '').strip()
            contact_person = data.get('contact_person', '').strip()
            phone = data.get('phone', '').strip()
            email = data.get('email', '').strip()
            address = data.get('address', '').strip()

            if not name:
                return jsonify({'success': False, 'error': 'Name is required'}), 400

            supplier_id = Supplier.create(name, contact_person, phone, email, address)
            if supplier_id:
                return jsonify({'success': True, 'supplier_id': supplier_id})
            else:
                return jsonify({'success': False, 'error': 'Creation failed'}), 500
        except Exception as e:
            app.logger.error(f"Error creating supplier: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    # Staff Supplier Delete API Route
    @app.route('/auth/staff/suppliers/<int:supplier_id>', methods=['DELETE'])
    def delete_supplier(supplier_id):
        try:
            deleted = Supplier.delete(supplier_id)
            if deleted:
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'error': 'Failed to delete supplier for an unknown reason'}), 500
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            app.logger.error(f"Error deleting supplier: {e}")
            return jsonify({'success': False, 'error': 'An unexpected error occurred'}), 500

    # Staff Orders Page Route
    @app.route('/auth/staff/orders/<int:order_id>/details')
    def staff_order_details(order_id):
        """Display detailed view of a specific order for staff"""
        app.logger.info(f"DEBUG: Route called for order {order_id}")
        
        if 'username' not in session:
            app.logger.warning("No username in session, redirecting to login")
            return redirect(url_for('admin_login'))
        
        # Check if user has permission (staff, admin, or super_admin)
        user_role = session.get('role', '')
        app.logger.info(f"DEBUG: User role: {user_role}")
        if user_role not in ['staff', 'admin', 'super_admin']:
            app.logger.warning(f"User {user_role} not authorized, redirecting to login")
            return redirect(url_for('admin_login'))
        
        try:
            # Get order with customer details and order items from database
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            try:
                # Get order with customer details and delivery address
                # First get the basic order and customer data
                app.logger.info(f"DEBUG: Executing query for order {order_id}")
                cur.execute("""
                    SELECT o.*, c.first_name, c.last_name, c.email, c.phone, c.address
                    FROM orders o
                    LEFT JOIN customers c ON o.customer_id = c.id
                    WHERE o.id = %s
                """, (order_id,))
                order_data = cur.fetchone()
                app.logger.info(f"DEBUG: Query result: {order_data is not None}")
                
                if not order_data:
                    app.logger.warning(f"Order {order_id} not found in database")
                    flash('Order not found', 'error')
                    return redirect(url_for('staff_orders'))
                
                # Now try to get address data from customer_addresses table
                address_data = None
                if order_data.get('address_id'):
                    # Try to get the specific address from order
                    cur.execute("""
                        SELECT * FROM customer_addresses WHERE id = %s
                    """, (order_data['address_id'],))
                    address_data = cur.fetchone()
                
                if not address_data:
                    # Try to get customer's default address
                    cur.execute("""
                        SELECT * FROM customer_addresses 
                        WHERE customer_id = %s AND is_default = TRUE AND is_active = TRUE
                        LIMIT 1
                    """, (order_data['customer_id'],))
                    address_data = cur.fetchone()
                
                if not address_data:
                    # Try to get any customer address
                    cur.execute("""
                        SELECT * FROM customer_addresses 
                        WHERE customer_id = %s AND is_active = TRUE
                        LIMIT 1
                    """, (order_data['customer_id'],))
                    address_data = cur.fetchone()
                
                # Merge address data into order_data
                if address_data:
                    for key, value in address_data.items():
                        if key not in ['id', 'customer_id', 'created_at', 'updated_at']:
                            order_data[key] = value
                
                # Get order items
                cur.execute("""
                    SELECT oi.product_id, p.name as product_name, p.photo as product_photo,
                           oi.quantity, oi.price,
                           COALESCE(oi.original_price, oi.price) as original_price
                    FROM order_items oi
                    JOIN products p ON oi.product_id = p.id
                    WHERE oi.order_id = %s
                """, (order_id,))
                order_items = cur.fetchall()
            finally:
                cur.close()
                conn.close()
            
            app.logger.info(f"DEBUG: Order data: {order_data}")
            app.logger.info(f"DEBUG: Order items: {order_items}")
            app.logger.info(f"DEBUG: Address ID: {order_data.get('address_id')}")
            app.logger.info(f"DEBUG: House number: {order_data.get('house_number')}")
            app.logger.info(f"DEBUG: Street name: {order_data.get('street_name')}")
            app.logger.info(f"DEBUG: Province: {order_data.get('province')}")
            
            # Add order items to the order data
            order_data['order_items'] = order_items
            
            # Format the customer name
            if order_data.get('first_name') and order_data.get('last_name'):
                order_data['customer_name'] = f"{order_data['first_name']} {order_data['last_name']}"
            elif order_data.get('first_name'):
                order_data['customer_name'] = order_data['first_name']
            else:
                order_data['customer_name'] = 'N/A'
            
            # Format the delivery address from atomic components
            delivery_address_parts = []
            if order_data.get('house_number'):
                delivery_address_parts.append(order_data['house_number'])
            if order_data.get('street_name'):
                delivery_address_parts.append(order_data['street_name'])
            if order_data.get('village'):
                delivery_address_parts.append(f"Village: {order_data['village']}")
            if order_data.get('sangkat'):
                delivery_address_parts.append(f"Sangkat: {order_data['sangkat']}")
            if order_data.get('commune'):
                delivery_address_parts.append(f"Commune: {order_data['commune']}")
            if order_data.get('khan'):
                delivery_address_parts.append(f"Khan: {order_data['khan']}")
            if order_data.get('province'):
                delivery_address_parts.append(f"Province: {order_data['province']}")
            if order_data.get('postal_code'):
                delivery_address_parts.append(f"Postal Code: {order_data['postal_code']}")
            if order_data.get('landmark'):
                delivery_address_parts.append(f"Landmark: {order_data['landmark']}")
            if order_data.get('delivery_notes'):
                delivery_address_parts.append(f"Notes: {order_data['delivery_notes']}")
            
            if delivery_address_parts:
                order_data['delivery_address'] = ', '.join(delivery_address_parts)
                app.logger.info(f"DEBUG: Formatted delivery address: {order_data['delivery_address']}")
            else:
                # Fallback to basic address field if no atomic address components
                order_data['delivery_address'] = order_data.get('address', 'N/A')
                app.logger.info(f"DEBUG: Using fallback address: {order_data['delivery_address']}")
            
            app.logger.info(f"DEBUG: About to render template with order: {order_data}")
            return render_template('order_details.html', order=order_data)
            
        except Exception as e:
            app.logger.error(f"Error in template rendering: {e}")
            import traceback
            app.logger.error(f"Traceback: {traceback.format_exc()}")
            flash('Error loading order details', 'error')
            return redirect(url_for('staff_orders'))

    @app.route('/auth/staff/orders')
    def staff_orders():
        # This route will now primarily render the page, and JavaScript will fetch data
        status = request.args.get('status', 'all')
        date = request.args.get('date')
        search = request.args.get('search')
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)

        try:
            summary = Order.get_status_summary()
            total_orders_amount = Order.get_total_amount_all()
            total_completed_amount = Order.get_total_completed_amount()
            pending_count = Order.get_pending_orders_count()
            
            # Calculate completed orders count from summary
            completed_count = 0
            cancelled_count = 0
            for item in summary:
                if item['status'].upper() == 'COMPLETED':
                    completed_count = item['count']
                elif item['status'].upper() == 'CANCELLED':
                    cancelled_count = item['count']
            
            # Calculate new order performance metrics
            pending_approval_count = Order.get_pending_approval_count()
            recent_orders_count = Order.get_recent_orders_count()
            
            app.logger.info(f"DEBUG: Order summary data: {summary}")
            app.logger.info(f"DEBUG: Completed orders count: {completed_count}")
            app.logger.info(f"DEBUG: Pending orders count: {pending_count}")
            app.logger.info(f"DEBUG: Pending approval count: {pending_approval_count}")
            app.logger.info(f"DEBUG: Recent orders count: {recent_orders_count}")
            # No longer fetching orders directly here, JS will do it via API
        except Exception as e:
            app.logger.error(f"Error fetching order summary data: {e}")
            summary = []
            total_orders_amount = 0.0
            total_completed_amount = 0.0
            completed_count = 0
            pending_count = 0
            cancelled_count = 0
            pending_approval_count = 0
            recent_orders_count = 0

        return render_template('staff_orders.html', summary=summary, search=search, completed_count=completed_count, pending_count=pending_count, cancelled_count=cancelled_count, pending_approval_count=pending_approval_count, recent_orders_count=recent_orders_count, total_completed_amount=total_completed_amount, active_page='orders')

    @app.route('/auth/staff/api/orders')
    def api_staff_orders():
        status = request.args.get('status', 'all')
        date = request.args.get('date')
        search = request.args.get('search')
        approval = request.args.get('approval', 'all')
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)

        # Sanitize input parameters to treat 'none' or similar as no filter
        if status and status.lower() == 'none':
            status = 'all'
        if date and date.lower() == 'none':
            date = None
        if search and search.lower() == 'none':
            search = None
        if approval and approval.lower() == 'none':
            approval = 'all'

        try:
            orders, total_orders = Order.get_paginated_orders(status=status, date=date, search=search, approval=approval, page=page, page_size=page_size)
            
            orders_list = []
            for order in orders:
                orders_list.append({
                    'id': order['id'],
                    'first_name': order['first_name'],
                    'last_name': order['last_name'],
                    'order_date': order['order_date'].strftime('%Y-%m-%d') if hasattr(order['order_date'], 'strftime') else order['order_date'],
                    'total': float(order['total']),
                    'status': order['status'],
                    'payment_method': order.get('payment_method', 'QR Payment'),
                    'approval_status': order.get('approval_status', 'Pending Approval')
                })
            return jsonify({'success': True, 'orders': orders_list, 'total_orders': total_orders})
        except Exception as e:
            app.logger.error(f"Error fetching paginated orders: {e}")
            return jsonify({'success': False, 'error': 'Failed to fetch orders'}), 500

    # Staff API Routes
    # Status update endpoint removed - orders are automatically managed

    @app.route('/staff/inventory/search')
    def search_inventory():
        query = request.args.get('q', '')
        brand_filter = request.args.get('brand_filter', '')
        category_filter = request.args.get('category_filter', '')
        stock_filter = request.args.get('stock_filter', '')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 10))
        sort_by = request.args.get('sort_by', 'id')
        sort_dir = request.args.get('sort_dir', 'desc').lower()
        if sort_dir not in ['asc', 'desc']:
            sort_dir = 'desc'

        product_id = request.args.get('product_id', '')
        try:
            cur = mysql.connection.cursor()

            # Build the WHERE clause dynamically
            where_clauses = []
            params = []

            if query:
                # Change to filter by product name instead of category name
                where_clauses.append("p.name LIKE %s")
                params.append(f'%{query}%')

            if brand_filter:
                where_clauses.append("p.name LIKE %s")
                params.append(f'%{brand_filter}%')

            if category_filter:
                where_clauses.append("p.category_id = %s")
                params.append(category_filter)

            if stock_filter:
                if stock_filter == 'out_of_stock':
                    where_clauses.append("p.stock = 0")
                elif stock_filter == 'low_stock':
                    where_clauses.append("p.stock > 0 AND p.stock <= 20")
                elif stock_filter == 'in_stock':
                    where_clauses.append("p.stock > 20")
                elif stock_filter == 'archived':
                    where_clauses.append("p.archived = TRUE")

            if product_id:
                where_clauses.append("p.id = %s")
                params.append(product_id)

            where_clause = " AND ".join(where_clauses)
            # Add condition to exclude archived products (unless specifically filtering for archived)
            if where_clause:
                if stock_filter != 'archived':
                    where_clause = "WHERE " + where_clause + " AND (p.archived IS NULL OR p.archived = FALSE)"
                else:
                    where_clause = "WHERE " + where_clause
            else:
                where_clause = "WHERE (p.archived IS NULL OR p.archived = FALSE)"
            app.logger.info(f"Product ID: {product_id}")
            app.logger.info(f"WHERE clause: {where_clause}")
            # Count total matching products
            count_query = f"""
SELECT COUNT(*)
FROM products p
LEFT JOIN categories c ON p.category_id = c.id
{where_clause}
            """
            cur.execute(count_query, tuple(params))
            total_count = cur.fetchone()[0]

            # Calculate pagination
            total_pages = (total_count + page_size - 1) // page_size
            offset = (page - 1) * page_size

            # Validate sort_by column to prevent SQL injection
            valid_sort_columns = ['id', 'name', 'price', 'original_price', 'stock']
            if sort_by not in valid_sort_columns:
                sort_by = 'id'

            # Fetch paginated products with sorting including category information
            # Optimized query with better performance
            fetch_query = f"""
SELECT p.id, p.name, p.description, p.price, p.stock, p.photo, p.cpu, p.ram, p.storage, p.display, p.os, p.keyboard, p.battery, p.weight, p.warranty_id, p.back_view, p.left_rear_view, p.category_id, p.original_price, p.archived, c.name as category_name
FROM products p
LEFT JOIN categories c ON p.category_id = c.id
                {where_clause}
                ORDER BY p.{sort_by} {sort_dir}
                LIMIT %s OFFSET %s
            """
            cur.execute(fetch_query, tuple(params) + (page_size, offset))
            results = cur.fetchall()
            cur.close()
            products = []
            for row in results:
                products.append({
                    'id': int(row[0]),
                    'name': row[1],
                    'description': row[2],
                    'price': float(row[3]),
                    'stock': int(row[4]),
                    'photo': row[5],
                    'cpu': row[6],
                    'ram': row[7],
                    'storage': row[8],
                    'display': row[9],
                    'os': row[10],
                    'keyboard': row[11],
                    'battery': row[12],
                    'weight': row[13],
                    'warranty_id': row[14],
                    'back_view': row[15],
                    'left_rear_view': row[16],
                    'category_id': row[17],
                    'original_price': float(row[18]) if row[18] is not None else None,
                    'archived': bool(row[19]) if row[19] is not None else False,
                    'category_name': row[20]
                })

            pagination = {
                'page': page,
                'total_pages': total_pages,
                'total_count': total_count
            }

            return jsonify({'success': True, 'products': products, 'pagination': pagination})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/staff/products/batch-order-check', methods=['POST'])
    def batch_order_check():
        """Check orders for multiple products in a single request"""
        if 'user_id' not in session or session.get('role') not in ['staff', 'admin', 'super_admin']:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 403
        
        try:
            data = request.get_json()
            product_ids = data.get('product_ids', [])
            
            if not product_ids:
                return jsonify({'success': True, 'order_checks': []})
            
            cur = mysql.connection.cursor()
            
            # Single query to check orders for all products
            placeholders = ','.join(['%s'] * len(product_ids))
            query = f"""
                SELECT 
                    p.id as product_id,
                    COUNT(DISTINCT oi.order_id) as order_count,
                    COUNT(DISTINCT CASE WHEN o.status = 'preorder' THEN oi.order_id END) as preorder_count
                FROM products p
                LEFT JOIN order_items oi ON p.id = oi.product_id
                LEFT JOIN orders o ON oi.order_id = o.id
                WHERE p.id IN ({placeholders})
                GROUP BY p.id
            """
            
            cur.execute(query, product_ids)
            results = cur.fetchall()
            cur.close()
            
            # Build response with all products
            order_checks = []
            result_map = {row[0]: {'order_count': row[1], 'preorder_count': row[2]} for row in results}
            
            for product_id in product_ids:
                if product_id in result_map:
                    result = result_map[product_id]
                    order_checks.append({
                        'product_id': product_id,
                        'has_orders': result['order_count'] > 0,
                        'order_count': result['order_count'],
                        'preorder_count': result['preorder_count']
                    })
                else:
                    order_checks.append({
                        'product_id': product_id,
                        'has_orders': False,
                        'order_count': 0,
                        'preorder_count': 0
                    })
            
            return jsonify({'success': True, 'order_checks': order_checks})
            
        except Exception as e:
            app.logger.error(f"Error in batch order check: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/staff/inventory/archived')
    def get_archived_products():
        """Get all archived products"""
        if 'user_id' not in session or session.get('role') not in ['staff', 'admin', 'super_admin']:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 403
        
        try:
            cur = mysql.connection.cursor()
            
            # Fetch all archived products
            query = """
                SELECT p.id, p.name, p.description, p.price, p.stock, p.photo, 
                       p.original_price, c.name as category_name, p.archived
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.archived = TRUE
                ORDER BY p.name
            """
            cur.execute(query)
            results = cur.fetchall()
            cur.close()
            
            products = []
            for row in results:
                products.append({
                    'id': int(row[0]),
                    'name': row[1],
                    'description': row[2],
                    'price': float(row[3]),
                    'stock': int(row[4]),
                    'photo': row[5],
                    'original_price': float(row[6]) if row[6] is not None else None,
                    'category_name': row[7],
                    'archived': bool(row[8])
                })
            
            return jsonify({'success': True, 'products': products})
        except Exception as e:
            app.logger.error(f"Error fetching archived products: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/staff/orders/create', methods=['POST'])
    def create_order():
        if not request.json:
            return jsonify({'success': False, 'error': 'Invalid request'}), 400
        
        from datetime import datetime

        data = request.json
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        email = data.get('email')
        order_date = data.get('order_date')
        items = data.get('items', [])

        if not first_name or not last_name or not email:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        # If order_date is missing or only date without time, set to current datetime
        if not order_date:
            order_date_obj = datetime.now()
        else:
            try:
                # Try parsing order_date string to datetime
                order_date_obj = datetime.strptime(order_date, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    # If time is missing, parse only date and add current time
                    date_part = datetime.strptime(order_date, '%Y-%m-%d')
                    now = datetime.now()
                    order_date_obj = datetime.combine(date_part.date(), now.time())
                except ValueError:
                    # If parsing fails, set to current datetime
                    order_date_obj = datetime.now()

        try:
            # Check if customer exists
            customer = Customer.get_by_name_or_email(first_name, last_name, email)
            if not customer:
                customer_id = Customer.create(first_name, last_name, email)
            else:
                customer_id = customer['id']

            # Create order (this will also reduce stock)
            order_id = Order.create(customer_id, order_date_obj, status='PENDING', items=items)
            return jsonify({'success': True, 'order_id': order_id})
        except ValueError as e:
            # Handle insufficient stock error specifically
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/staff/orders/test_status_summary')
    def api_order_test_status_summary():
        test_summary = {
            'completed': 10,
            'pending': 5,
            'cancelled': 2
        }
        return jsonify({'success': True, 'summary': test_summary})

    @app.route('/api/staff/orders/status_summary')
    def api_order_status_summary():
        try:
            summary = Order.get_status_summary()
            app.logger.info(f"DEBUG: Order status summary: {summary}")
            return jsonify({'success': True, 'summary': summary})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/staff/inventory/stock_summary')
    def api_inventory_stock_summary():
        try:
            conn = mysql.connection
            cur = conn.cursor()
            cur.execute("""
                SELECT
                    COUNT(CASE WHEN stock = 0 THEN 1 END) AS out_of_stock,
                    COUNT(CASE WHEN stock > 0 AND stock < 20 THEN 1 END) AS low_stock,
                    COUNT(CASE WHEN stock >= 20 THEN 1 END) AS in_stock
                FROM products
            """)
            row = cur.fetchone()
            cur.close()
            summary = {
                'out_of_stock': row[0] or 0,
                'low_stock': row[1] or 0,
                'in_stock': row[2] or 0
            }
            return jsonify({'success': True, 'summary': summary})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/auth/api/inventory/stats')
    def api_inventory_stats():
        try:
            conn = mysql.connection
            cur = conn.cursor()
            cur.execute("""
                SELECT
                    SUM(CASE WHEN stock = 0 THEN 1 ELSE 0 END) AS out_of_stock,
                    SUM(CASE WHEN stock > 0 AND stock < 20 THEN 1 ELSE 0 END) AS low_stock,
                    SUM(CASE WHEN stock >= 20 THEN 1 ELSE 0 END) AS in_stock
                FROM products
            """)
            row = cur.fetchone()
            cur.close()

            data = {
                'out_of_stock': row[0] or 0,
                'low_stock': row[1] or 0,
                'in_stock': row[2] or 0
            }

            return jsonify(data)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            app.logger.error(f"Error in /auth/api/inventory/stats: {e}\n{tb}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

    @app.route('/auth/api/inventory/product_stats')
    def api_inventory_product_stats():
        try:
            conn = mysql.connection
            cur = conn.cursor()
            # Count low stock products per brand
            query = """
                SELECT SUBSTRING_INDEX(TRIM(name), ' ', 1) as brand, COUNT(*) as low_stock_count
                FROM products
                WHERE stock > 0 AND stock < 20
                AND name IS NOT NULL
                AND TRIM(name) != ''
                AND SUBSTRING_INDEX(TRIM(name), ' ', 1) != ''
                GROUP BY brand
                ORDER BY low_stock_count DESC
                LIMIT 10
            """
            app.logger.info(f"Executing query: {query}")
            cur.execute(query)
            rows = cur.fetchall()
            cur.close()

            brands = []
            for row in rows:
                brands.append({
                    'brand': row[0],
                    'low_stock_count': row[1]
                })

            app.logger.info(f"Query result rows: {rows}")

            return jsonify({'success': True, 'brands': brands})
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            app.logger.error(f"Error in /auth/api/inventory/product_stats: {e}\n{tb}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

    @app.route('/api/staff/notifications')
    def api_staff_notifications():
        try:
            conn = mysql.connection
            cur = conn.cursor()

            # Fetch all relevant products with updated_at for recency
            cur.execute("""
                SELECT id, name, stock, updated_at FROM products
                WHERE stock = 0 OR (stock > 0 AND stock < 20) OR stock >= 20
                ORDER BY updated_at DESC
                LIMIT 10
            """)
            products = cur.fetchall()
            cur.close()

            notifications = []

            for p in products:
                p_id, p_name, p_stock, p_updated = p
                if p_stock == 0:
                    n_type = 'out_of_stock'
                    message = f"Out of stock alert: {p_name} is out of stock."
                elif 0 < p_stock < 20:
                    n_type = 'low_stock'
                    message = f"Low stock alert: {p_name} has only {p_stock} items left."
                else:
                    n_type = 'in_stock'
                    message = f"In stock alert: {p_name} has {p_stock} items available."

                notifications.append({
                    'type': n_type,
                    'product_id': p_id,
                    'name': p_name,
                    'stock': p_stock,
                    'message': message,
                    'updated_at': p_updated.isoformat() if hasattr(p_updated, 'isoformat') else str(p_updated)
                })

            return jsonify({'success': True, 'notifications': notifications})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/staff/inventory/<int:product_id>/update', methods=['POST'])
    def update_inventory(product_id):
        if session.get('role') not in ['staff', 'admin', 'super_admin']:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 403

        try:
            # Enhanced debug logging
            app.logger.info(f"=== UPDATE REQUEST START for product {product_id} ===")
            app.logger.info(f"Request files keys: {list(request.files.keys())}")
            app.logger.info(f"Request form keys: {list(request.form.keys())}")

            # Log file details
            for file_key in request.files.keys():
                file_obj = request.files[file_key]
                app.logger.info(f"File {file_key}: filename='{file_obj.filename}', content_type='{file_obj.content_type}', has_data={bool(file_obj.read(1))}")
                file_obj.seek(0)  # Reset file pointer after reading

            stock = request.form.get('stock')
            name = request.form.get('name')
            description = request.form.get('description')
            price = request.form.get('price')
            category_id = request.form.get('category')  # Changed to category_id

            # Convert empty strings to None for proper validation
            if category_id == '':
                category_id = None
            
            cpu = request.form.get('cpu')
            ram = request.form.get('ram')
            storage = request.form.get('storage')
            graphics = request.form.get('graphics')
            display = request.form.get('display')
            operating_system = request.form.get('os')
            keyboard = request.form.get('keyboard')
            battery = request.form.get('battery')
            weight = request.form.get('weight')
            warranty_id = request.form.get('warranty_id')
            original_price = request.form.get('original_price')
            color_name = request.form.get('color')
            color_id = None
            if color_name:
                cur = mysql.connection.cursor()
                cur.execute("SELECT id FROM colors WHERE name = %s", (color_name,))
                color = cur.fetchone()
                if color:
                    color_id = color[0]
                else:
                    cur.execute("INSERT INTO colors (name) VALUES (%s)", (color_name,))
                    mysql.connection.commit()
                    color_id = cur.lastrowid
                cur.close()

            field_updates = {}
            if stock is not None: field_updates['stock'] = stock
            if name is not None: field_updates['name'] = name
            if description is not None: field_updates['description'] = description
            if price is not None: field_updates['price'] = price
            if category_id is not None: field_updates['category_id'] = category_id
            if cpu is not None: field_updates['cpu'] = cpu
            if ram is not None: field_updates['ram'] = ram
            if storage is not None: field_updates['storage'] = storage
            if graphics is not None: field_updates['graphics'] = graphics
            if display is not None: field_updates['display'] = display
            if operating_system is not None: field_updates['os'] = operating_system
            if keyboard is not None: field_updates['keyboard'] = keyboard
            if battery is not None: field_updates['battery'] = battery
            if weight is not None: field_updates['weight'] = weight
            if warranty_id is not None: field_updates['warranty_id'] = warranty_id
            if color_id is not None: field_updates['color_id'] = color_id
            if original_price is not None: field_updates['original_price'] = original_price

            # Handle file uploads using the same logic as create route
            app.logger.info("=== STARTING FILE UPLOAD PROCESSING ===")
            for file_key, db_field in [
                ('photo', 'photo'),
                ('photo_back', 'back_view'),
                ('photo_left_rear', 'left_rear_view')
            ]:
                try:
                    app.logger.info(f"Processing file_key: {file_key} -> db_field: {db_field}")

                    if file_key in request.files:
                        file = request.files[file_key]
                        app.logger.info(f"File object found for {file_key}: filename='{file.filename}', content_type='{file.content_type}'")

                        if file.filename:  # File was selected and has a name
                            app.logger.info(f"File selected for {file_key}: {file.filename}")

                            if allowed_file(file.filename):
                                app.logger.info(f"File {file_key} has valid extension: {file.filename}")
                                filename = secure_filename(file.filename)
                                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                                app.logger.info(f"Saving {file_key} to: {upload_path}")

                                # Ensure upload directory exists
                                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

                                file.save(upload_path)
                                field_updates[db_field] = filename
                                app.logger.info(f"✓ Successfully saved {file_key} as {filename} and added to field_updates")
                            else:
                                app.logger.warning(f"✗ Skipping {file_key} - invalid file type for filename: {file.filename}")
                        else:
                            # Empty filename - this happens when no file is selected
                            # DO NOT update the database field - preserve existing image
                            app.logger.info(f"No file selected for {file_key}, preserving existing {db_field}")
                    else:
                        # File key not in request.files - no file input was sent
                        # DO NOT update the database field - preserve existing image
                        app.logger.info(f"No file input for {file_key}, preserving existing {db_field}")

                except Exception as file_error:
                    import traceback
                    app.logger.error(f"✗ Error processing {file_key}: {str(file_error)}")
                    app.logger.error(f"Traceback for {file_key}: {traceback.format_exc()}")
                    # Continue with other files

            app.logger.info(f"=== FILE PROCESSING COMPLETE. field_updates so far: {field_updates} ===")

            if not field_updates:
                app.logger.warning("No fields to update - returning error")
                return jsonify({'success': False, 'error': 'No fields to update'}), 400

            field_updates['updated_at'] = datetime.now() # Add updated_at
            app.logger.info(f"=== PREPARING DATABASE UPDATE ===")
            app.logger.info(f"Final field_updates: {field_updates}")

            set_clause_parts = []
            update_values = []
            for key, value in field_updates.items():
                set_clause_parts.append(f"`{key}` = %s")
                update_values.append(value)

            set_clause = ", ".join(set_clause_parts)
            update_values.append(product_id)

            final_query = f"UPDATE products SET {set_clause} WHERE id = %s"
            app.logger.info(f"SQL Query: {final_query}")
            app.logger.info(f"SQL Values: {update_values}")

            cur = mysql.connection.cursor()
            rows_affected = cur.execute(final_query, tuple(update_values))
            app.logger.info(f"Rows affected by update: {rows_affected}")

            mysql.connection.commit()
            app.logger.info("✓ Database commit successful")

            cur.close()
            app.logger.info("=== UPDATE REQUEST COMPLETE ===")
            return jsonify({'success': True})
        except Exception as e:
            import traceback
            app.logger.error(f"Error updating product {product_id}: {str(e)}")
            app.logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/staff/products/create', methods=['POST'])
    def create_product():
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 403
            
        try:
            name = request.form.get('name')
            description = request.form.get('description')
            price = request.form.get('price')
            stock = request.form.get('stock')
            category_id = request.form.get('category')  # Changed to category_id

            # Convert empty strings to None for proper validation
            if category_id == '':
                category_id = None

            # Validate required fields
            if not name or not price or not stock:
                return jsonify({'success': False, 'error': 'Name, price, and stock are required fields'}), 400

            if category_id is None:
                return jsonify({'success': False, 'error': 'Category is required'}), 400

            photo = None
            left_rear_view = None
            back_view = None
            color_name = request.form.get('color')
            color_id = None
            if color_name:
                cur = mysql.connection.cursor()
                cur.execute("SELECT id FROM colors WHERE name = %s", (color_name,))
                color = cur.fetchone()
                if color:
                    color_id = color[0]
                else:
                    cur.execute("INSERT INTO colors (name) VALUES (%s)", (color_name,))
                    mysql.connection.commit()
                    color_id = cur.lastrowid
                cur.close()

            # Handle file uploads
            if 'photo' in request.files:
                file = request.files['photo']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    photo = filename

            if 'photo_left_rear' in request.files:
                file = request.files['photo_left_rear']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    left_rear_view = filename



            if 'photo_back' in request.files:
                file = request.files['photo_back']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    back_view = filename

            product_id = Product.create(
                name=name,
                description=description,
                price=price,
                stock=stock,
                category_id=category_id,
                photo=photo,
                left_rear_view=left_rear_view,
                back_view=back_view,
                cpu=request.form.get('cpu'),
                ram=request.form.get('ram'),
                storage=request.form.get('storage'),
                graphics=request.form.get('graphics'),
                display=request.form.get('display'),
                os=request.form.get('os'),
                keyboard=request.form.get('keyboard'),
                battery=request.form.get('battery'),
                weight=request.form.get('weight'),
                warranty_id=request.form.get('warranty_id'),
                color_id=color_id,
                original_price=request.form.get('original_price')
            )
            cur = mysql.connection.cursor()
            cur.execute("UPDATE products SET updated_at = NOW() WHERE id = %s", (product_id,))
            mysql.connection.commit()
            cur.close()
            return jsonify({
                'success': True, 
                'product_id': product_id,
                'redirect': url_for('auth.staff_inventory')
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/staff/inventory/<int:product_id>/delete', methods=['DELETE'])
    def delete_product(product_id):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 403

        force_delete = request.args.get('force', 'false').lower() == 'true'

        try:
            # Use the Product.delete method with force option
            deleted = Product.delete(product_id, force=force_delete)
            if deleted:
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'error': 'Failed to delete or archive product for an unknown reason'}), 500
        except ValueError as e:
            # Handle specific error for active pre-orders or orders
            error_message = str(e)
            if 'active pre-orders' in error_message or 'active orders' in error_message:
                return jsonify({
                    'success': False,
                    'error': 'Cannot delete product with active pre-orders or orders. Please complete or cancel them first.'
                }), 400
            elif 'break order history' in error_message:
                return jsonify({
                    'success': False,
                    'error': error_message,
                    'archive_recommended': True
                }), 400
            return jsonify({'success': False, 'error': error_message}), 400
        except Exception as e:
            app.logger.error(f"Error deleting product: {e}")
            return jsonify({'success': False, 'error': 'An unexpected error occurred'}), 500

    @app.route('/api/staff/products/<int:product_id>/has-orders', methods=['GET'])
    def check_product_has_orders(product_id):
        """Check if a product has any orders (active or completed)"""
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 403

        try:
            conn = get_db()
            cur = conn.cursor()
            
            # Check for any orders with this product (including completed ones)
            cur.execute("""
                SELECT COUNT(*) FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                WHERE oi.product_id = %s
            """, (product_id,))
            order_count = cur.fetchone()[0]
            app.logger.info(f"Product {product_id} has {order_count} order items")
            
            # Check for any pre-orders with this product
            cur.execute("""
                SELECT COUNT(*) FROM pre_orders
                WHERE product_id = %s
            """, (product_id,))
            preorder_count = cur.fetchone()[0]
            app.logger.info(f"Product {product_id} has {preorder_count} pre-orders")
            
            has_orders = (order_count > 0) or (preorder_count > 0)
            app.logger.info(f"Product {product_id} has_orders: {has_orders}")
            
            cur.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'has_orders': has_orders,
                'order_count': order_count,
                'preorder_count': preorder_count
            })
            
        except Exception as e:
            app.logger.error(f"Error checking product orders: {e}")
            return jsonify({'success': False, 'error': 'An error occurred while checking orders'}), 500

    @app.route('/staff/inventory/<int:product_id>/archive', methods=['POST'])
    def archive_product(product_id):
        """Archive a product (mark as archived instead of deleting)"""
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 403

        try:
            conn = mysql.connection
            cur = conn.cursor()
            
            # Check if product exists and is not already archived
            cur.execute("SELECT name, archived FROM products WHERE id = %s", (product_id,))
            product = cur.fetchone()
            
            if not product:
                return jsonify({'success': False, 'error': 'Product not found'}), 404
            
            if product[1]:  # product[1] is the archived field
                return jsonify({'success': False, 'error': 'Product is already archived'}), 400
            
            # Archive the product
            cur.execute("UPDATE products SET archived = TRUE WHERE id = %s", (product_id,))
            conn.commit()
            
            app.logger.info(f"Product {product_id} archived successfully by user {session.get('user_id')}")
            return jsonify({'success': True, 'message': 'Product archived successfully'})
            
        except Exception as e:
            app.logger.error(f"Error archiving product: {e}")
            return jsonify({'success': False, 'error': 'An unexpected error occurred while archiving the product'}), 500
        finally:
            if 'cur' in locals():
                cur.close()

    @app.route('/staff/inventory/<int:product_id>/restore', methods=['POST'])
    def restore_product(product_id):
        """Restore an archived product (mark as not archived)"""
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 403

        try:
            conn = mysql.connection
            cur = conn.cursor()
            
            # Check if product exists and is archived
            cur.execute("SELECT name, archived FROM products WHERE id = %s", (product_id,))
            product = cur.fetchone()
            
            if not product:
                return jsonify({'success': False, 'error': 'Product not found'}), 404
            
            if not product[1]:  # product[1] is the archived field
                return jsonify({'success': False, 'error': 'Product is not archived'}), 400
            
            # Restore the product
            cur.execute("UPDATE products SET archived = FALSE WHERE id = %s", (product_id,))
            conn.commit()
            
            app.logger.info(f"Product {product_id} restored successfully by user {session.get('user_id')}")
            return jsonify({'success': True, 'message': 'Product restored successfully'})
            
        except Exception as e:
            app.logger.error(f"Error restoring product: {e}")
            return jsonify({'success': False, 'error': 'An unexpected error occurred while restoring the product'}), 500
        finally:
            if 'cur' in locals():
                cur.close()

    @app.route('/staff/inventory/create')
    def create_product_page():
        """Create product page"""
        if 'user_id' not in session or session.get('role') not in ['staff', 'admin', 'super_admin']:
            return redirect(url_for('auth.login'))
        
        try:
            # Get categories, warranties, and colors for dropdowns
            categories = Category.get_all()
            warranties = Warranty.get_all()
            colors = Color.get_all()
            
            return render_template('staff_product_form.html', 
                                 categories=categories,
                                 warranties=warranties,
                                 colors=colors,
                                 mode='create')
        except Exception as e:
            app.logger.error(f"Error loading create product page: {e}")
            return render_template('error.html', error='Internal server error'), 500

    @app.route('/staff/inventory/<int:product_id>/edit')
    def edit_product_page(product_id):
        """Edit product page"""
        if 'user_id' not in session or session.get('role') not in ['staff', 'admin', 'super_admin']:
            return redirect(url_for('auth.login'))
        
        try:
            # Get product data
            product = Product.get_by_id(product_id)
            if not product:
                return render_template('error.html', error='Product not found'), 404
            
            # Get categories, warranties, and colors for dropdowns
            categories = Category.get_all()
            warranties = Warranty.get_all()
            colors = Color.get_all()
            
            return render_template('staff_product_form.html', 
                                 product=product,
                                 categories=categories,
                                 warranties=warranties,
                                 colors=colors,
                                 mode='edit')
        except Exception as e:
            app.logger.error(f"Error loading edit product page: {e}")
            return render_template('error.html', error='Internal server error'), 500

    @app.route('/api/orders/<int:order_id>/items', methods=['GET'])
    def get_order_items(order_id):
        """Get order items for cart restoration"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        try:
            customer_id = session.get('user_id')
            if not customer_id:
                return jsonify({'success': False, 'error': 'Customer not found in session'}), 401

            conn = get_db()
            cur = conn.cursor(dictionary=True)

            try:
                # Verify the order belongs to the current customer
                cur.execute("""
                    SELECT id, customer_id, status
                    FROM orders
                    WHERE id = %s
                """, (order_id,))

                order = cur.fetchone()
                if not order:
                    return jsonify({'success': False, 'error': 'Order not found'}), 404

                if order['customer_id'] != customer_id:
                    return jsonify({'success': False, 'error': 'Unauthorized access to order'}), 403

                # Get order items
                cur.execute("""
                    SELECT oi.product_id, oi.quantity, oi.price, oi.product_name
                    FROM order_items oi
                    WHERE oi.order_id = %s AND oi.type != 'preorder'
                """, (order_id,))

                items = cur.fetchall()

                return jsonify({
                    'success': True,
                    'items': items
                })

            finally:
                cur.close()
                conn.close()

        except Exception as e:
            app.logger.error(f"Error getting order items: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/orders/<int:order_id>/cancel', methods=['POST'])
    def cancel_order_customer(order_id):
        """Cancel an order (customer only)"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        try:
            customer_id = session.get('user_id')
            if not customer_id:
                return jsonify({'success': False, 'error': 'Customer not found in session'}), 401

            conn = get_db()
            cur = conn.cursor(dictionary=True)

            try:
                # Verify the order belongs to the current customer
                cur.execute("""
                    SELECT id, customer_id, status
                    FROM orders
                    WHERE id = %s
                """, (order_id,))

                order = cur.fetchone()
                if not order:
                    return jsonify({'success': False, 'error': 'Order not found'}), 404

                if order['customer_id'] != customer_id:
                    return jsonify({'success': False, 'error': 'Unauthorized access to order'}), 403

                # Only allow cancellation of pending orders
                if order['status'].lower() not in ['pending', 'processing']:
                    return jsonify({'success': False, 'error': 'Only pending or processing orders can be cancelled'}), 400

                # Update order status to cancelled
                cur.execute("""
                    UPDATE orders
                    SET status = 'CANCELLED'
                    WHERE id = %s
                """, (order_id,))

                conn.commit()

                return jsonify({
                    'success': True,
                    'message': 'Order cancelled successfully'
                })

            finally:
                cur.close()
                conn.close()

        except Exception as e:
            app.logger.error(f"Error cancelling order: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/staff/inventory/<int:product_id>/delete/denormalized', methods=['DELETE'])
    def delete_product_denormalized(product_id):
        """Delete product using denormalization approach - preserves order history"""
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 403

        force_delete = request.args.get('force', 'false').lower() == 'true'
        staff_user_id = session.get('user_id')
        
        try:
            success = Product.delete_with_denormalization(
                product_id, force=force_delete, staff_user_id=staff_user_id
            )
            if success:
                return jsonify({'success': True, 'message': 'Product deleted successfully (order history preserved)'})
            else:
                return jsonify({'success': False, 'error': 'Failed to delete product'}), 500
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            app.logger.error(f"Error deleting product with denormalization: {e}")
            return jsonify({'success': False, 'error': 'An unexpected error occurred'}), 500

    # Discount Management Endpoints
    @app.route('/api/staff/discounts/products', methods=['GET'])
    def get_discounted_products():
        """Get all products currently on discount with pagination"""
        if 'user_id' not in session or session.get('role') not in ['staff', 'admin', 'super_admin']:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 403

        try:
            # Get pagination parameters
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('page_size', 10))

            conn = mysql.connection
            cur = conn.cursor()
            
            # Count total discounted products
            cur.execute("""
                SELECT COUNT(*)
                FROM products p
                WHERE p.discount_percentage IS NOT NULL
                AND (p.archived IS NULL OR p.archived = FALSE)
            """)
            total_count = cur.fetchone()[0]
            
            app.logger.info(f"Found {total_count} discounted products")

            # Calculate pagination
            total_pages = (total_count + page_size - 1) // page_size
            offset = (page - 1) * page_size

            # Fetch paginated discounted products
            cur.execute("""
                SELECT p.id, p.name, p.price, p.original_price, p.stock, c.name as category_name,
                       p.discount_percentage,
                       p.original_price as supplier_cost,
                       ROUND(p.price / (1 - p.discount_percentage / 100), 2) as selling_price_before_discount,
                       CASE 
                           WHEN p.discount_percentage > 0
                           THEN ROUND((p.price / (1 - p.discount_percentage / 100)) - p.price, 2)
                           ELSE 0
                       END as savings_amount
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.discount_percentage IS NOT NULL
                AND (p.archived IS NULL OR p.archived = FALSE)
                ORDER BY p.discount_percentage DESC
                LIMIT %s OFFSET %s
            """, (page_size, offset))
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            products = [dict(zip(columns, row)) for row in rows]
            cur.close()

            return jsonify({
                'success': True,
                'products': products,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_count': total_count,
                    'total_pages': total_pages
                }
            })
        except Exception as e:
            app.logger.error(f"Error fetching discounted products: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500




    @app.route('/api/staff/discounts/apply-single', methods=['POST'])
    def apply_single_discount():
        """Apply discount to a single product"""
        if 'user_id' not in session or session.get('role') not in ['staff', 'admin', 'super_admin']:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 403

        try:
            data = request.get_json()
            app.logger.info(f"Received discount request data: {data}")

            product_id = data.get('product_id')
            discount_percentage = float(data.get('discount_percentage', 0))
            # New parameter: apply_from_current_price (default to False for backward compatibility)
            apply_from_current_price = data.get('apply_from_current_price', False)

            app.logger.info(f"Parsed values - product_id: {product_id}, discount_percentage: {discount_percentage}, apply_from_current_price: {apply_from_current_price}")

            if not product_id or discount_percentage <= 0 or discount_percentage >= 100:
                app.logger.error(f"Invalid input - product_id: {product_id}, discount_percentage: {discount_percentage}")
                return jsonify({'success': False, 'error': 'Invalid product ID or discount percentage'}), 400

            conn = mysql.connection
            cur = conn.cursor()
            app.logger.info(f"Database connection established")

            # Get current product details
            cur.execute("SELECT price, original_price FROM products WHERE id = %s", (product_id,))
            product = cur.fetchone()
            app.logger.info(f"Product query result: {product}")
            
            if not product:
                app.logger.error(f"Product not found with ID: {product_id}")
                return jsonify({'success': False, 'error': 'Product not found'}), 404
            
            current_price, original_price = product

            # Convert Decimal to float for calculations
            current_price_float = float(current_price)
            
            # For discount detection, we need to ensure original_price represents the price BEFORE any discounts
            # We NEVER change original_price - it's the baseline reference that stays constant
            if original_price is None:
                # If no original_price is set, use current price as the "original" reference
                original_price_float = current_price_float
                cur.execute("UPDATE products SET original_price = %s WHERE id = %s", (original_price_float, product_id))
            else:
                original_price_float = float(original_price)
                app.logger.info(f"Using original_price ${original_price_float} as baseline reference (never changes)")

            # Always apply discount from current selling price
            base_price = current_price_float
            app.logger.info(f"Applying {discount_percentage}% discount from current selling price: ${base_price}")

            new_price = round(base_price * (1 - discount_percentage / 100), 2)
            
            # Log the values for debugging
            app.logger.info(f"Discount calculation: base_price=${base_price}, new_price=${new_price}, original_price=${original_price_float}")
            app.logger.info(f"Will this be detected as discounted? {new_price < original_price_float}")

            # Update product price and store the applied discount percentage
            cur.execute("UPDATE products SET price = %s, discount_percentage = %s WHERE id = %s", (new_price, discount_percentage, product_id))
            mysql.connection.commit()
            cur.close()

            return jsonify({
                'success': True,
                'message': f'Discount of {discount_percentage}% applied successfully',
                'new_price': new_price,
                'original_price': original_price_float,
                'base_price_used': base_price,
                'savings': round(base_price - new_price, 2),
                'total_savings_from_original': round(original_price_float - new_price, 2)
            })
            
        except Exception as e:
            app.logger.error(f"Error applying single discount: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/staff/discounts/apply-bulk', methods=['POST'])
    def apply_bulk_discount():
        """Apply discount to multiple products"""
        if 'user_id' not in session or session.get('role') not in ['staff', 'admin', 'super_admin']:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 403

        try:
            data = request.get_json()
            product_ids = data.get('product_ids', [])
            discount_percentage = float(data.get('discount_percentage', 0))

            if not product_ids or not isinstance(product_ids, list):
                return jsonify({'success': False, 'error': 'Invalid product IDs list'}), 400

            if discount_percentage <= 0 or discount_percentage >= 100:
                return jsonify({'success': False, 'error': 'Invalid discount percentage'}), 400

            conn = mysql.connection
            cur = conn.cursor()

            # Process each product
            updated_products = []
            failed_products = []

            for product_id in product_ids:
                try:
                    # Get current product details
                    cur.execute("SELECT name, price, original_price FROM products WHERE id = %s", (product_id,))
                    product = cur.fetchone()

                    if not product:
                        failed_products.append(f"Product ID {product_id} not found")
                        continue

                    product_name, current_price, original_price = product

                    # Convert Decimal to float for calculations
                    current_price_float = float(current_price)
                    
                    # For discount detection, we need to ensure original_price represents the price BEFORE any discounts
                    # We NEVER change original_price - it's the baseline reference that stays constant
                    if original_price is None:
                        # If no original_price is set, use current price as the "original" reference
                        original_price_float = current_price_float
                        cur.execute("UPDATE products SET original_price = %s WHERE id = %s", (original_price_float, product_id))
                    else:
                        original_price_float = float(original_price)
                        app.logger.info(f"Using original_price ${original_price_float} as baseline reference (never changes)")

                    # Calculate new discounted price from current selling price
                    new_price = round(current_price_float * (1 - discount_percentage / 100), 2)
                    
                    # Log the values for debugging
                    app.logger.info(f"Bulk discount for product {product_id}: base_price=${current_price_float}, new_price=${new_price}, original_price=${original_price_float}")
                    app.logger.info(f"Will this be detected as discounted? {new_price < original_price_float}")

                    # Update product price and store the applied discount percentage
                    cur.execute("UPDATE products SET price = %s, discount_percentage = %s WHERE id = %s", (new_price, discount_percentage, product_id))

                    updated_products.append({
                        'id': product_id,
                        'name': product_name,
                        'original_price': original_price_float,
                        'new_price': new_price,
                        'savings': round(original_price_float - new_price, 2)
                    })

                except Exception as e:
                    failed_products.append(f"Product ID {product_id}: {str(e)}")

            mysql.connection.commit()
            cur.close()

            success_count = len(updated_products)
            total_count = len(product_ids)

            if success_count == 0:
                return jsonify({
                    'success': False,
                    'error': 'No products were updated',
                    'failed_products': failed_products
                }), 400

            message = f'Bulk discount of {discount_percentage}% applied to {success_count} of {total_count} products'

            response_data = {
                'success': True,
                'message': message,
                'updated_products': updated_products,
                'success_count': success_count,
                'total_count': total_count
            }

            if failed_products:
                response_data['failed_products'] = failed_products

            return jsonify(response_data)

        except Exception as e:
            app.logger.error(f"Error applying bulk discount: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    # Customer History & Recognition Endpoints
    @app.route('/api/staff/customers/search', methods=['GET'])
    def search_customers():
        """Search customers by name, email, or phone"""
        if 'user_id' not in session or session.get('role') not in ['staff', 'admin', 'super_admin']:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 403

        try:
            query = (request.args.get('q') or '').strip()
            if not query:
                return jsonify({'success': False, 'error': 'Search query required'}), 400

            conn = mysql.connection
            cur = conn.cursor()

            # Search customers by name, email, or phone
            search_pattern = f"%{query}%"
            cur.execute("""
                SELECT id, CONCAT(first_name, ' ', last_name) as name, email, phone,
                       (SELECT COUNT(*) FROM orders WHERE customer_id = customers.id) as total_orders
                FROM customers
                WHERE CONCAT(first_name, ' ', last_name) LIKE %s
                   OR email LIKE %s
                   OR phone LIKE %s
                ORDER BY first_name, last_name
                LIMIT 10
            """, (search_pattern, search_pattern, search_pattern))

            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            customers = [dict(zip(columns, row)) for row in rows]
            cur.close()

            return jsonify({'success': True, 'customers': customers})

        except Exception as e:
            app.logger.error(f"Error searching customers: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/staff/customers/<int:customer_id>/discount-history', methods=['GET'])
    def get_customer_discount_history(customer_id):
        """Get discount history for a specific customer"""
        if 'user_id' not in session or session.get('role') not in ['staff', 'admin', 'super_admin']:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 403

        try:
            conn = mysql.connection
            cur = conn.cursor()

            # Get customer info
            cur.execute("""
                SELECT id, CONCAT(first_name, ' ', last_name) as name, email, phone,
                       (SELECT COUNT(*) FROM orders WHERE customer_id = customers.id) as total_orders
                FROM customers WHERE id = %s
            """, (customer_id,))

            customer_row = cur.fetchone()
            if not customer_row:
                return jsonify({'success': False, 'error': 'Customer not found'}), 404

            customer_columns = [desc[0] for desc in cur.description]
            customer = dict(zip(customer_columns, customer_row))

            # Get discount history by comparing order item prices with current product original prices
            # This is a simplified approach since we don't have original_price in order_items yet
            cur.execute("""
                SELECT
                    o.order_date as date,
                    p.name as product_name,
                    COALESCE(p.original_price, p.price) as original_price,
                    oi.price as final_price,
                    CASE
                        WHEN p.original_price IS NOT NULL AND p.original_price > oi.price
                        THEN ROUND(((p.original_price - oi.price) / p.original_price) * 100, 1)
                        ELSE 0
                    END as discount_percentage,
                    CASE
                        WHEN p.original_price IS NOT NULL AND p.original_price > oi.price
                        THEN ROUND(p.original_price - oi.price, 2)
                        ELSE 0
                    END as savings,
                    'Not Tracked' as staff_name
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                JOIN products p ON oi.product_id = p.id
                WHERE o.customer_id = %s
                AND o.order_date >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
                ORDER BY o.order_date DESC
                LIMIT 50
            """, (customer_id,))

            history_rows = cur.fetchall()
            history_columns = [desc[0] for desc in cur.description]
            history = [dict(zip(history_columns, row)) for row in history_rows]

            # Calculate insights
            insights = calculate_customer_insights(cur, customer_id, history)

            cur.close()

            return jsonify({
                'success': True,
                'customer': customer,
                'history': history,
                'insights': insights
            })

        except Exception as e:
            app.logger.error(f"Error getting customer discount history: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/staff/customers/recent-activity', methods=['GET'])
    def get_recent_customer_activity():
        """Get customers with recent discount activity"""
        if 'user_id' not in session or session.get('role') not in ['staff', 'admin', 'super_admin']:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 403

        try:
            conn = mysql.connection
            cur = conn.cursor()

            # Get customers with recent activity (including potential discounts)
            cur.execute("""
                SELECT
                    c.id,
                    CONCAT(c.first_name, ' ', c.last_name) as name,
                    c.email,
                    c.phone,
                    MAX(o.order_date) as last_visit,
                    COUNT(DISTINCT o.id) as order_count,
                    COUNT(DISTINCT oi.id) as item_count,
                    ROUND(AVG(
                        CASE
                            WHEN p.original_price IS NOT NULL AND p.original_price > oi.price
                            THEN ((p.original_price - oi.price) / p.original_price) * 100
                            ELSE 0
                        END
                    ), 1) as avg_discount
                FROM customers c
                JOIN orders o ON c.id = o.customer_id
                JOIN order_items oi ON o.id = oi.order_id
                JOIN products p ON oi.product_id = p.id
                WHERE o.order_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                GROUP BY c.id, c.first_name, c.last_name, c.email, c.phone
                HAVING avg_discount > 0 OR order_count >= 2
                ORDER BY last_visit DESC
                LIMIT 20
            """)

            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            customers = [dict(zip(columns, row)) for row in rows]
            cur.close()

            return jsonify({'success': True, 'customers': customers})

        except Exception as e:
            app.logger.error(f"Error getting recent customer activity: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    def calculate_customer_insights(cur, customer_id, history):
        """Calculate insights for customer discount behavior"""
        insights = {
            'most_common_discount': None,
            'total_purchases': 0,
            'total_savings': 0,
            'average_discount': 0,
            'last_visit': None
        }

        if not history:
            return insights

        # Calculate most common discount percentage
        discount_counts = {}
        total_savings = 0
        total_discount = 0

        for item in history:
            discount = item['discount_percentage']
            if discount:
                discount_counts[discount] = discount_counts.get(discount, 0) + 1
                total_discount += discount

            if item['savings']:
                total_savings += float(item['savings'])

        if discount_counts:
            insights['most_common_discount'] = max(discount_counts, key=discount_counts.get)
            insights['average_discount'] = round(total_discount / len(history), 1)

        insights['total_purchases'] = len(history)
        insights['total_savings'] = total_savings

        # Get last visit date
        if history:
            insights['last_visit'] = history[0]['date']  # Already ordered by date DESC

        return insights

    @app.route('/api/staff/discounts/apply-category', methods=['POST'])
    def apply_category_discount():
        """Apply discount to all products in a category"""
        if 'user_id' not in session or session.get('role') not in ['staff', 'admin', 'super_admin']:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 403

        try:
            data = request.get_json()
            category_id = data.get('category_id')
            discount_percentage = float(data.get('discount_percentage', 0))

            if not category_id or discount_percentage <= 0 or discount_percentage >= 100:
                return jsonify({'success': False, 'error': 'Invalid category ID or discount percentage'}), 400

            conn = mysql.connection
            cur = conn.cursor()

            # First, set original_price for products that don't have it
            # This ensures we can detect discounts properly
            cur.execute("""
                UPDATE products
                SET original_price = price
                WHERE category_id = %s AND original_price IS NULL
            """, (category_id,))

            # Apply discount to all products in category from current selling price
            cur.execute("""
                UPDATE products
                SET price = ROUND(price * %s, 2), discount_percentage = %s
                WHERE category_id = %s
            """, (1 - discount_percentage / 100, discount_percentage, category_id))

            affected_rows = cur.rowcount
            mysql.connection.commit()
            cur.close()

            return jsonify({
                'success': True,
                'message': f'Discount of {discount_percentage}% applied to {affected_rows} products in category',
                'affected_products': affected_rows
            })

        except Exception as e:
            app.logger.error(f"Error applying category discount: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/staff/discounts/apply-brand', methods=['POST'])
    def apply_brand_discount():
        """Apply discount to all products of a specific brand"""
        if 'user_id' not in session or session.get('role') not in ['staff', 'admin', 'super_admin']:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 403

        try:
            data = request.get_json()
            brand_name = (data.get('brand_name') or '').strip()
            discount_percentage = float(data.get('discount_percentage', 0))

            if not brand_name or discount_percentage <= 0 or discount_percentage > 50:
                return jsonify({'success': False, 'error': 'Invalid brand name or discount percentage. Brand discounts are limited to 50% maximum.'}), 400

            conn = mysql.connection
            cur = conn.cursor()

            # First, set original_price for products that don't have it
            # This ensures we can detect discounts properly
            cur.execute("""
                UPDATE products
                SET original_price = price
                WHERE name LIKE %s AND original_price IS NULL
            """, (f"{brand_name}%",))

            # Apply discount to all products of the brand from current selling price
            cur.execute("""
                UPDATE products
                SET price = ROUND(price * %s, 2), discount_percentage = %s
                WHERE name LIKE %s
            """, (1 - discount_percentage / 100, discount_percentage, f"{brand_name}%"))

            affected_rows = cur.rowcount
            mysql.connection.commit()
            cur.close()

            return jsonify({
                'success': True,
                'message': f'Discount of {discount_percentage}% applied to {affected_rows} {brand_name} products',
                'affected_products': affected_rows
            })

        except Exception as e:
            app.logger.error(f"Error applying brand discount: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/staff/discounts/remove', methods=['POST'])
    def remove_discount():
        """Remove discount from a product (restore original price)"""
        if 'user_id' not in session or session.get('role') not in ['staff', 'admin', 'super_admin']:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 403

        try:
            data = request.get_json()
            product_id = data.get('product_id')

            if not product_id:
                return jsonify({'success': False, 'error': 'Invalid product ID'}), 400

            conn = mysql.connection
            cur = conn.cursor()

            # Get current price and original price before removing discount
            cur.execute("""
                SELECT price, original_price FROM products 
                WHERE id = %s AND original_price IS NOT NULL
            """, (product_id,))
            
            result = cur.fetchone()
            if not result:
                return jsonify({'success': False, 'error': 'Product not found or no original price set'}), 404
                
            current_price, original_price = result
            
            # We need to restore the price to what it was BEFORE the discount was applied
            # Since we don't store the pre-discount price, we need to calculate it back
            # The current price is discounted, so we reverse the discount calculation
            # We NEVER clear original_price - it's the baseline reference
            
            # Get the discount percentage to calculate the original selling price
            cur.execute("SELECT discount_percentage FROM products WHERE id = %s", (product_id,))
            discount_result = cur.fetchone()
            
            if discount_result and discount_result[0] is not None:
                discount_percentage = float(discount_result[0])
                # Calculate the price before discount: current_price / (1 - discount_percentage/100)
                # Convert current_price to float to avoid decimal/float division error
                current_price_float = float(current_price)
                pre_discount_price = round(current_price_float / (1 - discount_percentage / 100), 2)
                app.logger.info(f"Calculating pre-discount price: ${current_price_float} / (1 - {discount_percentage}/100) = ${pre_discount_price}")
                
                # Restore the pre-discount price and clear discount_percentage
                cur.execute("""
                    UPDATE products
                    SET price = %s, discount_percentage = NULL
                    WHERE id = %s
                """, (pre_discount_price, product_id))
            else:
                # No discount percentage found, just clear it
                cur.execute("""
                    UPDATE products
                    SET discount_percentage = NULL
                    WHERE id = %s
                """, (product_id,))

            if cur.rowcount == 0:
                return jsonify({'success': False, 'error': 'Product not found or no original price set'}), 404

            # Get the updated price after restoration (before closing cursor)
            cur.execute("SELECT price FROM products WHERE id = %s", (product_id,))
            updated_price = cur.fetchone()[0]
            
            mysql.connection.commit()
            cur.close()
            
            return jsonify({
                'success': True, 
                'message': f'Discount removed successfully. Product price restored to ${updated_price}',
                'current_price': current_price,
                'original_price': original_price,
                'restored_price': updated_price
            })

        except Exception as e:
            app.logger.error(f"Error removing discount: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/staff/discounts/remove-all', methods=['POST'])
    def remove_all_discounts():
        """Remove all discounts from all products (restore original prices)"""
        if 'user_id' not in session or session.get('role') not in ['staff', 'admin', 'super_admin']:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 403

        try:
            app.logger.info(f"User {session['user_id']} (role: {session.get('role')}) attempting to remove all discounts")
            
            conn = mysql.connection
            cur = conn.cursor()

            # Count how many products have discounts
            cur.execute("""
                SELECT COUNT(*)
                FROM products
                WHERE discount_percentage IS NOT NULL
                AND (archived IS NULL OR archived = FALSE)
            """)
            discounted_count = cur.fetchone()[0]
            
            app.logger.info(f"Found {discounted_count} products with discounts")

            if discounted_count == 0:
                app.logger.info("No discounts to remove")
                return jsonify({'success': True, 'message': 'No discounts to remove', 'count': 0})

            # Remove all discounts by restoring pre-discount prices
            # We need to calculate back to the pre-discount price for each product
            # We NEVER clear original_price - it's the baseline reference
            app.logger.info("Executing UPDATE query to remove all discounts")
            
            # First, get all products with discounts to calculate their pre-discount prices
            cur.execute("""
                SELECT id, price, discount_percentage
                FROM products
                WHERE discount_percentage IS NOT NULL
                AND (archived IS NULL OR archived = FALSE)
            """)
            discounted_products = cur.fetchall()
            
            restored_count = 0
            for product in discounted_products:
                product_id, current_price, discount_percentage = product
                if discount_percentage is not None:
                    # Calculate the price before discount: current_price / (1 - discount_percentage/100)
                    # Convert both values to float to avoid decimal/float division error
                    current_price_float = float(current_price)
                    discount_percentage_float = float(discount_percentage)
                    pre_discount_price = round(current_price_float / (1 - discount_percentage_float / 100), 2)
                    app.logger.info(f"Product {product_id}: restoring from ${current_price_float} to ${pre_discount_price}")
                    
                    # Restore the pre-discount price and clear discount_percentage
                    cur.execute("""
                        UPDATE products
                        SET price = %s, discount_percentage = NULL
                        WHERE id = %s
                    """, (pre_discount_price, product_id))
                    restored_count += 1
            
            app.logger.info(f"Restored {restored_count} products to their pre-discount prices")

            affected_rows = restored_count
            app.logger.info(f"Restored {affected_rows} products to their pre-discount prices")
            
            mysql.connection.commit()
            cur.close()

            app.logger.info(f"User {session['user_id']} successfully removed all discounts from {affected_rows} products")
            
            return jsonify({
                'success': True, 
                'message': f'Successfully removed discounts from {affected_rows} products',
                'count': affected_rows
            })

        except Exception as e:
            app.logger.error(f"Error removing all discounts: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    # Volume Discount Management Routes
    @app.route('/api/staff/volume-discounts', methods=['GET'])
    def get_volume_discounts():
        """Get all volume discount rules"""
        if 'user_id' not in session or session.get('role') not in ['staff', 'admin', 'super_admin']:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 403

        try:
            conn = mysql.connection
            cur = conn.cursor()

            app.logger.info(f"Fetching volume discount rules for user {session['user_id']}")

            cur.execute("""
                SELECT vdr.id, vdr.name, vdr.minimum_amount, vdr.discount_percentage,
                       vdr.max_discount_amount, vdr.is_active, vdr.description, vdr.priority,
                       vdr.created_at, u.username as created_by_name
                FROM volume_discount_rules vdr
                LEFT JOIN users u ON vdr.created_by = u.id
                WHERE vdr.is_active = TRUE
                ORDER BY vdr.minimum_amount ASC
            """)

            rules = []
            for row in cur.fetchall():
                rule = {
                    'id': row[0],
                    'name': row[1],
                    'minimum_amount': float(row[2]),
                    'discount_percentage': float(row[3]),
                    'max_discount_amount': float(row[4]) if row[4] else None,
                    'is_active': bool(row[5]),
                    'description': row[6],
                    'priority': row[7],
                    'created_at': row[8].strftime('%Y-%m-%d %H:%M:%S') if row[8] else None,
                    'created_by_name': row[9]
                }
                rules.append(rule)

            cur.close()
            
            app.logger.info(f"Found {len(rules)} active volume discount rules")
            return jsonify({'success': True, 'rules': rules})

        except Exception as e:
            app.logger.error(f"Error fetching volume discounts: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/staff/volume-discounts', methods=['POST'])
    def create_volume_discount():
        """Create a new volume discount rule"""
        if 'user_id' not in session or session.get('role') not in ['staff', 'admin', 'super_admin']:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 403

        try:
            data = request.get_json()
            name = data.get('name', '').strip()
            minimum_amount = float(data.get('minimum_amount', 0))
            discount_percentage = float(data.get('discount_percentage', 0))
            max_discount_amount = None  # No longer supported - always unlimited
            description = data.get('description', '').strip()

            # Validation
            if not name or minimum_amount <= 0 or discount_percentage <= 0 or discount_percentage > 50:
                return jsonify({'success': False, 'error': 'Invalid input data'}), 400

            conn = mysql.connection
            cur = conn.cursor()

            # Check for duplicate minimum amounts
            cur.execute("SELECT COUNT(*) FROM volume_discount_rules WHERE minimum_amount = %s AND is_active = TRUE",
                       (minimum_amount,))
            if cur.fetchone()[0] > 0:
                return jsonify({'success': False, 'error': 'A rule with this minimum amount already exists'}), 400

            # Get next priority
            cur.execute("SELECT COALESCE(MAX(priority), 0) + 1 FROM volume_discount_rules")
            priority = cur.fetchone()[0]

            # Insert new rule
            cur.execute("""
                INSERT INTO volume_discount_rules
                (name, minimum_amount, discount_percentage, max_discount_amount, description, priority, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (name, minimum_amount, discount_percentage, max_discount_amount, description, priority, session['user_id']))

            mysql.connection.commit()
            cur.close()

            return jsonify({
                'success': True,
                'message': f'Volume discount rule "{name}" created successfully'
            })

        except Exception as e:
            app.logger.error(f"Error creating volume discount: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/staff/volume-discounts/<int:rule_id>', methods=['PUT'])
    def update_volume_discount(rule_id):
        """Update a volume discount rule"""
        if 'user_id' not in session or session.get('role') not in ['staff', 'admin', 'super_admin']:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 403

        try:
            data = request.get_json()
            name = data.get('name', '').strip()
            minimum_amount = float(data.get('minimum_amount', 0))
            discount_percentage = float(data.get('discount_percentage', 0))
            max_discount_amount = None  # No longer supported - always unlimited
            description = data.get('description', '').strip()

            # Validation
            if not name or minimum_amount <= 0 or discount_percentage <= 0 or discount_percentage > 50:
                return jsonify({'success': False, 'error': 'Invalid input data'}), 400

            conn = mysql.connection
            cur = conn.cursor()

            # Check for duplicate minimum amounts (excluding current rule)
            cur.execute("""
                SELECT COUNT(*) FROM volume_discount_rules
                WHERE minimum_amount = %s AND is_active = TRUE AND id != %s
            """, (minimum_amount, rule_id))
            if cur.fetchone()[0] > 0:
                return jsonify({'success': False, 'error': 'A rule with this minimum amount already exists'}), 400

            # Update rule
            cur.execute("""
                UPDATE volume_discount_rules
                SET name = %s, minimum_amount = %s, discount_percentage = %s,
                    max_discount_amount = %s, description = %s
                WHERE id = %s AND is_active = TRUE
            """, (name, minimum_amount, discount_percentage, max_discount_amount, description, rule_id))

            if cur.rowcount == 0:
                return jsonify({'success': False, 'error': 'Rule not found'}), 404

            mysql.connection.commit()
            cur.close()

            return jsonify({
                'success': True,
                'message': f'Volume discount rule "{name}" updated successfully'
            })

        except Exception as e:
            app.logger.error(f"Error updating volume discount: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/staff/volume-discounts/<int:rule_id>', methods=['DELETE'])
    def delete_volume_discount(rule_id):
        """Delete a volume discount rule"""
        if 'user_id' not in session or session.get('role') not in ['staff', 'admin', 'super_admin']:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 403

        try:
            conn = mysql.connection
            cur = conn.cursor()

            # First, verify the rule exists and is active
            cur.execute("""
                SELECT id, name FROM volume_discount_rules
                WHERE id = %s AND is_active = TRUE
            """, (rule_id,))
            
            rule = cur.fetchone()
            if not rule:
                return jsonify({'success': False, 'error': 'Rule not found or already deleted'}), 404

            # Check if there are any orders using this rule
            cur.execute("""
                SELECT COUNT(*) FROM orders 
                WHERE volume_discount_rule_id = %s
            """, (rule_id,))
            
            order_count = cur.fetchone()[0]
            app.logger.info(f"Volume discount rule {rule_id} is used by {order_count} orders")

            # Soft delete by setting is_active to FALSE
            update_sql = """
                UPDATE volume_discount_rules
                SET is_active = FALSE
                WHERE id = %s AND is_active = TRUE
            """
            app.logger.info(f"Executing SQL: {update_sql} with rule_id={rule_id}")
            
            cur.execute(update_sql, (rule_id,))

            if cur.rowcount == 0:
                return jsonify({'success': False, 'error': 'Rule not found or already deleted'}), 404

            mysql.connection.commit()
            cur.close()

            app.logger.info(f"Volume discount rule {rule_id} ({rule[1]}) deleted successfully by user {session['user_id']}")

            return jsonify({
                'success': True,
                'message': f'Volume discount rule "{rule[1]}" deleted successfully'
            })

        except Exception as e:
            app.logger.error(f"Error deleting volume discount rule {rule_id}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/calculate-volume-discount', methods=['POST'])
    def calculate_volume_discount():
        """Calculate volume discount for a given cart total"""
        try:
            data = request.get_json()
            cart_total = float(data.get('cart_total', 0))

            if cart_total <= 0:
                return jsonify({
                    'success': True,
                    'volume_discount': {
                        'applicable': False,
                        'rule_name': None,
                        'discount_percentage': 0,
                        'discount_amount': 0,
                        'final_total': cart_total,
                        'savings': 0
                    }
                })

            conn = mysql.connection
            cur = conn.cursor()

            # Find the best applicable volume discount rule
            cur.execute("""
                SELECT id, name, discount_percentage, max_discount_amount
                FROM volume_discount_rules
                WHERE minimum_amount <= %s AND is_active = TRUE
                ORDER BY minimum_amount DESC
                LIMIT 1
            """, (cart_total,))

            rule = cur.fetchone()
            cur.close()

            if rule:
                rule_id, rule_name, discount_percentage, _ = rule

                # Convert Decimal to float for calculations
                discount_percentage = float(discount_percentage)

                # Calculate discount amount (no maximum limit)
                discount_amount = cart_total * (discount_percentage / 100)

                final_total = cart_total - discount_amount

                return jsonify({
                    'success': True,
                    'volume_discount': {
                        'applicable': True,
                        'rule_id': rule_id,
                        'rule_name': rule_name,
                        'discount_percentage': float(discount_percentage),
                        'discount_amount': round(discount_amount, 2),
                        'final_total': round(final_total, 2),
                        'savings': round(discount_amount, 2),
                        'original_total': cart_total
                    }
                })
            else:
                # No applicable discount
                return jsonify({
                    'success': True,
                    'volume_discount': {
                        'applicable': False,
                        'rule_name': None,
                        'discount_percentage': 0,
                        'discount_amount': 0,
                        'final_total': cart_total,
                        'savings': 0,
                        'original_total': cart_total
                    }
                })

        except Exception as e:
            app.logger.error(f"Error calculating volume discount: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/staff/discounts/products-list', methods=['GET'])
    def get_products_for_discount():
        """Get all products for discount selection dropdown"""
        if 'user_id' not in session or session.get('role') not in ['staff', 'admin', 'super_admin']:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 403

        try:
            conn = mysql.connection
            cur = conn.cursor()
            cur.execute("""
                SELECT p.id, p.name, p.price, p.original_price, c.name as category_name
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE (p.archived IS NULL OR p.archived = FALSE)
                ORDER BY p.name
            """)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            products = [dict(zip(columns, row)) for row in rows]
            cur.close()

            return jsonify({'success': True, 'products': products})
        except Exception as e:
            app.logger.error(f"Error fetching products for discount: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/staff/discounts/search-products', methods=['GET'])
    def search_products_for_discount():
        """Search products for discount selection with filters"""
        if 'user_id' not in session or session.get('role') not in ['staff', 'admin', 'super_admin']:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 403

        try:
            search = (request.args.get('search') or '').strip()
            category_id = request.args.get('category_id', '')
            discount_only = request.args.get('discount_only', 'false').lower() == 'true'
            limit = int(request.args.get('limit', 10))
            offset = int(request.args.get('offset', 0))

            conn = mysql.connection
            cur = conn.cursor()

            # Build the query with filters
            where_conditions = []
            params = []

            if search:
                where_conditions.append("(p.name LIKE %s OR p.description LIKE %s)")
                search_param = f"%{search}%"
                params.extend([search_param, search_param])

            if category_id and category_id.isdigit():
                where_conditions.append("p.category_id = %s")
                params.append(int(category_id))

            if discount_only:
                where_conditions.append("p.original_price IS NOT NULL AND p.original_price > p.price")

            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""

            # Get total count
            count_query = f"""
                SELECT COUNT(*) as total
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                {where_clause}
                AND (p.archived IS NULL OR p.archived = FALSE)
            """
            cur.execute(count_query, params)
            total = cur.fetchone()[0]

            # Get products with pagination
            query = f"""
                SELECT p.id, p.name, p.price, p.original_price, p.stock, c.name as category_name
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                {where_clause}
                AND (p.archived IS NULL OR p.archived = FALSE)
                ORDER BY p.name
                LIMIT %s OFFSET %s
            """
            params.extend([limit, offset])
            cur.execute(query, params)

            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            products = [dict(zip(columns, row)) for row in rows]
            cur.close()

            return jsonify({
                'success': True,
                'products': products,
                'total': total,
                'limit': limit,
                'offset': offset
            })
        except Exception as e:
            app.logger.error(f"Error searching products for discount: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/staff/discounts/recently-used', methods=['GET'])
    def get_recently_used_products():
        """Get recently used products for discount selection"""
        if 'user_id' not in session or session.get('role') not in ['staff', 'admin', 'super_admin']:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 403

        try:
            user_id = session['user_id']
            conn = mysql.connection
            cur = conn.cursor()

            # Get recently modified products (products that had price changes recently)
            # This includes products that had discounts applied or removed
            cur.execute("""
                SELECT DISTINCT p.id, p.name, p.price, p.original_price, p.stock, c.name as category_name,
                       p.updated_at
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE (p.updated_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                   OR (p.original_price IS NOT NULL AND p.original_price > p.price))
                   AND (p.archived IS NULL OR p.archived = FALSE)
                ORDER BY p.updated_at DESC, p.id DESC
                LIMIT 8
            """)

            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            products = [dict(zip(columns, row)) for row in rows]

            # If we don't have enough recent products, add some popular ones
            if len(products) < 5:
                existing_ids = [str(p['id']) for p in products]
                placeholder = ','.join(['%s'] * len(existing_ids)) if existing_ids else 'NULL'

                cur.execute(f"""
                    SELECT DISTINCT p.id, p.name, p.price, p.original_price, p.stock, c.name as category_name,
                           p.updated_at
                    FROM products p
                    LEFT JOIN categories c ON p.category_id = c.id
                    LEFT JOIN order_items oi ON p.id = oi.product_id
                    WHERE p.stock > 0
                    AND (p.archived IS NULL OR p.archived = FALSE)
                    {f'AND p.id NOT IN ({placeholder})' if existing_ids else ''}
                    GROUP BY p.id
                    ORDER BY COUNT(oi.id) DESC, p.updated_at DESC
                    LIMIT %s
                """, existing_ids + [5 - len(products)])

                additional_rows = cur.fetchall()
                additional_columns = [desc[0] for desc in cur.description]
                additional_products = [dict(zip(additional_columns, row)) for row in additional_rows]
                products.extend(additional_products)

            cur.close()

            # Remove the updated_at field from response and limit to 5 products
            for product in products:
                if 'updated_at' in product:
                    del product['updated_at']

            return jsonify({'success': True, 'products': products[:5]})
        except Exception as e:
            app.logger.error(f"Error fetching recently used products: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/staff/discounts/track-usage', methods=['POST'])
    def track_product_usage():
        """Track when a product is used for discount application"""
        if 'user_id' not in session or session.get('role') not in ['staff', 'admin', 'super_admin']:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 403

        try:
            data = request.get_json()
            product_id = data.get('product_id')
            user_id = session['user_id']

            if not product_id:
                return jsonify({'success': False, 'error': 'Product ID required'}), 400

            # For now, we'll just return success
            # In a full implementation, you'd store this in a recent_usage table
            return jsonify({'success': True, 'message': 'Usage tracked'})
        except Exception as e:
            app.logger.error(f"Error tracking product usage: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/staff/discounts/categories', methods=['GET'])
    def get_categories_for_discount():
        """Get all categories for filter buttons (excluding Accessories)"""
        if 'user_id' not in session or session.get('role') not in ['staff', 'admin', 'super_admin']:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 403

        try:
            conn = mysql.connection
            cur = conn.cursor()
            cur.execute("""
                SELECT c.id, c.name, COUNT(p.id) as product_count
                FROM categories c
                LEFT JOIN products p ON c.id = p.category_id AND (p.archived IS NULL OR p.archived = FALSE)
                WHERE c.name != 'Accessories'
                  AND c.name IS NOT NULL
                  AND TRIM(c.name) != ''
                  AND c.name NOT LIKE '%test%'
                GROUP BY c.id, c.name
                HAVING product_count > 0
                ORDER BY c.name
            """)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            categories = [dict(zip(columns, row)) for row in rows]
            cur.close()

            return jsonify({'success': True, 'categories': categories})
        except Exception as e:
            app.logger.error(f"Error fetching categories for discount: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/products/discounted', methods=['GET'])
    def get_homepage_discounted_products():
        """Get discounted products for homepage display"""
        try:
            limit = int(request.args.get('limit', 12))
            app.logger.info(f"Homepage discount request for {limit} products")

            conn = mysql.connection
            cur = conn.cursor()
            cur.execute("""
                SELECT p.id, p.name, p.description, p.price, p.original_price, p.stock, p.photo,
                       p.allow_preorder, p.expected_restock_date, c.name as category_name,
                       p.discount_percentage,
                       -- Calculate the price before discount for display purposes
                       ROUND(p.price / (1 - p.discount_percentage / 100), 2) as pre_discount_price,
                       -- Calculate savings amount
                       ROUND(p.price / (1 - p.discount_percentage / 100) - p.price, 2) as savings_amount
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.discount_percentage IS NOT NULL
                AND (p.archived IS NULL OR p.archived = FALSE)
                ORDER BY p.discount_percentage DESC
                LIMIT %s
            """, (limit,))
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            products = [dict(zip(columns, row)) for row in rows]
            
            app.logger.info(f"Homepage discount query found {len(products)} discounted products")
            if products:
                app.logger.info(f"Sample product: ID={products[0].get('id')}, Name={products[0].get('name')}, Discount={products[0].get('discount_percentage')}%")
            
            cur.close()

            # Process products to add image_url
            for product in products:
                if product.get('photo'):
                    product['image_url'] = f"/static/images/{product['photo']}"
                else:
                    product['image_url'] = "/static/images/placeholder.jpg"

            return jsonify({'success': True, 'products': products})
        except Exception as e:
            app.logger.error(f"Error fetching homepage discounted products: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/products/new-arrivals', methods=['GET'])
    def get_homepage_new_arrivals_products():
        """Get new arrivals products for homepage display"""
        try:
            limit = int(request.args.get('limit', 12))

            conn = mysql.connection
            cur = conn.cursor()
            cur.execute("""
                SELECT p.id, p.name, p.description, p.price, p.original_price, p.stock, p.photo,
                       p.allow_preorder, p.expected_restock_date, c.name as category_name,
                       CASE
                           WHEN p.original_price IS NOT NULL AND p.price < p.original_price
                           THEN ROUND(((p.original_price - p.price) / p.original_price) * 100, 0)
                           ELSE 0
                       END as discount_percentage,
                       p.created_at
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                AND (p.archived IS NULL OR p.archived = FALSE)
                ORDER BY p.created_at DESC
                LIMIT %s
            """, (limit,))
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            products = [dict(zip(columns, row)) for row in rows]
            cur.close()

            # Process products to add image_url
            for product in products:
                if product.get('photo'):
                    product['image_url'] = f"/static/images/{product['photo']}"
                else:
                    product['image_url'] = "/static/images/placeholder.jpg"

            return jsonify({'success': True, 'products': products})
        except Exception as e:
            app.logger.error(f"Error fetching homepage new arrivals products: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    # Customer Management Endpoints
    @app.route('/staff/customers')
    def list_customers():
        try:
            customers = Customer.get_all()
            return jsonify({
                'success': True,
                'customers': customers
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/staff/customers/api')
    def list_customers_paginated():
        """API endpoint for paginated customer list with search"""
        if 'user_id' not in session or session.get('role') not in ['staff', 'admin', 'super_admin']:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 403

        try:
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 10))
            search = request.args.get('search') or ''
            app.logger.info(f"Customer search request - page: {page}, per_page: {per_page}, search: '{search}' (length: {len(search)}, has_spaces: {' ' in search})")

            conn = mysql.connection
            cur = conn.cursor()
            


            # Build search query - Simple and flexible like inventory search
            if search and search.strip():
                # Clean the search query: remove extra spaces but preserve single spaces
                clean_search = ' '.join(search.split())
                app.logger.info(f"Executing search with cleaned query: '{clean_search}' (original: '{search}')")
                
                # Use simple LIKE search (case-insensitive by default in MySQL)
                # This works for both single words and phrases with spaces
                search_query = """
                    SELECT id, first_name, last_name, email, phone, address, created_at
                    FROM customers
                    WHERE (LOWER(first_name) LIKE LOWER(%s) 
                       OR LOWER(last_name) LIKE LOWER(%s) 
                       OR LOWER(email) LIKE LOWER(%s) 
                       OR LOWER(phone) LIKE LOWER(%s)
                       OR LOWER(CONCAT(first_name, ' ', last_name)) LIKE LOWER(%s))
                       AND deleted_at IS NULL
                    ORDER BY created_at DESC
                """
                search_param = f"%{clean_search}%"
                cur.execute(search_query, (search_param, search_param, search_param, search_param, search_param))
                app.logger.info(f"Executing search with parameter: '{search_param}'")
            else:
                app.logger.info("No search query, fetching all active customers")
                cur.execute("""
                    SELECT id, first_name, last_name, email, phone, address, created_at
                    FROM customers
                    WHERE deleted_at IS NULL
                    ORDER BY created_at DESC
                """)

            all_customers = cur.fetchall()
            total_customers = len(all_customers)
            app.logger.info(f"Search returned {total_customers} customers")
            
            # Log first few results for debugging
            if all_customers and total_customers > 0:
                app.logger.info(f"First customer: {all_customers[0]}")
                if total_customers > 1:
                    app.logger.info(f"Second customer: {all_customers[1]}")

            # Calculate pagination
            offset = (page - 1) * per_page
            paginated_customers = all_customers[offset:offset + per_page]

            # Convert to dict format
            columns = [desc[0] for desc in cur.description]
            customers = [dict(zip(columns, row)) for row in paginated_customers]

            cur.close()

            return jsonify({
                'success': True,
                'customers': customers,
                'total': total_customers,
                'page': page,
                'per_page': per_page,
                'total_pages': (total_customers + per_page - 1) // per_page
            })

        except Exception as e:
            app.logger.error(f"Error fetching paginated customers: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/staff/customers/<int:customer_id>')
    def get_customer(customer_id):
        try:
            customer = Customer.get_by_id(customer_id)
            if not customer:
                return jsonify({'success': False, 'error': 'Customer not found'}), 404
            return jsonify({
                'success': True,
                'customer': customer
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/staff/customers', methods=['POST'])
    def create_customer():
        if not request.json:
            return jsonify({'success': False, 'error': 'Invalid request'}), 400
            
        try:
            customer_id = Customer.create(
                first_name=request.json['first_name'],
                last_name=request.json['last_name'],
                email=request.json['email'],
                password=request.json['password'],
                phone=request.json.get('phone'),
                address=request.json.get('address')
            )
            return jsonify({
                'success': True,
                'customer_id': customer_id
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/staff/customers/<int:customer_id>', methods=['PUT'])
    def update_customer(customer_id):
        if not request.json:
            return jsonify({'success': False, 'error': 'Invalid request'}), 400
            
        try:
            success = Customer.update(customer_id, **request.json)
            return jsonify({
                'success': success
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

    @app.route('/staff/customers/<int:customer_id>', methods=['DELETE'])
    def delete_customer(customer_id):
        try:
            # Use the Customer.delete method instead of SQLAlchemy ORM
            success = Customer.delete(customer_id)
            if success:
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'error': 'Customer not found'}), 404
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            app.logger.error(f"Error deleting customer: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/staff/customers/<int:customer_id>/restore', methods=['POST'])
    def restore_customer(customer_id):
        try:
            # Use the Customer.restore method
            success = Customer.restore(customer_id)
            if success:
                return jsonify({'success': True, 'message': 'Customer restored successfully'})
            else:
                return jsonify({'success': False, 'error': 'Customer not found or already active'}), 404
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            app.logger.error(f"Error restoring customer: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/staff/customers/export', methods=['POST'])
    def export_customers():
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        try:
            data = request.get_json()
            customer_ids = data.get('customer_ids', 'all')
            
            app.logger.info(f"Export request - customer_ids: {customer_ids}")
            
            if not mysql.connection:
                app.logger.error("No database connection available")
                return jsonify({'success': False, 'error': 'Database connection not available'}), 500
            
            # Try to create cursor with dictionary support, fallback to regular cursor
            try:
                cursor = mysql.connection.cursor(dictionary=True)
                use_dict_cursor = True
            except TypeError:
                cursor = mysql.connection.cursor()
                use_dict_cursor = False
            
            if customer_ids == 'all':
                # Export all active customers
                cursor.execute("""
                    SELECT id, first_name, last_name, email, phone, address, created_at
                    FROM customers
                    WHERE deleted_at IS NULL
                    ORDER BY id
                """)
            else:
                # Export selected customers
                placeholders = ', '.join(['%s'] * len(customer_ids))
                cursor.execute(f"""
                    SELECT id, first_name, last_name, email, phone, address, created_at
                    FROM customers
                    WHERE id IN ({placeholders}) AND deleted_at IS NULL
                    ORDER BY id
                """, tuple(customer_ids))
            
            customers = cursor.fetchall()
            
            # Get column names before closing cursor (for regular cursor conversion)
            if not use_dict_cursor:
                columns = [desc[0] for desc in cursor.description]
            
            cursor.close()
            
            app.logger.info(f"Found {len(customers)} customers to export")
            
            # Convert to dictionary format if using regular cursor
            if not use_dict_cursor:
                customers = [dict(zip(columns, row)) for row in customers]
            
            if customers:
                app.logger.info(f"Sample customer data: {customers[0]}")
            
            if not customers:
                return jsonify({'success': False, 'error': 'No customers found to export'}), 404
            
            # Generate CSV content
            csv_content = []
            
            # Add header row
            csv_content.append('ID,First Name,Last Name,Email,Phone,Address,Created Date')
            
            # Add data rows
            for customer in customers:
                # Escape commas and quotes in CSV
                first_name = customer["first_name"].replace('"', '""') if customer["first_name"] else ""
                last_name = customer["last_name"].replace('"', '""') if customer["last_name"] else ""
                email = customer["email"].replace('"', '""') if customer["email"] else ""
                phone = customer.get("phone", "").replace('"', '""') if customer.get("phone") else ""
                address = customer.get("address", "").replace('"', '""') if customer.get("address") else ""
                created_date = customer["created_at"].strftime("%Y-%m-%d %H:%M:%S") if customer["created_at"] else ""
                
                row = [
                    str(customer['id']),
                    f'"{first_name}"',
                    f'"{last_name}"',
                    f'"{email}"',
                    f'"{phone}"',
                    f'"{address}"',
                    f'"{created_date}"'
                ]
                csv_content.append(','.join(row))
            
            # Return CSV as plain text
            response = make_response('\n'.join(csv_content))
            response.headers['Content-Type'] = 'text/csv; charset=utf-8'
            response.headers['Content-Disposition'] = f'attachment; filename=customers_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            
            return response
            
        except Exception as e:
            app.logger.error(f"Error exporting customers: {e}")
            app.logger.error(f"Error type: {type(e)}")
            app.logger.error(f"Error details: {str(e)}")
            import traceback
            app.logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/staff/customers/export-orders', methods=['POST'])
    def export_customer_orders():
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        try:
            data = request.get_json()
            customer_ids = data.get('customer_ids', 'all')
            export_format = data.get('format', 'csv')  # csv or pdf
            
            app.logger.info(f"Export orders request - customer_ids: {customer_ids}, format: {export_format}")
            
            if not mysql.connection:
                app.logger.error("No database connection available")
                return jsonify({'success': False, 'error': 'Database connection not available'}), 500
            
            # Try to create cursor with dictionary support, fallback to regular cursor
            try:
                cursor = mysql.connection.cursor(dictionary=True)
                use_dict_cursor = True
            except TypeError:
                cursor = mysql.connection.cursor()
                use_dict_cursor = False
            
            if customer_ids == 'all':
                # Export all active customers with their orders and products
                cursor.execute("""
                    SELECT c.id, c.first_name, c.last_name, c.email, c.phone, c.address,
                           o.id as order_id, o.order_date, o.total_amount, o.status, o.approval_status,
                           GROUP_CONCAT(p.name SEPARATOR ', ') as product_names
                    FROM customers c
                    LEFT JOIN orders o ON c.id = o.customer_id
                    LEFT JOIN order_items oi ON o.id = oi.order_id
                    LEFT JOIN products p ON oi.product_id = p.id
                    WHERE c.deleted_at IS NULL
                    GROUP BY c.id, o.id
                    ORDER BY c.id, o.order_date DESC
                """)
            else:
                # Export selected customers with their orders and products
                placeholders = ', '.join(['%s'] * len(customer_ids))
                cursor.execute(f"""
                    SELECT c.id, c.first_name, c.last_name, c.email, c.phone, c.address,
                           o.id as order_id, o.order_date, o.total_amount, o.status, o.approval_status,
                           GROUP_CONCAT(p.name SEPARATOR ', ') as product_names
                    FROM customers c
                    LEFT JOIN orders o ON c.id = o.customer_id
                    LEFT JOIN order_items oi ON o.id = oi.order_id
                    LEFT JOIN products p ON oi.product_id = p.id
                    WHERE c.id IN ({placeholders}) AND c.deleted_at IS NULL
                    GROUP BY c.id, o.id
                    ORDER BY c.id, o.order_date DESC
                """, tuple(customer_ids))
            
            rows = cursor.fetchall()
            
            # Get column names before closing cursor (for regular cursor conversion)
            if not use_dict_cursor:
                columns = [desc[0] for desc in cursor.description]
            
            cursor.close()
            
            app.logger.info(f"Found {len(rows)} order records to export")
            
            # Convert to dictionary format if using regular cursor
            if not use_dict_cursor:
                rows = [dict(zip(columns, row)) for row in rows]
            
            if not rows:
                return jsonify({'success': False, 'error': 'No orders found to export'}), 404
            
            # Group orders by customer
            customers_with_orders = {}
            for row in rows:
                customer_id = row['id']
                if customer_id not in customers_with_orders:
                    customers_with_orders[customer_id] = {
                        'customer': {
                            'id': row['id'],
                            'first_name': row['first_name'],
                            'last_name': row['last_name'],
                            'email': row['email'],
                            'phone': row['phone'],
                            'address': row['address']
                        },
                        'orders': []
                    }
                
                if row['order_id']:  # Only add if there's an order
                    customers_with_orders[customer_id]['orders'].append({
                        'order_id': row['order_id'],
                        'order_date': row['order_date'],
                        'total_amount': row['total_amount'],
                        'status': row['status'],
                        'product_names': row.get('product_names', '')
                    })
            
            # Always return CSV data, PDF will be generated client-side
            return generate_orders_csv(customers_with_orders)
            
        except Exception as e:
            app.logger.error(f"Error exporting customer orders: {e}")
            app.logger.error(f"Error type: {type(e)}")
            app.logger.error(f"Error details: {str(e)}")
            import traceback
            app.logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({'success': False, 'error': str(e)}), 500

    def generate_orders_csv(customers_with_orders):
        """Generate CSV content for customer orders"""
        csv_content = []
        
        # Add header row
        csv_content.append('Customer ID,Customer Name,Email,Phone,Address,Product Names,Order ID,Order Date,Total Amount,Status')
        
        # Add data rows
        for customer_data in customers_with_orders.values():
            customer = customer_data['customer']
            orders = customer_data['orders']
            
            if not orders:  # Customer with no orders
                row = [
                    str(customer['id']),
                    f'"{customer["first_name"]} {customer["last_name"]}"',
                    f'"{customer["email"]}"',
                    f'"{customer.get("phone", "")}"',
                    f'"{customer.get("address", "")}"',
                    'No Orders',
                    '',
                    '',
                    '',
                    ''
                ]
                csv_content.append(','.join(row))
            else:
                for order in orders:
                    row = [
                        str(customer['id']),
                        f'"{customer["first_name"]} {customer["last_name"]}"',
                        f'"{customer["email"]}"',
                        f'"{customer.get("phone", "")}"',
                        f'"{customer.get("address", "")}"',
                        f'"{order.get("product_names", "")}"',
                        str(order['order_id']),
                        f'"{order["order_date"].strftime("%Y-%m-%d %H:%M:%S")}"',
                        f'"${order["total_amount"]}"',
                        f'"{order["status"]}"'
                    ]
                    csv_content.append(','.join(row))
        
        # Return CSV as plain text
        response = make_response('\n'.join(csv_content))
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename=customer_orders_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return response

    def generate_orders_pdf(customers_with_orders):
        """Generate PDF content for customer orders"""
        try:
            # Create HTML content for PDF
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Customer Orders Export</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .header {{ text-align: center; margin-bottom: 30px; }}
                    .customer-section {{ margin-bottom: 30px; page-break-inside: avoid; }}
                    .customer-info {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 15px; }}
                    .orders-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                    .orders-table th, .orders-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    .orders-table th {{ background: #f0f0f0; }}
                    .no-orders {{ font-style: italic; color: #666; }}
                    .total-row {{ font-weight: bold; background: #e8f5e8; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>Customer Orders Report</h1>
                    <p>Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                </div>
            """
            
            for customer_data in customers_with_orders.values():
                customer = customer_data['customer']
                orders = customer_data['orders']
                
                html_content += f"""
                <div class="customer-section">
                    <div class="customer-info">
                        <h3>{customer['first_name']} {customer['last_name']}</h3>
                        <p><strong>ID:</strong> {customer['id']}</p>
                        <p><strong>Email:</strong> {customer['email']}</p>
                        <p><strong>Phone:</strong> {customer.get('phone', 'N/A')}</p>
                        <p><strong>Address:</strong> {customer.get('address', 'N/A')}</p>
                    </div>
                """
                
                if not orders:
                    html_content += '<p class="no-orders">No orders found for this customer.</p>'
                else:
                    html_content += """
                    <table class="orders-table">
                        <thead>
                            <tr>
                                <th>Order ID</th>
                                <th>Order Date</th>
                                <th>Total Amount</th>
                                <th>Status</th>
                                <th>Approval Status</th>
                            </tr>
                        </thead>
                        <tbody>
                    """
                    
                    total_amount = 0
                    for order in orders:
                        amount = float(order['total_amount']) if order['total_amount'] else 0
                        total_amount += amount
                        html_content += f"""
                            <tr>
                                <td>{order['order_id']}</td>
                                <td>{order['order_date'].strftime("%Y-%m-%d %H:%M:%S")}</td>
                                <td>${amount:.2f}</td>
                                <td>{order['status']}</td>
                                <td>{order['approval_status']}</td>
                            </tr>
                        """
                    
                    html_content += f"""
                            <tr class="total-row">
                                <td colspan="2"><strong>Total Orders:</strong> {len(orders)}</td>
                                <td colspan="3"><strong>Total Amount:</strong> ${total_amount:.2f}</td>
                            </tr>
                        </tbody>
                    </table>
                    """
                
                html_content += "</div>"
            
            html_content += """
            </body>
            </html>
            """
            
            # Generate PDF using pdfkit
            try:
                pdf = pdfkit.from_string(html_content, False)
                response = make_response(pdf)
                response.headers['Content-Type'] = 'application/pdf'
                response.headers['Content-Disposition'] = f'attachment; filename=customer_orders_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
                return response
            except Exception as pdf_error:
                app.logger.error(f"PDF generation error: {pdf_error}")
                # Fallback to CSV if PDF fails
                return generate_orders_csv(customers_with_orders)
                
        except Exception as e:
            app.logger.error(f"Error generating PDF: {e}")
            # Fallback to CSV if HTML generation fails
            return generate_orders_csv(customers_with_orders)

    @app.route('/staff/customers/deleted', methods=['GET'])
    def get_deleted_customers():
        try:
            conn = mysql.connection
            # Try to create cursor with dictionary support, fallback to regular cursor
            try:
                cur = conn.cursor(dictionary=True)
                use_dict_cursor = True
            except TypeError:
                cur = conn.cursor()
                use_dict_cursor = False
            
            try:
                cur.execute("""
                    SELECT id, first_name, last_name, email, phone, address, created_at, deleted_at
                    FROM customers
                    WHERE deleted_at IS NOT NULL
                    ORDER BY deleted_at DESC
                """)
                rows = cur.fetchall()
                
                if use_dict_cursor:
                    customers = rows
                else:
                    # Convert to dictionary format manually
                    columns = [desc[0] for desc in cur.description]
                    customers = [dict(zip(columns, row)) for row in rows]
                
                cur.close()
                return jsonify({'success': True, 'customers': customers})
            except Exception as e:
                cur.close()
                app.logger.error(f"Error executing query: {e}")
                return jsonify({'success': False, 'error': 'Database error'}), 500
        except Exception as e:
            app.logger.error(f"Error fetching deleted customers: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/staff/categories/<int:category_id>/products/count')
    def get_category_product_count(category_id):
        try:
            # Get database connection
            cur = mysql.connection.cursor()
            
            # Query to count products in the category
            cur.execute("""
                SELECT COUNT(*) 
                FROM products 
                WHERE category_id = %s AND archived = FALSE
            """, (category_id,))
            
            count = cur.fetchone()[0]
            cur.close()
            
            return jsonify({
                'success': True,
                'count': count
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/staff/categories/<int:category_id>/products')
    def get_category_products(category_id):
        try:
            conn = mysql.connection
            cur = conn.cursor()
            try:
                cur.execute("""
                    SELECT id, name, description, price, stock as stock_quantity, photo,
                           allow_preorder, expected_restock_date
                    FROM products
                    WHERE category_id = %s AND archived = FALSE
                """, (category_id,))
                rows = cur.fetchall()
                columns = [desc[0] for desc in cur.description]
                products = [dict(zip(columns, row)) for row in rows]
                cur.close()
                return jsonify({'success': True, 'products': products})
            except Exception as e:
                cur.close()
                app.logger.error(f"Error executing query: {e}")
                return jsonify({'success': False, 'error': 'Database error'}), 500
        except Exception as e:
            app.logger.error(f"Error fetching products for category {category_id}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/staff/customers/<int:customer_id>/orders')
    def get_customer_orders(customer_id):
        status = request.args.get('status')
        try:
            orders = Customer.get_orders(customer_id, status=status)
            return jsonify({
                'success': True,
                'orders': orders
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/staff/customers/<int:customer_id>/orders/completed_count')
    def get_completed_order_count(customer_id):
        try:
            conn = mysql.connection
            cur = conn.cursor()
            cur.execute("""
                SELECT COUNT(*) FROM orders
                WHERE customer_id = %s AND LOWER(status) = 'completed'
            """, (customer_id,))
            result = cur.fetchone()
            cur.close()
            count = result[0] if result else 0
            return jsonify({'success': True, 'completed_count': count})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/staff/customers/<int:customer_id>/orders/view')
    def view_customer_orders(customer_id):
        status = request.args.get('status')
        try:
            # Get regular orders
            orders = Customer.get_orders(customer_id, status=status)

            # Get completed pre-orders
            from models import PreOrder
            completed_preorders = PreOrder.get_by_customer(customer_id, status='completed')

            # Convert pre-orders to order-like format for display
            preorder_items = []
            if completed_preorders:
                for preorder in completed_preorders:
                    preorder_item = {
                        'id': f"P{preorder['id']}",  # Prefix with P to distinguish
                        'order_date': preorder.get('created_date', ''),
                        'status': 'Completed',
                        'total_amount': preorder['expected_price'] * preorder['quantity'],
                        'type': 'preorder',
                        'items': [{
                            'product_name': preorder['product_name'],
                            'quantity': preorder['quantity'],
                            'price': preorder['expected_price']
                        }]
                    }
                    preorder_items.append(preorder_item)

            # Add items field to regular orders if not present
            for order in orders:
                if 'items' not in order:
                    order['items'] = []
                order['type'] = 'order'

            # Combine orders and pre-orders
            all_orders = orders + preorder_items

            # Sort by date (most recent first)
            all_orders.sort(key=lambda x: x.get('order_date', ''), reverse=True)

            app.logger.info(f"Combined orders for customer {customer_id}: {len(orders)} regular orders + {len(preorder_items)} completed pre-orders")
            return render_template('customer_orders.html', orders=all_orders)
        except Exception as e:
            app.logger.error(f"Error fetching customer orders: {e}")
            return render_template('customer_orders.html', orders=[])

    @app.route('/auth/staff/reports')
    def staff_reports_page():
        try:
            # Fetch order summary data
            order_summary = Order.get_status_summary()
            # Fetch other report data if needed
            # For now, just pass order summary
            return render_template('staff_reports.html', order_summary=order_summary)
        except Exception as e:
            app.logger.error(f"Error rendering reports page: {e}")
            return render_template('error.html', error='Failed to load reports'), 500
    
    # Serve static files explicitly
    @app.route('/static/<path:filename>')
    def static_files(filename):
        return app.send_static_file(filename)
    
    # Register auth blueprint
    with app.app_context():
        from auth import auth_bp
        app.register_blueprint(auth_bp, url_prefix='/auth')
        
        # Register QR payment API routes
        from api_payment_endpoints import add_payment_api_routes
        add_payment_api_routes(app)
        
        # Automatic payment verification enabled - real-time detection
        app.logger.info("✅ Automatic payment verification mode - payments will be detected automatically")

    # API for Sales Trends
    @app.route('/auth/staff/api/reports/sales_trends')
    def api_sales_trends():
        try:
            # Default to the last 30 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            sales_data = Report.get_sales(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            
            # Format date for chart
            for sale in sales_data:
                sale['date'] = sale['date'].strftime('%Y-%m-%d')
                sale['daily_sales'] = float(sale['daily_sales'])
            
            app.logger.info(f"Sales trends data being sent: {sales_data}")
            return jsonify({'success': True, 'trends': sales_data})
        except Exception as e:
            app.logger.error(f"Error fetching sales trends: {e}")
            return jsonify({'success': False, 'error': 'Failed to fetch sales trends: ' + str(e)}), 500

    # API for Top Selling Products
    @app.route('/auth/staff/api/reports/top_products')
    def api_top_products():
        try:
            top_products = Report.get_top_products(limit=5)
            app.logger.info(f"Top products data being sent: {top_products}")
            return jsonify({'success': True, 'products': top_products})
        except Exception as e:
            app.logger.error(f"Error fetching top products: {e}")
            return jsonify({'success': False, 'error': 'Failed to fetch top products: ' + str(e)}), 500

    # API for Revenue by Category
    @app.route('/auth/staff/api/reports/revenue_by_category')
    def api_revenue_by_category():
        try:
            revenue_data = Report.get_revenue_by_category()
            app.logger.info(f"Revenue by category data being sent: {revenue_data}")
            return jsonify({'success': True, 'categories': revenue_data})
        except Exception as e:
            app.logger.error(f"Error fetching revenue by category: {e}")
            return jsonify({'success': False, 'error': 'Failed to fetch revenue by category: ' + str(e)}), 500

    # API for Top Selling Products by Category (with quantity and revenue)
    @app.route('/auth/staff/api/reports/top_selling_products_by_category')
    def api_top_selling_products_by_category():
        try:
            cur = mysql.connection.cursor()
            cur.execute("""
                SELECT
                    c.name as category_name,
                    SUM(oi.quantity) as total_products_sold,
                    SUM(oi.quantity * oi.price) as total_revenue
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                JOIN categories c ON p.category_id = c.id
                JOIN orders o ON oi.order_id = o.id
                WHERE LOWER(o.status) IN ('completed', 'processing')
                AND (p.archived IS NULL OR p.archived = FALSE)
                GROUP BY c.id, c.name
                ORDER BY total_revenue DESC
            """)

            results = cur.fetchall()
            cur.close()

            # Format the results
            category_data = []
            for row in results:
                category_name = row[0]
                total_products_sold = int(row[1]) if row[1] is not None else 0
                total_revenue = float(row[2]) if row[2] is not None else 0.0

                category_data.append({
                    'category_name': category_name,
                    'total_products_sold': total_products_sold,
                    'total_revenue': total_revenue
                })

            app.logger.info(f"Top selling products by category data being sent: {category_data}")
            return jsonify({'success': True, 'categories': category_data})

        except Exception as e:
            app.logger.error(f"Error fetching top selling products by category: {e}")
            return jsonify({'success': False, 'error': 'Failed to fetch top selling products by category: ' + str(e)}), 500

    # API for Top Selling Products in a Specific Category
    @app.route('/auth/staff/api/reports/category_products_detail')
    def api_category_products_detail():
        category_name = request.args.get('category_name')
        if not category_name:
            return jsonify({'success': False, 'error': 'Category name parameter is required'}), 400

        try:
            cur = mysql.connection.cursor()
            cur.execute("""
                SELECT
                    p.name as product_name,
                    SUM(oi.quantity) as total_quantity_sold,
                    SUM(oi.quantity * oi.price) as total_revenue,
                    AVG(oi.price) as average_price
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                JOIN categories c ON p.category_id = c.id
                JOIN orders o ON oi.order_id = o.id
                WHERE c.name = %s
                AND LOWER(o.status) IN ('completed', 'processing')
                AND (p.archived IS NULL OR p.archived = FALSE)
                GROUP BY p.id, p.name
                ORDER BY total_quantity_sold DESC
                LIMIT 10
            """, (category_name,))

            results = cur.fetchall()
            cur.close()

            # Format the results
            products_data = []
            for row in results:
                product_name = row[0]
                total_quantity_sold = int(row[1]) if row[1] is not None else 0
                total_revenue = float(row[2]) if row[2] is not None else 0.0
                average_price = float(row[3]) if row[3] is not None else 0.0

                products_data.append({
                    'product_name': product_name,
                    'total_quantity_sold': total_quantity_sold,
                    'total_revenue': total_revenue,
                    'average_price': average_price
                })

            app.logger.info(f"Category products detail for {category_name} being sent: {products_data}")
            return jsonify({'success': True, 'products': products_data, 'category_name': category_name})

        except Exception as e:
            app.logger.error(f"Error fetching category products detail for {category_name}: {e}")
            return jsonify({'success': False, 'error': 'Failed to fetch category products detail: ' + str(e)}), 500

    # API for Product Purchase History Detail
    @app.route('/auth/staff/api/reports/product_purchase_history')
    def api_product_purchase_history():
        product_name = request.args.get('product_name')
        if not product_name:
            return jsonify({'success': False, 'error': 'Product name parameter is required'}), 400

        try:
            cur = mysql.connection.cursor()

            # Get overall product statistics
            cur.execute("""
                SELECT
                    p.name as product_name,
                    p.price as current_price,
                    SUM(oi.quantity) as total_quantity_sold,
                    COUNT(DISTINCT o.id) as total_orders,
                    SUM(oi.quantity * oi.price) as total_revenue,
                    AVG(oi.price) as average_selling_price,
                    MIN(o.order_date) as first_purchase_date,
                    MAX(o.order_date) as last_purchase_date
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                JOIN orders o ON oi.order_id = o.id
                WHERE p.name = %s
                AND LOWER(o.status) IN ('completed', 'processing')
                AND (p.archived IS NULL OR p.archived = FALSE)
                GROUP BY p.id, p.name, p.price
            """, (product_name,))

            product_stats = cur.fetchone()

            if not product_stats:
                return jsonify({'success': False, 'error': 'Product not found or no sales data available'}), 404

            # Get detailed purchase history
            cur.execute("""
                SELECT
                    o.id as order_id,
                    o.order_date,
                    CONCAT(c.first_name, ' ', c.last_name) as customer_name,
                    oi.quantity,
                    oi.price as unit_price,
                    (oi.quantity * oi.price) as total_amount,
                    o.status
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                JOIN orders o ON oi.order_id = o.id
                JOIN customers c ON o.customer_id = c.id
                WHERE p.name = %s
                AND LOWER(o.status) IN ('completed', 'processing')
                AND (p.archived IS NULL OR p.archived = FALSE)
                ORDER BY o.order_date DESC
                LIMIT 20
            """, (product_name,))

            purchase_history = cur.fetchall()
            cur.close()

            # Format product statistics
            stats = {
                'product_name': product_stats[0],
                'current_price': float(product_stats[1]) if product_stats[1] is not None else 0.0,
                'total_quantity_sold': int(product_stats[2]) if product_stats[2] is not None else 0,
                'total_orders': int(product_stats[3]) if product_stats[3] is not None else 0,
                'total_revenue': float(product_stats[4]) if product_stats[4] is not None else 0.0,
                'average_selling_price': float(product_stats[5]) if product_stats[5] is not None else 0.0,
                'first_purchase_date': product_stats[6].strftime('%Y-%m-%d %H:%M:%S') if product_stats[6] else None,
                'last_purchase_date': product_stats[7].strftime('%Y-%m-%d %H:%M:%S') if product_stats[7] else None
            }

            # Format purchase history
            history = []
            for row in purchase_history:
                history.append({
                    'order_id': row[0],
                    'order_date': row[1].strftime('%Y-%m-%d %H:%M:%S') if row[1] else None,
                    'customer_name': row[2],
                    'quantity': int(row[3]) if row[3] is not None else 0,
                    'unit_price': float(row[4]) if row[4] is not None else 0.0,
                    'total_amount': float(row[5]) if row[5] is not None else 0.0,
                    'status': row[6]
                })

            app.logger.info(f"Product purchase history for {product_name} being sent: {len(history)} records")
            return jsonify({
                'success': True,
                'product_stats': stats,
                'purchase_history': history
            })

        except Exception as e:
            app.logger.error(f"Error fetching product purchase history for {product_name}: {e}")
            return jsonify({'success': False, 'error': 'Failed to fetch product purchase history: ' + str(e)}), 500

    # API for Product Orders with Profit
    @app.route('/auth/staff/api/reports/product_orders')
    def api_product_orders():
        product_name = request.args.get('product_name')
        if not product_name:
            return jsonify({'success': False, 'error': 'Product name parameter is required'}), 400

        try:
            cur = mysql.connection.cursor()

            # Get product orders with customer details and profit calculation
            cur.execute("""
                SELECT
                    o.id as order_id,
                    o.order_date,
                    CONCAT(c.first_name, ' ', c.last_name) as customer_name,
                    oi.quantity,
                    oi.price as unit_price,
                    (oi.quantity * oi.price) as total_amount,
                    o.status,
                    ROUND((oi.quantity * oi.price) * 0.15, 2) as estimated_profit
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                JOIN orders o ON oi.order_id = o.id
                JOIN customers c ON o.customer_id = c.id
                WHERE p.name = %s
                AND LOWER(o.status) IN ('completed', 'processing')
                AND (p.archived IS NULL OR p.archived = FALSE)
                ORDER BY o.order_date DESC
            """, (product_name,))

            orders = cur.fetchall()
            cur.close()

            # Format orders with profit
            formatted_orders = []
            for row in orders:
                formatted_orders.append({
                    'order_id': row[0],
                    'order_date': row[1].strftime('%Y-%m-%d %H:%M:%S') if row[1] else None,
                    'customer_name': row[2],
                    'quantity': int(row[3]) if row[3] is not None else 0,
                    'unit_price': float(row[4]) if row[4] is not None else 0.0,
                    'total_amount': float(row[5]) if row[5] is not None else 0.0,
                    'status': row[6],
                    'estimated_profit': float(row[7]) if row[7] is not None else 0.0
                })

            app.logger.info(f"Product orders for {product_name} being sent: {len(formatted_orders)} records")
            return jsonify({'success': True, 'orders': formatted_orders})

        except Exception as e:
            app.logger.error(f"Error fetching product orders for {product_name}: {e}")
            return jsonify({'success': False, 'error': 'Failed to fetch product orders: ' + str(e)}), 500

    # API for Monthly Sales
    @app.route('/auth/staff/api/reports/monthly_sales')
    def api_monthly_sales():
        try:
            # Accept optional start_date and end_date query parameters
            start_date_str = request.args.get('start_date')
            end_date_str = request.args.get('end_date')
            if start_date_str and end_date_str:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999)
            else:
                # Default to last 12 months
                end_date = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
                start_date = end_date - timedelta(days=365)
            monthly_sales_data = Report.get_monthly_sales(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))

            # Calculate totals for debugging
            total_sales = sum(item['total_sales'] for item in monthly_sales_data)
            total_profit = sum(item['total_profit'] for item in monthly_sales_data)
            app.logger.info(f"Dashboard widget totals - Total Sales: ${total_sales:.2f}, Total Profit: ${total_profit:.2f}")
            app.logger.info(f"Monthly sales data being sent: {monthly_sales_data}")
            return jsonify({'success': True, 'sales': monthly_sales_data})
        except Exception as e:
            app.logger.error(f"Error fetching monthly sales: {e}")
            return jsonify({'success': False, 'error': 'Failed to fetch monthly sales: ' + str(e)}), 500

    # API for Detailed Sales by Month
    @app.route('/auth/staff/api/reports/monthly_sales_detail')
    def api_monthly_sales_detail():
        month = request.args.get('month')
        status = request.args.get('status')  # Add status parameter support
        if not month:
            return jsonify({'success': False, 'error': 'Month parameter is required'}), 400
        try:
            # Assuming Report.get_monthly_sales_detail returns list of sales details for the month
            sales_detail = Report.get_monthly_sales_detail(month)
            app.logger.info(f"Monthly sales detail for {month} with status {status} being sent: {len(sales_detail)} records")

            # Calculate totals for debugging
            total_grand_total = sum(sale['grand_total'] for sale in sales_detail)
            total_profit = sum(sale['total_profit'] for sale in sales_detail)
            app.logger.info(f"Modal totals - Grand Total: ${total_grand_total:.2f}, Total Profit: ${total_profit:.2f}")

            return jsonify({'success': True, 'sales_detail': sales_detail})
        except Exception as e:
            app.logger.error(f"Error fetching monthly sales detail for {month}: {e}")
            return jsonify({'success': False, 'error': 'Failed to fetch monthly sales detail: ' + str(e)}), 500

    # API for KPIs
    @app.route('/auth/staff/api/kpis')
    def api_kpis():
        try:
            total_revenue = Report.get_total_revenue_this_month()
            new_customers = Customer.get_new_customers_this_month()
            average_order_value = Report.get_average_order_value_this_month()
            order_summary = Order.get_status_summary()
            
            return jsonify({
                'success': True,
                'total_revenue': total_revenue,
                'new_customers': new_customers,
                'average_order_value': average_order_value,
                'order_summary': order_summary
            })
        except Exception as e:
            app.logger.error(f"Error fetching KPIs: {e}")
            return jsonify({'success': False, 'error': 'Failed to fetch KPIs: ' + str(e)}), 500
            
    @app.route('/api/staff/orders')
    def api_get_orders_by_status():
        status = request.args.get('status', '').lower()
        if not status:
            return jsonify({'success': False, 'error': 'Status parameter is required'}), 400
        try:
            # Assuming Order model has a method to get orders by status
            orders = Order.get_by_status(status)
            # Format orders for JSON response
            orders_list = []
            for order in orders:
                order_date = order['order_date'] if 'order_date' in order else ''
                if hasattr(order_date, 'strftime'):
                    order_date = order_date.strftime('%Y-%m-%d')
                orders_list.append({
                    'id': order['id'],
                    'customer_name': f"{order['first_name']} {order['last_name']}" if 'first_name' in order and 'last_name' in order else '',
                    'date': order_date,
                    'status': order['status'] if 'status' in order else '',
                    'total': float(order['total']) if 'total' in order else 0.0
                })
            return jsonify({'success': True, 'orders': orders_list})
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            app.logger.error(f"Error fetching orders by status {status}: {e}\n{tb}")
            return jsonify({'success': False, 'error': 'Failed to fetch orders'}), 500

    @app.route('/api/colors')
    def api_colors():
        try:
            conn = mysql.connection
            cur = conn.cursor()
            cur.execute("SELECT id, name FROM colors ORDER BY name ASC")
            rows = cur.fetchall()
            cur.close()
            colors = [{'id': row[0], 'name': row[1]} for row in rows]
            return jsonify({'success': True, 'colors': colors})
        except Exception as e:
            app.logger.error(f"Error fetching colors: {e}")
            return jsonify({'success': False, 'error': 'Failed to fetch colors'}), 500


    @app.route('/api/staff/product_brand_counts')
    def api_product_brand_counts():
        try:
            conn = mysql.connection
            cur = conn.cursor()
            cur.execute("""
                SELECT SUBSTRING_INDEX(TRIM(name), ' ', 1) as brand, COUNT(*) as count
                FROM products
                WHERE name IS NOT NULL
                AND TRIM(name) != ''
                AND SUBSTRING_INDEX(TRIM(name), ' ', 1) != ''
                AND (archived IS NULL OR archived = FALSE)
                GROUP BY brand
                ORDER BY count DESC
            """)
            rows = cur.fetchall()
            cur.close()

            # Define brand mappings - merge sub-brands with parent brands
            brand_mappings = {
                'ProBook': 'HP',    # HP ProBook → HP
                'MK': 'HP',         # HP MK → HP  
                'Modern': 'MSI'     # MSI Modern → MSI
            }

            # Aggregate counts by merging sub-brands
            brand_counts = {}
            for row in rows:
                brand, count = row
                # Map sub-brand to parent brand or keep original
                parent_brand = brand_mappings.get(brand, brand)
                
                if parent_brand in brand_counts:
                    brand_counts[parent_brand] += count
                else:
                    brand_counts[parent_brand] = count

            # Convert to result format and sort by count
            result = []
            for brand, count in brand_counts.items():
                result.append({'brand': brand, 'count': count})
            
            # Sort by count in descending order
            result.sort(key=lambda x: x['count'], reverse=True)

            return jsonify({'success': True, 'data': result})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/staff/product_names_with_brand_counts')
    def api_product_names_with_brand_counts():
        try:
            conn = mysql.connection
            cur = conn.cursor()
            # Get counts of products grouped by brand (first word of name)
            cur.execute("""
                SELECT SUBSTRING_INDEX(TRIM(name), ' ', 1) as brand, COUNT(*) as brand_count
                FROM products
                WHERE name IS NOT NULL
                AND TRIM(name) != ''
                AND SUBSTRING_INDEX(TRIM(name), ' ', 1) != ''
                AND (archived IS NULL OR archived = FALSE)
                GROUP BY brand
            """)
            brand_counts = cur.fetchall()
            brand_count_map = {row[0]: row[1] for row in brand_counts}

            # Get all product names (excluding empty/null names)
            cur.execute("""
                SELECT name FROM products
                WHERE name IS NOT NULL AND TRIM(name) != ''
                AND (archived IS NULL OR archived = FALSE)
            """)
            products = cur.fetchall()
            cur.close()

            result = []
            for row in products:
                product_name = row[0]
                brand = product_name.strip().split(' ')[0] if product_name and product_name.strip() else ''
                if brand:  # Only include products with valid brands
                    count = brand_count_map.get(brand, 0)
                    result.append({'name': product_name, 'count': count})

            return jsonify({'success': True, 'data': result})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/search_suggestions')
    def search_suggestions():
        query = (request.args.get('q') or '').strip()
        if not query:
            return jsonify({'success': True, 'suggestions': []})
        try:
            cur = mysql.connection.cursor()
            like_query = f"%{query}%"
            cur.execute("""
                SELECT id, name FROM products
                WHERE name LIKE %s
                AND (archived IS NULL OR archived = FALSE)
                ORDER BY name ASC
                LIMIT 10
            """, (like_query,))
            results = cur.fetchall()
            cur.close()
            suggestions = [{'id': row[0], 'name': row[1]} for row in results]
            return jsonify({'success': True, 'suggestions': suggestions})
        except Exception as e:
            app.logger.error(f"Error fetching search suggestions: {e}")
            return jsonify({'success': False, 'suggestions': [], 'error': str(e)}), 500

    # API for Monthly Revenue (Jan to June breakdown)
    @app.route('/auth/staff/api/reports/monthly_revenue')
    def api_monthly_revenue():
        try:
            from datetime import datetime

            # Get year from query parameter, default to 2025
            year_param = request.args.get('year', '2025')
            try:
                current_year = int(year_param)
            except ValueError:
                current_year = 2025
            
            # For years other than 2025, we'll need to check if data exists
            # For now, we'll use 2025 data as fallback for other years
            if current_year != 2025:
                # Check if we have data for the requested year
                conn = get_db()
                cur = conn.cursor()
                cur.execute("""
                    SELECT COUNT(*) FROM orders 
                    WHERE YEAR(order_date) = %s AND LOWER(status) = 'completed'
                """, (current_year,))
                count = cur.fetchone()[0]
                cur.close()
                
                if count == 0:
                    # No data for this year, use 2025 data as fallback
                    current_year = 2025
            
            start_date = f"{current_year}-01-01"
            end_date = f"{current_year}-12-31"

            cur = mysql.connection.cursor()
            cur.execute("""
                SELECT
                    DATE_FORMAT(o.order_date, '%%Y-%%m') as month,
                    COUNT(DISTINCT o.id) as orders_count,
                    SUM(oi.quantity * oi.price) as monthly_revenue
                FROM orders o
                JOIN order_items oi ON o.id = oi.order_id
                JOIN products p ON oi.product_id = p.id
                WHERE o.order_date BETWEEN %s AND %s
                AND LOWER(o.status) = 'completed'
                AND (p.archived IS NULL OR p.archived = FALSE)
                GROUP BY DATE_FORMAT(o.order_date, '%%Y-%%m')
                ORDER BY month ASC
            """, (start_date, end_date))

            results = cur.fetchall()
            cur.close()

            # Create a complete list of months from Jan to December
            months = [
                {'month': f'{current_year}-01', 'month_label': 'January', 'orders_count': 0, 'monthly_revenue': 0.0},
                {'month': f'{current_year}-02', 'month_label': 'February', 'orders_count': 0, 'monthly_revenue': 0.0},
                {'month': f'{current_year}-03', 'month_label': 'March', 'orders_count': 0, 'monthly_revenue': 0.0},
                {'month': f'{current_year}-04', 'month_label': 'April', 'orders_count': 0, 'monthly_revenue': 0.0},
                {'month': f'{current_year}-05', 'month_label': 'May', 'orders_count': 0, 'monthly_revenue': 0.0},
                {'month': f'{current_year}-06', 'month_label': 'June', 'orders_count': 0, 'monthly_revenue': 0.0},
                {'month': f'{current_year}-07', 'month_label': 'July', 'orders_count': 0, 'monthly_revenue': 0.0},
                {'month': f'{current_year}-08', 'month_label': 'August', 'orders_count': 0, 'monthly_revenue': 0.0},
                {'month': f'{current_year}-09', 'month_label': 'September', 'orders_count': 0, 'monthly_revenue': 0.0},
                {'month': f'{current_year}-10', 'month_label': 'October', 'orders_count': 0, 'monthly_revenue': 0.0},
                {'month': f'{current_year}-11', 'month_label': 'November', 'orders_count': 0, 'monthly_revenue': 0.0},
                {'month': f'{current_year}-12', 'month_label': 'December', 'orders_count': 0, 'monthly_revenue': 0.0}
            ]

            # Fill in actual revenue and order count data
            for row in results:
                month_key = row[0]
                orders_count = int(row[1]) if row[1] is not None else 0
                revenue = float(row[2]) if row[2] is not None else 0.0
                for month_data in months:
                    if month_data['month'] == month_key:
                        month_data['orders_count'] = orders_count
                        month_data['monthly_revenue'] = revenue
                        break

            app.logger.info(f"Monthly revenue data being sent: {months}")
            return jsonify({'success': True, 'revenue': months})
        except Exception as e:
            app.logger.error(f"Error fetching monthly revenue: {e}")
            return jsonify({'success': False, 'error': 'Failed to fetch monthly revenue: ' + str(e)}), 500

    # API for Current Month Daily Revenue
    @app.route('/auth/staff/api/reports/current_month_revenue')
    def api_current_month_revenue():
        try:
            from datetime import datetime, date
            import calendar

            # Get current month's first and last day
            today = date.today()
            first_day = today.replace(day=1)
            last_day_num = calendar.monthrange(today.year, today.month)[1]
            last_day = today.replace(day=last_day_num)

            cur = mysql.connection.cursor()
            cur.execute("""
                SELECT
                    DATE(o.order_date) as order_date,
                    COUNT(DISTINCT o.id) as orders_count,
                    SUM(oi.quantity * oi.price) as daily_revenue
                FROM orders o
                JOIN order_items oi ON o.id = oi.order_id
                JOIN products p ON oi.product_id = p.id
                WHERE DATE(o.order_date) BETWEEN %s AND %s
                AND LOWER(o.status) = 'completed'
                AND (p.archived IS NULL OR p.archived = FALSE)
                GROUP BY DATE(o.order_date)
                ORDER BY order_date ASC
            """, (first_day, last_day))

            results = cur.fetchall()
            cur.close()

            # Format the results
            revenue_data = []
            for row in results:
                order_date = row[0]
                orders_count = row[1]
                daily_revenue = float(row[2]) if row[2] is not None else 0.0

                revenue_data.append({
                    'date': order_date.strftime('%Y-%m-%d'),
                    'date_formatted': order_date.strftime('%B %d, %Y'),
                    'orders_count': orders_count,
                    'daily_revenue': daily_revenue
                })

            app.logger.info(f"Current month revenue data being sent: {revenue_data}")
            return jsonify({'success': True, 'revenue': revenue_data})

        except Exception as e:
            app.logger.error(f"Error fetching current month revenue: {e}")
            return jsonify({'success': False, 'error': 'Failed to fetch current month revenue: ' + str(e)}), 500

    # API for Daily Sales Detail
    @app.route('/auth/staff/api/reports/daily_sales_detail')
    def api_daily_sales_detail():
        date_param = request.args.get('date')

        try:
            from datetime import datetime

            # Handle "today" parameter or parse the date
            if date_param == 'today':
                # Use database's current date to avoid timezone issues
                cur = mysql.connection.cursor()
                cur.execute("SELECT CURDATE() as today_date")
                result = cur.fetchone()
                target_date = result[0] if result else datetime.now().date()
            else:
                if not date_param:
                    return jsonify({'success': False, 'error': 'Date parameter is required'}), 400
            target_date = datetime.strptime(date_param, '%Y-%m-%d').date()

            cur = mysql.connection.cursor()
            cur.execute("""
                SELECT
                    o.id as order_id,
                    o.order_date,
                    CONCAT(c.first_name, ' ', c.last_name) as customer_name,
                    o.total_amount,
                    o.status,
                    o.approval_status,
                    COALESCE(GROUP_CONCAT(p.name SEPARATOR ', '), 'No products') as products,
                    COALESCE(SUM(oi.quantity * (oi.price - p.original_price)), 0) as total_profit
                FROM orders o
                JOIN customers c ON o.customer_id = c.id
                JOIN order_items oi ON o.id = oi.order_id
                JOIN products p ON oi.product_id = p.id
                WHERE DATE(o.order_date) = %s
                AND (LOWER(o.status) = 'completed' OR o.approval_status = 'APPROVED')
                GROUP BY o.id, o.order_date, c.first_name, c.last_name, o.total_amount, o.status, o.approval_status
                ORDER BY o.order_date DESC
            """, (target_date,))

            results = cur.fetchall()
            cur.close()

            # Format the results
            sales_detail = []
            for row in results:
                app.logger.info(f"Raw row data: {row}")
                formatted_row = {
                    'order_id': row[0],
                    'order_date': row[1].strftime('%Y-%m-%d'),
                    'customer_name': row[2],
                    'grand_total': float(row[3]) if row[3] is not None else 0.0,
                    'status': row[4],
                    'approval_status': row[5] if row[5] else None,
                    'products': row[6] if row[6] else 'No products',
                    'total_profit': float(row[7]) if row[7] is not None else 0.0
                }
                app.logger.info(f"Formatted row: {formatted_row}")
                sales_detail.append(formatted_row)

            app.logger.info(f"Daily sales detail for {target_date}: {len(sales_detail)} orders")
            return jsonify({
                'success': True, 
                'sales_detail': sales_detail,
                'date': target_date.strftime('%Y-%m-%d')
            })

        except ValueError as e:
            app.logger.error(f"Invalid date format: {e}")
            return jsonify({'success': False, 'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        except Exception as e:
            app.logger.error(f"Error fetching daily sales detail: {e}")
            return jsonify({'success': False, 'error': 'Failed to fetch daily sales detail: ' + str(e)}), 500

    # API for Monthly Sales Detail (Simplified version)
    @app.route('/auth/staff/api/reports/monthly_sales_detail_simple')
    def api_monthly_sales_detail_simple():
        month_param = request.args.get('month')  # Format: "2025-08"
        if not month_param:
            return jsonify({'success': False, 'error': 'Month parameter is required (format: YYYY-MM)'}), 400

        try:
            from datetime import datetime
            import calendar

            # Parse the month parameter
            year, month = map(int, month_param.split('-'))
            
            # Calculate start and end dates for the month
            start_date = f"{year}-{month:02d}-01"
            last_day = calendar.monthrange(year, month)[1]
            end_date = f"{year}-{month:02d}-{last_day:02d}"

            app.logger.info(f"Monthly sales detail for {month_param}: {start_date} to {end_date}")

            cur = mysql.connection.cursor()
            cur.execute("""
                SELECT
                    o.id as order_id,
                    o.order_date,
                    CONCAT(c.first_name, ' ', c.last_name) as customer_name,
                    o.total_amount,
                    o.status,
                    GROUP_CONCAT(p.name SEPARATOR ', ') as products
                FROM orders o
                JOIN customers c ON o.customer_id = c.id
                JOIN order_items oi ON o.id = oi.order_id
                JOIN products p ON oi.product_id = p.id
                WHERE DATE(o.order_date) BETWEEN %s AND %s
                AND LOWER(o.status) = 'completed'
                GROUP BY o.id, o.order_date, c.first_name, c.last_name, o.total_amount, o.status
                ORDER BY o.order_date DESC
            """, (start_date, end_date))

            results = cur.fetchall()
            cur.close()

            # Format the results
            sales_detail = []
            for row in results:
                sales_detail.append({
                    'order_id': row[0],
                    'order_date': row[1].strftime('%Y-%m-%d %H:%M:%S'),
                    'customer_name': row[2],
                    'grand_total': float(row[3]) if row[3] is not None else 0.0,
                    'status': row[4],
                    'products': row[5] if row[5] else 'No products'
                })

            app.logger.info(f"Monthly sales detail for {month_param}: {len(sales_detail)} orders")
            return jsonify({'success': True, 'sales_detail': sales_detail})

        except ValueError as e:
            app.logger.error(f"Invalid month format: {e}")
            return jsonify({'success': False, 'error': 'Invalid month format. Use YYYY-MM'}), 400
        except Exception as e:
            app.logger.error(f"Error fetching monthly sales detail: {e}")
            return jsonify({'success': False, 'error': 'Failed to fetch monthly sales detail: ' + str(e)}), 500

    # API for Daily Orders
    @app.route('/auth/staff/api/reports/orders_data')
    def api_orders_data():
        """Get orders data for dashboard widgets"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401
        
        try:
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            
            # Get recent orders (last 30 days)
            cur.execute("""
                SELECT o.id, o.order_date, o.total_amount, o.status, o.payment_method,
                       c.first_name, c.last_name, c.email
                FROM orders o
                LEFT JOIN customers c ON o.customer_id = c.id
                WHERE o.order_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                ORDER BY o.order_date DESC
                LIMIT 50
            """)
            
            orders = cur.fetchall()
            
            # Format orders data
            orders_data = []
            for order in orders:
                orders_data.append({
                    'id': order['id'],
                    'date': order['order_date'].strftime('%Y-%m-%d') if order['order_date'] else 'Unknown',
                    'amount': float(order['total_amount']) if order['total_amount'] else 0.0,
                    'status': order['status'],
                    'payment_method': order['payment_method'],
                    'customer_name': f"{order['first_name']} {order['last_name']}" if order['first_name'] else 'Unknown',
                    'customer_email': order['email'] or 'No email'
                })
            
            cur.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'orders': orders_data,
                'count': len(orders_data)
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching orders data: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/auth/staff/api/reports/date_range_orders')
    def api_date_range_orders():
        """Get orders data for a specific date range"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401
        
        try:
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            
            if not start_date or not end_date:
                return jsonify({'success': False, 'error': 'start_date and end_date parameters are required'}), 400
            
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            
            # Get orders within the specified date range
            cur.execute("""
                SELECT o.id, o.order_date, o.total_amount, o.status, o.payment_method,
                       c.first_name, c.last_name, c.email
                FROM orders o
                LEFT JOIN customers c ON o.customer_id = c.id
                WHERE DATE(o.order_date) BETWEEN %s AND %s
                ORDER BY o.order_date DESC
            """, (start_date, end_date))
            
            orders = cur.fetchall()
            
            # Format orders data
            orders_data = []
            for order in orders:
                orders_data.append({
                    'order_id': order['id'],
                    'order_date': order['order_date'].strftime('%Y-%m-%d') if order['order_date'] else 'Unknown',
                    'total_amount': float(order['total_amount']) if order['total_amount'] else 0.0,
                    'status': order['status'],
                    'payment_method': order['payment_method'],
                    'customer_name': f"{order['first_name']} {order['last_name']}" if order['first_name'] else 'Unknown',
                    'customer_email': order['email'] or 'No email'
                })
            
            cur.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'orders': orders_data,
                'count': len(orders_data)
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching date range orders: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/auth/staff/api/reports/daily_orders')
    def api_daily_orders():
        """Get daily orders for a specific date"""
        try:
            date = request.args.get('date')
            if not date:
                return jsonify({'success': False, 'error': 'Date parameter required'})
            
            # Parse the date - try multiple formats
            formatted_date = None
            try:
                # Try YYYY-MM-DD format first (most common)
                parsed_date = datetime.strptime(date, "%Y-%m-%d")
                formatted_date = parsed_date.strftime("%Y-%m-%d")
                app.logger.info(f"Parsed date as YYYY-MM-DD: {formatted_date}")
            except ValueError:
                try:
                    # Try "August 06, 2025" format
                    parsed_date = datetime.strptime(date, "%B %d, %Y")
                    formatted_date = parsed_date.strftime("%Y-%m-%d")
                    app.logger.info(f"Parsed date as Month DD, YYYY: {formatted_date}")
                except ValueError:
                    return jsonify({'success': False, 'error': f'Invalid date format: {date}. Expected YYYY-MM-DD or Month DD, YYYY'})
            
            # Get orders for this date
            orders = get_daily_orders(formatted_date)
            app.logger.info(f"Found {len(orders)} orders for date {formatted_date}")
            
            return jsonify({
                'success': True,
                'orders': orders,
                'date': formatted_date
            })
            
        except Exception as e:
            app.logger.error(f"Error in daily_orders API: {str(e)}")
            return jsonify({'success': False, 'error': str(e)})

    def get_daily_orders(date):
        """Get orders for a specific date"""
        try:
            app.logger.info(f"Getting daily orders for date: {date}")
            cur = mysql.connection.cursor()
            
            # Get orders for the specific date
            query = """
                SELECT 
                    o.id as order_id,
                    o.order_date,
                    o.total_amount as grand_total,
                    o.status,
                    CONCAT(c.first_name, ' ', c.last_name) as customer_name,
                    COALESCE(GROUP_CONCAT(p.name SEPARATOR ', '), 'No products') as products
                FROM orders o
                LEFT JOIN customers c ON o.customer_id = c.id
                LEFT JOIN order_items oi ON o.id = oi.order_id
                LEFT JOIN products p ON oi.product_id = p.id
                WHERE DATE(o.order_date) = %s
                AND LOWER(o.status) = 'completed'
                GROUP BY o.id, o.order_date, o.total_amount, o.status, c.first_name, c.last_name
                ORDER BY o.order_date DESC
            """
            app.logger.info(f"Executing query with date parameter: {date}")
            cur.execute(query, (date,))
            orders = cur.fetchall()
            app.logger.info(f"Raw database results: {len(orders)} rows")
            cur.close()
            
            # Convert to list of dicts
            formatted_orders = []
            for row in orders:
                app.logger.info(f"Raw order row: {row}")
                formatted_order = {
                    'order_id': row[0],
                    'order_date': row[1].strftime('%Y-%m-%d %H:%M:%S') if row[1] else '',
                    'grand_total': float(row[2]) if row[2] is not None else 0.0,
                    'status': row[3],
                    'customer_name': row[4] if row[4] else 'Walk-in Customer',
                    'products': row[5] if row[5] else 'No products'
                }
                app.logger.info(f"Formatted order: {formatted_order}")
                formatted_orders.append(formatted_order)
            
            app.logger.info(f"Formatted {len(formatted_orders)} orders")
            return formatted_orders
            
        except Exception as e:
            app.logger.error(f"Error getting daily orders: {str(e)}")
            return []

    # API for Daily Sales Data
    @app.route('/auth/staff/api/reports/daily_sales')
    def api_daily_sales():
        """Get daily sales data including profit for a specific date"""
        try:
            date = request.args.get('date')
            if not date:
                return jsonify({'success': False, 'error': 'Date parameter required'})
            
            # Parse the date - try multiple formats
            formatted_date = None
            try:
                # Try YYYY-MM-DD format first (most common)
                parsed_date = datetime.strptime(date, "%Y-%m-%d")
                formatted_date = parsed_date.strftime("%Y-%m-%d")
                app.logger.info(f"Parsed date as YYYY-MM-DD: {formatted_date}")
            except ValueError:
                try:
                    # Try "August 06, 2025" format
                    parsed_date = datetime.strptime(date, "%B %d, %Y")
                    formatted_date = parsed_date.strftime("%Y-%m-%d")
                    app.logger.info(f"Parsed date as Month DD, YYYY: {formatted_date}")
                except ValueError:
                    return jsonify({'success': False, 'error': f'Invalid date format: {date}. Expected YYYY-MM-DD or Month DD, YYYY'})
            
            # Get daily sales data
            sales_data = get_daily_sales_data(formatted_date)
            app.logger.info(f"Daily sales data for {formatted_date}: {sales_data}")
            
            return jsonify({
                'success': True,
                'daily_profit': sales_data.get('daily_profit', 0),
                'total_sales': sales_data.get('total_sales', 0),
                'orders_count': sales_data.get('orders_count', 0),
                'date': formatted_date
            })
            
        except Exception as e:
            app.logger.error(f"Error in daily_sales API: {str(e)}")
            return jsonify({'success': False, 'error': str(e)})

    def get_daily_sales_data(date):
        """Get daily sales data including estimated profit"""
        try:
            cur = mysql.connection.cursor()
            
            # Get total sales and orders count for the day
            query = """
                SELECT 
                    COUNT(*) as orders_count,
                    COALESCE(SUM(total_amount), 0) as total_sales
                FROM orders 
                WHERE DATE(order_date) = %s AND LOWER(status) = 'completed'
            """
            cur.execute(query, (date,))
            result = cur.fetchone()
            cur.close()
            
            if result:
                orders_count = result[0] or 0
                total_sales = float(result[1] or 0)
                
                # Calculate estimated profit (assume 15% profit margin)
                daily_profit = total_sales * 0.15
                
                return {
                    'orders_count': orders_count,
                    'total_sales': total_sales,
                    'daily_profit': daily_profit
                }
            
            return {'orders_count': 0, 'total_sales': 0, 'daily_profit': 0}
            
        except Exception as e:
            app.logger.error(f"Error getting daily sales data: {str(e)}")
            return {'orders_count': 0, 'total_sales': 0, 'daily_profit': 0}

    # API for Individual Order Profit
    @app.route('/auth/staff/api/order/<int:order_id>/profit')
    def api_order_profit(order_id):
        """Get profit data for a specific order"""
        try:
            # Get order details and calculate estimated profit
            profit_data = get_order_profit_data(order_id)
            
            return jsonify({
                'success': True,
                'profit': profit_data.get('profit', 0),
                'order_id': order_id
            })
            
        except Exception as e:
            app.logger.error(f"Error in order profit API: {str(e)}")
            return jsonify({'success': False, 'error': str(e)})

    def get_order_profit_data(order_id):
        """Get profit data for a specific order"""
        try:
            cur = mysql.connection.cursor()
            
            # Get order total amount
            query = """
                SELECT total_amount
                FROM orders 
                WHERE id = %s AND LOWER(status) = 'completed'
            """
            cur.execute(query, (order_id,))
            result = cur.fetchone()
            cur.close()
            
            if result and result[0]:
                total_amount = float(result[0])
                # Calculate estimated profit (assume 15% profit margin)
                profit = total_amount * 0.15
                return {'profit': profit}
            
            return {'profit': 0}
            
        except Exception as e:
            app.logger.error(f"Error getting order profit data: {str(e)}")
            return {'profit': 0}

    @app.route('/auth/staff/api/order/<int:order_id>/items')
    def api_order_items(order_id):
        """Get order items for a specific order"""
        try:
            cursor = mysql.connection.cursor()
            
            # Get order items with product details
            query = """
                SELECT oi.quantity, oi.price as unit_price, p.name as product_name
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = %s
            """
            app.logger.info(f"Executing query: {query} with order_id: {order_id}")
            cursor.execute(query, (order_id,))
            
            rows = cursor.fetchall()
            # Convert rows to list of dictionaries manually
            items = []
            for row in rows:
                items.append({
                    'quantity': row[0],
                    'unit_price': float(row[1]) if row[1] is not None else 0.0,
                    'product_name': row[2] if row[2] is not None else 'Unknown Product'
                })
            
            app.logger.info(f"Found {len(items)} items: {items}")
            cursor.close()
            
            return jsonify({
                'success': True,
                'order_id': order_id,
                'items': items
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching order items: {str(e)}")
            app.logger.error(f"Exception type: {type(e)}")
            app.logger.error(f"Exception details: {e}")
            return jsonify({'success': False, 'message': f'Error fetching order items: {str(e)}'})

    @app.route('/auth/staff/api/reports/today_revenue')
    def api_today_revenue():
        """Get today's revenue for completed/approved orders only"""
        try:
            cursor = mysql.connection.cursor()
            
            # Get today's revenue for COMPLETED orders or APPROVED orders using database's current date
            query = """
                SELECT 
                    COALESCE(SUM(o.total_amount), 0) as total_revenue,
                    COALESCE(SUM(oi.quantity * (oi.price - p.original_price)), 0) as total_profit
                FROM orders o
                JOIN order_items oi ON o.id = oi.order_id
                JOIN products p ON oi.product_id = p.id
                WHERE DATE(o.order_date) = CURDATE() 
                AND (LOWER(o.status) = 'completed' OR o.approval_status = 'APPROVED')
            """
            
            app.logger.info(f"Executing today revenue query: {query}")
            cursor.execute(query)
            
            row = cursor.fetchone()
            total_revenue = float(row[0]) if row[0] else 0.0
            total_profit = float(row[1]) if row[1] else 0.0
            
            app.logger.info(f"Today's revenue: ${total_revenue}, Profit: ${total_profit}")
            cursor.close()
            
            return jsonify({
                'success': True,
                'total_revenue': total_revenue,
                'total_profit': total_profit
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching today's revenue: {str(e)}")
            return jsonify({'success': False, 'message': f'Error fetching today\'s revenue: {str(e)}'})

    @app.route('/api/revenue/daily')
    def api_daily_revenue():
        """Get revenue for a specific date"""
        try:
            date = request.args.get('date')
            if not date:
                return jsonify({'success': False, 'error': 'Date parameter is required'}), 400
            
            cursor = mysql.connection.cursor()
            
            query = """
                SELECT 
                    COALESCE(SUM(o.total_amount), 0) as revenue,
                    COUNT(DISTINCT o.id) as orders
                FROM orders o
                WHERE DATE(o.order_date) = %s 
                AND (LOWER(o.status) = 'completed' OR o.approval_status = 'APPROVED')
            """
            
            cursor.execute(query, (date,))
            row = cursor.fetchone()
            revenue = float(row[0]) if row[0] else 0.0
            orders = int(row[1]) if row[1] else 0
            
            cursor.close()
            
            return jsonify({
                'success': True,
                'revenue': revenue,
                'orders': orders
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching daily revenue: {str(e)}")
            return jsonify({'success': False, 'error': f'Error fetching daily revenue: {str(e)}'}), 500

    @app.route('/api/revenue/range')
    def api_revenue_range():
        """Get revenue data for a date range"""
        try:
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            
            if not start_date or not end_date:
                return jsonify({'success': False, 'error': 'start_date and end_date parameters are required'}), 400
            
            cursor = mysql.connection.cursor()
            
            query = """
                SELECT 
                    DATE(o.order_date) as date,
                    COUNT(DISTINCT o.id) as orders,
                    COALESCE(SUM(o.total_amount), 0) as revenue
                FROM orders o
                WHERE DATE(o.order_date) BETWEEN %s AND %s 
                AND (LOWER(o.status) = 'completed' OR o.approval_status = 'APPROVED')
                GROUP BY DATE(o.order_date)
                ORDER BY date ASC
            """
            
            cursor.execute(query, (start_date, end_date))
            results = cursor.fetchall()
            
            data = []
            for row in results:
                data.append({
                    'date': row[0].strftime('%Y-%m-%d'),
                    'orders': int(row[1]),
                    'revenue': float(row[2])
                })
            
            cursor.close()
            
            return jsonify({
                'success': True,
                'data': data
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching revenue range: {str(e)}")
            return jsonify({'success': False, 'error': f'Error fetching revenue range: {str(e)}'}), 500

    @app.route('/api/revenue/selected-days', methods=['POST'])
    def api_revenue_selected_days():
        """Get revenue data for selected days"""
        try:
            data = request.get_json()
            dates = data.get('dates', [])
            
            if not dates:
                return jsonify({'success': False, 'error': 'No dates provided'}), 400
            
            cursor = mysql.connection.cursor()
            
            # Create placeholders for the dates
            placeholders = ','.join(['%s'] * len(dates))
            query = f"""
                SELECT 
                    DATE(o.order_date) as date,
                    COUNT(DISTINCT o.id) as orders,
                    COALESCE(SUM(o.total_amount), 0) as revenue
                FROM orders o
                WHERE DATE(o.order_date) IN ({placeholders})
                AND (LOWER(o.status) = 'completed' OR o.approval_status = 'APPROVED')
                GROUP BY DATE(o.order_date)
                ORDER BY date ASC
            """
            
            cursor.execute(query, dates)
            results = cursor.fetchall()
            
            data = []
            for row in results:
                data.append({
                    'date': row[0].strftime('%Y-%m-%d'),
                    'orders': int(row[1]),
                    'revenue': float(row[2])
                })
            
            cursor.close()
            
            return jsonify({
                'success': True,
                'data': data
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching selected days revenue: {str(e)}")
            return jsonify({'success': False, 'error': f'Error fetching selected days revenue: {str(e)}'}), 500

    @app.route('/api/revenue/daily-details')
    def api_daily_details():
        """Get detailed revenue and order data for a specific date"""
        try:
            date = request.args.get('date')
            if not date:
                return jsonify({'success': False, 'error': 'Date parameter is required'}), 400
            
            app.logger.info(f"Fetching daily details for date: {date}")
            
            # First, let's see what dates actually exist in the database
            cursor = mysql.connection.cursor()
            
            # Check what dates have orders
            date_check_query = """
                SELECT DISTINCT DATE(order_date) as order_date, COUNT(*) as order_count
                FROM orders 
                WHERE order_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                GROUP BY DATE(order_date)
                ORDER BY order_date DESC
                LIMIT 10
            """
            cursor.execute(date_check_query)
            available_dates = cursor.fetchall()
            app.logger.info(f"Available dates with orders: {available_dates}")
            
            # First, let's check if there are any orders for this date (with more relaxed conditions)
            check_query = """
                SELECT COUNT(*) as order_count
                FROM orders o
                WHERE DATE(o.order_date) = %s
            """
            
            cursor.execute(check_query, (date,))
            check_result = cursor.fetchone()
            total_orders_check = int(check_result[0]) if check_result[0] else 0
            
            app.logger.info(f"Total orders found for {date}: {total_orders_check}")
            
            # Get summary statistics - include ALL orders for the date
            summary_query = """
                SELECT 
                    COALESCE(SUM(o.total_amount), 0) as total_revenue,
                    COUNT(DISTINCT o.id) as total_orders,
                    COALESCE(AVG(o.total_amount), 0) as avg_order_value,
                    COUNT(DISTINCT oi.product_id) as total_products
                FROM orders o
                LEFT JOIN order_items oi ON o.id = oi.order_id
                WHERE DATE(o.order_date) = %s
            """
            
            cursor.execute(summary_query, (date,))
            summary_row = cursor.fetchone()
            
            total_revenue = float(summary_row[0]) if summary_row[0] else 0.0
            total_orders = int(summary_row[1]) if summary_row[1] else 0
            avg_order_value = float(summary_row[2]) if summary_row[2] else 0.0
            total_products = int(summary_row[3]) if summary_row[3] else 0
            
            app.logger.info(f"Summary - Revenue: {total_revenue}, Orders: {total_orders}, Avg: {avg_order_value}, Products: {total_products}")
            
            # Get detailed orders with actual customer names
            orders_query = """
                SELECT 
                    o.id,
                    COALESCE(CONCAT(c.first_name, ' ', c.last_name), 'Walk-in Customer') as customer_name,
                    TIME(o.order_date) as time,
                    COUNT(oi.id) as items_count,
                    o.total_amount as total,
                    COALESCE(o.status, 'pending') as status
                FROM orders o
                LEFT JOIN order_items oi ON o.id = oi.order_id
                LEFT JOIN customers c ON o.customer_id = c.id
                WHERE DATE(o.order_date) = %s 
                GROUP BY o.id, o.order_date, o.total_amount, o.status, c.first_name, c.last_name
                ORDER BY o.order_date ASC
            """
            
            cursor.execute(orders_query, (date,))
            orders_results = cursor.fetchall()
            
            orders = []
            for row in orders_results:
                orders.append({
                    'id': row[0],
                    'customer_name': row[1],
                    'time': str(row[2]) if row[2] else 'N/A',
                    'items_count': int(row[3]) if row[3] else 0,
                    'total': float(row[4]) if row[4] else 0.0,
                    'status': row[5] or 'N/A'
                })
            
            app.logger.info(f"Found {len(orders)} orders for {date}")
            
            cursor.close()
            
            return jsonify({
                'success': True,
                'total_revenue': total_revenue,
                'total_orders': total_orders,
                'avg_order_value': avg_order_value,
                'total_products': total_products,
                'orders': orders,
                'debug_info': {
                    'date': date,
                    'total_orders_check': total_orders_check,
                    'orders_found': len(orders),
                    'available_dates': [{'date': str(row[0]), 'count': row[1]} for row in available_dates]
                }
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching daily details: {str(e)}")
            return jsonify({'success': False, 'error': f'Error fetching daily details: {str(e)}'}), 500

    @app.route('/api/orders/today_count')
    def api_orders_today_count():
        from datetime import datetime
        conn = mysql.connection
        cur = conn.cursor()
        try:
            # Use database's current date to avoid timezone issues
            cur.execute("""
                SELECT HOUR(order_date) AS hour, COUNT(*) AS order_count
                FROM orders
                WHERE DATE(order_date) = CURDATE() AND LOWER(status) = 'completed'
                GROUP BY hour
                ORDER BY hour
            """)
            rows = cur.fetchall()
            # Convert rows to list of dicts manually
            data = []
            for row in rows:
                data.append({'hour': row[0], 'order_count': row[1]})
            return jsonify({'success': True, 'data': data})
        except Exception as e:
            app.logger.error(f"Error fetching today's orders count: {e}")
            return jsonify({'success': False, 'data': []})
        finally:
            cur.close()

    @app.route('/api/orders/today_total_count')
    def api_orders_today_total_count():
        """Get total count of orders for today"""
        from datetime import datetime
        conn = mysql.connection
        cur = conn.cursor()
        try:
            # Use database's current date to avoid timezone issues
            cur.execute("""
                SELECT COUNT(*) AS total_orders
                FROM orders
                WHERE DATE(order_date) = CURDATE() AND (LOWER(status) = 'completed' OR approval_status = 'APPROVED')
            """)
            row = cur.fetchone()
            total_orders = row[0] if row else 0
            return jsonify({'success': True, 'total_orders': total_orders})
        except Exception as e:
            app.logger.error(f"Error fetching today's total orders count: {e}")
            return jsonify({'success': False, 'total_orders': 0})
        finally:
            cur.close()

    @app.route('/api/reports/monthly_comparison')
    def api_monthly_comparison():
        """Get last 30 days vs previous 30 days comparison data"""
        from datetime import datetime, timedelta
        conn = mysql.connection
        cur = conn.cursor()
        try:
            now = datetime.now()
            
            # Last 30 days date range
            last_30_end = now.strftime('%Y-%m-%d')
            last_30_start = (now - timedelta(days=30)).strftime('%Y-%m-%d')
            
            # Previous 30 days date range (30-60 days ago)
            prev_30_end = (now - timedelta(days=30)).strftime('%Y-%m-%d')
            prev_30_start = (now - timedelta(days=60)).strftime('%Y-%m-%d')
            
            # Get last 30 days data
            cur.execute("""
                SELECT 
                    COALESCE(SUM(o.total_amount), 0) as total_revenue,
                    COALESCE(SUM(oi.quantity * (oi.price - p.original_price)), 0) as total_profit
                FROM orders o
                JOIN order_items oi ON o.id = oi.order_id
                JOIN products p ON oi.product_id = p.id
                WHERE DATE(o.order_date) >= %s AND DATE(o.order_date) <= %s 
                AND (LOWER(o.status) = 'completed' OR o.approval_status = 'APPROVED')
            """, (last_30_start, last_30_end))
            
            last_30_row = cur.fetchone()
            last_30_revenue = float(last_30_row[0]) if last_30_row[0] else 0.0
            last_30_profit = float(last_30_row[1]) if last_30_row[1] else 0.0
            
            # Get previous 30 days data (30-60 days ago)
            cur.execute("""
                SELECT 
                    COALESCE(SUM(o.total_amount), 0) as total_revenue,
                    COALESCE(SUM(oi.quantity * (oi.price - p.original_price)), 0) as total_profit
                FROM orders o
                JOIN order_items oi ON o.id = oi.order_id
                JOIN products p ON oi.product_id = p.id
                WHERE DATE(o.order_date) >= %s AND DATE(o.order_date) <= %s 
                AND (LOWER(o.status) = 'completed' OR o.approval_status = 'APPROVED')
            """, (prev_30_start, prev_30_end))
            
            prev_30_row = cur.fetchone()
            prev_30_revenue = float(prev_30_row[0]) if prev_30_row[0] else 0.0
            prev_30_profit = float(prev_30_row[1]) if prev_30_row[1] else 0.0
            
            # Calculate percentage changes
            revenue_change = 0
            profit_change = 0
            
            if prev_30_revenue > 0:
                revenue_change = ((last_30_revenue - prev_30_revenue) / prev_30_revenue) * 100
            elif last_30_revenue > 0:
                revenue_change = 100  # 100% increase if previous 30 days was 0
                
            if prev_30_profit > 0:
                profit_change = ((last_30_profit - prev_30_profit) / prev_30_profit) * 100
            elif last_30_profit > 0:
                profit_change = 100  # 100% increase if previous 30 days was 0
            
            return jsonify({
                'success': True,
                'last_30_days': {
                    'revenue': last_30_revenue,
                    'profit': last_30_profit
                },
                'prev_30_days': {
                    'revenue': prev_30_revenue,
                    'profit': prev_30_profit
                },
                'changes': {
                    'revenue_change': revenue_change,
                    'profit_change': profit_change
                }
            })
            
        except Exception as e:
            app.logger.error(f"Error fetching monthly comparison: {e}")
            return jsonify({'success': False, 'message': str(e)})
        finally:
            cur.close()

    @app.route('/api/orders/today_details')
    def api_orders_today_details():
        from datetime import datetime
        hour = request.args.get('hour', type=int)
        if hour is None or hour < 0 or hour > 23:
            return jsonify({'success': False, 'error': 'Invalid hour parameter', 'orders': []}), 400
        conn = mysql.connection
        cur = conn.cursor()
        try:
            today_str = datetime.now().strftime('%Y-%m-%d')
            cur.execute("""
                SELECT o.id as order_id, o.order_date, c.first_name, c.last_name, o.total_amount, o.status, o.payment_method
                FROM orders o
                JOIN customers c ON o.customer_id = c.id
                WHERE DATE(o.order_date) = %s AND HOUR(o.order_date) = %s AND LOWER(o.status) = 'completed'
                ORDER BY o.order_date ASC
            """, (today_str, hour))
            rows = cur.fetchall()
            orders = []
            for row in rows:
                order = {
                    'id': row[0],
                    'order_date': row[1].strftime('%Y-%m-%d %H:%M:%S') if hasattr(row[1], 'strftime') else row[1],
                    'customer_name': f"{row[2]} {row[3]}",
                    'total_amount': float(row[4]) if row[4] is not None else 0.0,
                    'status': row[5],
                    'payment_method': row[6] if row[6] is not None else 'QR Payment',
                    'items': []
                }
                # Fetch order items
                cur.execute("""
                    SELECT p.name as product_name, oi.quantity, oi.price
                    FROM order_items oi
                    JOIN products p ON oi.product_id = p.id
                    WHERE oi.order_id = %s
                """, (order['id'],))
                items_rows = cur.fetchall()
                for item_row in items_rows:
                    item = {
                        'product_name': item_row[0],
                        'quantity': item_row[1],
                        'price': float(item_row[2]) if item_row[2] is not None else 0.0
                    }
                    order['items'].append(item)
                orders.append(order)
            return jsonify({'success': True, 'orders': orders})
        except Exception as e:
            app.logger.error(f"Error fetching order details for hour {hour}: {e}")
            return jsonify({'success': False, 'error': str(e), 'orders': []})
        finally:
            cur.close()

    @app.route('/api/orders/today_details/<int:order_id>')
    def api_orders_today_details_by_order(order_id):
        conn = mysql.connection
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT p.name as product_name, oi.quantity, oi.price, p.original_price
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = %s
            """, (order_id,))
            rows = cur.fetchall()
            products = []
            for row in rows:
                product = {
                    'product_name': row[0],
                    'quantity': row[1],
                    'price': float(row[2]) if row[2] is not None else 0.0,
                    'original_price': float(row[3]) if row[3] is not None else None
                }
                products.append(product)
            return jsonify({'success': True, 'products': products})
        except Exception as e:
            app.logger.error(f"Error fetching product details for order {order_id}: {e}")
            return jsonify({'success': False, 'error': str(e), 'products': []})
        finally:
            cur.close()

    @app.route('/api/orders/comprehensive_details/<int:order_id>')
    def api_orders_comprehensive_details(order_id):
        """Get comprehensive order details including customer info, address, and screenshot"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401
        
        try:
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            
            # Get order basic info
            cur.execute("""
                SELECT o.*, c.first_name, c.last_name, c.email, c.phone, c.address
                FROM orders o
                JOIN customers c ON o.customer_id = c.id
                WHERE o.id = %s
            """, (order_id,))
            
            order = cur.fetchone()
            if not order:
                return jsonify({'success': False, 'error': 'Order not found'}), 404
            
            # Get order items with product details
            cur.execute("""
                SELECT oi.*, p.name as product_name, p.original_price, p.photo as product_image
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = %s
            """, (order_id,))
            
            order_items = cur.fetchall()
            
            # Get payment screenshot if exists (from orders table)
            cur.execute("""
                SELECT payment_screenshot_path as screenshot_path, screenshot_uploaded_at as created_at
                FROM orders
                WHERE id = %s AND payment_screenshot_path IS NOT NULL
            """, (order_id,))
            
            screenshot = cur.fetchone()
            
            # Get delivery address if exists (try default first, then any address)
            cur.execute("""
                SELECT ca.*
                FROM customer_addresses ca
                WHERE ca.customer_id = %s AND ca.is_active = TRUE
                ORDER BY ca.is_default DESC, ca.created_at DESC
                LIMIT 1
            """, (order['customer_id'],))
            
            delivery_address = cur.fetchone()
            
            cur.close()
            conn.close()
            
            # Format order items
            formatted_items = []
            total_profit = 0
            
            for item in order_items:
                item_total = float(item['quantity']) * float(item['price'])
                original_total = float(item['quantity']) * float(item['original_price'] or item['price'])
                item_profit = item_total - original_total
                total_profit += item_profit
                
                formatted_items.append({
                    'product_name': item['product_name'],
                    'product_image': item['product_image'],
                    'quantity': int(item['quantity']),
                    'price': float(item['price']),
                    'original_price': float(item['original_price']) if item['original_price'] else None,
                    'total': float(item_total),
                    'profit': float(item_profit)
                })
            
            # Format response
            response_data = {
                'success': True,
                'order': {
                    'id': order['id'],
                    'order_date': order['order_date'].strftime('%Y-%m-%d %H:%M:%S') if order['order_date'] else None,
                    'status': order['status'],
                    'approval_status': order['approval_status'],
                    'payment_method': order['payment_method'],
                    'shipping_method': order.get('shipping_method', 'delivery'),
                    'delivery_status': order.get('delivery_status', 'Pending'),
                    'delivery_date': order['delivery_date'].strftime('%Y-%m-%d %H:%M:%S') if order.get('delivery_date') else None,
                    'delivery_notes': order.get('delivery_notes', ''),
                    'total_amount': float(order['total_amount']) if order['total_amount'] else 0.0,
                    'transaction_id': order['transaction_id'],
                    'notes': order.get('notes', '')
                },
                'customer': {
                    'first_name': order['first_name'],
                    'last_name': order['last_name'],
                    'email': order['email'],
                    'phone': order['phone'],
                    'address': order['address']
                },
                'delivery_address': {
                    'house_number': delivery_address['house_number'] if delivery_address else None,
                    'street_name': delivery_address['street_name'] if delivery_address else None,
                    'street_number': delivery_address['street_number'] if delivery_address else None,
                    'village': delivery_address['village'] if delivery_address else None,
                    'sangkat': delivery_address['sangkat'] if delivery_address else None,
                    'commune': delivery_address['commune'] if delivery_address else None,
                    'khan': delivery_address['khan'] if delivery_address else None,
                    'province': delivery_address['province'] if delivery_address else None,
                    'postal_code': delivery_address['postal_code'] if delivery_address else None,
                    'country': delivery_address['country'] if delivery_address else None,
                    'building_name': delivery_address['building_name'] if delivery_address else None,
                    'landmark': delivery_address['landmark'] if delivery_address else None,
                    'delivery_notes': delivery_address['delivery_notes'] if delivery_address else None
                } if delivery_address else None,
                'items': formatted_items,
                'screenshot': {
                    'path': screenshot['screenshot_path'] if screenshot else None,
                    'created_at': screenshot['created_at'].strftime('%Y-%m-%d %H:%M:%S') if screenshot and screenshot['created_at'] else None
                } if screenshot else None,
                'summary': {
                    'total_amount': float(order['total_amount']) if order['total_amount'] else 0.0,
                    'total_profit': total_profit,
                    'items_count': len(formatted_items)
                }
            }
            
            return jsonify(response_data)
            
        except Exception as e:
            app.logger.error(f"Error fetching comprehensive order details: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    # KHQR Payment Endpoints
    @app.route('/api/khqr/create-payment', methods=['POST'])
    def create_khqr_payment():
        """Create a new KHQR payment with dynamic QR code"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        try:
            from utils.khqr_payment import khqr_handler

            data = request.get_json()
            amount = data.get('amount')
            currency = data.get('currency', 'USD')
            reference_id = data.get('reference_id')
            order_id = data.get('order_id')  # Add order_id parameter

            if not amount or amount <= 0:
                return jsonify({'success': False, 'error': 'Invalid amount'}), 400

            # Create KHQR payment
            result = khqr_handler.create_payment_qr(
                amount=amount,
                currency=currency,
                reference_id=reference_id,
                order_id=order_id  # Pass order_id to the handler
            )

            if result['success']:
                app.logger.info(f"✅ KHQR payment created: {result['payment_id']} for order: {order_id}")
                return jsonify(result)
            else:
                app.logger.error(f"❌ KHQR payment creation failed: {result['error']}")
                return jsonify(result), 400

        except Exception as e:
            app.logger.error(f"Error creating KHQR payment: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/orders/<int:order_id>/update-payment-method', methods=['POST'])
    def update_order_payment_method(order_id):
        """Update payment method for an order"""
        try:
            data = request.get_json()
            payment_method = data.get('payment_method')
            
            if not payment_method:
                return jsonify({'success': False, 'error': 'Payment method is required'}), 400
            
            # Validate payment method
            valid_methods = ['KHQR_BAKONG', 'Cash', 'Pay on Delivery']
            if payment_method not in valid_methods:
                return jsonify({'success': False, 'error': 'Invalid payment method'}), 400
            
            # Check if order exists and is pending
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            
            cur.execute("""
                SELECT id, status, approval_status, payment_method 
                FROM orders 
                WHERE id = %s
            """, (order_id,))
            
            order = cur.fetchone()
            
            if not order:
                cur.close()
                conn.close()
                return jsonify({'success': False, 'error': 'Order not found'}), 404
            
            # Check if order can be updated (only pending orders)
            if order['status'] not in ['PENDING', 'Confirmed'] or order['approval_status'] == 'Approved':
                cur.close()
                conn.close()
                return jsonify({'success': False, 'error': 'Order cannot be updated. Only pending orders can have their payment method changed.'}), 400
            
            # Update payment method
            cur.execute("""
                UPDATE orders 
                SET payment_method = %s
                WHERE id = %s
            """, (payment_method, order_id))
            
            conn.commit()
            cur.close()
            conn.close()
            
            app.logger.info(f"✅ Payment method updated for order {order_id}: {payment_method}")
            
            return jsonify({
                'success': True, 
                'message': 'Payment method updated successfully',
                'payment_method': payment_method
            })
            
        except Exception as e:
            app.logger.error(f"Error updating payment method for order {order_id}: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/orders/<int:order_id>/update-shipping-method', methods=['POST'])
    def update_order_shipping_method(order_id):
        """Update shipping method for an order"""
        try:
            data = request.get_json()
            shipping_method = data.get('shipping_method')
            
            if not shipping_method:
                return jsonify({'success': False, 'error': 'Shipping method is required'}), 400
            
            # Validate shipping method
            valid_methods = ['delivery', 'pickup']
            if shipping_method not in valid_methods:
                return jsonify({'success': False, 'error': 'Invalid shipping method'}), 400
            
            # Check if order exists
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            
            cur.execute("""
                SELECT id, status, approval_status 
                FROM orders 
                WHERE id = %s
            """, (order_id,))
            
            order = cur.fetchone()
            
            if not order:
                cur.close()
                conn.close()
                return jsonify({'success': False, 'error': 'Order not found'}), 404
            
            # Add shipping_method column if it doesn't exist
            try:
                cur.execute("ALTER TABLE orders ADD COLUMN shipping_method VARCHAR(50) DEFAULT 'delivery'")
                app.logger.info("Added shipping_method column to orders table")
            except Exception as e:
                # Column already exists, ignore the error
                if "already exists" not in str(e).lower():
                    app.logger.warning(f"Could not add shipping_method column: {str(e)}")
            
            # Update the shipping method
            cur.execute("""
                UPDATE orders 
                SET shipping_method = %s 
                WHERE id = %s
            """, (shipping_method, order_id))
            
            conn.commit()
            cur.close()
            conn.close()
            
            app.logger.info(f"✅ Shipping method updated for order {order_id}: {shipping_method}")
            
            return jsonify({
                'success': True, 
                'message': 'Shipping method updated successfully',
                'shipping_method': shipping_method
            })
            
        except Exception as e:
            app.logger.error(f"Error updating shipping method for order {order_id}: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/orders/<int:order_id>/shipping-method', methods=['GET'])
    def get_order_shipping_method(order_id):
        """Get shipping method for an order"""
        try:
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            
            # Check if shipping_method column exists
            try:
                cur.execute("""
                    SELECT shipping_method 
                    FROM orders 
                    WHERE id = %s
                """, (order_id,))
            except Exception as e:
                # If column doesn't exist, return default
                if "column" in str(e).lower() and "does not exist" in str(e).lower():
                    cur.close()
                    conn.close()
                    return jsonify({
                        'success': True,
                        'shipping_method': 'delivery'
                    })
                else:
                    raise e
            
            order = cur.fetchone()
            cur.close()
            conn.close()
            
            if not order:
                return jsonify({'success': False, 'error': 'Order not found'}), 404
            
            shipping_method = order.get('shipping_method', 'delivery')
            
            return jsonify({
                'success': True,
                'shipping_method': shipping_method
            })
            
        except Exception as e:
            app.logger.error(f"Error getting shipping method for order {order_id}: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/orders/<int:order_id>/update-delivery-status', methods=['POST'])
    def update_order_delivery_status(order_id):
        """Update delivery status for an order"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401
        
        try:
            data = request.get_json()
            delivery_status = data.get('delivery_status')
            delivery_notes = data.get('delivery_notes', '')
            
            if not delivery_status:
                return jsonify({'success': False, 'error': 'Delivery status is required'}), 400
            
            # Validate delivery status
            valid_statuses = ['Pending', 'Ready for Pickup', 'Out for Delivery', 'Delivered', 'Picked Up', 'Delivery Failed', 'Returned to Store']
            if delivery_status not in valid_statuses:
                return jsonify({'success': False, 'error': 'Invalid delivery status'}), 400
            
            conn = get_db()
            cur = conn.cursor()
            
            # Check if order exists
            cur.execute("SELECT id FROM orders WHERE id = %s", (order_id,))
            if not cur.fetchone():
                cur.close()
                conn.close()
                return jsonify({'success': False, 'error': 'Order not found'}), 404
            
            # Add delivery_status column if it doesn't exist
            try:
                cur.execute("ALTER TABLE orders ADD COLUMN delivery_status ENUM('Pending', 'Ready for Pickup', 'Out for Delivery', 'Delivered', 'Picked Up', 'Delivery Failed', 'Returned to Store') DEFAULT 'Pending'")
                app.logger.info("Added delivery_status column to orders table")
            except Exception as e:
                if "already exists" not in str(e).lower():
                    app.logger.warning(f"Could not add delivery_status column: {str(e)}")
            
            # Add delivery_notes column if it doesn't exist
            try:
                cur.execute("ALTER TABLE orders ADD COLUMN delivery_notes TEXT NULL")
                app.logger.info("Added delivery_notes column to orders table")
            except Exception as e:
                if "already exists" not in str(e).lower():
                    app.logger.warning(f"Could not add delivery_notes column: {str(e)}")
            
            # Add delivery_date column if it doesn't exist
            try:
                cur.execute("ALTER TABLE orders ADD COLUMN delivery_date DATETIME NULL")
                app.logger.info("Added delivery_date column to orders table")
            except Exception as e:
                if "already exists" not in str(e).lower():
                    app.logger.warning(f"Could not add delivery_date column: {str(e)}")
            
            # Update the delivery status
            cur.execute("""
                UPDATE orders 
                SET delivery_status = %s, 
                    delivery_notes = %s,
                    delivery_date = CASE 
                        WHEN %s IN ('Delivered', 'Picked Up') THEN NOW()
                        ELSE delivery_date
                    END
                WHERE id = %s
            """, (delivery_status, delivery_notes, delivery_status, order_id))
            
            conn.commit()
            cur.close()
            conn.close()
            
            app.logger.info(f"✅ Delivery status updated for order {order_id}: {delivery_status}")
            
            return jsonify({
                'success': True, 
                'message': 'Delivery status updated successfully',
                'delivery_status': delivery_status,
                'delivery_notes': delivery_notes
            })
            
        except Exception as e:
            app.logger.error(f"Error updating delivery status for order {order_id}: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/orders/<int:order_id>/upload-screenshot', methods=['POST'])
    def upload_payment_screenshot(order_id):
        """Upload payment screenshot for order verification with fraud detection"""
        try:
            # Check if order exists
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            
            cur.execute("""
                SELECT id, status, payment_method, total_amount 
                FROM orders 
                WHERE id = %s
            """, (order_id,))
            
            order = cur.fetchone()
            
            if not order:
                cur.close()
                conn.close()
                return jsonify({'success': False, 'error': 'Order not found'}), 404
            
            # Check if file was uploaded
            if 'screenshot' not in request.files:
                cur.close()
                conn.close()
                return jsonify({'success': False, 'error': 'No file uploaded'}), 400
            
            file = request.files['screenshot']
            
            if file.filename == '':
                cur.close()
                conn.close()
                return jsonify({'success': False, 'error': 'No file selected'}), 400
            
            # Validate file type
            allowed_extensions = {'png', 'jpg', 'jpeg'}
            if not ('.' in file.filename and 
                    file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
                cur.close()
                conn.close()
                return jsonify({'success': False, 'error': 'Invalid file type. Only PNG, JPG, JPEG allowed.'}), 400
            
            # Create upload directory if it doesn't exist
            import os
            upload_dir = os.path.join(app.static_folder, 'uploads', 'payment_screenshots')
            os.makedirs(upload_dir, exist_ok=True)
            
            # Generate unique filename
            import uuid
            file_extension = file.filename.rsplit('.', 1)[1].lower()
            unique_filename = f"order_{order_id}_{uuid.uuid4().hex[:8]}.{file_extension}"
            
            # Save file temporarily for fraud detection
            file_path = os.path.join(upload_dir, unique_filename)
            file.save(file_path)
            
            # Run fraud detection
            verification_result = screenshot_detector.comprehensive_verification(
                file_path, 
                order_id, 
                float(order['total_amount'])
            )
            
            # If fraud detected, delete file and return error
            if verification_result['is_fraud']:
                os.remove(file_path)  # Delete the suspicious file
                cur.close()
                conn.close()
                
                app.logger.warning(f"🚨 Fraud detected in screenshot for order {order_id}: {verification_result['fraud_reasons']}")
                
                return jsonify({
                    'success': False, 
                    'error': 'Screenshot verification failed',
                    'fraud_reasons': verification_result['fraud_reasons'],
                    'confidence_score': verification_result['confidence_score'],
                    'verification_details': verification_result['verification_details']
                }), 400
            
            # If verification passed, proceed with normal processing
            relative_path = f"uploads/payment_screenshots/{unique_filename}"
            
            # Store image hash for future duplicate detection
            image_hash = hashlib.md5(open(file_path, 'rb').read()).hexdigest()
            
            # Update order with screenshot path and verification status
            cur.execute("""
                UPDATE orders 
                SET payment_screenshot_path = %s, 
                    screenshot_uploaded_at = CURRENT_TIMESTAMP,
                    payment_verification_status = 'verified'
                WHERE id = %s
            """, (relative_path, order_id))
            
            # Store screenshot metadata for fraud detection
            cur.execute("""
                INSERT INTO order_screenshots (order_id, image_hash, file_path, uploaded_at, verification_score)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s)
                ON DUPLICATE KEY UPDATE
                image_hash = VALUES(image_hash),
                file_path = VALUES(file_path),
                uploaded_at = VALUES(uploaded_at),
                verification_score = VALUES(verification_score)
            """, (order_id, image_hash, relative_path, verification_result['confidence_score']))
            
            conn.commit()
            cur.close()
            conn.close()
            
            app.logger.info(f"✅ Payment screenshot uploaded and verified for order {order_id}: {unique_filename} (confidence: {verification_result['confidence_score']:.2f})")
            
            return jsonify({
                'success': True, 
                'message': 'Screenshot uploaded and verified successfully',
                'file_path': relative_path,
                'verification_score': verification_result['confidence_score'],
                'verification_details': verification_result['verification_details']
            })
            
        except Exception as e:
            app.logger.error(f"Error uploading screenshot for order {order_id}: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/khqr/check-payment/<payment_id>', methods=['GET'])
    def check_khqr_payment(payment_id):
        """Check KHQR payment status"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        try:
            from utils.khqr_payment import khqr_handler

            result = khqr_handler.check_payment_status(payment_id)
            return jsonify(result)

        except Exception as e:
            app.logger.error(f"Error checking KHQR payment: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/orders/<int:order_id>/regenerate-qr', methods=['POST'])
    def regenerate_order_qr(order_id):
        """Regenerate QR code for a pending order with the same MD5 hash"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Please log in'}), 401

        try:
            from utils.khqr_payment import khqr_handler
            from models import Order

            # Get order details
            order = Order.get_by_id(order_id)
            if not order:
                return jsonify({'success': False, 'error': 'Order not found'}), 404

            # Check if order is pending and has KHQR payment method
            if order['status'] != 'PENDING' or order['payment_method'] != 'KHQR_BAKONG':
                return jsonify({'success': False, 'error': 'Order is not eligible for QR regeneration'}), 400

            # Check if order has transaction_id (MD5 hash)
            if not order.get('transaction_id'):
                return jsonify({'success': False, 'error': 'Order does not have a transaction ID'}), 400

            app.logger.info(f"🔄 Regenerating QR for order {order_id} with transaction_id: {order['transaction_id']}")

            # Regenerate QR with the same transaction_id (MD5 hash)
            result = khqr_handler.regenerate_qr_with_same_hash(
                amount=float(order['total_amount']),
                currency='USD',
                transaction_id=order['transaction_id'],
                order_id=order_id
            )

            if result['success']:
                app.logger.info(f"✅ QR regenerated successfully for order {order_id}")
                return jsonify(result)
            else:
                app.logger.error(f"❌ QR regeneration failed for order {order_id}: {result['error']}")
                return jsonify(result), 400

        except Exception as e:
            app.logger.error(f"Error regenerating QR for order {order_id}: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/orders/<int:order_id>/generate-khqr', methods=['POST'])
    def generate_khqr(order_id):
        """Generate QR code for KHQR payment method"""
        try:
            from models import Order
            from utils.khqr_payment import khqr_handler
            import hashlib
            import time

            # Get order details
            order = Order.get_by_id(order_id)
            if not order:
                return jsonify({'success': False, 'error': 'Order not found'}), 404

            # Check if order is pending
            if order['status'] != 'PENDING':
                return jsonify({'success': False, 'error': 'Order is not pending'}), 400

            app.logger.info(f"🔄 Generating KHQR for order {order_id}")

            # Generate transaction ID (MD5 hash)
            timestamp = str(int(time.time()))
            transaction_id = hashlib.md5(f"{order_id}_{timestamp}".encode()).hexdigest()

            # Update order with transaction_id and payment method
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                UPDATE orders 
                SET transaction_id = %s, payment_method = 'KHQR_BAKONG'
                WHERE id = %s
            """, (transaction_id, order_id))
            conn.commit()
            cur.close()
            conn.close()
            
            # Generate QR code
            result = khqr_handler.create_payment_qr(
                amount=float(order['total_amount']),
                currency='USD',
                reference_id=transaction_id,
                order_id=order_id
            )

            if result['success']:
                app.logger.info(f"✅ KHQR generated successfully for order {order_id}")
                return jsonify(result)
            else:
                app.logger.error(f"❌ KHQR generation failed for order {order_id}: {result['error']}")
                return jsonify(result), 400

        except Exception as e:
            app.logger.error(f"Error generating KHQR for order {order_id}: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/orders/<int:order_id>/generate-cash-qr', methods=['POST'])
    def generate_cash_qr(order_id):
        """Generate QR code for Cash payment method"""
        try:
            from models import Order
            from utils.khqr_payment import khqr_handler
            import hashlib
            import time

            # Get order details
            order = Order.get_by_id(order_id)
            if not order:
                return jsonify({'success': False, 'error': 'Order not found'}), 404

            # Check if order is pending
            if order['status'] != 'PENDING':
                return jsonify({'success': False, 'error': 'Order is not pending'}), 400

            app.logger.info(f"🔄 Generating Cash QR for order {order_id}")

            # Generate transaction ID (MD5 hash)
            timestamp = str(int(time.time()))
            transaction_id = hashlib.md5(f"{order_id}_{timestamp}_cash".encode()).hexdigest()

            # Update order with transaction_id and payment method
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                UPDATE orders 
                SET transaction_id = %s, payment_method = 'Cash'
                WHERE id = %s
            """, (transaction_id, order_id))
            conn.commit()
            cur.close()
            conn.close()
            
            # Generate QR code
            result = khqr_handler.create_payment_qr(
                amount=float(order['total_amount']),
                currency='USD',
                reference_id=transaction_id,
                order_id=order_id
            )

            if result['success']:
                app.logger.info(f"✅ Cash QR generated successfully for order {order_id}")
                return jsonify(result)
            else:
                app.logger.error(f"❌ Cash QR generation failed for order {order_id}: {result['error']}")
                return jsonify(result), 400

        except Exception as e:
            app.logger.error(f"Error generating Cash QR for order {order_id}: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/orders/<int:order_id>/generate-delivery-qr', methods=['POST'])
    def generate_delivery_qr(order_id):
        """Generate QR code for Pay on Delivery payment method"""
        try:
            from models import Order
            from utils.khqr_payment import khqr_handler
            import hashlib
            import time

            # Get order details
            order = Order.get_by_id(order_id)
            if not order:
                return jsonify({'success': False, 'error': 'Order not found'}), 404

            # Check if order is pending
            if order['status'] != 'PENDING':
                return jsonify({'success': False, 'error': 'Order is not pending'}), 400

            app.logger.info(f"🔄 Generating Delivery QR for order {order_id}")

            # Generate transaction ID (MD5 hash)
            timestamp = str(int(time.time()))
            transaction_id = hashlib.md5(f"{order_id}_{timestamp}_delivery".encode()).hexdigest()

            # Update order with transaction_id and payment method
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                UPDATE orders 
                SET transaction_id = %s, payment_method = 'Pay on Delivery'
                WHERE id = %s
            """, (transaction_id, order_id))
            conn.commit()
            cur.close()
            conn.close()
            
            # Generate QR code
            result = khqr_handler.create_payment_qr(
                amount=float(order['total_amount']),
                currency='USD',
                reference_id=transaction_id,
                order_id=order_id
            )

            if result['success']:
                app.logger.info(f"✅ Delivery QR generated successfully for order {order_id}")
                return jsonify(result)
            else:
                app.logger.error(f"❌ Delivery QR generation failed for order {order_id}: {result['error']}")
                return jsonify(result), 400

        except Exception as e:
            app.logger.error(f"Error generating Delivery QR for order {order_id}: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/orders/<int:order_id>/approve', methods=['POST'])
    def approve_order(order_id):
        """Approve a pending order (staff only)"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        try:
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            
            # Get order details
            cur.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
            order = cur.fetchone()
            
            if not order:
                return jsonify({'success': False, 'error': 'Order not found'}), 404
            
            # Check if order can be approved
            if order['status'] not in ['PENDING', 'COMPLETED']:
                return jsonify({'success': False, 'error': f'Order cannot be approved. Current status: {order["status"]}'}), 400
            
            # Update order status to confirmed/approved
            cur.execute("UPDATE orders SET status = 'CONFIRMED', approval_status = 'Approved' WHERE id = %s", (order_id,))
            conn.commit()
            
            app.logger.info(f"Order {order_id} approved by staff: {session['username']}")
            
            return jsonify({
                'success': True,
                'message': f'Order #{order_id} approved successfully'
            })
            
        except Exception as e:
            app.logger.error(f"Error approving order {order_id}: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()

    @app.route('/api/orders/<int:order_id>/re-pending', methods=['POST'])
    def re_pending_order(order_id):
        """Change approved order back to pending (staff/admin/superadmin only)"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        # Check if user has permission (staff, admin, or superadmin)
        user_role = session.get('role', '')
        app.logger.info(f"Re-pending order {order_id} - User: {session.get('username')}, Role: '{user_role}'")
        
        if user_role not in ['staff', 'admin', 'super_admin']:
            app.logger.warning(f"Permission denied for user {session.get('username')} with role '{user_role}'")
            return jsonify({'success': False, 'error': f'Insufficient permissions. Current role: {user_role}'}), 403
        
        try:
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            
            # Get order details
            cur.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
            order = cur.fetchone()
            
            if not order:
                return jsonify({'success': False, 'error': 'Order not found'}), 404
            
            # Check if order can be re-pending (must be approved/confirmed)
            if order['approval_status'] not in ['Approved', 'CONFIRMED']:
                return jsonify({'success': False, 'error': f'Order cannot be re-pending. Current approval status: {order["approval_status"]}'}), 400
            
            # Update order status back to pending
            cur.execute("""
                UPDATE orders 
                SET status = 'PENDING', 
                    approval_status = 'Pending Approval',
                    approval_date = NULL,
                    approved_by = NULL
                WHERE id = %s
            """, (order_id,))
            conn.commit()
            
            app.logger.info(f"Order {order_id} changed back to pending by {session['username']} (role: {user_role})")
            
            return jsonify({
                'success': True,
                'message': f'Order #{order_id} changed back to pending approval'
            })
            
        except Exception as e:
            app.logger.error(f"Error re-pending order {order_id}: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()

    @app.route('/api/orders/<int:order_id>/reject-after-approval', methods=['POST'])
    def reject_after_approval(order_id):
        """Reject an already approved order (staff/admin/superadmin only)"""
        if 'username' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        # Check if user has permission (staff, admin, or superadmin)
        user_role = session.get('role', '')
        if user_role not in ['staff', 'admin', 'super_admin']:
            return jsonify({'success': False, 'error': 'Insufficient permissions'}), 403
        
        try:
            data = request.get_json() or {}
            reason = data.get('reason', 'No reason provided')
            
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            
            # Get order details
            cur.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
            order = cur.fetchone()
            
            if not order:
                return jsonify({'success': False, 'error': 'Order not found'}), 404
            
            # Check if order can be rejected (must be approved/confirmed)
            if order['approval_status'] not in ['Approved', 'CONFIRMED']:
                return jsonify({'success': False, 'error': f'Order cannot be rejected. Current approval status: {order["approval_status"]}'}), 400
            
            # Update order status to rejected
            cur.execute("""
                UPDATE orders 
                SET status = 'REJECTED', 
                    approval_status = 'Rejected',
                    approval_date = NOW(),
                    approved_by = %s,
                    rejection_reason = %s
                WHERE id = %s
            """, (session.get('user_id', 1), reason, order_id))
            conn.commit()
            
            app.logger.info(f"Order {order_id} rejected after approval by {session['username']} (role: {user_role}), Reason: {reason}")
            
            return jsonify({
                'success': True,
                'message': f'Order #{order_id} rejected successfully'
            })
            
        except Exception as e:
            app.logger.error(f"Error rejecting approved order {order_id}: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()

    @app.route('/api/orders/<int:order_id>/status', methods=['GET'])
    def get_order_status(order_id):
        """Get current order status"""
        try:
            order = Order.get_by_id(order_id)
            if not order:
                return jsonify({'success': False, 'error': 'Order not found'}), 404

            return jsonify({
                'success': True,
                'order_id': order_id,
                'status': order['status'],
                'payment_method': order.get('payment_method'),
                'approval_status': order.get('approval_status')
            })

        except Exception as e:
            app.logger.error(f"Error getting order status for {order_id}: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/orders/<int:order_id>/check-screenshot', methods=['POST'])
    def check_screenshot_detection(order_id):
        """Check if payment was detected from screenshot or QR download"""
        try:
            order = Order.get_by_id(order_id)
            if not order:
                return jsonify({'success': False, 'error': 'Order not found'}), 404
            
            # Check if order status changed to COMPLETED (payment detected)
            if order['status'] == 'COMPLETED':
                return jsonify({
                    'success': True,
                    'payment_detected': True,
                    'message': 'Payment automatically detected!'
                })
            
            return jsonify({
                'success': True,
                'payment_detected': False,
                'message': 'Still waiting for payment...'
            })

        except Exception as e:
            app.logger.error(f"Error checking screenshot detection for {order_id}: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/payment/auto-detect', methods=['POST'])
    def auto_detect_payment():
        """Automatically detect payment from screenshot or QR download"""
        try:
            if 'payment_screenshot' not in request.files:
                return jsonify({'success': False, 'error': 'No screenshot provided'}), 400
            
            file = request.files['payment_screenshot']
            order_id = request.form.get('order_id')
            auto_detect = request.form.get('auto_detect', 'false').lower() == 'true'
            
            if not order_id:
                return jsonify({'success': False, 'error': 'Order ID required'}), 400
            
            if file.filename == '':
                return jsonify({'success': False, 'error': 'No file selected'}), 400
            
            # Get order details
            order = Order.get_by_id(int(order_id))
            if not order:
                return jsonify({'success': False, 'error': 'Order not found'}), 404

            # Save the screenshot
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"auto_detect_{order_id}_{timestamp}_{filename}"
                
                # Save to uploads directory
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'payment_screenshots', filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                file.save(file_path)
                
                app.logger.info(f"📸 Auto-detected screenshot saved: {filename}")
                
                # If auto-detect is enabled, automatically complete the payment
                if auto_detect:
                    # Update order status to COMPLETED
                    conn = get_db()
                    cur = conn.cursor()
                    
                    try:
                        cur.execute("""
                            UPDATE orders
                            SET status = 'COMPLETED', payment_method = 'KHQR_BAKONG'
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
                        
                        app.logger.info(f"✅ Order {order_id} automatically completed from screenshot detection!")

                        return jsonify({
                            'success': True,
                            'message': 'Payment automatically detected and order completed!',
                            'order_id': order_id,
                            'status': 'COMPLETED'
                        })

                    except Exception as e:
                        conn.rollback()
                        raise e
                    finally:
                        cur.close()
                        conn.close()

                return jsonify({
                    'success': True,
                    'message': 'Screenshot received and saved',
                    'filename': filename
                })
            
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400

        except Exception as e:
            app.logger.error(f"Error in auto-detect payment: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    return app

if __name__ == '__main__':
    # Use the create_app function to get the properly configured app
    app = create_app()
    
    # Start automatic payment verifier for instant payment detection
    from utils.automatic_payment_verifier import initialize_payment_verifier
    payment_verifier = initialize_payment_verifier(app, check_interval=5, test_mode=False)
    payment_verifier.start()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
