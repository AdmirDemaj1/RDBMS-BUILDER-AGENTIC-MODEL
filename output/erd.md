# ERD

```mermaid
# Entity Relationship Diagram

```mermaid
erDiagram
    COMPANIES {  %% ⚠️PII:3 📊IDX:4
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        varchar name*
        varchar registration_number* UK
        text address 🔐
        varchar contact_email 🔐
        varchar contact_phone 🔐
        boolean is_active*
        timestamptz deleted_at
    }
    VEHICLE-TYPES {  %% 📊IDX:2
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        varchar name* UK
        text description
        varchar fuel_type*
        decimal average_fuel_consumption
    }
    VEHICLES {  %% 📊IDX:8
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        uuid company_id* FK
        uuid vehicle_type_id* FK
        varchar license_plate* UK
        varchar make*
        varchar model*
        integer year*
        varchar vin* UK
        date purchase_date
        integer mileage*
        varchar status*
        timestamptz deleted_at
    }
    DRIVERS {  %% ⚠️PII:5 📊IDX:6
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        varchar first_name* 🔐
        varchar last_name* 🔐
        varchar license_number* UK🔐
        date license_expiry_date*
        varchar contact_phone 🔐
        varchar email 🔐
        boolean is_active*
        timestamptz deleted_at
    }
    ROLES {  %% 📊IDX:2
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        varchar name* UK
        text description
        jsonb permissions*
    }
    USERS {  %% 🔒RLS ⚠️PII:3 📊IDX:6
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        uuid role_id* FK
        varchar username* UK
        varchar email* UK🔐
        varchar first_name* 🔐
        varchar last_name* 🔐
        varchar password_hash*
        boolean is_active*
        timestamptz last_login_at
        timestamptz deleted_at
    }
    MAINTENANCE-SCHEDULES {  %% 📊IDX:5
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        uuid vehicle_id* FK
        varchar maintenance_type*
        text description
        integer interval_miles
        integer interval_days
        date last_performed_date
        date next_due_date
        boolean is_active*
    }
    FUEL-LOGS {  %% 📊IDX:6
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        uuid vehicle_id* FK
        uuid driver_id FK
        date date*
        decimal amount*
        decimal cost*
        decimal price_per_unit*
        integer odometer*
        varchar location
    }
    LOCATION-LOGS {  %% 📊IDX:5
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        uuid vehicle_id* FK
        timestamptz timestamp*
        decimal latitude*
        decimal longitude*
        decimal speed
        decimal heading
        decimal accuracy
    }
    DRIVER-ASSIGNMENTS {  %% 📊IDX:7
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        uuid driver_id* FK
        uuid vehicle_id* FK
        date start_date*
        date end_date
        boolean is_active*
        text notes
    }
    USER-COMPANY-ACCESS {  %% 🔒RLS 📊IDX:7
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        uuid user_id* FK
        uuid company_id* FK
        varchar access_level*
        date granted_date*
        uuid granted_by FK
        boolean is_active*
    }
    DRIVER-COMPANY-EMPLOYMENT {  %% 📊IDX:7
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        uuid driver_id* FK
        uuid company_id* FK
        date start_date*
        date end_date
        varchar employment_status*
        varchar position
        decimal salary
        text notes
    }

    COMPANIES ||--|{ VEHICLES : company
    VEHICLE-TYPES ||--|{ VEHICLES : vehicle_type
    ROLES ||--|{ USERS : role
    VEHICLES ||--|{ MAINTENANCE-SCHEDULES : vehicle [CASCADE]
    VEHICLES ||--|{ FUEL-LOGS : vehicle [CASCADE]
    DRIVERS ||--o{ FUEL-LOGS : driver
    VEHICLES ||--|{ LOCATION-LOGS : vehicle [CASCADE]
    DRIVERS ||--|{ DRIVER-ASSIGNMENTS : driver [CASCADE]
    VEHICLES ||--|{ DRIVER-ASSIGNMENTS : vehicle [CASCADE]
    USERS ||--|{ USER-COMPANY-ACCESS : user [CASCADE]
    COMPANIES ||--|{ USER-COMPANY-ACCESS : company [CASCADE]
    USERS ||--o{ USER-COMPANY-ACCESS : granted_by
    DRIVERS ||--|{ DRIVER-COMPANY-EMPLOYMENT : driver [CASCADE]
    COMPANIES ||--|{ DRIVER-COMPANY-EMPLOYMENT : company [CASCADE]
```

# Schema Summary

**Tables:** 12
**Columns:** 121
**Indexes:** 65
**Foreign Keys:** 14

## Security
**Tables with PII:** companies, drivers, users
**Tables with RLS:** users, user_company_access

## Tables Overview
- **companies** (10 cols, 0 FKs, 4 indexes)
- **vehicle_types** (7 cols, 0 FKs, 2 indexes)
- **vehicles** (14 cols, 2 FKs, 8 indexes)
- **drivers** (11 cols, 0 FKs, 6 indexes)
- **roles** (6 cols, 0 FKs, 2 indexes)
- **users** (12 cols, 1 FKs, 6 indexes)
- **maintenance_schedules** (11 cols, 1 FKs, 5 indexes)
- **fuel_logs** (11 cols, 2 FKs, 6 indexes)
- **location_logs** (10 cols, 1 FKs, 5 indexes)
- **driver_assignments** (9 cols, 2 FKs, 7 indexes)
- **user_company_access** (9 cols, 3 FKs, 7 indexes)
- **driver_company_employment** (11 cols, 2 FKs, 7 indexes)

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
