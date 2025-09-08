# 🖥️ Computer Shop E-commerce System - Level 0 Context Diagram

## Visual Context Diagram (Level 0 DFD)

```mermaid
graph TB
    %% External Entities
    Customer["👤<br/>CUSTOMER<br/>Web Browser<br/>Mobile/Desktop"]
    Admin["👨‍💼<br/>ADMIN USER<br/>Management Interface<br/>Desktop Browser"]
    Staff["👥<br/>STAFF MEMBERS<br/>Sales & Support<br/>Various Devices"]
    
    %% External Systems
    Gmail["📧<br/>GMAIL SMTP<br/>Email Service<br/>smtp.gmail.com:587"]
    AivenDB["🗄️<br/>AIVEN MYSQL<br/>Database Server<br/>mysql-5a32e04-...d.aivencloud.com:23044"]
    RailwayStatic["☁️<br/>RAILWAY STATIC<br/>File Storage<br/>static.railway.app"]
    BakongKHQR["💳<br/>BAKONG KHQR<br/>Payment System<br/>QR Code Generation"]
    
    %% Central System (Process 0)
    ComputerShop["🖥️<br/>COMPUTER SHOP<br/>E-COMMERCE SYSTEM<br/>Process 0<br/>Flask Application"]
    
    %% Data Flows from External Entities
    Customer -->|Browse Products<br/>Add to Cart<br/>Place Orders<br/>Upload Payments<br/>Account Management| ComputerShop
    Admin -->|Manage Inventory<br/>Process Orders<br/>Generate Reports<br/>User Management<br/>System Config| ComputerShop
    Staff -->|Handle Orders<br/>Customer Support<br/>Inventory Updates<br/>Sales Processing| ComputerShop
    
    %% Data Flows to External Systems
    ComputerShop -->|Send OTP<br/>Order Confirmations<br/>Password Reset<br/>Notifications| Gmail
    ComputerShop -->|Store Data<br/>Retrieve Information<br/>Transaction Records<br/>User Data| AivenDB
    ComputerShop -->|Store Images<br/>Serve Static Files<br/>File Management<br/>Payment Screenshots| RailwayStatic
    ComputerShop -->|Generate QR Codes<br/>Process Payments<br/>Payment Verification<br/>Transaction Processing| BakongKHQR
    
    %% Data Flows from External Systems
    Gmail -->|Email Delivery Status<br/>SMTP Responses| ComputerShop
    AivenDB -->|Database Queries<br/>Data Retrieval<br/>Transaction Results| ComputerShop
    RailwayStatic -->|File Access<br/>CDN Responses<br/>Storage Confirmation| ComputerShop
    BakongKHQR -->|QR Code Data<br/>Payment Status<br/>Transaction Confirmations| ComputerShop
    
    %% Styling
    classDef externalEntity fill:#e3f2fd,stroke:#1976d2,stroke-width:3px,color:#000
    classDef externalSystem fill:#f3e5f5,stroke:#7b1fa2,stroke-width:3px,color:#000
    classDef centralSystem fill:#e8f5e8,stroke:#388e3c,stroke-width:4px,color:#000
    
    class Customer,Admin,Staff externalEntity
    class Gmail,AivenDB,RailwayStatic,BakongKHQR externalSystem
    class ComputerShop centralSystem
```

## ASCII-Style Context Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL ENTITIES                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  CUSTOMER   │  │ ADMIN USER  │  │   STAFF     │             │
│  │Web Browser  │  │Management   │  │Sales &      │             │
│  │Mobile/Desktop│  │Interface    │  │Support      │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│              COMPUTER SHOP E-COMMERCE SYSTEM                   │
│                    (Process 0)                                 │
│              Flask Application - Railway Platform              │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                  EXTERNAL SYSTEMS                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │GMAIL SMTP   │  │AIVEN MYSQL  │  │RAILWAY STATIC│  │BAKONG   │ │
│  │Email Service│  │Database     │  │File Storage │  │KHQR     │ │
│  │smtp.gmail   │  │mysql-5a32e04│  │static.railway│  │Payment  │ │
│  │.com:587     │  │...d.aiven   │  │.app         │  │System   │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow Summary

### **Input Flows (Into System):**
- **Customer** → Browse Products, Add to Cart, Place Orders, Upload Payments
- **Admin** → Manage Inventory, Process Orders, Generate Reports, User Management
- **Staff** → Handle Orders, Customer Support, Inventory Updates, Sales Processing

### **Output Flows (From System):**
- **Gmail** → Send OTP, Order Confirmations, Password Reset, Notifications
- **AivenDB** → Store Data, Retrieve Information, Transaction Records, User Data
- **RailwayStatic** → Store Images, Serve Static Files, File Management
- **BakongKHQR** → Generate QR Codes, Process Payments, Payment Verification

### **Response Flows (Back to System):**
- **Gmail** → Email Delivery Status, SMTP Responses
- **AivenDB** → Database Queries, Data Retrieval, Transaction Results
- **RailwayStatic** → File Access, CDN Responses, Storage Confirmation
- **BakongKHQR** → QR Code Data, Payment Status, Transaction Confirmations

---

**Document Version**: 1.0  
**Created**: December 2024  
**System**: Computer Shop E-commerce Management System

