-- Simple Customer Multiple Addresses System
-- No address types (Home/Office), just multiple addresses per customer

-- Create the customer_addresses table (if it doesn't exist)
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

-- Migrate existing customer atomic address data to customer_addresses table
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
WHERE (house_number IS NOT NULL OR street_name IS NOT NULL OR province IS NOT NULL)
AND NOT EXISTS (
    SELECT 1 FROM customer_addresses ca 
    WHERE ca.customer_id = customers.id
);

-- Ensure only one default address per customer
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

-- Verification queries
SELECT 'Customer Addresses System Created Successfully' as status;

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
