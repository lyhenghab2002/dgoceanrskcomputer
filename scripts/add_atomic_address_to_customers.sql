-- Add atomic address columns to customers table
-- This is a simpler approach that adds the columns without migrating existing data

ALTER TABLE customers 
ADD COLUMN house_number VARCHAR(50) AFTER address,
ADD COLUMN street_name VARCHAR(100) AFTER house_number,
ADD COLUMN street_number VARCHAR(50) AFTER street_name,
ADD COLUMN village VARCHAR(100) AFTER street_number,
ADD COLUMN sangkat VARCHAR(100) AFTER village,
ADD COLUMN commune VARCHAR(100) AFTER sangkat,
ADD COLUMN khan VARCHAR(100) AFTER commune,
ADD COLUMN province VARCHAR(100) AFTER khan,
ADD COLUMN postal_code VARCHAR(20) AFTER province,
ADD COLUMN country VARCHAR(50) DEFAULT 'Cambodia' AFTER postal_code,
ADD COLUMN building_name VARCHAR(100) AFTER country,
ADD COLUMN floor_number VARCHAR(20) AFTER building_name,
ADD COLUMN unit_number VARCHAR(20) AFTER floor_number,
ADD COLUMN landmark VARCHAR(100) AFTER unit_number,
ADD COLUMN delivery_notes TEXT AFTER landmark;
