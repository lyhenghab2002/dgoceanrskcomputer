-- Migration script to add delivery status to orders table
-- This enables tracking of physical delivery/pickup status for orders
-- Works with existing shipping_method field (delivery/pickup)

-- Add delivery_status column to orders table
ALTER TABLE orders 
ADD COLUMN delivery_status ENUM('Pending', 'Ready for Pickup', 'Out for Delivery', 'Delivered', 'Picked Up', 'Delivery Failed', 'Returned to Store') 
DEFAULT 'Pending' 
AFTER approval_status;

-- Add delivery_date column to track when delivery/pickup occurred
ALTER TABLE orders 
ADD COLUMN delivery_date DATETIME NULL 
AFTER delivery_status;

-- Add delivered_by column to track who handled the delivery/pickup
ALTER TABLE orders 
ADD COLUMN delivered_by INT NULL 
AFTER delivery_date;

-- Add delivery_notes column for delivery instructions or issues
ALTER TABLE orders 
ADD COLUMN delivery_notes TEXT NULL 
AFTER delivered_by;

-- Add foreign key constraint for delivered_by to reference users table
ALTER TABLE orders 
ADD CONSTRAINT fk_orders_delivered_by 
FOREIGN KEY (delivered_by) REFERENCES users(id) 
ON DELETE SET NULL;

-- Add indexes for better query performance
CREATE INDEX idx_orders_delivery_status ON orders(delivery_status);
CREATE INDEX idx_orders_delivery_date ON orders(delivery_date);

-- Update existing completed orders to be marked as delivered/picked up
-- (This maintains backward compatibility for existing orders)
UPDATE orders 
SET delivery_status = 'Delivered', 
    delivery_date = order_date
WHERE status = 'Completed' 
AND delivery_status = 'Pending';

-- Add comments to document the new columns
ALTER TABLE orders 
MODIFY COLUMN delivery_status ENUM('Pending', 'Ready for Pickup', 'Out for Delivery', 'Delivered', 'Picked Up', 'Delivery Failed', 'Returned to Store') 
DEFAULT 'Pending' 
COMMENT 'Physical delivery/pickup status for order fulfillment',
MODIFY COLUMN delivery_date DATETIME NULL 
COMMENT 'Date when order was delivered or picked up',
MODIFY COLUMN delivered_by INT NULL 
COMMENT 'User ID of staff member who handled delivery/pickup',
MODIFY COLUMN delivery_notes TEXT NULL 
COMMENT 'Notes about delivery process, issues, or special instructions';
