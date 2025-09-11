# Computer Shop E-commerce System

A comprehensive e-commerce platform built with Flask for computer and electronics retail. This system provides a complete solution for managing inventory, orders, customers, and payments with modern web technologies.

## 🚀 Features

### Customer Features
- **Product Catalog**: Browse products by categories and brands
- **Advanced Search**: Search products with filters and sorting
- **Shopping Cart**: Add/remove items with real-time updates
- **User Authentication**: Secure registration and login with OTP verification
- **Order Management**: Track order history and status
- **Payment Integration**: Multiple payment methods including KHQR (Bakong)
- **Address Management**: Multiple shipping addresses
- **Pre-orders**: Reserve products with payment options

### Admin/Staff Features
- **Dashboard**: Comprehensive analytics and reporting
- **Inventory Management**: Add, edit, and manage products
- **Order Processing**: Handle orders, cancellations, and refunds
- **Customer Management**: View and manage customer accounts
- **Discount System**: Create and manage promotional discounts
- **Reports**: Sales analytics, profit calculations, and insights
- **Notification System**: Real-time notifications for staff
- **Walk-in Sales**: Point-of-sale functionality

### Technical Features
- **Responsive Design**: Mobile-first approach
- **Real-time Updates**: Live cart updates and notifications
- **Payment Processing**: Integrated payment gateways
- **QR Code Generation**: Dynamic QR codes for payments
- **Image Upload**: Product image management
- **Database Management**: MySQL with proper relationships
- **Security**: Password hashing, session management, CSRF protection

## 🛠️ Technology Stack

- **Backend**: Flask (Python)
- **Database**: MySQL
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Payment**: Bakong KHQR integration
- **Authentication**: OTP-based verification
- **Deployment**: Docker support, Railway/Render ready

## 📋 Prerequisites

- Python 3.8+
- MySQL 5.7+
- pip (Python package manager)

## 🚀 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/computer-shop-ecommerce.git
   cd computer-shop-ecommerce
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Setup**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials and other settings
   ```

5. **Database Setup**
   - Create a MySQL database
   - Update database credentials in `.env`
   - Run the application to create tables automatically

6. **Run the application**
   ```bash
   python app.py
   ```

   The application will be available at `http://localhost:5000`

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
SECRET_KEY=your-secret-key-here
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your-password
MYSQL_DB=computershop
MYSQL_PORT=3306

# Email configuration (for OTP)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# Payment configuration
BAKONG_ACCOUNT_ID=your-bakong-account
BAKONG_ACCOUNT_NAME=your-account-name
```

## 📁 Project Structure

```
computer-shop-ecommerce/
├── app.py                 # Main Flask application
├── auth.py               # Authentication blueprint
├── models.py             # Database models
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
├── static/              # Static assets
│   ├── css/             # Stylesheets
│   ├── js/              # JavaScript files
│   ├── icons/           # Icons and images
│   └── uploads/         # User uploads
├── templates/           # HTML templates
├── utils/               # Utility functions
├── migrations/          # Database migrations
└── docs/               # Documentation
```

## 🚀 Deployment

### DigitalOcean App Platform

1. **Prepare for deployment**
   ```bash
   # Ensure all dependencies are in requirements.txt
   pip freeze > requirements.txt
   ```

2. **Create Procfile**
   ```
   web: gunicorn app:app
   ```

3. **Deploy to DigitalOcean**
   - Connect your GitHub repository
   - Configure environment variables
   - Set up MySQL database
   - Deploy!

### Docker Deployment

```bash
# Build Docker image
docker build -t computer-shop .

# Run container
docker run -p 5000:5000 computer-shop
```

## 📊 Database Schema

The system uses MySQL with the following main tables:
- `products` - Product catalog
- `customers` - Customer information
- `orders` - Order management
- `categories` - Product categories
- `suppliers` - Supplier information
- `notifications` - System notifications
- `preorders` - Pre-order management

## 🔐 Security Features

- Password hashing with Werkzeug
- Session management
- CSRF protection
- Input validation and sanitization
- SQL injection prevention
- XSS protection

## 📱 API Endpoints

The system provides RESTful API endpoints for:
- Product management
- Order processing
- Customer authentication
- Payment processing
- Admin operations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support, email support@computershop.com or create an issue in the repository.

## 🎯 Roadmap

- [ ] Mobile app development
- [ ] Advanced analytics dashboard
- [ ] Multi-language support
- [ ] Advanced payment integrations
- [ ] Inventory forecasting
- [ ] Customer loyalty program

---

**Built with ❤️ for modern e-commerce**
