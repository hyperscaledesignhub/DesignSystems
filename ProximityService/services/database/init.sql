CREATE DATABASE proximity_db;

\c proximity_db;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE businesses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    address VARCHAR(500),
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    category VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE geohash_index (
    geohash VARCHAR(12) NOT NULL,
    business_id UUID NOT NULL,
    PRIMARY KEY (geohash, business_id),
    FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE
);

CREATE INDEX idx_geohash ON geohash_index(geohash);
CREATE INDEX idx_business_location ON businesses(latitude, longitude);
CREATE INDEX idx_business_category ON businesses(category);

INSERT INTO businesses (name, latitude, longitude, address, city, state, country, category) VALUES
('Golden Gate Pizza', 37.7749, -122.4194, '123 Market St', 'San Francisco', 'CA', 'USA', 'Restaurant'),
('Bay Area Coffee', 37.7751, -122.4180, '456 Powell St', 'San Francisco', 'CA', 'USA', 'Cafe'),
('SF Tech Store', 37.7745, -122.4189, '789 Mission St', 'San Francisco', 'CA', 'USA', 'Electronics'),
('Union Square Hotel', 37.7879, -122.4074, '321 Geary St', 'San Francisco', 'CA', 'USA', 'Hotel'),
('Fishermans Wharf Restaurant', 37.8080, -122.4177, '555 Beach St', 'San Francisco', 'CA', 'USA', 'Restaurant');

INSERT INTO geohash_index (geohash, business_id)
SELECT 
    substring(md5(random()::text), 1, 4) AS geohash,
    id
FROM businesses;

INSERT INTO geohash_index (geohash, business_id)
SELECT 
    substring(md5(random()::text), 1, 5) AS geohash,
    id
FROM businesses;

INSERT INTO geohash_index (geohash, business_id)
SELECT 
    substring(md5(random()::text), 1, 6) AS geohash,
    id
FROM businesses;