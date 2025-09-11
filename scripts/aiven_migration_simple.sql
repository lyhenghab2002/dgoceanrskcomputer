-- Simple Aiven Migration - Essential Commands Only
-- Run these commands one by one

-- 1. Create customer_addresses table
CREATE TABLE customer_addresses (
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
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

-- 2. Add atomic columns to customers
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

-- 3. Add address_id to orders
ALTER TABLE orders ADD COLUMN address_id INT;
ALTER TABLE orders ADD CONSTRAINT fk_address_id FOREIGN KEY (address_id) REFERENCES customer_addresses(id);

-- 4. Migrate existing data
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
WHERE (house_number IS NOT NULL OR street_name IS NOT NULL OR province IS NOT NULL);

-- 5. Verify migration
SELECT COUNT(*) as total_addresses FROM customer_addresses;
SELECT COUNT(*) as customers_with_addresses FROM customers WHERE street_name IS NOT NULL;
