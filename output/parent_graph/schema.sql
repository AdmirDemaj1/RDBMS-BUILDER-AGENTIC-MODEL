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

-- Store locations
-- ⚠️  PII columns: phone, manager_name - Consider encryption
CREATE TABLE locations (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    deleted_at TIMESTAMPTZ,
    name VARCHAR(255)(255) NOT NULL,
    address VARCHAR(500)(500) NOT NULL,
    phone VARCHAR(20)(20),
    manager_name VARCHAR(255)(255),
    opening_hours VARCHAR(255)(255),
    is_active BOOLEAN NOT NULL DEFAULT true
);

-- Customer records
-- ⚠️  PII columns: first_name, last_name, email, phone, date_of_birth - Consider encryption
CREATE TABLE customers (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    deleted_at TIMESTAMPTZ,
    first_name VARCHAR(255)(255) NOT NULL,
    last_name VARCHAR(255)(255) NOT NULL,
    email VARCHAR(255)(255) NOT NULL UNIQUE,
    phone VARCHAR(20)(20),
    date_of_birth DATE,
    registration_date TIMESTAMPTZ NOT NULL
);

-- Customer loyalty
CREATE TABLE loyalty_accounts (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    deleted_at TIMESTAMPTZ,
    customer_id UUID NOT NULL UNIQUE,
    points_balance INTEGER NOT NULL DEFAULT 0,
    membership_level VARCHAR(50)(50) NOT NULL DEFAULT BRONZE,
    join_date TIMESTAMPTZ NOT NULL,
    last_activity_date TIMESTAMPTZ,
    CONSTRAINT fk_loyalty_accounts_customer_id FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Employee records
-- ⚠️  PII columns: first_name, last_name, email, phone, hourly_rate - Consider encryption
CREATE TABLE employees (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    deleted_at TIMESTAMPTZ,
    first_name VARCHAR(255)(255) NOT NULL,
    last_name VARCHAR(255)(255) NOT NULL,
    email VARCHAR(255)(255) NOT NULL UNIQUE,
    phone VARCHAR(20)(20),
    hire_date DATE NOT NULL,
    hourly_rate DECIMAL(10,2)(10,2) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true
);

-- Employee roles
CREATE TABLE roles (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    deleted_at TIMESTAMPTZ,
    name VARCHAR(255)(255) NOT NULL UNIQUE,
    description VARCHAR(500)(500),
    permissions TEXT
);

-- Employee assignments
CREATE TABLE employee_locations (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    deleted_at TIMESTAMPTZ,
    employee_id UUID NOT NULL,
    location_id UUID NOT NULL,
    role_id UUID NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    CONSTRAINT fk_employee_locations_employee_id FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_employee_locations_location_id FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_employee_locations_role_id FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Product categories
CREATE TABLE categories (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    deleted_at TIMESTAMPTZ,
    name VARCHAR(255)(255) NOT NULL UNIQUE,
    description VARCHAR(500)(500),
    display_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT true
);

-- Product catalog
CREATE TABLE products (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    deleted_at TIMESTAMPTZ,
    category_id UUID NOT NULL,
    name VARCHAR(255)(255) NOT NULL,
    description TEXT,
    base_price DECIMAL(10,2)(10,2) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    requires_customization BOOLEAN NOT NULL DEFAULT false,
    CONSTRAINT fk_products_category_id FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Product variations
CREATE TABLE product_variants (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    deleted_at TIMESTAMPTZ,
    product_id UUID NOT NULL,
    name VARCHAR(255)(255) NOT NULL,
    size VARCHAR(50)(50),
    price_adjustment DECIMAL(10,2)(10,2) NOT NULL DEFAULT 0.00,
    is_default BOOLEAN NOT NULL DEFAULT false,
    is_available BOOLEAN NOT NULL DEFAULT true,
    CONSTRAINT fk_product_variants_product_id FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Supplier directory
-- ⚠️  PII columns: contact_person, email, phone - Consider encryption
CREATE TABLE suppliers (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    deleted_at TIMESTAMPTZ,
    name VARCHAR(255)(255) NOT NULL UNIQUE,
    contact_person VARCHAR(255)(255),
    email VARCHAR(255)(255),
    phone VARCHAR(20)(20),
    address VARCHAR(500)(500),
    payment_terms VARCHAR(255)(255)
);

-- Inventory catalog
CREATE TABLE inventory_items (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    deleted_at TIMESTAMPTZ,
    supplier_id UUID NOT NULL,
    name VARCHAR(255)(255) NOT NULL,
    unit VARCHAR(50)(50) NOT NULL,
    current_stock INTEGER NOT NULL DEFAULT 0,
    minimum_stock INTEGER NOT NULL DEFAULT 0,
    maximum_stock INTEGER NOT NULL DEFAULT 0,
    unit_cost DECIMAL(10,2)(10,2) NOT NULL,
    CONSTRAINT fk_inventory_items_supplier_id FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Location stock
CREATE TABLE location_inventories (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    deleted_at TIMESTAMPTZ,
    location_id UUID NOT NULL,
    inventory_item_id UUID NOT NULL,
    current_stock INTEGER NOT NULL DEFAULT 0,
    minimum_stock INTEGER NOT NULL DEFAULT 0,
    maximum_stock INTEGER NOT NULL DEFAULT 0,
    last_restocked TIMESTAMPTZ,
    CONSTRAINT fk_location_inventories_location_id FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_location_inventories_inventory_item_id FOREIGN KEY (inventory_item_id) REFERENCES inventory_items(id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Purchase orders
CREATE TABLE purchase_orders (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    deleted_at TIMESTAMPTZ,
    location_id UUID NOT NULL,
    supplier_id UUID NOT NULL,
    order_number VARCHAR(100)(100) NOT NULL UNIQUE,
    order_date TIMESTAMPTZ NOT NULL,
    expected_delivery_date DATE,
    total_amount DECIMAL(12,2)(12,2) NOT NULL,
    status VARCHAR(50)(50) NOT NULL DEFAULT PENDING,
    CONSTRAINT fk_purchase_orders_location_id FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_purchase_orders_supplier_id FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Order line items
CREATE TABLE purchase_order_items (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    deleted_at TIMESTAMPTZ,
    purchase_order_id UUID NOT NULL,
    inventory_item_id UUID NOT NULL,
    quantity INTEGER NOT NULL,
    unit_cost DECIMAL(10,2)(10,2) NOT NULL,
    total_cost DECIMAL(12,2)(12,2) NOT NULL,
    CONSTRAINT fk_purchase_order_items_purchase_order_id FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_purchase_order_items_inventory_item_id FOREIGN KEY (inventory_item_id) REFERENCES inventory_items(id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Sales transactions
CREATE TABLE sales (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    deleted_at TIMESTAMPTZ,
    customer_id UUID,
    location_id UUID NOT NULL,
    sale_number VARCHAR(100)(100) NOT NULL UNIQUE,
    sale_date TIMESTAMPTZ NOT NULL,
    subtotal DECIMAL(12,2)(12,2) NOT NULL,
    tax DECIMAL(12,2)(12,2) NOT NULL DEFAULT 0.00,
    total DECIMAL(12,2)(12,2) NOT NULL,
    payment_method VARCHAR(50)(50) NOT NULL,
    points_earned INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT fk_sales_customer_id FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_sales_location_id FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE RESTRICT ON UPDATE CASCADE
);

-- ============================================================
-- INDEXES (Critical for query performance)
-- ============================================================

-- Indexes for loyalty_accounts
CREATE INDEX idx_loyalty_accounts_customer_id ON loyalty_accounts (customer_id);

-- Indexes for employee_locations
CREATE INDEX idx_employee_locations_employee_id ON employee_locations (employee_id);
CREATE INDEX idx_employee_locations_location_id ON employee_locations (location_id);
CREATE INDEX idx_employee_locations_role_id ON employee_locations (role_id);

-- Indexes for products
CREATE INDEX idx_products_category_id ON products (category_id);

-- Indexes for product_variants
CREATE INDEX idx_product_variants_product_id ON product_variants (product_id);

-- Indexes for inventory_items
CREATE INDEX idx_inventory_items_supplier_id ON inventory_items (supplier_id);

-- Indexes for location_inventories
CREATE INDEX idx_location_inventories_location_id ON location_inventories (location_id);
CREATE INDEX idx_location_inventories_inventory_item_id ON location_inventories (inventory_item_id);

-- Indexes for purchase_orders
CREATE INDEX idx_purchase_orders_location_id ON purchase_orders (location_id);
CREATE INDEX idx_purchase_orders_supplier_id ON purchase_orders (supplier_id);

-- Indexes for purchase_order_items
CREATE INDEX idx_purchase_order_items_purchase_order_id ON purchase_order_items (purchase_order_id);
CREATE INDEX idx_purchase_order_items_inventory_item_id ON purchase_order_items (inventory_item_id);

-- Indexes for sales
CREATE INDEX idx_sales_customer_id ON sales (customer_id);
CREATE INDEX idx_sales_location_id ON sales (location_id);

-- ============================================================
-- TRIGGERS (Auto-update timestamps)
-- ============================================================

-- Auto-update updated_at trigger for locations
CREATE TRIGGER trg_locations_updated_at
    BEFORE UPDATE ON locations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for customers
CREATE TRIGGER trg_customers_updated_at
    BEFORE UPDATE ON customers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for loyalty_accounts
CREATE TRIGGER trg_loyalty_accounts_updated_at
    BEFORE UPDATE ON loyalty_accounts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for employees
CREATE TRIGGER trg_employees_updated_at
    BEFORE UPDATE ON employees
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for roles
CREATE TRIGGER trg_roles_updated_at
    BEFORE UPDATE ON roles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for employee_locations
CREATE TRIGGER trg_employee_locations_updated_at
    BEFORE UPDATE ON employee_locations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for categories
CREATE TRIGGER trg_categories_updated_at
    BEFORE UPDATE ON categories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for products
CREATE TRIGGER trg_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for product_variants
CREATE TRIGGER trg_product_variants_updated_at
    BEFORE UPDATE ON product_variants
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for suppliers
CREATE TRIGGER trg_suppliers_updated_at
    BEFORE UPDATE ON suppliers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for inventory_items
CREATE TRIGGER trg_inventory_items_updated_at
    BEFORE UPDATE ON inventory_items
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for location_inventories
CREATE TRIGGER trg_location_inventories_updated_at
    BEFORE UPDATE ON location_inventories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for purchase_orders
CREATE TRIGGER trg_purchase_orders_updated_at
    BEFORE UPDATE ON purchase_orders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for purchase_order_items
CREATE TRIGGER trg_purchase_order_items_updated_at
    BEFORE UPDATE ON purchase_order_items
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at trigger for sales
CREATE TRIGGER trg_sales_updated_at
    BEFORE UPDATE ON sales
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
