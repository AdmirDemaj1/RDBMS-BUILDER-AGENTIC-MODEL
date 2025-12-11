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

-- Companies that own and manage vehicle fleets
-- ⚠️  PII columns: address, phone, email - Consider encryption
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255)(255) NOT NULL,
    address TEXT,
    phone VARCHAR(20)(20),
    email VARCHAR(255)(255),
    registration_number VARCHAR(100)(100) UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Types of vehicles (truck, van, car, etc.)
CREATE TABLE vehicle_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type_name VARCHAR(100)(100) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Types of maintenance activities (oil change, tire rotation, etc.)
CREATE TABLE maintenance_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type_name VARCHAR(100)(100) NOT NULL UNIQUE,
    description TEXT,
    default_interval INTEGER CHECK (default_interval > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Fleet vehicles owned by companies
CREATE TABLE vehicles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL,
    vehicle_type_id UUID NOT NULL,
    make VARCHAR(100)(100) NOT NULL,
    model VARCHAR(100)(100) NOT NULL,
    year INTEGER NOT NULL CHECK (year >= 1900 AND year <= EXTRACT(YEAR FROM NOW()) + 1),
    license_plate VARCHAR(20)(20) NOT NULL UNIQUE,
    vin VARCHAR(17)(17) NOT NULL UNIQUE CHECK (LENGTH(vin) = 17),
    mileage INTEGER DEFAULT 0 CHECK (mileage >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_vehicles_company_id FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_vehicles_vehicle_type_id FOREIGN KEY (vehicle_type_id) REFERENCES vehicle_types(id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Drivers employed by companies
-- ⚠️  PII columns: first_name, last_name, license_number, phone, email - Consider encryption
CREATE TABLE drivers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL,
    first_name VARCHAR(100)(100) NOT NULL,
    last_name VARCHAR(100)(100) NOT NULL,
    license_number VARCHAR(50)(50) NOT NULL UNIQUE,
    phone VARCHAR(20)(20),
    email VARCHAR(255)(255),
    hire_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_drivers_company_id FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- System users with access to the fleet management system
-- ⚠️  PII columns: email, first_name, last_name - Consider encryption
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL,
    driver_id UUID UNIQUE,
    username VARCHAR(100)(100) NOT NULL UNIQUE,
    email VARCHAR(255)(255) NOT NULL UNIQUE,
    first_name VARCHAR(100)(100) NOT NULL,
    last_name VARCHAR(100)(100) NOT NULL,
    role VARCHAR(50)(50) NOT NULL CHECK (role IN ('admin', 'manager', 'driver', 'viewer')),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_users_company_id FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_users_driver_id FOREIGN KEY (driver_id) REFERENCES drivers(id) ON DELETE SET NULL ON UPDATE CASCADE
);

-- Assignment of drivers to vehicles for specific time periods
CREATE TABLE driver_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id UUID NOT NULL,
    driver_id UUID NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_driver_assignments_vehicle_id FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_driver_assignments_driver_id FOREIGN KEY (driver_id) REFERENCES drivers(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_driver_assignments_10 CHECK (end_date IS NULL OR end_date >= start_date)
);

-- Scheduled maintenance activities for vehicles
CREATE TABLE maintenance_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id UUID NOT NULL,
    maintenance_type_id UUID NOT NULL,
    description TEXT,
    scheduled_date DATE NOT NULL,
    due_date DATE NOT NULL,
    is_completed BOOLEAN NOT NULL DEFAULT false,
    mileage_interval INTEGER CHECK (mileage_interval > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_maintenance_schedules_vehicle_id FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_maintenance_schedules_maintenance_type_id FOREIGN KEY (maintenance_type_id) REFERENCES maintenance_types(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_maintenance_schedules_12 CHECK (due_date >= scheduled_date)
);

-- Fuel purchase and consumption records for vehicles
CREATE TABLE fuel_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id UUID NOT NULL,
    date DATE NOT NULL,
    amount DECIMAL(10,3)(10,3) NOT NULL CHECK (amount > 0),
    cost DECIMAL(12,2)(12,2) NOT NULL CHECK (cost > 0),
    odometer INTEGER NOT NULL CHECK (odometer >= 0),
    fuel_type VARCHAR(50)(50) NOT NULL CHECK (fuel_type IN ('gasoline', 'diesel', 'electric', 'hybrid', 'cng', 'lpg')),
    location VARCHAR(255)(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_fuel_logs_vehicle_id FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- GPS tracking data for vehicles
CREATE TABLE location_trackings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id UUID NOT NULL,
    latitude DECIMAL(10,8)(10,8) NOT NULL CHECK (latitude >= -90 AND latitude <= 90),
    longitude DECIMAL(11,8)(11,8) NOT NULL CHECK (longitude >= -180 AND longitude <= 180),
    timestamp TIMESTAMPTZ NOT NULL,
    speed DECIMAL(6,2)(6,2) CHECK (speed >= 0),
    heading DECIMAL(5,2)(5,2) CHECK (heading >= 0 AND heading < 360),
    accuracy DECIMAL(8,2)(8,2) CHECK (accuracy >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_location_trackings_vehicle_id FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- ============================================================
-- INDEXES (Critical for query performance)
-- ============================================================

-- Indexes for companies
CREATE UNIQUE INDEX idx_companies_registration_number ON companies (registration_number);
CREATE INDEX idx_companies_email ON companies (email);

-- Indexes for vehicle_types
CREATE UNIQUE INDEX idx_vehicle_types_type_name ON vehicle_types (type_name);

-- Indexes for maintenance_types
CREATE UNIQUE INDEX idx_maintenance_types_type_name ON maintenance_types (type_name);

-- Indexes for vehicles
CREATE INDEX idx_vehicles_company_id ON vehicles (company_id);
CREATE INDEX idx_vehicles_vehicle_type_id ON vehicles (vehicle_type_id);
CREATE UNIQUE INDEX idx_vehicles_license_plate ON vehicles (license_plate);
CREATE UNIQUE INDEX idx_vehicles_vin ON vehicles (vin);
CREATE INDEX idx_vehicles_make_model ON vehicles (make, model);

-- Indexes for drivers
CREATE INDEX idx_drivers_company_id ON drivers (company_id);
CREATE UNIQUE INDEX idx_drivers_license_number ON drivers (license_number);
CREATE INDEX idx_drivers_email ON drivers (email);
CREATE INDEX idx_drivers_hire_date ON drivers (hire_date);

-- Indexes for users
CREATE INDEX idx_users_company_id ON users (company_id);
CREATE UNIQUE INDEX idx_users_driver_id ON users (driver_id);
CREATE UNIQUE INDEX idx_users_username ON users (username);
CREATE UNIQUE INDEX idx_users_email ON users (email);
CREATE INDEX idx_users_role ON users (role);
CREATE INDEX idx_users_is_active ON users (is_active);

-- Indexes for driver_assignments
CREATE INDEX idx_driver_assignments_vehicle_id ON driver_assignments (vehicle_id);
CREATE INDEX idx_driver_assignments_driver_id ON driver_assignments (driver_id);
CREATE INDEX idx_driver_assignments_is_active ON driver_assignments (is_active);
CREATE INDEX idx_driver_assignments_start_date ON driver_assignments (start_date);
CREATE INDEX idx_driver_assignments_vehicle_active ON driver_assignments (vehicle_id, is_active);
CREATE INDEX idx_driver_assignments_driver_active ON driver_assignments (driver_id, is_active);

-- Indexes for maintenance_schedules
CREATE INDEX idx_maintenance_schedules_vehicle_id ON maintenance_schedules (vehicle_id);
CREATE INDEX idx_maintenance_schedules_maintenance_type_id ON maintenance_schedules (maintenance_type_id);
CREATE INDEX idx_maintenance_schedules_is_completed ON maintenance_schedules (is_completed);
CREATE INDEX idx_maintenance_schedules_due_date ON maintenance_schedules (due_date);
CREATE INDEX idx_maintenance_schedules_vehicle_due ON maintenance_schedules (vehicle_id, due_date);
CREATE INDEX idx_maintenance_schedules_pending ON maintenance_schedules (is_completed, due_date);

-- Indexes for fuel_logs
CREATE INDEX idx_fuel_logs_vehicle_id ON fuel_logs (vehicle_id);
CREATE INDEX idx_fuel_logs_date ON fuel_logs (date);
CREATE INDEX idx_fuel_logs_fuel_type ON fuel_logs (fuel_type);
CREATE INDEX idx_fuel_logs_vehicle_date ON fuel_logs (vehicle_id, date);
CREATE INDEX idx_fuel_logs_odometer ON fuel_logs (odometer);

-- Indexes for location_trackings
CREATE INDEX idx_location_trackings_vehicle_id ON location_trackings (vehicle_id);
CREATE INDEX idx_location_trackings_timestamp ON location_trackings (timestamp);
CREATE INDEX idx_location_trackings_vehicle_timestamp ON location_trackings (vehicle_id, timestamp);
CREATE INDEX idx_location_trackings_coordinates ON location_trackings (latitude, longitude);

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

-- Auto-update updated_at trigger for maintenance_types
CREATE TRIGGER trg_maintenance_types_updated_at
    BEFORE UPDATE ON maintenance_types
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

-- Auto-update updated_at trigger for users
CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for driver_assignments
CREATE TRIGGER trg_driver_assignments_updated_at
    BEFORE UPDATE ON driver_assignments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for maintenance_schedules
CREATE TRIGGER trg_maintenance_schedules_updated_at
    BEFORE UPDATE ON maintenance_schedules
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

-- Row Level Security for users
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- Example policy (customize based on your auth):
-- CREATE POLICY users_tenant_isolation ON users
--     USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- Row Level Security for driver_assignments
ALTER TABLE driver_assignments ENABLE ROW LEVEL SECURITY;
-- Example policy (customize based on your auth):
-- CREATE POLICY driver_assignments_tenant_isolation ON driver_assignments
--     USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- Row Level Security for maintenance_schedules
ALTER TABLE maintenance_schedules ENABLE ROW LEVEL SECURITY;
-- Example policy (customize based on your auth):
-- CREATE POLICY maintenance_schedules_tenant_isolation ON maintenance_schedules
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
