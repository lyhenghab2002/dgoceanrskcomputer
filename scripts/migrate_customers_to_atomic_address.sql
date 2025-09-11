-- Migration script to break down customers.address into atomic components
-- and remove dependency on customer_addresses table

-- Step 1: Add atomic address columns to customers table
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

-- Step 2: Migrate existing address data from customer_addresses to customers
-- This will use the most recent address for each customer
UPDATE customers c
JOIN (
    SELECT 
        customer_id,
        house_number,
        street_name,
        street_number,
        village,
        sangkat,
        commune,
        khan,
        province,
        postal_code,
        country,
        building_name,
        floor_number,
        unit_number,
        landmark,
        delivery_notes
    FROM customer_addresses 
    WHERE is_active = TRUE
    AND (customer_id, id) IN (
        SELECT customer_id, MAX(id) 
        FROM customer_addresses 
        WHERE is_active = TRUE 
        GROUP BY customer_id
    )
) ca ON c.id = ca.customer_id
SET 
    c.house_number = ca.house_number,
    c.street_name = ca.street_name,
    c.street_number = ca.street_number,
    c.village = ca.village,
    c.sangkat = ca.sangkat,
    c.commune = ca.commune,
    c.khan = ca.khan,
    c.province = ca.province,
    c.postal_code = ca.postal_code,
    c.country = ca.country,
    c.building_name = ca.building_name,
    c.floor_number = ca.floor_number,
    c.unit_number = ca.unit_number,
    c.landmark = ca.landmark,
    c.delivery_notes = ca.delivery_notes;

-- Step 3: Remove the old address column
ALTER TABLE customers DROP COLUMN address;

-- Step 4: Update orders table to remove address_id foreign key
-- (We'll keep the column but remove the foreign key constraint)
ALTER TABLE orders DROP FOREIGN KEY orders_ibfk_2;

-- Step 5: Update the invoice query to use customers table directly
-- (This will be done in the application code)
