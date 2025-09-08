# 🖥️ Computer Shop E-commerce Management System

## ប្រព័ន្ធគ្រប់គ្រងហាងលក់កុំព្យូទ័រ
## Computer Shop E-commerce Management System

---

## 🌐 Web Application System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Client Workstations                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│  │   Admin     │ │  Customer   │ │  Customer   │               │
│  │  Desktop    │ │  Desktop    │ │  Mobile     │               │
│  │             │ │             │ │             │               │
│  └─────────────┘ └─────────────┘ └─────────────┘               │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                    Internet                                    │
│              (Global Network Access)                           │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                  Railway Platform                              │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Flask E-commerce Application                  │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │ │
│  │  │   Frontend  │ │   Backend   │ │   Database  │           │ │
│  │  │  (Templates)│ │   (Flask)   │ │   (MySQL)   │           │ │
│  │  └─────────────┘ └─────────────┘ └─────────────┘           │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │ │
│  │  │File Storage │ │   Email     │ │   Payment   │           │ │
│  │  │ (Static)    │ │   (SMTP)    │ │   (QR/KHQR) │           │ │
│  │  └─────────────┘ └─────────────┘ └─────────────┘           │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## I. Technology and Scope of Work Briefly

### Core Technologies:
1. **Flask 2.3** (Python 3.9+)
2. **MySQL Database** (Railway Managed)
3. **Gunicorn WSGI Server**
4. **Cloud hosting on Railway Platform**
5. **Static file storage** (Railway Static)
6. **Email service** (Gmail SMTP)
7. **QR Code Payment** (Bakong KHQR Integration)

### System Functionalities:
1. **User Management** - Customer registration, authentication, OTP verification
2. **Product Management** - Categories, subcategories, product catalog
3. **Shopping Cart** - Add/remove items, session-based cart
4. **Order Management** - Checkout, order tracking, status updates
5. **Payment System** - QR code generation, payment verification
6. **Admin Dashboard** - Inventory management, order processing
7. **Reports** - Sales analytics, profit calculations, export features
8. **File Management** - Product images, payment screenshots

---

## II. Software Project

### Development Tools:
1. **Visual Studio Code** - Primary IDE
2. **GitHub** - Version control and collaboration
3. **Railway CLI** - Deployment and management
4. **MySQL Workbench** - Database management
5. **Postman** - API testing
6. **Browser DevTools** - Frontend debugging

### Key Libraries and Dependencies:
1. **Flask** - Web framework
2. **Flask-SQLAlchemy** - Database ORM
3. **Flask-Mail** - Email functionality
4. **QRCode** - QR code generation
5. **Bakong-KHQR** - Payment integration
6. **PyOTP** - OTP generation
7. **Pillow** - Image processing
8. **Gunicorn** - Production WSGI server

---

## III. Server Role Description

### 1. **Railway Web Application Server**
- **Platform**: Railway Cloud Platform
- **OS**: Ubuntu Linux 22.04 LTS
- **Runtime**: Python 3.9+
- **Framework**: Flask 2.3
- **WSGI Server**: Gunicorn
- **Access Method**: Domain name `your-app.railway.app`
- **Internal Network**: `web.railway.internal` (Railway managed)
- **Resources**: 
  - RAM: 512MB - 1GB (scalable)
  - CPU: 1-2 vCPU (scalable)
  - Storage: 1GB (ephemeral)
- **Role**: 
  - Web application hosting
  - API endpoints serving
  - Session management
  - File upload handling
  - QR code generation
  - Payment processing

### 2. **MySQL Database Server (Hosted on Aiven)**
- **Platform**: Aiven for MySQL
- **OS**: Managed by Aiven (Linux-based)
- **Version**: MySQL 8.0
- **Storage**: 1GB (expandable, managed by Aiven)
- **Backup**: Automated daily backups (managed by Aiven)
- **Access Method**: External connection via Aiven host
- **Host**: `mysql-5a32e04-lyhenghab3-10a2.d.aivencloud.com`
- **Port**: `23044`
- **User**: `avnadmin`
- **SSL Mode**: `REQUIRED`
- **Connection String**: `MYSQL_URL` environment variable
- **Role**:
  - User data storage
  - Product catalog management
  - Order and transaction records
  - Session data persistence
  - Report data aggregation

### 3. **Static File Storage**
- **Platform**: Railway Static File Service
- **Storage Type**: CDN-backed static storage
- **Access Method**: `static.railway.app` (Railway managed)
- **File Types**: Images, documents, exports
- **Role**:
  - Product image hosting
  - Payment screenshot storage
  - Report file storage
  - Asset delivery (CSS, JS, images)

### 4. **Email Service**
- **Provider**: Gmail SMTP
- **Server**: smtp.gmail.com:587
- **Authentication**: OAuth2/App Password
- **Role**:
  - OTP delivery
  - Order confirmations
  - Password reset emails
  - System notifications

---

## IV. Client Server Role

### **Admin Workstation**
- **OS**: Windows 10/11, macOS, or Linux
- **Browser**: Chrome/Edge/Firefox (version 120+)
- **IP Address**: Dynamic (home/office network, no static IP)
- **Hardware**: 
  - RAM: 8GB minimum
  - CPU: Intel i5 or equivalent
  - Storage: 100GB available
- **Role**: 
  - System administration
  - Product management
  - Order processing
  - Report generation
  - User management

### **Customer Workstations**
- **OS**: Windows/macOS/Linux/Android/iOS
- **Browser**: Chrome/Edge/Safari/Firefox (version 120+)
- **IP Address**: Dynamic (home/mobile network, no static IP)
- **Hardware**: 
  - RAM: 4GB minimum
  - CPU: Any modern processor
  - Storage: 10GB available
- **Role**:
  - Product browsing
  - Shopping cart management
  - Order placement
  - Payment processing
  - Account management

---

## V. Railway Networking Architecture

### **How Services Connect (No IP Addresses Needed):**

```
┌─────────────────────────────────────────────────────────────────┐
│                    Railway Platform                            │
│  ┌─────────────────┐                                          │
│  │   Web Service   │                                          │
│  │web.railway.internal│                                        │
│  └─────────────────┘                                          │
│           │                                                    │
│           ▼                                                    │
│  ┌─────────────────┐    ┌─────────────────┐                   │
│  │ Static Storage  │    │  Email Service  │                   │
│  │static.railway.app│    │smtp.gmail.com  │                   │
│  └─────────────────┘    └─────────────────┘                   │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                    Aiven Platform                              │
│  ┌─────────────────┐                                          │
│  │  MySQL Service  │                                          │
│  │mysql-5a32e04-...│                                          │
│  │d.aivencloud.com │                                          │
│  └─────────────────┘                                          │
└─────────────────────────────────────────────────────────────────┘
```

### **Connection Methods:**
1. **Web App → Database**: External connection to Aiven MySQL
2. **Web App → Static Files**: Uses `RAILWAY_STATIC_URL` environment variable  
3. **Web App → Email**: Uses `SMTP_SERVER` configuration
4. **External Access**: Uses `your-app.railway.app` domain name

### **Environment Variables:**
```bash
# Aiven MySQL Connection
MYSQL_URL=mysql://avnadmin:YOUR_PASSWORD@mysql-5a32e04-lyhenghab3-10a2.d.aivencloud.com:23044/defaultdb?ssl-mode=REQUIRED

# Railway Services
RAILWAY_STATIC_URL=https://static.railway.app/your-project
PORT=8000

# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

---

## VI. System Features and Capabilities

### **E-commerce Core Features**
1. **Product Catalog**
   - Hierarchical categories and subcategories
   - Product search and filtering
   - Image galleries and descriptions
   - Price management and discounts

2. **Shopping Experience**
   - Session-based shopping cart
   - Guest checkout capability
   - Real-time cart updates
   - Wishlist functionality

3. **Order Management**
   - Multi-step checkout process
   - Order status tracking
   - Order history and reordering
   - Invoice generation

4. **Payment Integration**
   - Bakong KHQR payment system
   - QR code generation and scanning
   - Payment verification
   - Receipt generation

5. **User Management**
   - Customer registration and login
   - OTP-based authentication
   - Profile management
   - Address book

6. **Admin Dashboard**
   - Inventory management
   - Order processing
   - Customer management
   - Sales analytics
   - Report generation

### **Technical Features**
1. **Security**
   - Password hashing and encryption
   - Session management
   - CSRF protection
   - Input validation and sanitization

2. **Performance**
   - Database query optimization
   - Static file caching
   - Image compression
   - Responsive design

3. **Scalability**
   - Cloud-based hosting
   - Auto-scaling capabilities
   - Load balancing ready
   - Database replication support

4. **Monitoring**
   - Application logging
   - Error tracking
   - Performance metrics
   - Health checks

---

## VI. Deployment Architecture

### **Production Environment**
```
Internet → Railway Platform → Flask App → MySQL Database
    ↓
Static Files (CDN) ← File Storage ← Application
    ↓
Email Service (SMTP) ← Notification System
```

### **Development Environment**
```
Local Machine → Git Repository → Railway Platform
    ↓
Local Database ← Development Server ← Flask App
```

---

## VII. Security and Compliance

### **Data Protection**
- User data encryption
- Secure password storage
- HTTPS enforcement
- Session security

### **Payment Security**
- PCI DSS compliance ready
- Secure QR code generation
- Payment verification
- Transaction logging

### **Access Control**
- Role-based permissions
- Admin authentication
- Customer verification
- API endpoint protection

---

## VIII. Performance Specifications

### **Response Times**
- Page load: < 2 seconds
- API responses: < 500ms
- Database queries: < 100ms
- File uploads: < 5 seconds

### **Scalability**
- Concurrent users: 100+ (scalable to 1000+)
- Database connections: 20+ (scalable)
- File storage: 1GB+ (expandable)
- Bandwidth: Unlimited (Railway managed)

### **Availability**
- Uptime target: 99.9%
- Backup frequency: Daily
- Recovery time: < 1 hour
- Monitoring: 24/7

---

## IX. Future Enhancements

### **Planned Features**
1. **Mobile App** - Native iOS/Android applications
2. **Advanced Analytics** - Business intelligence dashboard
3. **Multi-language Support** - Khmer and English
4. **Inventory Management** - Real-time stock tracking
5. **Customer Support** - Live chat integration
6. **Marketing Tools** - Email campaigns, promotions

### **Technical Improvements**
1. **Microservices Architecture** - Service separation
2. **API Gateway** - Centralized API management
3. **Caching Layer** - Redis integration
4. **CDN Integration** - Global content delivery
5. **Monitoring Stack** - Advanced observability

---

## X. Cost Analysis

### **Current Monthly Costs**
- **Railway Platform**: $5-20/month
- **Aiven MySQL Database**: $15-30/month
- **Static Storage**: Included (Railway)
- **Email Service**: Free (Gmail)
- **Domain**: $10-15/year
- **Total**: ~$20-50/month

### **Scaling Costs**
- **High Traffic**: $50-100/month
- **Enterprise Features**: $200-500/month
- **Dedicated Resources**: $500-1000/month

---

## XI. Support and Maintenance

### **Technical Support**
- Railway platform support
- Community documentation
- GitHub issue tracking
- Email support system

### **Maintenance Schedule**
- **Daily**: Automated backups
- **Weekly**: Security updates
- **Monthly**: Performance optimization
- **Quarterly**: Feature updates

---

## XII. Conclusion

The Computer Shop E-commerce Management System represents a modern, scalable, and cost-effective solution for online retail operations. Built on the Railway platform with Flask and MySQL, it provides a robust foundation for e-commerce activities while maintaining flexibility for future growth and enhancement.

The system successfully integrates modern web technologies with traditional business requirements, offering both technical excellence and practical functionality for computer shop management and customer service.

---

**Document Version**: 1.0  
**Last Updated**: December 2024  
**Prepared By**: System Architecture Team  
**Status**: Production Ready
