-- Create databases for each service
CREATE DATABASE user_service;
CREATE DATABASE wallet_service;
CREATE DATABASE transaction_service;
CREATE DATABASE state_service;

-- Create users (optional, using default postgres user for simplicity)
-- CREATE USER user_service_user WITH PASSWORD 'password';
-- GRANT ALL PRIVILEGES ON DATABASE user_service TO user_service_user;

-- CREATE USER wallet_service_user WITH PASSWORD 'password';
-- GRANT ALL PRIVILEGES ON DATABASE wallet_service TO wallet_service_user;

-- CREATE USER transaction_service_user WITH PASSWORD 'password';
-- GRANT ALL PRIVILEGES ON DATABASE transaction_service TO transaction_service_user;

-- CREATE USER state_service_user WITH PASSWORD 'password';
-- GRANT ALL PRIVILEGES ON DATABASE state_service TO state_service_user;