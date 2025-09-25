-- Create table for tracking payment screenshots and fraud detection
CREATE TABLE IF NOT EXISTS order_screenshots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    image_hash VARCHAR(64) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    verification_score DECIMAL(3,2) DEFAULT 0.00,
    fraud_detected BOOLEAN DEFAULT FALSE,
    fraud_reasons TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_order_id (order_id),
    INDEX idx_image_hash (image_hash),
    INDEX idx_uploaded_at (uploaded_at),
    INDEX idx_verification_score (verification_score),
    
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
