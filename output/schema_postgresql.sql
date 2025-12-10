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

-- Fleet management companies with their basic information
-- ⚠️  PII columns: address, phone, email - Consider encryption
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    name VARCHAR(255)(255) NOT NULL,
    address TEXT,
    phone VARCHAR(20)(20),
    email VARCHAR(255)(255),
    registration_number VARCHAR(100)(100) UNIQUE,
    deleted_at TIMESTAMPTZ
);

-- Types of vehicles with their characteristics
CREATE TABLE vehicle_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    type_name VARCHAR(100)(100) NOT NULL UNIQUE,
    description TEXT,
    fuel_type VARCHAR(50)(50) CHECK (fuel_type IN ('gasoline', 'diesel', 'electric', 'hybrid', 'cng', 'lpg')),
    capacity INTEGER CHECK (capacity > 0),
    deleted_at TIMESTAMPTZ
);

-- Types of maintenance activities with cost and duration estimates
CREATE TABLE maintenance_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    type_name VARCHAR(100)(100) NOT NULL UNIQUE,
    description TEXT,
    estimated_cost DECIMAL(12,2)(12,2) CHECK (estimated_cost >= 0),
    estimated_duration INTEGER CHECK (estimated_duration > 0),
    deleted_at TIMESTAMPTZ
);

-- Company managers with access levels and department information
-- ⚠️  PII columns: first_name, last_name, email, phone - Consider encryption
CREATE TABLE managers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    company_id UUID NOT NULL,
    first_name VARCHAR(100)(100) NOT NULL,
    last_name VARCHAR(100)(100) NOT NULL,
    email VARCHAR(255)(255) NOT NULL UNIQUE,
    phone VARCHAR(20)(20),
    department VARCHAR(100)(100),
    access_level VARCHAR(20)(20) NOT NULL DEFAULT 'standard' CHECK (access_level IN ('admin', 'manager', 'standard', 'readonly')),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT fk_managers_company_id FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- Company drivers with license and contact information
-- ⚠️  PII columns: first_name, last_name, license_number, phone, email - Consider encryption
CREATE TABLE drivers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    company_id UUID NOT NULL,
    first_name VARCHAR(100)(100) NOT NULL,
    last_name VARCHAR(100)(100) NOT NULL,
    license_number VARCHAR(50)(50) NOT NULL UNIQUE,
    phone VARCHAR(20)(20),
    email VARCHAR(255)(255),
    hire_date DATE NOT NULL,
    deleted_at TIMESTAMPTZ,
    CONSTRAINT fk_drivers_company_id FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- Fleet vehicles with detailed specifications and ownership information
CREATE TABLE vehicles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    company_id UUID NOT NULL,
    vehicle_type_id UUID NOT NULL,
    make VARCHAR(100)(100) NOT NULL,
    model VARCHAR(100)(100) NOT NULL,
    year INTEGER NOT NULL CHECK (year >= 1900 AND year <= EXTRACT(YEAR FROM NOW()) + 1),
    license_plate VARCHAR(20)(20) NOT NULL UNIQUE,
    vin VARCHAR(17)(17) NOT NULL UNIQUE CHECK (LENGTH(vin) = 17),
    purchase_date DATE,
    mileage INTEGER DEFAULT 0 CHECK (mileage >= 0),
    status VARCHAR(20)(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'maintenance', 'retired', 'sold')),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT fk_vehicles_company_id FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_vehicles_vehicle_type_id FOREIGN KEY (vehicle_type_id) REFERENCES vehicle_types(id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Assignment history of drivers to vehicles
CREATE TABLE vehicle_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    driver_id UUID NOT NULL,
    vehicle_id UUID NOT NULL,
    assignment_date DATE NOT NULL,
    end_date DATE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    notes TEXT,
    deleted_at TIMESTAMPTZ,
    CONSTRAINT fk_vehicle_assignments_driver_id FOREIGN KEY (driver_id) REFERENCES drivers(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_vehicle_assignments_vehicle_id FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- Scheduled maintenance plans for vehicles
CREATE TABLE maintenance_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    vehicle_id UUID NOT NULL,
    maintenance_type_id UUID NOT NULL,
    interval_miles INTEGER CHECK (interval_miles > 0),
    interval_days INTEGER CHECK (interval_days > 0),
    last_performed DATE,
    next_due DATE,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    deleted_at TIMESTAMPTZ,
    CONSTRAINT fk_maintenance_schedules_vehicle_id FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_maintenance_schedules_maintenance_type_id FOREIGN KEY (maintenance_type_id) REFERENCES maintenance_types(id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Historical records of performed maintenance activities
CREATE TABLE maintenance_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    vehicle_id UUID NOT NULL,
    maintenance_type_id UUID NOT NULL,
    performed_date DATE NOT NULL,
    description TEXT,
    cost DECIMAL(12,2)(12,2) CHECK (cost >= 0),
    mileage_at_service INTEGER CHECK (mileage_at_service >= 0),
    service_provider VARCHAR(255)(255),
    invoice_number VARCHAR(100)(100),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT fk_maintenance_records_vehicle_id FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_maintenance_records_maintenance_type_id FOREIGN KEY (maintenance_type_id) REFERENCES maintenance_types(id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Fuel purchase and consumption records for vehicles
CREATE TABLE fuel_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    vehicle_id UUID NOT NULL,
    date DATE NOT NULL,
    amount DECIMAL(8,3)(8,3) NOT NULL CHECK (amount > 0),
    cost DECIMAL(12,2)(12,2) NOT NULL CHECK (cost > 0),
    price_per_unit DECIMAL(8,3)(8,3) NOT NULL CHECK (price_per_unit > 0),
    mileage INTEGER CHECK (mileage >= 0),
    location VARCHAR(255)(255),
    receipt_number VARCHAR(100)(100),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT fk_fuel_logs_vehicle_id FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- GPS tracking data for vehicles with timestamp and location details
CREATE TABLE location_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    vehicle_id UUID NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    latitude DECIMAL(10,8)(10,8) NOT NULL CHECK (latitude >= -90 AND latitude <= 90),
    longitude DECIMAL(11,8)(11,8) NOT NULL CHECK (longitude >= -180 AND longitude <= 180),
    speed DECIMAL(6,2)(6,2) CHECK (speed >= 0),
    heading DECIMAL(5,2)(5,2) CHECK (heading >= 0 AND heading < 360),
    accuracy DECIMAL(8,2)(8,2) CHECK (accuracy >= 0),
    altitude DECIMAL(8,2)(8,2),
    CONSTRAINT fk_location_logs_vehicle_id FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- ============================================================
-- INDEXES (Critical for query performance)
-- ============================================================

-- Indexes for companies
CREATE INDEX idx_companies_name ON companies (name);
CREATE UNIQUE INDEX idx_companies_registration_number ON companies (registration_number);
CREATE INDEX idx_companies_deleted_at ON companies (deleted_at);

-- Indexes for vehicle_types
CREATE UNIQUE INDEX idx_vehicle_types_type_name ON vehicle_types (type_name);
CREATE INDEX idx_vehicle_types_fuel_type ON vehicle_types (fuel_type);
CREATE INDEX idx_vehicle_types_deleted_at ON vehicle_types (deleted_at);

-- Indexes for maintenance_types
CREATE UNIQUE INDEX idx_maintenance_types_type_name ON maintenance_types (type_name);
CREATE INDEX idx_maintenance_types_deleted_at ON maintenance_types (deleted_at);

-- Indexes for managers
CREATE INDEX idx_managers_company_id ON managers (company_id);
CREATE UNIQUE INDEX idx_managers_email ON managers (email);
CREATE INDEX idx_managers_access_level ON managers (access_level);
CREATE INDEX idx_managers_department ON managers (department);
CREATE INDEX idx_managers_deleted_at ON managers (deleted_at);

-- Indexes for drivers
CREATE INDEX idx_drivers_company_id ON drivers (company_id);
CREATE UNIQUE INDEX idx_drivers_license_number ON drivers (license_number);
CREATE INDEX idx_drivers_hire_date ON drivers (hire_date);
CREATE INDEX idx_drivers_email ON drivers (email);
CREATE INDEX idx_drivers_deleted_at ON drivers (deleted_at);

-- Indexes for vehicles
CREATE INDEX idx_vehicles_company_id ON vehicles (company_id);
CREATE INDEX idx_vehicles_vehicle_type_id ON vehicles (vehicle_type_id);
CREATE UNIQUE INDEX idx_vehicles_license_plate ON vehicles (license_plate);
CREATE UNIQUE INDEX idx_vehicles_vin ON vehicles (vin);
CREATE INDEX idx_vehicles_status ON vehicles (status);
CREATE INDEX idx_vehicles_make_model ON vehicles (make, model);
CREATE INDEX idx_vehicles_year ON vehicles (year);
CREATE INDEX idx_vehicles_deleted_at ON vehicles (deleted_at);

-- Indexes for vehicle_assignments
CREATE INDEX idx_vehicle_assignments_driver_id ON vehicle_assignments (driver_id);
CREATE INDEX idx_vehicle_assignments_vehicle_id ON vehicle_assignments (vehicle_id);
CREATE INDEX idx_vehicle_assignments_is_active ON vehicle_assignments (is_active);
CREATE INDEX idx_vehicle_assignments_assignment_date ON vehicle_assignments (assignment_date);
CREATE INDEX idx_vehicle_assignments_driver_active ON vehicle_assignments (driver_id, is_active);
CREATE INDEX idx_vehicle_assignments_vehicle_active ON vehicle_assignments (vehicle_id, is_active);
CREATE INDEX idx_vehicle_assignments_deleted_at ON vehicle_assignments (deleted_at);

-- Indexes for maintenance_schedules
CREATE INDEX idx_maintenance_schedules_vehicle_id ON maintenance_schedules (vehicle_id);
CREATE INDEX idx_maintenance_schedules_maintenance_type_id ON maintenance_schedules (maintenance_type_id);
CREATE INDEX idx_maintenance_schedules_next_due ON maintenance_schedules (next_due);
CREATE INDEX idx_maintenance_schedules_is_active ON maintenance_schedules (is_active);
CREATE INDEX idx_maintenance_schedules_vehicle_active ON maintenance_schedules (vehicle_id, is_active);
CREATE INDEX idx_maintenance_schedules_deleted_at ON maintenance_schedules (deleted_at);

-- Indexes for maintenance_records
CREATE INDEX idx_maintenance_records_vehicle_id ON maintenance_records (vehicle_id);
CREATE INDEX idx_maintenance_records_maintenance_type_id ON maintenance_records (maintenance_type_id);
CREATE INDEX idx_maintenance_records_performed_date ON maintenance_records (performed_date);
CREATE INDEX idx_maintenance_records_vehicle_date ON maintenance_records (vehicle_id, performed_date);
CREATE INDEX idx_maintenance_records_service_provider ON maintenance_records (service_provider);
CREATE INDEX idx_maintenance_records_deleted_at ON maintenance_records (deleted_at);

-- Indexes for fuel_logs
CREATE INDEX idx_fuel_logs_vehicle_id ON fuel_logs (vehicle_id);
CREATE INDEX idx_fuel_logs_date ON fuel_logs (date);
CREATE INDEX idx_fuel_logs_vehicle_date ON fuel_logs (vehicle_id, date);
CREATE INDEX idx_fuel_logs_location ON fuel_logs (location);
CREATE INDEX idx_fuel_logs_deleted_at ON fuel_logs (deleted_at);

-- Indexes for location_logs
CREATE INDEX idx_location_logs_vehicle_id ON location_logs (vehicle_id);
CREATE INDEX idx_location_logs_timestamp ON location_logs (timestamp);
CREATE INDEX idx_location_logs_vehicle_timestamp ON location_logs (vehicle_id, timestamp);
CREATE INDEX idx_location_logs_lat_lng ON location_logs (latitude, longitude);
CREATE INDEX idx_location_logs_speed ON location_logs (speed);

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

-- Auto-update updated_at trigger for managers
CREATE TRIGGER trg_managers_updated_at
    BEFORE UPDATE ON managers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for drivers
CREATE TRIGGER trg_drivers_updated_at
    BEFORE UPDATE ON drivers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for vehicles
CREATE TRIGGER trg_vehicles_updated_at
    BEFORE UPDATE ON vehicles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for vehicle_assignments
CREATE TRIGGER trg_vehicle_assignments_updated_at
    BEFORE UPDATE ON vehicle_assignments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for maintenance_schedules
CREATE TRIGGER trg_maintenance_schedules_updated_at
    BEFORE UPDATE ON maintenance_schedules
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for maintenance_records
CREATE TRIGGER trg_maintenance_records_updated_at
    BEFORE UPDATE ON maintenance_records
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for fuel_logs
CREATE TRIGGER trg_fuel_logs_updated_at
    BEFORE UPDATE ON fuel_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for location_logs
CREATE TRIGGER trg_location_logs_updated_at
    BEFORE UPDATE ON location_logs
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

-- Row Level Security for managers
ALTER TABLE managers ENABLE ROW LEVEL SECURITY;
-- Example policy (customize based on your auth):
-- CREATE POLICY managers_tenant_isolation ON managers
--     USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- Row Level Security for drivers
ALTER TABLE drivers ENABLE ROW LEVEL SECURITY;
-- Example policy (customize based on your auth):
-- CREATE POLICY drivers_tenant_isolation ON drivers
--     USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- Row Level Security for vehicles
ALTER TABLE vehicles ENABLE ROW LEVEL SECURITY;
-- Example policy (customize based on your auth):
-- CREATE POLICY vehicles_tenant_isolation ON vehicles
--     USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- Row Level Security for vehicle_assignments
ALTER TABLE vehicle_assignments ENABLE ROW LEVEL SECURITY;
-- Example policy (customize based on your auth):
-- CREATE POLICY vehicle_assignments_tenant_isolation ON vehicle_assignments
--     USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- Row Level Security for maintenance_schedules
ALTER TABLE maintenance_schedules ENABLE ROW LEVEL SECURITY;
-- Example policy (customize based on your auth):
-- CREATE POLICY maintenance_schedules_tenant_isolation ON maintenance_schedules
--     USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- Row Level Security for maintenance_records
ALTER TABLE maintenance_records ENABLE ROW LEVEL SECURITY;
-- Example policy (customize based on your auth):
-- CREATE POLICY maintenance_records_tenant_isolation ON maintenance_records
--     USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- Row Level Security for fuel_logs
ALTER TABLE fuel_logs ENABLE ROW LEVEL SECURITY;
-- Example policy (customize based on your auth):
-- CREATE POLICY fuel_logs_tenant_isolation ON fuel_logs
--     USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- Row Level Security for location_logs
ALTER TABLE location_logs ENABLE ROW LEVEL SECURITY;
-- Example policy (customize based on your auth):
-- CREATE POLICY location_logs_tenant_isolation ON location_logs
--     USING (tenant_id = current_setting('app.current_tenant')::uuid);
