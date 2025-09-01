-- Initialize databases for all services

-- Create databases
CREATE DATABASE guest_db;
CREATE DATABASE inventory_db;
CREATE DATABASE reservation_db;
CREATE DATABASE payment_db;

-- Hotel Service Tables (in hotel_db)
\c hotel_db;

CREATE TABLE IF NOT EXISTS hotels (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address TEXT,
    city VARCHAR(100),
    country VARCHAR(100),
    phone VARCHAR(50),
    email VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS room_types (
    id VARCHAR(36) PRIMARY KEY,
    hotel_id VARCHAR(36) REFERENCES hotels(id),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    base_price DECIMAL(10, 2),
    max_occupancy INTEGER,
    total_rooms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Guest Service Tables
\c guest_db;

CREATE TABLE IF NOT EXISTS guests (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inventory Service Tables
\c inventory_db;

CREATE TABLE IF NOT EXISTS room_inventory (
    id SERIAL PRIMARY KEY,
    hotel_id VARCHAR(36) NOT NULL,
    room_type_id VARCHAR(36) NOT NULL,
    date DATE NOT NULL,
    total_inventory INTEGER NOT NULL,
    total_reserved INTEGER DEFAULT 0,
    price DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(hotel_id, room_type_id, date)
);

-- Reservation Service Tables
\c reservation_db;

CREATE TABLE IF NOT EXISTS reservations (
    id VARCHAR(36) PRIMARY KEY,
    guest_id VARCHAR(36) NOT NULL,
    hotel_id VARCHAR(36) NOT NULL,
    room_type_id VARCHAR(36) NOT NULL,
    check_in_date DATE NOT NULL,
    check_out_date DATE NOT NULL,
    num_rooms INTEGER DEFAULT 1,
    total_amount DECIMAL(10, 2),
    status VARCHAR(50) DEFAULT 'confirmed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Payment Service Tables
\c payment_db;

CREATE TABLE IF NOT EXISTS payments (
    id VARCHAR(36) PRIMARY KEY,
    reservation_id VARCHAR(36) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    payment_method VARCHAR(50),
    status VARCHAR(50) DEFAULT 'pending',
    processed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);