# Entity Relationship Diagram

```mermaid
# Entity Relationship Diagram

```mermaid
erDiagram
    LOCATIONS {  %% ⚠️PII:2
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        timestamptz deleted_at
        varchar name*
        varchar address*
        varchar phone 🔐
        varchar manager_name 🔐
        varchar opening_hours
        boolean is_active*
    }
    CUSTOMERS {  %% ⚠️PII:5
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        timestamptz deleted_at
        varchar first_name* 🔐
        varchar last_name* 🔐
        varchar email* UK🔐
        varchar phone 🔐
        date date_of_birth 🔐
        timestamptz registration_date*
    }
    LOYALTY-ACCOUNTS {  %% 📊IDX:1
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        timestamptz deleted_at
        uuid customer_id* FK
        integer points_balance*
        varchar membership_level*
        timestamptz join_date*
        timestamptz last_activity_date
    }
    EMPLOYEES {  %% ⚠️PII:5
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        timestamptz deleted_at
        varchar first_name* 🔐
        varchar last_name* 🔐
        varchar email* UK🔐
        varchar phone 🔐
        date hire_date*
        decimal hourly_rate* 🔐
        boolean is_active*
    }
    ROLES {
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        timestamptz deleted_at
        varchar name* UK
        varchar description
        text permissions
    }
    EMPLOYEE-LOCATIONS {  %% 📊IDX:3
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        timestamptz deleted_at
        uuid employee_id* FK
        uuid location_id* FK
        uuid role_id* FK
        date start_date*
        date end_date
        boolean is_active*
    }
    CATEGORIES {
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        timestamptz deleted_at
        varchar name* UK
        varchar description
        integer display_order*
        boolean is_active*
    }
    PRODUCTS {  %% 📊IDX:1
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        timestamptz deleted_at
        uuid category_id* FK
        varchar name*
        text description
        decimal base_price*
        boolean is_active*
        boolean requires_customization*
    }
    PRODUCT-VARIANTS {  %% 📊IDX:1
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        timestamptz deleted_at
        uuid product_id* FK
        varchar name*
        varchar size
        decimal price_adjustment*
        boolean is_default*
        boolean is_available*
    }
    SUPPLIERS {  %% ⚠️PII:3
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        timestamptz deleted_at
        varchar name* UK
        varchar contact_person 🔐
        varchar email 🔐
        varchar phone 🔐
        varchar address
        varchar payment_terms
    }
    INVENTORY-ITEMS {  %% 📊IDX:1
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        timestamptz deleted_at
        uuid supplier_id* FK
        varchar name*
        varchar unit*
        integer current_stock*
        integer minimum_stock*
        integer maximum_stock*
        decimal unit_cost*
    }
    LOCATION-INVENTORIES {  %% 📊IDX:2
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        timestamptz deleted_at
        uuid location_id* FK
        uuid inventory_item_id* FK
        integer current_stock*
        integer minimum_stock*
        integer maximum_stock*
        timestamptz last_restocked
    }
    PURCHASE-ORDERS {  %% 📊IDX:2
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        timestamptz deleted_at
        uuid location_id* FK
        uuid supplier_id* FK
        varchar order_number* UK
        timestamptz order_date*
        date expected_delivery_date
        decimal total_amount*
        varchar status*
    }
    PURCHASE-ORDER-ITEMS {  %% 📊IDX:2
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        timestamptz deleted_at
        uuid purchase_order_id* FK
        uuid inventory_item_id* FK
        integer quantity*
        decimal unit_cost*
        decimal total_cost*
    }
    SALES {  %% 📊IDX:2
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        timestamptz deleted_at
        uuid customer_id FK
        uuid location_id* FK
        varchar sale_number* UK
        timestamptz sale_date*
        decimal subtotal*
        decimal tax*
        decimal total*
        varchar payment_method*
        integer points_earned*
    }

    CUSTOMERS ||--|| LOYALTY-ACCOUNTS : customer
    EMPLOYEES ||--|{ EMPLOYEE-LOCATIONS : employee
    LOCATIONS ||--|{ EMPLOYEE-LOCATIONS : location
    ROLES ||--|{ EMPLOYEE-LOCATIONS : role
    CATEGORIES ||--|{ PRODUCTS : category
    PRODUCTS ||--|{ PRODUCT-VARIANTS : product
    SUPPLIERS ||--|{ INVENTORY-ITEMS : supplier
    LOCATIONS ||--|{ LOCATION-INVENTORIES : location
    INVENTORY-ITEMS ||--|{ LOCATION-INVENTORIES : inventory_item
    LOCATIONS ||--|{ PURCHASE-ORDERS : location
    SUPPLIERS ||--|{ PURCHASE-ORDERS : supplier
    PURCHASE-ORDERS ||--|{ PURCHASE-ORDER-ITEMS : purchase_order
    INVENTORY-ITEMS ||--|{ PURCHASE-ORDER-ITEMS : inventory_item
    CUSTOMERS ||--o{ SALES : customer
    LOCATIONS ||--|{ SALES : location
```

# Schema Summary

**Tables:** 15
**Columns:** 149
**Indexes:** 15
**Foreign Keys:** 15

## Security
**Tables with PII:** locations, customers, employees, suppliers
**Tables with RLS:** None

## Tables Overview
- **locations** (10 cols, 0 FKs, 0 indexes)
- **customers** (10 cols, 0 FKs, 0 indexes)
- **loyalty_accounts** (9 cols, 1 FKs, 1 indexes)
- **employees** (11 cols, 0 FKs, 0 indexes)
- **roles** (7 cols, 0 FKs, 0 indexes)
- **employee_locations** (10 cols, 3 FKs, 3 indexes)
- **categories** (8 cols, 0 FKs, 0 indexes)
- **products** (10 cols, 1 FKs, 1 indexes)
- **product_variants** (10 cols, 1 FKs, 1 indexes)
- **suppliers** (10 cols, 0 FKs, 0 indexes)
- **inventory_items** (11 cols, 1 FKs, 1 indexes)
- **location_inventories** (10 cols, 2 FKs, 2 indexes)
- **purchase_orders** (11 cols, 2 FKs, 2 indexes)
- **purchase_order_items** (9 cols, 2 FKs, 2 indexes)
- **sales** (13 cols, 2 FKs, 2 indexes)

## Legend
- **PK** = Primary Key
- **FK** = Foreign Key  
- **UK** = Unique Key
- **🔐** = PII (Personal Identifiable Information)
- **🔒RLS** = Row Level Security enabled
- **📊IDX** = Indexed columns
- **\*** after column name = NOT NULL (required)
- **[CASCADE]** = ON DELETE CASCADE

```
