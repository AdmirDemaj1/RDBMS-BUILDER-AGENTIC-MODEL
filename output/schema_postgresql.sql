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

-- Stores company account data
-- ⚠️  PII columns: address, contact_email, contact_phone - Consider encryption
CREATE TABLE companies (
    id UUID PRIMARY KEY,
    name VARCHAR(255)(255) NOT NULL,
    address TEXT,
    contact_email VARCHAR(255)(255),
    contact_phone VARCHAR(20)(20),
    registration_number VARCHAR(50)(50) UNIQUE,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

-- Defines vehicle type categories
CREATE TABLE vehicle_types (
    id UUID PRIMARY KEY,
    type_name VARCHAR(100)(100) NOT NULL UNIQUE,
    description TEXT,
    fuel_capacity DECIMAL(8,2)(8,2),
    max_load_capacity DECIMAL(10,2)(10,2),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

-- Stores fleet vehicle information
CREATE TABLE vehicles (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL,
    vehicle_type_id UUID NOT NULL,
    make VARCHAR(100)(100) NOT NULL,
    model VARCHAR(100)(100) NOT NULL,
    year INTEGER NOT NULL CHECK (year >= 1900 AND year <= EXTRACT(YEAR FROM CURRENT_DATE) + 1),
    license_plate VARCHAR(20)(20) NOT NULL UNIQUE,
    vin VARCHAR(17)(17) UNIQUE,
    current_mileage DECIMAL(10,2)(10,2) NOT NULL CHECK (current_mileage >= 0),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT fk_vehicles_company_id FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_vehicles_vehicle_type_id FOREIGN KEY (vehicle_type_id) REFERENCES vehicle_types(id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Stores driver profile data
-- ⚠️  PII columns: first_name, last_name, license_number, contact_phone, email - Consider encryption
CREATE TABLE drivers (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL,
    vehicle_id UUID UNIQUE,
    first_name VARCHAR(100)(100) NOT NULL,
    last_name VARCHAR(100)(100) NOT NULL,
    license_number VARCHAR(50)(50) NOT NULL UNIQUE,
    license_expiry_date DATE NOT NULL,
    contact_phone VARCHAR(20)(20),
    email VARCHAR(255)(255),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT fk_drivers_company_id FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_drivers_vehicle_id FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE SET NULL ON UPDATE CASCADE
);

-- Stores manager account data
-- ⚠️  PII columns: first_name, last_name, email - Consider encryption
CREATE TABLE managers (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL,
    first_name VARCHAR(100)(100) NOT NULL,
    last_name VARCHAR(100)(100) NOT NULL,
    email VARCHAR(255)(255) NOT NULL UNIQUE,
    access_level VARCHAR(20)(20) NOT NULL CHECK (access_level IN ('admin', 'manager', 'viewer')),
    department VARCHAR(100)(100),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT fk_managers_company_id FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- Tracks vehicle maintenance records
CREATE TABLE maintenance_logs (
    id UUID PRIMARY KEY,
    vehicle_id UUID NOT NULL,
    maintenance_date DATE NOT NULL,
    description TEXT NOT NULL,
    cost DECIMAL(12,2)(12,2) NOT NULL CHECK (cost >= 0),
    service_provider VARCHAR(255)(255),
    mileage_at_service DECIMAL(10,2)(10,2) NOT NULL CHECK (mileage_at_service >= 0),
    next_service_due DECIMAL(10,2)(10,2) CHECK (next_service_due >= mileage_at_service),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT fk_maintenance_logs_vehicle_id FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- Tracks vehicle fuel records
CREATE TABLE fuel_logs (
    id UUID PRIMARY KEY,
    vehicle_id UUID NOT NULL,
    fuel_date DATE NOT NULL,
    amount DECIMAL(8,2)(8,2) NOT NULL CHECK (amount > 0),
    cost DECIMAL(12,2)(12,2) NOT NULL CHECK (cost > 0),
    price_per_unit DECIMAL(8,4)(8,4) NOT NULL CHECK (price_per_unit > 0),
    location VARCHAR(255)(255),
    mileage_at_fueling DECIMAL(10,2)(10,2) NOT NULL CHECK (mileage_at_fueling >= 0),
    fuel_type VARCHAR(50)(50) NOT NULL CHECK (fuel_type IN ('gasoline', 'diesel', 'electric', 'hybrid', 'cng', 'lpg')),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT fk_fuel_logs_vehicle_id FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- Stores vehicle GPS tracking
CREATE TABLE location_trackings (
    id UUID PRIMARY KEY,
    vehicle_id UUID NOT NULL,
    latitude DECIMAL(10,8)(10,8) NOT NULL CHECK (latitude >= -90 AND latitude <= 90),
    longitude DECIMAL(11,8)(11,8) NOT NULL CHECK (longitude >= -180 AND longitude <= 180),
    timestamp TIMESTAMPTZ NOT NULL,
    speed DECIMAL(6,2)(6,2) CHECK (speed >= 0),
    heading DECIMAL(5,2)(5,2) CHECK (heading >= 0 AND heading < 360),
    accuracy DECIMAL(8,2)(8,2) CHECK (accuracy >= 0),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT fk_location_trackings_vehicle_id FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- ============================================================
-- INDEXES (Critical for query performance)
-- ============================================================

-- Indexes for companies
CREATE UNIQUE INDEX idx_companies_registration_number ON companies (registration_number);
CREATE INDEX idx_companies_contact_email ON companies (contact_email);

-- Indexes for vehicle_types
CREATE UNIQUE INDEX idx_vehicle_types_type_name ON vehicle_types (type_name);

-- Indexes for vehicles
CREATE INDEX idx_vehicles_company_id ON vehicles (company_id);
CREATE INDEX idx_vehicles_vehicle_type_id ON vehicles (vehicle_type_id);
CREATE UNIQUE INDEX idx_vehicles_license_plate ON vehicles (license_plate);
CREATE UNIQUE INDEX idx_vehicles_vin ON vehicles (vin);

-- Indexes for drivers
CREATE INDEX idx_drivers_company_id ON drivers (company_id);
CREATE UNIQUE INDEX idx_drivers_vehicle_id ON drivers (vehicle_id);
CREATE UNIQUE INDEX idx_drivers_license_number ON drivers (license_number);
CREATE INDEX idx_drivers_license_expiry_date ON drivers (license_expiry_date);
CREATE INDEX idx_drivers_email ON drivers (email);

-- Indexes for managers
CREATE INDEX idx_managers_company_id ON managers (company_id);
CREATE UNIQUE INDEX idx_managers_email ON managers (email);
CREATE INDEX idx_managers_access_level ON managers (access_level);

-- Indexes for maintenance_logs
CREATE INDEX idx_maintenance_logs_vehicle_id ON maintenance_logs (vehicle_id);
CREATE INDEX idx_maintenance_logs_maintenance_date ON maintenance_logs (maintenance_date);
CREATE INDEX idx_maintenance_logs_next_service_due ON maintenance_logs (next_service_due);

-- Indexes for fuel_logs
CREATE INDEX idx_fuel_logs_vehicle_id ON fuel_logs (vehicle_id);
CREATE INDEX idx_fuel_logs_fuel_date ON fuel_logs (fuel_date);
CREATE INDEX idx_fuel_logs_fuel_type ON fuel_logs (fuel_type);

-- Indexes for location_trackings
CREATE INDEX idx_location_trackings_vehicle_id ON location_trackings (vehicle_id);
CREATE INDEX idx_location_trackings_timestamp ON location_trackings (timestamp);
CREATE INDEX idx_location_trackings_vehicle_timestamp ON location_trackings (vehicle_id, timestamp);

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

-- ============================================================
-- ROW LEVEL SECURITY (Multi-tenant isolation)
-- ============================================================

-- Row Level Security for companies
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
-- Example policy (customize based on your auth):
-- CREATE POLICY companies_tenant_isolation ON companies
--     USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- Row Level Security for vehicles
ALTER TABLE vehicles ENABLE ROW LEVEL SECURITY;
-- Example policy (customize based on your auth):
-- CREATE POLICY vehicles_tenant_isolation ON vehicles
--     USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- Row Level Security for drivers
ALTER TABLE drivers ENABLE ROW LEVEL SECURITY;
-- Example policy (customize based on your auth):
-- CREATE POLICY drivers_tenant_isolation ON drivers
--     USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- Row Level Security for managers
ALTER TABLE managers ENABLE ROW LEVEL SECURITY;
-- Example policy (customize based on your auth):
-- CREATE POLICY managers_tenant_isolation ON managers
--     USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- Row Level Security for maintenance_logs
ALTER TABLE maintenance_logs ENABLE ROW LEVEL SECURITY;
-- Example policy (customize based on your auth):
-- CREATE POLICY maintenance_logs_tenant_isolation ON maintenance_logs
--     USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- Row Level Security for fuel_logs
ALTER TABLE fuel_logs ENABLE ROW LEVEL SECURITY;
-- Example policy (customize based on your auth):
-- CREATE POLICY fuel_logs_tenant_isolation ON fuel_logs
--     USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- Row Level Security for location_trackings
ALTER TABLE location_trackings ENABLE ROW LEVEL SECURITY;
-- Example policy (customize based on your auth):
-- CREATE POLICY location_trackings_tenant_isolation ON location_trackings
--     USING (tenant_id = current_setting('app.current_tenant')::uuid);
