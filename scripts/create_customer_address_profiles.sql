-- Create Customer Address Profiles Table
-- This allows customers to save multiple addresses and select from dropdown

-- Create the customer_address_profiles table
CREATE TABLE IF NOT EXISTS customer_address_profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    profile_name VARCHAR(100) NOT NULL, -- e.g., "Home", "Work", "Office"
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

-- Migrate existing customer addresses from customer_addresses table (if it exists)
INSERT INTO customer_address_profiles (
    customer_id, profile_name, house_number, street_name, street_number,
    village, sangkat, commune, khan, province, postal_code, country,
    building_name, floor_number, unit_number, landmark, delivery_notes,
    is_default, is_active
)
SELECT 
    customer_id,
    CASE 
        WHEN is_default = 1 THEN 'Home'
        ELSE CONCAT('Address ', ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY id))
    END as profile_name,
    house_number, street_name, street_number,
    village, sangkat, commune, khan, province, postal_code, country,
    building_name, floor_number, unit_number, landmark, delivery_notes,
    is_default, is_active
FROM customer_addresses 
WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'customer_addresses');

-- Also migrate from customers table atomic fields as a default address
INSERT INTO customer_address_profiles (
    customer_id, profile_name, house_number, street_name, street_number,
    village, sangkat, commune, khan, province, postal_code, country,
    building_name, floor_number, unit_number, landmark, delivery_notes,
    is_default, is_active
)
SELECT 
    id as customer_id,
    'Home' as profile_name,
    house_number, street_name, street_number,
    village, sangkat, commune, khan, province, postal_code, country,
    building_name, floor_number, unit_number, landmark, delivery_notes,
    TRUE as is_default,
    TRUE as is_active
FROM customers 
WHERE (house_number IS NOT NULL OR street_name IS NOT NULL OR province IS NOT NULL)
AND NOT EXISTS (
    SELECT 1 FROM customer_address_profiles cap 
    WHERE cap.customer_id = customers.id
);

-- Ensure only one default address per customer
UPDATE customer_address_profiles cap1
SET is_default = FALSE
WHERE cap1.id NOT IN (
    SELECT * FROM (
        SELECT MIN(id) 
        FROM customer_address_profiles cap2 
        WHERE cap2.customer_id = cap1.customer_id 
        AND cap2.is_active = TRUE
        GROUP BY customer_id
    ) as subquery
);

-- Verification queries
SELECT 'Address Profiles Created Successfully' as status;

-- Check how many profiles each customer has
SELECT 
    c.first_name, c.last_name, c.email,
    COUNT(cap.id) as address_count,
    SUM(CASE WHEN cap.is_default = TRUE THEN 1 ELSE 0 END) as default_count
FROM customers c
LEFT JOIN customer_address_profiles cap ON c.id = cap.customer_id AND cap.is_active = TRUE
GROUP BY c.id, c.first_name, c.last_name, c.email
ORDER BY address_count DESC;

-- Sample address profiles
SELECT 
    cap.id, cap.customer_id, cap.profile_name, cap.street_name, cap.province, cap.is_default
FROM customer_address_profiles cap
WHERE cap.is_active = TRUE
ORDER BY cap.customer_id, cap.is_default DESC, cap.id
LIMIT 10;
