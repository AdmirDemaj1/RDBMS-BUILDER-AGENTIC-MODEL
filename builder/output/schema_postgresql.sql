-- ============================================================
-- RDBMS Schema - Production Ready
-- Dialect: PostgreSQL
-- Generated with optimization, security, and best practices
-- ============================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Function for auto-updating updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- ============================================================
-- TABLES
-- ============================================================

-- Business entities
-- ⚠️  PII columns: contact_email, contact_phone - Consider encryption
CREATE TABLE companies (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    deleted_at TIMESTAMPTZ,
    name VARCHAR(255)(255) NOT NULL,
    address VARCHAR(500)(500) NOT NULL,
    contact_email VARCHAR(255)(255) NOT NULL,
    contact_phone VARCHAR(20)(20) NOT NULL,
    registration_number VARCHAR(50)(50) NOT NULL
);

-- Vehicle categories
CREATE TABLE vehicle_types (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    deleted_at TIMESTAMPTZ,
    type_name VARCHAR(100)(100) NOT NULL,
    description VARCHAR(500)(500),
    fuel_capacity DECIMAL(10,2)(10,2),
    max_weight DECIMAL(10,2)(10,2)
);

-- Fleet vehicles
CREATE TABLE vehicles (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    deleted_at TIMESTAMPTZ,
    company_id UUID NOT NULL,
    vehicle_type_id UUID NOT NULL,
    make VARCHAR(100)(100) NOT NULL,
    model VARCHAR(100)(100) NOT NULL,
    year VARCHAR(4)(4) NOT NULL,
    license_plate VARCHAR(20)(20) NOT NULL UNIQUE,
    vin VARCHAR(17)(17) NOT NULL UNIQUE,
    current_mileage DECIMAL(10,2)(10,2) NOT NULL,
    CONSTRAINT fk_vehicles_company_id FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_vehicles_vehicle_type_id FOREIGN KEY (vehicle_type_id) REFERENCES vehicle_types(id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Vehicle drivers
-- ⚠️  PII columns: first_name, last_name, license_number, contact_phone, email - Consider encryption
CREATE TABLE drivers (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    deleted_at TIMESTAMPTZ,
    company_id UUID NOT NULL,
    vehicle_id UUID,
    first_name VARCHAR(100)(100) NOT NULL,
    last_name VARCHAR(100)(100) NOT NULL,
    license_number VARCHAR(50)(50) NOT NULL UNIQUE,
    license_expiry_date TIMESTAMPTZ NOT NULL,
    contact_phone VARCHAR(20)(20) NOT NULL,
    email VARCHAR(255)(255) NOT NULL,
    CONSTRAINT fk_drivers_company_id FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_drivers_vehicle_id FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Company managers
-- ⚠️  PII columns: first_name, last_name, email - Consider encryption
CREATE TABLE managers (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    deleted_at TIMESTAMPTZ,
    company_id UUID NOT NULL,
    first_name VARCHAR(100)(100) NOT NULL,
    last_name VARCHAR(100)(100) NOT NULL,
    email VARCHAR(255)(255) NOT NULL,
    access_level VARCHAR(50)(50) NOT NULL,
    department VARCHAR(100)(100) NOT NULL,
    CONSTRAINT fk_managers_company_id FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Vehicle maintenance records
CREATE TABLE maintenance_logs (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    deleted_at TIMESTAMPTZ,
    vehicle_id UUID NOT NULL,
    maintenance_date TIMESTAMPTZ NOT NULL,
    description VARCHAR(1000)(1000) NOT NULL,
    cost DECIMAL(10,2)(10,2) NOT NULL,
    service_provider VARCHAR(255)(255) NOT NULL,
    mileage_at_service DECIMAL(10,2)(10,2) NOT NULL,
    next_service_due DECIMAL(10,2)(10,2),
    CONSTRAINT fk_maintenance_logs_vehicle_id FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Vehicle fuel records
CREATE TABLE fuel_logs (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    deleted_at TIMESTAMPTZ,
    vehicle_id UUID NOT NULL,
    fuel_date TIMESTAMPTZ NOT NULL,
    amount DECIMAL(10,2)(10,2) NOT NULL,
    cost DECIMAL(10,2)(10,2) NOT NULL,
    fuel_type VARCHAR(50)(50) NOT NULL,
    location VARCHAR(255)(255) NOT NULL,
    mileage_at_fueling DECIMAL(10,2)(10,2) NOT NULL,
    CONSTRAINT fk_fuel_logs_vehicle_id FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Vehicle location data
CREATE TABLE location_trackings (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    deleted_at TIMESTAMPTZ,
    vehicle_id UUID NOT NULL,
    latitude DECIMAL(10,8)(10,8) NOT NULL,
    longitude DECIMAL(11,8)(11,8) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    speed DECIMAL(6,2)(6,2),
    heading DECIMAL(5,2)(5,2),
    accuracy DECIMAL(8,2)(8,2),
    CONSTRAINT fk_location_trackings_vehicle_id FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- ============================================================
-- INDEXES (Critical for query performance)
-- ============================================================

-- Indexes for vehicles
CREATE INDEX idx_vehicles_company_id ON vehicles (company_id);
CREATE INDEX idx_vehicles_vehicle_type_id ON vehicles (vehicle_type_id);

-- Indexes for drivers
CREATE INDEX idx_drivers_company_id ON drivers (company_id);
CREATE INDEX idx_drivers_vehicle_id ON drivers (vehicle_id);

-- Indexes for managers
CREATE INDEX idx_managers_company_id ON managers (company_id);

-- Indexes for maintenance_logs
CREATE INDEX idx_maintenance_logs_vehicle_id ON maintenance_logs (vehicle_id);

-- Indexes for fuel_logs
CREATE INDEX idx_fuel_logs_vehicle_id ON fuel_logs (vehicle_id);

-- Indexes for location_trackings
CREATE INDEX idx_location_trackings_vehicle_id ON location_trackings (vehicle_id);

-- ============================================================
-- TRIGGERS (Auto-update timestamps)
-- ============================================================

-- Auto-update updated_at trigger for companies
CREATE TRIGGER trg_companies_updated_at
    BEFORE UPDATE ON companies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for vehicle_types
CREATE TRIGGER trg_vehicle_types_updated_at
    BEFORE UPDATE ON vehicle_types
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for vehicles
CREATE TRIGGER trg_vehicles_updated_at
    BEFORE UPDATE ON vehicles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for drivers
CREATE TRIGGER trg_drivers_updated_at
    BEFORE UPDATE ON drivers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for managers
CREATE TRIGGER trg_managers_updated_at
    BEFORE UPDATE ON managers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for maintenance_logs
CREATE TRIGGER trg_maintenance_logs_updated_at
    BEFORE UPDATE ON maintenance_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for fuel_logs
CREATE TRIGGER trg_fuel_logs_updated_at
    BEFORE UPDATE ON fuel_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for location_trackings
CREATE TRIGGER trg_location_trackings_updated_at
    BEFORE UPDATE ON location_trackings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
