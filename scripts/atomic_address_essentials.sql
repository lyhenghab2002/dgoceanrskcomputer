-- Essential Atomic Address Migration SQL
-- Run these commands in order

-- 1. Add atomic address columns (already done)
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

-- 2. Migrate existing address data (optional)
UPDATE customers 
SET 
    street_name = address,
    province = CASE 
        WHEN address LIKE '%Phnom Penh%' THEN 'Phnom Penh'
        WHEN address LIKE '%Siem Reap%' THEN 'Siem Reap'
        WHEN address LIKE '%Battambang%' THEN 'Battambang'
        ELSE 'Phnom Penh'
    END,
    country = 'Cambodia'
WHERE address IS NOT NULL AND address != '';

-- 3. Verify the migration
SELECT 
    id, first_name, last_name, email,
    house_number, street_name, village, sangkat, commune, khan, province, country
FROM customers 
WHERE street_name IS NOT NULL 
LIMIT 5;
