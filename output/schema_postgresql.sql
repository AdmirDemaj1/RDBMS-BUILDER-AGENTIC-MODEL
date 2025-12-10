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

-- Organizations that own and manage vehicle fleets
-- ⚠️  PII columns: address, contact_email, contact_phone - Consider encryption
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    name VARCHAR(255)(255) NOT NULL,
    registration_number VARCHAR(100)(100) NOT NULL UNIQUE,
    address TEXT,
    contact_email VARCHAR(255)(255),
    contact_phone VARCHAR(20)(20),
    is_active BOOLEAN NOT NULL DEFAULT true,
    deleted_at TIMESTAMPTZ
);

-- Categories of vehicles with fuel consumption specifications
CREATE TABLE vehicle_types (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    name VARCHAR(100)(100) NOT NULL UNIQUE,
    description TEXT,
    fuel_type VARCHAR(50)(50) NOT NULL CHECK (fuel_type IN ('gasoline', 'diesel', 'electric', 'hybrid', 'cng', 'lpg')),
    average_fuel_consumption DECIMAL(8,2)(8,2) CHECK (average_fuel_consumption > 0)
);

-- Fleet vehicles owned by companies
CREATE TABLE vehicles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    company_id UUID NOT NULL,
    vehicle_type_id UUID NOT NULL,
    license_plate VARCHAR(20)(20) NOT NULL UNIQUE,
    make VARCHAR(50)(50) NOT NULL,
    model VARCHAR(50)(50) NOT NULL,
    year INTEGER NOT NULL CHECK (year >= 1900 AND year <= EXTRACT(YEAR FROM NOW()) + 1),
    vin VARCHAR(17)(17) NOT NULL UNIQUE,
    purchase_date DATE,
    mileage INTEGER NOT NULL DEFAULT 0 CHECK (mileage >= 0),
    status VARCHAR(20)(20) NOT NULL DEFAULT active CHECK (status IN ('active', 'maintenance', 'retired', 'sold')),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT fk_vehicles_company_id FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_vehicles_vehicle_type_id FOREIGN KEY (vehicle_type_id) REFERENCES vehicle_types(id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Licensed drivers who can operate vehicles
-- ⚠️  PII columns: first_name, last_name, license_number, contact_phone, email - Consider encryption
CREATE TABLE drivers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    first_name VARCHAR(100)(100) NOT NULL,
    last_name VARCHAR(100)(100) NOT NULL,
    license_number VARCHAR(50)(50) NOT NULL UNIQUE,
    license_expiry_date DATE NOT NULL,
    contact_phone VARCHAR(20)(20),
    email VARCHAR(255)(255),
    is_active BOOLEAN NOT NULL DEFAULT true,
    deleted_at TIMESTAMPTZ
);

-- User roles defining permissions and access levels
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    name VARCHAR(100)(100) NOT NULL UNIQUE,
    description TEXT,
    permissions JSONB NOT NULL DEFAULT '{}'
);

-- System users with authentication and role-based access
-- ⚠️  PII columns: email, first_name, last_name - Consider encryption
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    role_id UUID NOT NULL,
    username VARCHAR(50)(50) NOT NULL UNIQUE,
    email VARCHAR(255)(255) NOT NULL UNIQUE,
    first_name VARCHAR(100)(100) NOT NULL,
    last_name VARCHAR(100)(100) NOT NULL,
    password_hash VARCHAR(255)(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    last_login_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ,
    CONSTRAINT fk_users_role_id FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Scheduled maintenance tasks for vehicles
CREATE TABLE maintenance_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    vehicle_id UUID NOT NULL,
    maintenance_type VARCHAR(100)(100) NOT NULL,
    description TEXT,
    interval_miles INTEGER CHECK (interval_miles > 0),
    interval_days INTEGER CHECK (interval_days > 0),
    last_performed_date DATE,
    next_due_date DATE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    CONSTRAINT fk_maintenance_schedules_vehicle_id FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- Fuel purchase and consumption records for vehicles
CREATE TABLE fuel_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    vehicle_id UUID NOT NULL,
    driver_id UUID,
    date DATE NOT NULL,
    amount DECIMAL(10,3)(10,3) NOT NULL CHECK (amount > 0),
    cost DECIMAL(12,2)(12,2) NOT NULL CHECK (cost > 0),
    price_per_unit DECIMAL(8,3)(8,3) NOT NULL CHECK (price_per_unit > 0),
    odometer INTEGER NOT NULL CHECK (odometer >= 0),
    location VARCHAR(255)(255),
    CONSTRAINT fk_fuel_logs_vehicle_id FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_fuel_logs_driver_id FOREIGN KEY (driver_id) REFERENCES drivers(id) ON DELETE SET NULL ON UPDATE CASCADE
);

-- GPS tracking data for vehicles
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
    CONSTRAINT fk_location_logs_vehicle_id FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- Assignment of drivers to specific vehicles
CREATE TABLE driver_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    driver_id UUID NOT NULL,
    vehicle_id UUID NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    notes TEXT,
    CONSTRAINT fk_driver_assignments_driver_id FOREIGN KEY (driver_id) REFERENCES drivers(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_driver_assignments_vehicle_id FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- User access permissions to specific companies
CREATE TABLE user_company_access (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_id UUID NOT NULL,
    company_id UUID NOT NULL,
    access_level VARCHAR(20)(20) NOT NULL CHECK (access_level IN ('read', 'write', 'admin', 'owner')),
    granted_date DATE NOT NULL DEFAULT CURRENT_DATE,
    granted_by UUID,
    is_active BOOLEAN NOT NULL DEFAULT true,
    CONSTRAINT fk_user_company_access_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_user_company_access_company_id FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_user_company_access_granted_by FOREIGN KEY (granted_by) REFERENCES users(id) ON DELETE SET NULL ON UPDATE CASCADE
);

-- Employment relationship between drivers and companies
CREATE TABLE driver_company_employment (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    driver_id UUID NOT NULL,
    company_id UUID NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    employment_status VARCHAR(20)(20) NOT NULL DEFAULT active CHECK (employment_status IN ('active', 'terminated', 'suspended', 'on_leave')),
    position VARCHAR(100)(100),
    salary DECIMAL(12,2)(12,2) CHECK (salary >= 0),
    notes TEXT,
    CONSTRAINT fk_driver_company_employment_driver_id FOREIGN KEY (driver_id) REFERENCES drivers(id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_driver_company_employment_company_id FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE ON UPDATE CASCADE
);

-- ============================================================
-- INDEXES (Critical for query performance)
-- ============================================================

-- Indexes for companies
CREATE UNIQUE INDEX idx_companies_registration_number ON companies (registration_number);
CREATE INDEX idx_companies_name ON companies (name);
CREATE INDEX idx_companies_is_active ON companies (is_active);
CREATE INDEX idx_companies_deleted_at ON companies (deleted_at);

-- Indexes for vehicle_types
CREATE UNIQUE INDEX idx_vehicle_types_name ON vehicle_types (name);
CREATE INDEX idx_vehicle_types_fuel_type ON vehicle_types (fuel_type);

-- Indexes for vehicles
CREATE INDEX idx_vehicles_company_id ON vehicles (company_id);
CREATE INDEX idx_vehicles_vehicle_type_id ON vehicles (vehicle_type_id);
CREATE UNIQUE INDEX idx_vehicles_license_plate ON vehicles (license_plate);
CREATE UNIQUE INDEX idx_vehicles_vin ON vehicles (vin);
CREATE INDEX idx_vehicles_status ON vehicles (status);
CREATE INDEX idx_vehicles_company_status ON vehicles (company_id, status);
CREATE INDEX idx_vehicles_make_model ON vehicles (make, model);
CREATE INDEX idx_vehicles_deleted_at ON vehicles (deleted_at);

-- Indexes for drivers
CREATE UNIQUE INDEX idx_drivers_license_number ON drivers (license_number);
CREATE INDEX idx_drivers_email ON drivers (email);
CREATE INDEX idx_drivers_is_active ON drivers (is_active);
CREATE INDEX idx_drivers_license_expiry ON drivers (license_expiry_date);
CREATE INDEX idx_drivers_name ON drivers (last_name, first_name);
CREATE INDEX idx_drivers_deleted_at ON drivers (deleted_at);

-- Indexes for roles
CREATE UNIQUE INDEX idx_roles_name ON roles (name);
CREATE INDEX idx_roles_permissions ON roles USING gin (permissions);

-- Indexes for users
CREATE INDEX idx_users_role_id ON users (role_id);
CREATE UNIQUE INDEX idx_users_username ON users (username);
CREATE UNIQUE INDEX idx_users_email ON users (email);
CREATE INDEX idx_users_is_active ON users (is_active);
CREATE INDEX idx_users_last_login ON users (last_login_at);
CREATE INDEX idx_users_deleted_at ON users (deleted_at);

-- Indexes for maintenance_schedules
CREATE INDEX idx_maintenance_schedules_vehicle_id ON maintenance_schedules (vehicle_id);
CREATE INDEX idx_maintenance_schedules_next_due ON maintenance_schedules (next_due_date);
CREATE INDEX idx_maintenance_schedules_type ON maintenance_schedules (maintenance_type);
CREATE INDEX idx_maintenance_schedules_vehicle_due ON maintenance_schedules (vehicle_id, next_due_date);
CREATE INDEX idx_maintenance_schedules_is_active ON maintenance_schedules (is_active);

-- Indexes for fuel_logs
CREATE INDEX idx_fuel_logs_vehicle_id ON fuel_logs (vehicle_id);
CREATE INDEX idx_fuel_logs_driver_id ON fuel_logs (driver_id);
CREATE INDEX idx_fuel_logs_date ON fuel_logs (date);
CREATE INDEX idx_fuel_logs_vehicle_date ON fuel_logs (vehicle_id, date);
CREATE INDEX idx_fuel_logs_odometer ON fuel_logs (odometer);
CREATE INDEX idx_fuel_logs_location ON fuel_logs (location);

-- Indexes for location_logs
CREATE INDEX idx_location_logs_vehicle_id ON location_logs (vehicle_id);
CREATE INDEX idx_location_logs_timestamp ON location_logs (timestamp);
CREATE INDEX idx_location_logs_vehicle_timestamp ON location_logs (vehicle_id, timestamp);
CREATE INDEX idx_location_logs_coordinates ON location_logs (latitude, longitude);
CREATE INDEX idx_location_logs_speed ON location_logs (speed);

-- Indexes for driver_assignments
CREATE INDEX idx_driver_assignments_driver_id ON driver_assignments (driver_id);
CREATE INDEX idx_driver_assignments_vehicle_id ON driver_assignments (vehicle_id);
CREATE INDEX idx_driver_assignments_is_active ON driver_assignments (is_active);
CREATE INDEX idx_driver_assignments_start_date ON driver_assignments (start_date);
CREATE INDEX idx_driver_assignments_end_date ON driver_assignments (end_date);
CREATE INDEX idx_driver_assignments_active_vehicle ON driver_assignments (vehicle_id, is_active);
CREATE INDEX idx_driver_assignments_active_driver ON driver_assignments (driver_id, is_active);

-- Indexes for user_company_access
CREATE INDEX idx_user_company_access_user_id ON user_company_access (user_id);
CREATE INDEX idx_user_company_access_company_id ON user_company_access (company_id);
CREATE INDEX idx_user_company_access_granted_by ON user_company_access (granted_by);
CREATE INDEX idx_user_company_access_level ON user_company_access (access_level);
CREATE INDEX idx_user_company_access_is_active ON user_company_access (is_active);
CREATE UNIQUE INDEX idx_user_company_access_unique ON user_company_access (user_id, company_id);
CREATE INDEX idx_user_company_access_active ON user_company_access (user_id, company_id, is_active);

-- Indexes for driver_company_employment
CREATE INDEX idx_driver_company_employment_driver_id ON driver_company_employment (driver_id);
CREATE INDEX idx_driver_company_employment_company_id ON driver_company_employment (company_id);
CREATE INDEX idx_driver_company_employment_status ON driver_company_employment (employment_status);
CREATE INDEX idx_driver_company_employment_start_date ON driver_company_employment (start_date);
CREATE INDEX idx_driver_company_employment_end_date ON driver_company_employment (end_date);
CREATE INDEX idx_driver_company_employment_active ON driver_company_employment (driver_id, company_id, employment_status);
CREATE INDEX idx_driver_company_employment_position ON driver_company_employment (position);

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

-- Auto-update updated_at trigger for roles
CREATE TRIGGER trg_roles_updated_at
    BEFORE UPDATE ON roles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for users
CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
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

-- Auto-update updated_at trigger for location_logs
CREATE TRIGGER trg_location_logs_updated_at
    BEFORE UPDATE ON location_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for driver_assignments
CREATE TRIGGER trg_driver_assignments_updated_at
    BEFORE UPDATE ON driver_assignments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for user_company_access
CREATE TRIGGER trg_user_company_access_updated_at
    BEFORE UPDATE ON user_company_access
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for driver_company_employment
CREATE TRIGGER trg_driver_company_employment_updated_at
    BEFORE UPDATE ON driver_company_employment
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- ROW LEVEL SECURITY (Multi-tenant isolation)
-- ============================================================

-- Row Level Security for users
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- Example policy (customize based on your auth):
-- CREATE POLICY users_tenant_isolation ON users
--     USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- Row Level Security for user_company_access
ALTER TABLE user_company_access ENABLE ROW LEVEL SECURITY;
-- Example policy (customize based on your auth):
-- CREATE POLICY user_company_access_tenant_isolation ON user_company_access
--     USING (tenant_id = current_setting('app.current_tenant')::uuid);
