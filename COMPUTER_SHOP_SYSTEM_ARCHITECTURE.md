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
│                DigitalOcean Droplet                            │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Ubuntu 22.04 LTS Server                       │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │ │
│  │  │   Nginx     │ │   Gunicorn  │ │   MySQL     │           │ │
│  │  │ (Web Server)│ │ (WSGI Server)│ │ (Database)  │           │ │
│  │  └─────────────┘ └─────────────┘ └─────────────┘           │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │ │
│  │  │   Flask     │ │   Static    │ │   SSL/HTTPS │           │ │
│  │  │ (App Logic) │ │   Files     │ │ (Let's Encrypt)│         │ │
│  │  └─────────────┘ └─────────────┘ └─────────────┘           │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## I. Technology and Scope of Work Briefly

### Core Technologies:
1. **Flask 2.3** (Python 3.9+)
2. **MySQL Database** (Self-hosted on DigitalOcean)
3. **Gunicorn WSGI Server** (Production WSGI)
4. **Nginx Web Server** (Reverse Proxy)
5. **Ubuntu 22.04 LTS** (Operating System)
6. **SSL/HTTPS** (Let's Encrypt Certificate)
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
3. **SSH/SCP** - Server deployment and management
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

### 1. **DigitalOcean Droplet (Main Server)**
- **Platform**: DigitalOcean Cloud Platform
- **OS**: Ubuntu 22.04 LTS
- **Runtime**: Python 3.9+
- **Framework**: Flask 2.3
- **WSGI Server**: Gunicorn
- **Web Server**: Nginx (Reverse Proxy)
- **Domain**: `rskpc.duckdns.org` (Free subdomain)
- **IP Address**: `152.42.227.254` (Static)
- **Resources**: 
  - RAM: 1GB
  - CPU: 1 vCPU
  - Storage: 25GB SSD
  - Bandwidth: 1TB/month
- **Role**: 
  - Web application hosting
  - API endpoints serving
  - Session management
  - File upload handling
  - QR code generation
  - Payment processing
  - Static file serving

### 2. **MySQL Database Server (Self-hosted)**
- **Platform**: Self-hosted on DigitalOcean Droplet
- **OS**: Ubuntu 22.04 LTS
- **Version**: MySQL 8.0
- **Storage**: 25GB SSD (shared with application)
- **Backup**: Automated daily backups via cron job
- **Access Method**: Local connection (127.0.0.1:3306)
- **Database**: `computer_shop`
- **User**: `root` (with strong password)
- **SSL Mode**: Local (no external access)
- **Role**:
  - User data storage
  - Product catalog management
  - Order and transaction records
  - Session data persistence
  - Report data aggregation

### 3. **Static File Storage**
- **Platform**: Local file system on DigitalOcean Droplet
- **Storage Type**: Local directory storage
- **Path**: `/var/www/computer-shop/static/`
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

### 5. **SSL/HTTPS Security**
- **Provider**: Let's Encrypt (Free)
- **Certificate**: Auto-renewed every 90 days
- **Domain**: `rskpc.duckdns.org`
- **Role**:
  - Encrypted data transmission
  - Secure authentication
  - Trusted website access

---

## IV. Client Server Role

### **Admin Workstation**
- **OS**: Windows 10/11, macOS, or Linux
- **Browser**: Chrome/Edge/Firefox (version 120+)
- **IP Address**: Dynamic (home/office network)
- **Hardware**: 
  - RAM: 8GB minimum
  - CPU: Intel i3 or equivalent
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
- **IP Address**: Dynamic (home/mobile network)
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

## V. DigitalOcean Networking Architecture

### **How Services Connect:**

```
┌─────────────────────────────────────────────────────────────────┐
│                DigitalOcean Droplet                            │
│  ┌─────────────────┐                                          │
│  │   Nginx (Port 80/443)                                      │
│  │   (Reverse Proxy)                                          │
│  └─────────────────┘                                          │
│           │                                                    │
│           ▼                                                    │
│  ┌─────────────────┐    ┌─────────────────┐                   │
│  │  Gunicorn       │    │  MySQL Database │                   │
│  │ (Port 5000)     │    │ (Port 3306)     │                   │
│  └─────────────────┘    └─────────────────┘                   │
│           │                                                    │
│           ▼                                                    │
│  ┌─────────────────┐                                          │
│  │  Flask App      │                                          │
│  │  (Application)  │                                          │
│  └─────────────────┘                                          │
└─────────────────────────────────────────────────────────────────┘
```

### **Connection Methods:**
1. **Internet → Nginx**: Port 80/443 (HTTP/HTTPS)
2. **Nginx → Gunicorn**: Port 5000 (Internal)
3. **Gunicorn → MySQL**: Port 3306 (Local)
4. **External Access**: `https://rskpc.duckdns.org`

### **Environment Variables:**
```bash
# MySQL Connection (Local)
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=ComputerShop123!
MYSQL_DB=computer_shop

# Flask Configuration
FLASK_ENV=production
SECRET_KEY=your-secret-key

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
   - SSL/HTTPS encryption

2. **Performance**
   - Nginx reverse proxy
   - Gunicorn WSGI server
   - Database query optimization
   - Static file serving
   - Responsive design

3. **Scalability**
   - Cloud-based hosting
   - Load balancing ready
   - Database replication support
   - Easy server scaling

4. **Monitoring**
   - Uptime Robot monitoring
   - Application logging
   - Error tracking
   - Automated backups

---

## VII. Deployment Architecture

### **Production Environment**
```
Internet → Duck DNS → DigitalOcean Droplet → Nginx → Gunicorn → Flask App → MySQL
    ↓
SSL/HTTPS (Let's Encrypt) ← Security Layer
    ↓
Static Files ← Local Storage ← Application
    ↓
Email Service (SMTP) ← Notification System
```

### **Development Environment**
```
Local Machine → Git Repository → GitHub → DigitalOcean Droplet
    ↓
Local Database ← Development Server ← Flask App
```

---

## VIII. Security and Compliance

### **Data Protection**
- User data encryption
- Secure password storage
- HTTPS enforcement
- Session security
- SSL certificate (Let's Encrypt)

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

## IX. Performance Specifications

### **Response Times**
- Page load: < 2 seconds
- API responses: < 500ms
- Database queries: < 100ms
- File uploads: < 5 seconds

### **Scalability**
- Concurrent users: 50+ (scalable to 200+)
- Database connections: 20+ (scalable)
- File storage: 25GB (expandable)
- Bandwidth: 1TB/month

### **Availability**
- Uptime target: 99.9%
- Backup frequency: Daily (automated)
- Recovery time: < 1 hour
- Monitoring: 24/7 (Uptime Robot)

---

## X. Cost Analysis

### **Current Monthly Costs**
- **DigitalOcean Droplet**: $6/month (1GB RAM, 1 vCPU, 25GB SSD)
- **Duck DNS Domain**: Free
- **SSL Certificate**: Free (Let's Encrypt)
- **Email Service**: Free (Gmail)
- **Monitoring**: Free (Uptime Robot)
- **Total**: ~$6/month

### **Scaling Costs**
- **Higher Performance**: $12-24/month (2-4GB RAM)
- **More Storage**: $0.10/GB/month
- **Additional Bandwidth**: $0.01/GB

---

## XI. Support and Maintenance

### **Technical Support**
- DigitalOcean platform support
- Community documentation
- GitHub issue tracking
- Email support system

### **Maintenance Schedule**
- **Daily**: Automated database backups
- **Weekly**: Security updates
- **Monthly**: Performance optimization
- **Quarterly**: Feature updates

---

## XII. Conclusion

The Computer Shop E-commerce Management System represents a modern, cost-effective, and self-managed solution for online retail operations. Built on DigitalOcean with Flask, Nginx, Gunicorn, and MySQL, it provides a robust foundation for e-commerce activities while maintaining full control over the infrastructure.

The system successfully integrates modern web technologies with traditional business requirements, offering both technical excellence and practical functionality for computer shop management and customer service at an extremely low cost.

---

**Document Version**: 2.0  
**Last Updated**: January 2025  
**Prepared By**: System Architecture Team  
**Status**: Production Ready (DigitalOcean Implementation)