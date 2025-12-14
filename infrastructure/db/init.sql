-- IoT Network Database Initialization Script
-- ==========================================

-- Create extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    wallet_address VARCHAR(42),
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Devices table
CREATE TABLE IF NOT EXISTS devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(100) UNIQUE NOT NULL,
    device_type VARCHAR(50) NOT NULL,
    owner_address VARCHAR(42),
    status VARCHAR(20) DEFAULT 'PENDING',
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    total_bytes BIGINT DEFAULT 0,
    quality_score INTEGER DEFAULT 100,
    signature VARCHAR(255),
    hashed_signature VARCHAR(255),
    location_lat DOUBLE PRECISION,
    location_lng DOUBLE PRECISION,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Network usage table
CREATE TABLE IF NOT EXISTS network_usage (
    usage_id VARCHAR(100) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    device_id VARCHAR(100) REFERENCES devices(device_id) ON DELETE CASCADE,
    bytes_transmitted BIGINT NOT NULL DEFAULT 0,
    bytes_received BIGINT DEFAULT 0,
    connection_quality INTEGER DEFAULT 100,
    user_sessions INTEGER DEFAULT 0,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    compensated BOOLEAN DEFAULT FALSE,
    metadata JSONB
);

-- Compensation Transactions table (Replacing Earnings)
CREATE TABLE IF NOT EXISTS compensation_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id VARCHAR(100) REFERENCES devices(device_id) ON DELETE CASCADE,
    owner_address VARCHAR(42),
    usage_period_start TIMESTAMP WITH TIME ZONE,
    usage_period_end TIMESTAMP WITH TIME ZONE,
    total_bytes BIGINT,
    average_quality DOUBLE PRECISION,
    reward_amount DOUBLE PRECISION,
    blockchain_tx_hash VARCHAR(66) UNIQUE,
    status VARCHAR(20) DEFAULT 'PENDING',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_devices_user_id ON devices(user_id);
CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
CREATE INDEX IF NOT EXISTS idx_network_usage_device_id ON network_usage(device_id);
CREATE INDEX IF NOT EXISTS idx_network_usage_timestamp ON network_usage(timestamp);
CREATE INDEX IF NOT EXISTS idx_compensation_transactions_owner ON compensation_transactions(owner_address);
CREATE INDEX IF NOT EXISTS idx_compensation_transactions_created_at ON compensation_transactions(created_at);

-- Insert default admin user (password: admin123)
INSERT INTO users (username, email, hashed_password, full_name, is_superuser, role)
VALUES (
    'admin',
    'admin@iot-network.local',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOu.xNCjq5X7tM.YVHc.p3aFk.qCNVqYe',
    'Administrator',
    TRUE,
    'admin'
) ON CONFLICT (username) DO NOTHING;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO iot_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO iot_user;
