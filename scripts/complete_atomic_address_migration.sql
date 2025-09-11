-- Complete Atomic Address Migration Script
-- This script migrates from the old 'address' TEXT column to atomic address components

-- Step 1: Add atomic address columns to customers table
-- (These columns have already been added, but included for reference)

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

-- Step 2: Optional - Migrate existing address data to atomic fields
-- This is a basic migration that tries to parse the old 'address' column
-- You may need to adjust the parsing logic based on your data format

UPDATE customers 
SET 
    street_name = CASE 
        WHEN address IS NOT NULL AND address != '' THEN address
        ELSE NULL
    END,
    province = CASE 
        WHEN address LIKE '%Phnom Penh%' THEN 'Phnom Penh'
        WHEN address LIKE '%Siem Reap%' THEN 'Siem Reap'
        WHEN address LIKE '%Battambang%' THEN 'Battambang'
        WHEN address LIKE '%Kampong Cham%' THEN 'Kampong Cham'
        WHEN address LIKE '%Kampong Thom%' THEN 'Kampong Thom'
        WHEN address LIKE '%Kampong Speu%' THEN 'Kampong Speu'
        WHEN address LIKE '%Kampong Chhnang%' THEN 'Kampong Chhnang'
        WHEN address LIKE '%Kampong Som%' THEN 'Kampong Som'
        WHEN address LIKE '%Kampot%' THEN 'Kampot'
        WHEN address LIKE '%Kandal%' THEN 'Kandal'
        WHEN address LIKE '%Koh Kong%' THEN 'Koh Kong'
        WHEN address LIKE '%Kratie%' THEN 'Kratie'
        WHEN address LIKE '%Mondulkiri%' THEN 'Mondulkiri'
        WHEN address LIKE '%Oddar Meanchey%' THEN 'Oddar Meanchey'
        WHEN address LIKE '%Pailin%' THEN 'Pailin'
        WHEN address LIKE '%Preah Vihear%' THEN 'Preah Vihear'
        WHEN address LIKE '%Prey Veng%' THEN 'Prey Veng'
        WHEN address LIKE '%Pursat%' THEN 'Pursat'
        WHEN address LIKE '%Ratanakiri%' THEN 'Ratanakiri'
        WHEN address LIKE '%Stung Treng%' THEN 'Stung Treng'
        WHEN address LIKE '%Svay Rieng%' THEN 'Svay Rieng'
        WHEN address LIKE '%Takeo%' THEN 'Takeo'
        WHEN address LIKE '%Tboung Khmum%' THEN 'Tboung Khmum'
        ELSE NULL
    END,
    country = 'Cambodia'
WHERE address IS NOT NULL AND address != '';

-- Step 3: Optional - Remove the old address column (ONLY after confirming everything works)
-- WARNING: This will permanently delete the old address data
-- Uncomment the line below ONLY after you've verified the migration worked correctly

-- ALTER TABLE customers DROP COLUMN address;

-- Step 4: Optional - Remove the customer_addresses table (ONLY after confirming everything works)
-- WARNING: This will permanently delete all address data in the customer_addresses table
-- Uncomment the lines below ONLY after you've verified the migration worked correctly

-- DROP TABLE IF EXISTS customer_addresses;

-- Step 5: Optional - Remove the address_id column from orders table (ONLY after confirming everything works)
-- WARNING: This will permanently delete the address_id foreign key
-- Uncomment the lines below ONLY after you've verified the migration worked correctly

-- ALTER TABLE orders DROP FOREIGN KEY fk_address_id;
-- ALTER TABLE orders DROP COLUMN address_id;

-- Verification queries
-- Run these to check the migration results:

-- Check the new table structure
DESCRIBE customers;

-- Check how many customers have atomic address data
SELECT 
    COUNT(*) as total_customers,
    COUNT(house_number) as has_house_number,
    COUNT(street_name) as has_street_name,
    COUNT(province) as has_province,
    COUNT(country) as has_country
FROM customers;

-- Sample of migrated data
SELECT 
    id, first_name, last_name, email,
    house_number, street_name, village, sangkat, commune, khan, province, country
FROM customers 
WHERE street_name IS NOT NULL 
LIMIT 5;
