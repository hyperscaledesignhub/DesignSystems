-- Stock Exchange Demo Database Initialization
-- This script creates all required tables for the demo system

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Wallets table  
CREATE TABLE IF NOT EXISTS wallets (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    available_balance DECIMAL(15,2) DEFAULT 100000.00,
    blocked_balance DECIMAL(15,2) DEFAULT 0.00,
    currency VARCHAR(10) DEFAULT 'USD',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('BUY', 'SELL')),
    quantity INTEGER NOT NULL,
    price DECIMAL(15,2) NOT NULL,
    filled_quantity INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'PARTIAL', 'FILLED', 'CANCELLED', 'REJECTED')),
    order_type VARCHAR(20) DEFAULT 'LIMIT' CHECK (order_type IN ('MARKET', 'LIMIT')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Executions/Trades table
CREATE TABLE IF NOT EXISTS executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    buy_order_id UUID REFERENCES orders(id),
    sell_order_id UUID REFERENCES orders(id),
    symbol VARCHAR(20) NOT NULL,
    quantity INTEGER NOT NULL,
    price DECIMAL(15,2) NOT NULL,
    buyer_id INTEGER REFERENCES users(id),
    seller_id INTEGER REFERENCES users(id),
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trade reports table
CREATE TABLE IF NOT EXISTS trade_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    order_id UUID REFERENCES orders(id),
    execution_id UUID REFERENCES executions(id),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity INTEGER NOT NULL,
    price DECIMAL(15,2) NOT NULL,
    total_value DECIMAL(15,2) NOT NULL,
    commission DECIMAL(15,2) DEFAULT 0.00,
    trade_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Transactions table for wallet operations
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('DEPOSIT', 'WITHDRAWAL', 'TRADE_BUY', 'TRADE_SELL', 'BLOCK', 'UNBLOCK')),
    amount DECIMAL(15,2) NOT NULL,
    reference_id UUID, -- Can reference order_id or execution_id
    description TEXT,
    balance_after DECIMAL(15,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);

CREATE INDEX IF NOT EXISTS idx_executions_symbol ON executions(symbol);
CREATE INDEX IF NOT EXISTS idx_executions_executed_at ON executions(executed_at);

CREATE INDEX IF NOT EXISTS idx_trade_reports_user_id ON trade_reports(user_id);
CREATE INDEX IF NOT EXISTS idx_trade_reports_trade_date ON trade_reports(trade_date);

CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(transaction_type);

-- Insert demo data
INSERT INTO users (username, email, password_hash) VALUES 
    ('buyer_demo', 'buyer@demo.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj2/FgrApJ8e'),
    ('seller_demo', 'seller@demo.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj2/FgrApJ8e')
ON CONFLICT (username) DO NOTHING;

-- Create wallets for demo users
INSERT INTO wallets (user_id, available_balance, blocked_balance) 
SELECT id, 100000.00, 0.00 FROM users WHERE username IN ('buyer_demo', 'seller_demo')
ON CONFLICT DO NOTHING;

-- Insert initial balance transactions
INSERT INTO transactions (user_id, transaction_type, amount, description, balance_after)
SELECT id, 'DEPOSIT', 100000.00, 'Initial demo balance', 100000.00 
FROM users WHERE username IN ('buyer_demo', 'seller_demo')
ON CONFLICT DO NOTHING;