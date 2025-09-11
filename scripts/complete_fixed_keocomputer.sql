-- Complete fixed SQL file for Aiven MySQL import
-- This adds the primary key disable command at the beginning

-- Disable sql_require_primary_key for this session
SET sql_require_primary_key = 0;

-- Your complete original SQL content follows:
CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    stock INT NOT NULL,
    category_id INT,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

CREATE TABLE categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    description TEXT
);

CREATE TABLE customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(15),
    address TEXT
);

CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT,
    order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(10, 2) NOT NULL,
    status ENUM('Pending', 'Completed', 'Cancelled') DEFAULT 'Pending',
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE suppliers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    contact_person VARCHAR(50),
    phone VARCHAR(15),
    email VARCHAR(100),
    address TEXT
);

CREATE TABLE inventory (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT,
    changes INT NOT NULL,
    change_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

select * from products;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role ENUM('admin', 'staff') DEFAULT 'staff'
);

CREATE TABLE order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT,
    product_id INT,
    quantity INT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

ALTER TABLE users
MODIFY COLUMN role ENUM('super_admin', 'admin', 'staff') DEFAULT 'staff';

INSERT INTO categories (name, description) VALUES ('laptops', 'Category for various types of laptops');
INSERT INTO categories (name, description) VALUES ('Desktops', 'Category for different desktop computers');
INSERT INTO categories (name, description) VALUES ('Accessories', 'Category for computer accessories');
INSERT INTO categories (name, description) VALUES ('Pc Component', 'Category for PC components');
INSERT INTO categories (name, description) VALUES ('Network', 'Category for networking equipment');
INSERT INTO categories (name, description) VALUES ('Gaming', 'Category for gaming-related products');

INSERT INTO products (name, description, price, stock, category_id) VALUES
-- Laptops
('Apple MacBook Air', 'Lightweight and powerful laptop with M1 chip', 999.99, 20, 1),
('Dell Inspiron 15', 'Budget-friendly laptop for everyday use', 649.99, 50, 1),
('HP Spectre x360', 'Premium 2-in-1 convertible laptop', 1299.99, 15, 1),
('Lenovo Yoga 7i', 'Stylish convertible laptop with excellent performance', 899.99, 25, 1),
('Asus VivoBook 15', 'Reliable laptop for home and office use', 749.99, 40, 1),
('Acer Swift 3', 'Compact and lightweight laptop for travelers', 699.99, 30, 1),
('MSI Prestige 14', 'Portable laptop designed for creators', 1199.99, 10, 1),

-- Desktops
('Dell OptiPlex 3090', 'Compact and powerful desktop for businesses', 749.99, 35, 2),
('HP Envy Desktop', 'Stylish desktop for home and office', 999.99, 20, 2),
('Lenovo ThinkCentre M70', 'Reliable desktop with expandable storage', 849.99, 15, 2),
('Apple iMac 24"', 'All-in-one desktop with M1 chip', 1299.99, 10, 2),
('Asus ROG Gaming PC', 'High-performance gaming desktop', 1599.99, 12, 2),
('Acer Aspire TC', 'Affordable desktop for basic tasks', 649.99, 30, 2),
('MSI Trident 3', 'Compact gaming desktop with powerful specs', 1399.99, 8, 2),

-- Accessories
('Logitech Wireless Mouse', 'Compact and ergonomic wireless mouse', 29.99, 100, 3),
('Razer Gaming Mouse', 'High-precision gaming mouse with RGB lighting', 69.99, 50, 3),
('Corsair Mechanical Keyboard', 'Gaming keyboard with customizable keys', 89.99, 40, 3),
('Logitech Webcam C920', 'Full HD webcam for video conferencing', 99.99, 25, 3),
('Samsung Portable SSD T7', 'Fast and secure external storage', 119.99, 30, 3),
('SanDisk Ultra USB 3.0', 'High-speed USB drive with 128GB capacity', 34.99, 80, 3),

-- PC Components
('Intel Core i7 Processor', 'High-performance CPU for demanding tasks', 349.99, 20, 4),
('AMD Ryzen 7 5800X', 'Powerful processor for gaming and multitasking', 399.99, 15, 4),
('NVIDIA GeForce RTX 3060', 'Graphics card for 1080p gaming and VR', 399.99, 10, 4),
('Corsair 16GB DDR4 RAM', 'High-speed memory for desktops', 79.99, 30, 4),
('Samsung 970 EVO SSD', 'Reliable NVMe SSD for fast storage', 149.99, 20, 4),
('Seagate Barracuda 2TB HDD', 'High-capacity hard drive for data storage', 69.99, 40, 4),

-- Network
('TP-Link Archer AX50', 'Wi-Fi 6 router with fast speeds', 129.99, 20, 5),
('Netgear Nighthawk AX12', 'Premium router with advanced features', 499.99, 8, 5),
('Asus RT-AC86U', 'Dual-band router for high-speed internet', 189.99, 15, 5),
('Google Nest WiFi', 'Mesh WiFi system for whole-home coverage', 299.99, 10, 5),
('Ubiquiti UniFi Access Point', 'Enterprise-grade wireless access point', 99.99, 25, 5),
('D-Link Gigabit Switch', 'Reliable 8-port network switch', 59.99, 30, 5),

-- Gaming
('PlayStation 5 Console', 'Next-gen gaming console by Sony', 499.99, 15, 6),
('Xbox Series X', 'High-performance gaming console by Microsoft', 499.99, 10, 6),
('Nintendo Switch OLED Model', 'Hybrid gaming console with vibrant display', 349.99, 20, 6),
('Razer Kraken Headset', 'Gaming headset with surround sound', 79.99, 30, 6),
('Logitech G29 Racing Wheel', 'Steering wheel for realistic racing games', 299.99, 10, 6),
('SteelSeries Arctis 7', 'Wireless gaming headset with clear audio', 149.99, 25, 6),
('Elgato Stream Deck', 'Customizable control panel for streamers', 149.99, 12, 6);

INSERT INTO customers (first_name, last_name, email, phone, address) VALUES
('John', 'Doe', 'john.doe@example.com', '1234567890', '123 Main St, New York, NY 10001'),
('Jane', 'Smith', 'jane.smith@example.com', '0987654321', '456 Elm St, Los Angeles, CA 90001'),
('Michael', 'Brown', 'michael.brown@example.com', '4561237890', '789 Oak St, Chicago, IL 60007'),
('Emily', 'Davis', 'emily.davis@example.com', '3216549870', '159 Pine St, Houston, TX 77001'),
('Robert', 'Johnson', 'robert.johnson@example.com', '9876543210', '753 Maple St, Phoenix, AZ 85001'),
('Linda', 'Wilson', 'linda.wilson@example.com', '6549871230', '951 Birch St, Philadelphia, PA 19019'),
('William', 'Lee', 'william.lee@example.com', '8523697410', '456 Spruce St, San Antonio, TX 78201'),
('Elizabeth', 'Taylor', 'elizabeth.taylor@example.com', '7891234560', '369 Cedar St, San Diego, CA 92101'),
('James', 'White', 'james.white@example.com', '7412589630', '147 Walnut St, Dallas, TX 75201'),
('Patricia', 'Harris', 'patricia.harris@example.com', '9638527410', '258 Willow St, Austin, TX 73301'),
('Mark', 'Hall', 'mark.hall@example.com', '6987452310', '123 Aspen Dr, Seattle, WA 98101'),
('Susan', 'Clark', 'susan.clark@example.com', '1236985470', '456 Oak Ln, Boston, MA 02101'),
('Thomas', 'Lewis', 'thomas.lewis@example.com', '8796541230', '789 Pine Rd, Denver, CO 80201'),
('Mary', 'Martinez', 'mary.martinez@example.com', '5698741230', '951 Cedar Blvd, Miami, FL 33101'),
('David', 'Moore', 'david.moore@example.com', '3698527410', '753 Walnut Ave, Atlanta, GA 30301'),
('Jennifer', 'Anderson', 'jennifer.anderson@example.com', '9871236540', '159 Birch Ct, Minneapolis, MN 55401'),
('Charles', 'King', 'charles.king@example.com', '8527419630', '147 Willow St, Portland, OR 97201'),
('Sarah', 'Young', 'sarah.young@example.com', '2589631470', '258 Elm Dr, Orlando, FL 32801'),
('Steven', 'Wright', 'steven.wright@example.com', '7894561230', '369 Maple Ct, Sacramento, CA 94203'),
('Barbara', 'Scott', 'barbara.scott@example.com', '6541237890', '951 Pine Ln, Las Vegas, NV 89101'),
('Andrew', 'Harris', 'andrew.harris@example.com', '8529637410', '753 Birch Blvd, Tampa, FL 33601'),
('Angela', 'Brown', 'angela.brown@example.com', '7413698520', '456 Cedar Rd, Columbus, OH 43201'),
('Paul', 'Walker', 'paul.walker@example.com', '3691478520', '369 Walnut Dr, Indianapolis, IN 46201'),
('Catherine', 'Adams', 'catherine.adams@example.com', '7898523690', '159 Willow Ct, Charlotte, NC 28201'),
('Daniel', 'Perez', 'daniel.perez@example.com', '8521473690', '753 Oak Ln, Milwaukee, WI 53201'),
('Laura', 'Collins', 'laura.collins@example.com', '9632587410', '456 Maple Blvd, Kansas City, MO 64101'),
('Peter', 'Evans', 'peter.evans@example.com', '1473692580', '123 Cedar Dr, Louisville, KY 40201'),
('Rachel', 'Taylor', 'rachel.taylor@example.com', '3214569870', '789 Birch Ct, Baltimore, MD 21201'),
('Christopher', 'Hill', 'christopher.hill@example.com', '9876542580', '159 Elm Ln, Memphis, TN 38101'),
('Kimberly', 'Campbell', 'kimberly.campbell@example.com', '8523691470', '753 Pine Ave, Omaha, NE 68101'),
('Matthew', 'Howard', 'matthew.howard@example.com', '3698521470', '369 Walnut Ct, Nashville, TN 37201'),
('Karen', 'Carter', 'karen.carter@example.com', '7891234567', '951 Willow Dr, Phoenix, AZ 85001'),
('Jeffrey', 'Ward', 'jeffrey.ward@example.com', '7418529630', '147 Birch Ln, San Francisco, CA 94101'),
('Sophia', 'Reed', 'sophia.reed@example.com', '9631478520', '258 Elm St, St. Louis, MO 63101'),
('Brian', 'Parker', 'brian.parker@example.com', '1234569870', '951 Maple Rd, Cincinnati, OH 45201'),
('Michelle', 'Cook', 'michelle.cook@example.com', '8523697410', '753 Cedar Blvd, New Orleans, LA 70101'),
('Timothy', 'Bell', 'timothy.bell@example.com', '3698521230', '369 Pine Ln, Honolulu, HI 96801'),
('Laura', 'Morgan', 'laura.morgan@example.com', '9632587410', '159 Willow Ct, Salt Lake City, UT 84101'),
('Nathan', 'Mitchell', 'nathan.mitchell@example.com', '8521479630', '147 Oak St, Dallas, TX 75201'),
('Amy', 'Sanchez', 'amy.sanchez@example.com', '7894568520', '258 Walnut Blvd, Austin, TX 73301'),
('Victoria', 'Garcia', 'victoria.garcia@example.com', '4561237890', '456 Cedar Rd, San Antonio, TX 78201'),
('Kevin', 'Ross', 'kevin.ross@example.com', '3216548520', '369 Maple Ct, San Diego, CA 92101'),
('Tiffany', 'Clark', 'tiffany.clark@example.com', '8529631230', '753 Elm Ln, Las Vegas, NV 89101'),
('Eric', 'Thompson', 'eric.thompson@example.com', '1473698520', '159 Birch St, Miami, FL 33101'),
('Stephanie', 'Lopez', 'stephanie.lopez@example.com', '3214569630', '258 Oak Dr, Houston, TX 77001'),
('Thomas', 'Allen', 'thomas.allen@example.com', '9871236547', '951 Spruce Ct, Chicago, IL 60007'),
('Kelly', 'Murphy', 'kelly.murphy@example.com', '8523691470', '123 Pine Ave, Los Angeles, CA 90001'),
('Sean', 'Foster', 'sean.foster@example.com', '9638527410', '753 Cedar Blvd, New York, NY 10001'),
('Megan', 'Long', 'megan.long@example.com', '3697418520', '456 Maple Rd, Seattle, WA 98101');

INSERT INTO orders (customer_id, order_date, total_amount, status) VALUES
(1, '2025-04-01 14:00:00', 299.99, 'Completed'),
(2, '2025-04-02 10:30:00', 499.99, 'Pending'),
(3, '2025-04-03 16:45:00', 129.99, 'Cancelled'),
(4, '2025-04-04 12:15:00', 59.99, 'Completed'),
(5, '2025-04-05 09:00:00', 89.99, 'Completed'),
(6, '2025-04-06 15:40:00', 89.99, 'Pending'),
(7, '2025-04-07 10:20:00', 249.99, 'Completed'),
(8, '2025-04-08 18:10:00', 159.99, 'Cancelled'),
(9, '2025-04-09 09:55:00', 479.99, 'Pending'),
(10, '2025-04-10 14:45:00', 229.99, 'Completed'),
(11, '2025-04-11 12:35:00', 119.99, 'Completed'),
(12, '2025-04-12 17:00:00', 299.99, 'Pending'),
(13, '2025-04-13 10:45:00', 399.99, 'Completed'),
(14, '2025-04-14 13:30:00', 189.99, 'Completed'),
(15, '2025-04-15 16:20:00', 279.99, 'Pending'),
(16, '2025-04-16 11:10:00', 99.99, 'Cancelled'),
(17, '2025-04-17 19:00:00', 359.99, 'Completed'),
(18, '2025-04-18 08:40:00', 459.99, 'Pending'),
(19, '2025-04-19 14:25:00', 159.99, 'Completed'),
(20, '2025-04-20 12:50:00', 109.99, 'Cancelled'),
(21, '2025-04-21 10:10:00', 299.99, 'Completed'),
(22, '2025-04-22 15:30:00', 199.99, 'Pending'),
(23, '2025-04-23 11:00:00', 349.99, 'Cancelled'),
(24, '2025-04-24 13:15:00', 469.99, 'Completed'),
(25, '2025-04-25 14:40:00', 149.99, 'Completed'),
(26, '2025-04-26 18:30:00', 249.99, 'Pending'),
(27, '2025-04-27 09:20:00', 369.99, 'Completed'),
(28, '2025-04-28 15:45:00', 459.99, 'Cancelled'),
(29, '2025-04-29 12:25:00', 159.99, 'Completed'),
(30, '2025-04-30 10:35:00', 199.99, 'Pending'),
(31, '2025-05-01 14:50:00', 279.99, 'Completed'),
(32, '2025-05-02 13:10:00', 89.99, 'Completed'),
(33, '2025-05-03 15:30:00', 479.99, 'Pending'),
(34, '2025-05-04 09:40:00', 139.99, 'Completed'),
(35, '2025-05-05 14:10:00', 229.99, 'Cancelled'),
(36, '2025-05-06 16:15:00', 319.99, 'Completed'),
(37, '2025-05-07 10:20:00', 199.99, 'Pending'),
(38, '2025-05-08 12:45:00', 349.99, 'Completed'),
(39, '2025-05-09 17:30:00', 89.99, 'Cancelled');

select * from orders;

INSERT INTO order_items (order_id, product_id, quantity, price) VALUES
(51, 1, 2, 299.99),  
(52, 3, 1, 59.99),   
(53, 5, 3, 89.99), 
(54, 2, 1, 499.99),  
(55, 6, 1, 199.99),
(113, 9, 2, 319.99),
(114, 10, 3, 99.99),
(115, 11, 1, 199.99),
(116, 12, 2, 229.99),
(117, 13, 3, 399.99),
(118, 14, 1, 119.99),
(119, 15, 4, 89.99),
(120, 16, 1, 289.99),
(121, 17, 2, 179.99),
(122, 18, 1, 329.99),
(123, 19, 2, 499.99),
(124, 20, 1, 139.99),
(125, 21, 1, 249.99),
(126, 22, 3, 99.99),
(127, 23, 2, 199.99),
(128, 24, 1, 149.99),
(129, 25, 1, 359.99),
(130, 26, 2, 89.99),
(131, 27, 1, 199.99),
(132, 28, 3, 139.99),
(133, 29, 1, 459.99),
(134, 30, 1, 299.99);

INSERT INTO inventory (product_id, changes) VALUES
(1, 10),   
(2, 5),    
(3, -2),   
(4, 20),   
(5, -5),   
(6, 15),   
(7, 8),    
(8, -3),   
(9, 12),  
(10, 10),  
(11, -6),  
(12, 9),   
(13, 7),   
(14, -4),  
(15, 20),  
(16, -8),  
(17, 3),   
(18, -1),  
(19, 25),  
(20, -10), 
(21, 5),   
(22, 15),  
(23, -3),  
(24, 18),  
(25, 12),  
(26, -7),  
(27, 10),  
(28, -2), 
(29, 20),  
(30, 9),   
(31, -5),  
(32, 14),  
(33, 6),   
(34, -1), 
(35, 11),  
(36, 3),   
(37, -4),  
(38, 8),   
(39, 17);  

select * from inventory;

INSERT INTO suppliers (name, contact_person, phone, email, address) VALUES
('Tech Solutions Inc.', 'Alice Johnson', '1234567890', 'alice.johnson@techsolutions.com', '123 Main St, New York, NY 10001'),
('Global Electronics', 'John Smith', '0987654321', 'john.smith@globalelectronics.com', '456 Elm St, San Francisco, CA 94101'),
('Smart Components', 'Mary Brown', '4561237890', 'mary.brown@smartcomponents.com', '789 Pine Rd, Chicago, IL 60601'),
('Innovative Supplies', 'David Wilson', '3216549870', 'david.wilson@innovativesupplies.com', '951 Maple Ave, Houston, TX 77002'),
('Future Tech Co.', 'Emma Davis', '6549871230', 'emma.davis@futuretech.com', '753 Cedar Dr, Austin, TX 73301'),
('Pro Hardware', 'Robert Miller', '9876543210', 'robert.miller@prohardware.com', '369 Walnut St, Seattle, WA 98101'),
('Electro World', 'Linda Harris', '8527419630', 'linda.harris@electroworld.com', '159 Birch Ct, Denver, CO 80201'),
('Digital Central', 'James Lee', '7891234560', 'james.lee@digitalcentral.com', '258 Willow Blvd, Orlando, FL 32801'),
('Core Technology', 'Elizabeth White', '9638527410', 'elizabeth.white@coretech.com', '123 Aspen Ln, Miami, FL 33101'),
('NextGen Computing', 'Christopher Moore', '7412589630', 'christopher.moore@nextgencomputing.com', '951 Spruce Ave, Boston, MA 02108'),
('Alpha Systems', 'Sarah Martin', '4567891234', 'sarah.martin@alphasystems.com', '753 Cedar St, Dallas, TX 75201'),
('Peak Performance', 'William Evans', '9634567890', 'william.evans@peakperformance.com', '369 Maple Rd, San Antonio, TX 78201'),
('Prime Parts', 'Karen Turner', '8529637410', 'karen.turner@primeparts.com', '456 Oak Dr, Las Vegas, NV 89101'),
('Quantum Supplies', 'Angela Thomas', '3217894560', 'angela.thomas@quantumsupplies.com', '789 Pine Ct, Portland, OR 97201'),
('E-Tech Wholesale', 'Daniel Garcia', '8521479630', 'daniel.garcia@etechwholesale.com', '147 Willow St, Kansas City, MO 64101'),
('Nova Parts Co.', 'Emily Martinez', '1472583690', 'emily.martinez@novaparts.com', '258 Birch Rd, Philadelphia, PA 19103'),
('Bright Tech', 'Michael Lewis', '9637412580', 'michael.lewis@brighttech.com', '951 Cedar Blvd, Charlotte, NC 28201'),
('Digital Power', 'Patricia Young', '7894561230', 'patricia.young@digitalpower.com', '753 Walnut Dr, Nashville, TN 37201'),
('Infinity Tech', 'Matthew Anderson', '4569638520', 'matthew.anderson@infinitytech.com', '123 Elm Ln, Columbus, OH 43201'),
('Advanced Systems', 'Barbara King', '8523697410', 'barbara.king@advancedsystems.com', '951 Maple Ave, Phoenix, AZ 85001'),
('Elite Electronics', 'Richard Hall', '9631478520', 'richard.hall@eliteelectronics.com', '753 Cedar Blvd, Cincinnati, OH 45201'),
('Smart Innovations', 'Deborah Wright', '3216547890', 'deborah.wright@smartinnovations.com', '369 Oak St, Indianapolis, IN 46201'),
('Eco Tech Supplies', 'Steven Scott', '8529631470', 'steven.scott@ecotechsupplies.com', '951 Pine Dr, Louisville, KY 40201'),
('Reliable Hardware', 'Jessica Hill', '9638521470', 'jessica.hill@reliablehardware.com', '123 Cedar Ln, Milwaukee, WI 53201'),
('Giga Source', 'Jonathan Lopez', '7891236540', 'jonathan.lopez@gigasource.com', '258 Aspen Ct, Baltimore, MD 21201'),
('Vertex Tech', 'Susan Green', '4567893210', 'susan.green@vertextech.com', '753 Elm Rd, Memphis, TN 38101'),
('Metro Components', 'Kevin Perez', '7418529630', 'kevin.perez@metrocomponents.com', '951 Willow Dr, Omaha, NE 68101'),
('Ultra Parts', 'Maria Carter', '8527419630', 'maria.carter@ultraparts.com', '369 Maple Blvd, St. Louis, MO 63101'),
('SmartCore Solutions', 'Charles Ward', '9631478520', 'charles.ward@smartcore.com', '753 Oak Ct, Raleigh, NC 27601'),
('Skyline Technologies', 'Sandra Kelly', '1237894560', 'sandra.kelly@skyline.com', '258 Cedar Blvd, Richmond, VA 23201'),
('Dynamic Electronics', 'Edward Collins', '7896541230', 'edward.collins@dynamicelectronics.com', '951 Elm Dr, Salt Lake City, UT 84101'),
('Global Hardware', 'Dorothy Morgan', '9638527410', 'dorothy.morgan@globalhardware.com', '753 Maple Ct, New Orleans, LA 70112'),
('Tech Distributors', 'Jason Jenkins', '8529637410', 'jason.jenkins@techdistributors.com', '123 Cedar St, Boise, ID 83701'),
('Network Solutions', 'Betty Griffin', '9631478520', 'betty.griffin@networksolutions.com', '258 Willow Blvd, Albuquerque, NM 87101'),
('Pioneer Supplies', 'Scott Reed', '7896541230', 'scott.reed@pioneersupplies.com', '951 Oak Blvd, Honolulu, HI 96801'),
('Everest Components', 'Helen Long', '8529631470', 'helen.long@everestcomponents.com', '753 Elm Dr, Fargo, ND 58102'),
('Bright Horizons', 'Ryan Richardson', '4567891230', 'ryan.richardson@brighthorizons.com', '369 Birch Rd, Anchorage, AK 99501'),
('Optima Tech', 'Karen Bennett', '9638521470', 'karen.bennett@optimatech.com', '147 Willow St, Cheyenne, WY 82001'),
('Summit Systems', 'Gregory Russell', '8523691470', 'gregory.russell@summitsystems.com', '456 Cedar Ln, Jackson, MS 39201'),
('Pro Systems', 'Sharon Diaz', '7891234560', 'sharon.diaz@prosystems.com', '753 Walnut Dr, Columbia, SC 29201'),
('TechSource', 'Larry Fernandez', '3216549870', 'larry.fernandez@techsource.com', '951 Maple Blvd, Charleston, WV 25301'),
('Digital Experts', 'Cynthia Simmons', '9637412580', 'cynthia.simmons@digitalexperts.com', '369 Oak Ln, Little Rock, AR 72201'),
('NextWave Supplies', 'Andrew Foster', '7894561230', 'andrew.foster@nextwave.com', '258 Aspen Dr, Sioux Falls, SD 57101'),
('Vanguard Technologies', 'Rachel Bell', '8529637410', 'rachel.bell@vanguardtech.com', '753 Birch Ave, Des Moines, IA 50301'),
('New Era Electronics', 'Brian Carter', '9631478520', 'brian.carter@newera.com', '951 Willow Blvd, Wilmington, DE 19801'),
('Pinnacle Hardware', 'Theresa Rose', '1237894560', 'theresa.rose@pinnaclehardware.com', '123 Cedar Rd, Montpelier, VT 05601'),
('Asus Electronics', 'Tom Huang', '9876541234', 'tom.huang@asus.com', '123 Innovation Rd, Taipei, Taiwan'),
('MSI Technology', 'Sophia Lin', '4567891230', 'sophia.lin@msi.com', '456 Gaming St, Taipei, Taiwan'),
('Apple Inc.', 'Tim Cook', '8005551234', 'tim.cook@apple.com', '1 Infinite Loop, Cupertino, CA 95014'),
('Lenovo Group', 'Yang Yuanqing', '8521479630', 'yang.yuanqing@lenovo.com', '789 Tech Ave, Beijing, China'),
('Acer Incorporated', 'Jason Chen', '9638527410', 'jason.chen@acer.com', '369 Productivity Ln, Taipei, Taiwan');

select * from products;

INSERT INTO users (username, password, role) VALUES
('lyhenghab', '12345', 'super_admin'),
('heng', '12345', 'admin'),      
('hab', '12345', 'admin'),      
('dalin', '12345', 'staff'),    
('vidtou', '12345', 'staff'),   
('kimla', '12345', 'staff');    

-- Re-enable sql_require_primary_key
SET sql_require_primary_key = 1;
