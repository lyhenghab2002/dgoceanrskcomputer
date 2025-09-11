-- Add address_id column to orders table to store selected address
ALTER TABLE orders ADD COLUMN address_id INT NULL;
ALTER TABLE orders ADD FOREIGN KEY (address_id) REFERENCES customer_addresses(id) ON DELETE SET NULL;
