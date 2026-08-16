
-- ACCOUNTS SERVICE

CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100),
    email VARCHAR(150) UNIQUE,
    password_hash VARCHAR(255),
    created_at DATETIME
);

CREATE TABLE addresses (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    label VARCHAR(50),
    line1 VARCHAR(200),
    city VARCHAR(100),
    pincode VARCHAR(10),
    FOREIGN KEY (user_id) REFERENCES users(id)
);


-- CATALOGUE SERVICE

CREATE TABLE restaurants (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(150),
    area VARCHAR(100),
    is_active BOOLEAN
);

CREATE TABLE menu_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    restaurant_id INT,
    name VARCHAR(150),
    price DECIMAL(8,2),
    available BOOLEAN,
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
);


-- ORDERS SERVICE


CREATE TABLE carts (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT,
    created_at DATETIME
);

CREATE TABLE cart_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    cart_id INT,
    item_id INT,
    quantity INT,
    FOREIGN KEY (cart_id) REFERENCES carts(id)
);

CREATE TABLE orders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT,
    address_id INT,
    status VARCHAR(30),
    total DECIMAL(8,2),
    created_at DATETIME
);

CREATE TABLE order_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT,
    item_id INT,
    quantity INT,
    price_at_order DECIMAL(8,2),
    FOREIGN KEY (order_id) REFERENCES orders(id)
);


-- PAYMENTS SERVICE

CREATE TABLE transactions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT,
    amount DECIMAL(8,2),
    status VARCHAR(30),
    payment_method VARCHAR(50),
    created_at DATETIME
);


-- DELIVERY SERVICE

CREATE TABLE riders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100),
    phone VARCHAR(15),
    is_available BOOLEAN
);

CREATE TABLE assignments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT,
    rider_id INT,
    status VARCHAR(30),
    assigned_at DATETIME,
    FOREIGN KEY (rider_id) REFERENCES riders(id)
);


-- NOTIFICATIONS SERVICE

CREATE TABLE messages (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT,
    type VARCHAR(50),
    content VARCHAR(500),
    sent_at DATETIME
);