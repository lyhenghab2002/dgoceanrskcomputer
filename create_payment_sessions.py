#!/usr/bin/env python3
"""
Script to create payment_sessions table if it doesn't exist
"""

import mysql.connector

def create_payment_sessions_table():
    try:
        # Connect to database
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='computer_shop'
        )
        cur = conn.cursor()

        # Check if payment_sessions table exists
        cur.execute("SHOW TABLES LIKE 'payment_sessions'")
        if not cur.fetchone():
            print("Creating payment_sessions table...")
            cur.execute("""
                CREATE TABLE payment_sessions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(255) UNIQUE NOT NULL,
                    payment_id VARCHAR(255) UNIQUE NOT NULL,
                    order_id INT NULL,
                    customer_id INT NULL,
                    amount DECIMAL(10,2) NOT NULL,
                    currency VARCHAR(3) DEFAULT 'USD',
                    qr_data TEXT NOT NULL,
                    md5_hash VARCHAR(32) NOT NULL,
                    bill_number VARCHAR(50) NOT NULL,
                    reference_id VARCHAR(255) NULL,
                    status ENUM('pending', 'completed', 'failed', 'expired') DEFAULT 'pending',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME NOT NULL,
                    completed_at DATETIME NULL,
                    payment_screenshot_path VARCHAR(500) NULL,
                    screenshot_uploaded_at DATETIME NULL,
                    payment_verification_status ENUM('pending', 'verified', 'rejected') DEFAULT 'pending',
                    notes TEXT NULL,
                    
                    INDEX idx_session_id (session_id),
                    INDEX idx_payment_id (payment_id),
                    INDEX idx_order_id (order_id),
                    INDEX idx_customer_id (customer_id),
                    INDEX idx_status (status),
                    INDEX idx_expires_at (expires_at),
                    INDEX idx_md5_hash (md5_hash),
                    
                    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE SET NULL,
                    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL
                )
            """)
            conn.commit()
            print("✅ payment_sessions table created successfully")
        else:
            print("✅ payment_sessions table already exists")

        # Show table structure
        cur.execute("DESCRIBE payment_sessions")
        print("\nTable structure:")
        for row in cur.fetchall():
            print(f"  {row[0]} - {row[1]}")

        cur.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ Error creating payment_sessions table: {e}")
        return False

if __name__ == "__main__":
    create_payment_sessions_table()
