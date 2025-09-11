-- Complete Aiven Database Migration for Multiple Addresses System
-- Run these commands in order on your Aiven database

-- =====================================================
-- STEP 1: Create customer_addresses table
-- =====================================================

CREATE TABLE IF NOT EXISTS customer_addresses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    house_number VARCHAR(50),
    street_name VARCHAR(100),
    street_number VARCHAR(50),
    village VARCHAR(100),
    sangkat VARCHAR(100),
    commune VARCHAR(100),
    khan VARCHAR(100),
    province VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(50) DEFAULT 'Cambodia',
    building_name VARCHAR(100),
    floor_number VARCHAR(20),
    unit_number VARCHAR(20),
    landmark VARCHAR(100),
    delivery_notes TEXT,
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    INDEX idx_customer_id (customer_id),
    INDEX idx_is_default (is_default),
    INDEX idx_is_active (is_active)
);

-- =====================================================
-- STEP 2: Add atomic address columns to customers table
-- =====================================================

ALTER TABLE customers ADD COLUMN house_number VARCHAR(50) AFTER address;
ALTER TABLE customers ADD COLUMN street_name VARCHAR(100) AFTER house_number;
ALTER TABLE customers ADD COLUMN street_number VARCHAR(50) AFTER street_name;
ALTER TABLE customers ADD COLUMN village VARCHAR(100) AFTER street_number;
ALTER TABLE customers ADD COLUMN sangkat VARCHAR(100) AFTER village;
ALTER TABLE customers ADD COLUMN commune VARCHAR(100) AFTER sangkat;
ALTER TABLE customers ADD COLUMN khan VARCHAR(100) AFTER commune;
ALTER TABLE customers ADD COLUMN province VARCHAR(100) AFTER khan;
ALTER TABLE customers ADD COLUMN postal_code VARCHAR(20) AFTER province;
ALTER TABLE customers ADD COLUMN country VARCHAR(50) DEFAULT 'Cambodia' AFTER postal_code;
ALTER TABLE customers ADD COLUMN building_name VARCHAR(100) AFTER country;
ALTER TABLE customers ADD COLUMN floor_number VARCHAR(20) AFTER building_name;
ALTER TABLE customers ADD COLUMN unit_number VARCHAR(20) AFTER floor_number;
ALTER TABLE customers ADD COLUMN landmark VARCHAR(100) AFTER unit_number;
ALTER TABLE customers ADD COLUMN delivery_notes TEXT AFTER landmark;

-- =====================================================
-- STEP 3: Add address_id column to orders table
-- =====================================================

ALTER TABLE orders ADD COLUMN address_id INT;
ALTER TABLE orders ADD CONSTRAINT fk_address_id FOREIGN KEY (address_id) REFERENCES customer_addresses(id);

-- =====================================================
-- STEP 4: Migrate existing customer addresses
-- =====================================================

-- Migrate from customers table atomic fields to customer_addresses
INSERT INTO customer_addresses (
    customer_id, house_number, street_name, street_number,
    village, sangkat, commune, khan, province, postal_code, country,
    building_name, floor_number, unit_number, landmark, delivery_notes,
    is_default, is_active
)
SELECT 
    id as customer_id,
    house_number, street_name, street_number,
    village, sangkat, commune, khan, province, postal_code, country,
    building_name, floor_number, unit_number, landmark, delivery_notes,
    TRUE as is_default,
    TRUE as is_active
FROM customers 
WHERE (house_number IS NOT NULL OR street_name IS NOT NULL OR province IS NOT NULL 
       OR village IS NOT NULL OR sangkat IS NOT NULL)
AND NOT EXISTS (
    SELECT 1 FROM customer_addresses ca 
    WHERE ca.customer_id = customers.id
);

-- =====================================================
-- STEP 5: Ensure only one default address per customer
-- =====================================================

UPDATE customer_addresses ca1
SET is_default = FALSE
WHERE ca1.id NOT IN (
    SELECT * FROM (
        SELECT MIN(id) 
        FROM customer_addresses ca2 
        WHERE ca2.customer_id = ca1.customer_id 
        AND ca2.is_active = TRUE
        GROUP BY customer_id
    ) as subquery
);

-- =====================================================
-- STEP 6: Verification queries
-- =====================================================

-- Check table structure
DESCRIBE customer_addresses;
DESCRIBE customers;
DESCRIBE orders;

-- Check how many addresses each customer has
SELECT 
    c.first_name, c.last_name, c.email,
    COUNT(ca.id) as address_count,
    SUM(CASE WHEN ca.is_default = TRUE THEN 1 ELSE 0 END) as default_count
FROM customers c
LEFT JOIN customer_addresses ca ON c.id = ca.customer_id AND ca.is_active = TRUE
GROUP BY c.id, c.first_name, c.last_name, c.email
ORDER BY address_count DESC;

-- Sample addresses
SELECT 
    ca.id, ca.customer_id, ca.street_name, ca.province, ca.is_default,
    CONCAT(c.first_name, ' ', c.last_name) as customer_name
FROM customer_addresses ca
JOIN customers c ON ca.customer_id = c.id
WHERE ca.is_active = TRUE
ORDER BY ca.customer_id, ca.is_default DESC, ca.id
LIMIT 10;

-- Check orders with address_id
SELECT 
    o.id, o.customer_id, o.address_id, o.status,
    ca.street_name, ca.province
FROM orders o
LEFT JOIN customer_addresses ca ON o.address_id = ca.id
ORDER BY o.id DESC
LIMIT 10;
