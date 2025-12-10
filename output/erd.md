# ERD

```mermaid
# Entity Relationship Diagram

```mermaid
erDiagram
    COMPANIES {  %% 🔒RLS ⚠️PII:3 📊IDX:3
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        varchar name*
        text address 🔐
        varchar phone 🔐
        varchar email 🔐
        varchar registration_number UK
        timestamptz deleted_at
    }
    VEHICLE-TYPES {  %% 📊IDX:3
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        varchar type_name* UK
        text description
        varchar fuel_type
        integer capacity
        timestamptz deleted_at
    }
    MAINTENANCE-TYPES {  %% 📊IDX:2
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        varchar type_name* UK
        text description
        decimal estimated_cost
        integer estimated_duration
        timestamptz deleted_at
    }
    MANAGERS {  %% 🔒RLS ⚠️PII:4 📊IDX:5
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        uuid company_id* FK
        varchar first_name* 🔐
        varchar last_name* 🔐
        varchar email* UK🔐
        varchar phone 🔐
        varchar department
        varchar access_level*
        timestamptz deleted_at
    }
    DRIVERS {  %% 🔒RLS ⚠️PII:5 📊IDX:5
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        uuid company_id* FK
        varchar first_name* 🔐
        varchar last_name* 🔐
        varchar license_number* UK🔐
        varchar phone 🔐
        varchar email 🔐
        date hire_date*
        timestamptz deleted_at
    }
    VEHICLES {  %% 🔒RLS 📊IDX:8
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        uuid company_id* FK
        uuid vehicle_type_id* FK
        varchar make*
        varchar model*
        integer year*
        varchar license_plate* UK
        varchar vin* UK
        date purchase_date
        integer mileage
        varchar status*
        timestamptz deleted_at
    }
    VEHICLE-ASSIGNMENTS {  %% 🔒RLS 📊IDX:7
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        uuid driver_id* FK
        uuid vehicle_id* FK
        date assignment_date*
        date end_date
        boolean is_active*
        text notes
        timestamptz deleted_at
    }
    MAINTENANCE-SCHEDULES {  %% 🔒RLS 📊IDX:6
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        uuid vehicle_id* FK
        uuid maintenance_type_id* FK
        integer interval_miles
        integer interval_days
        date last_performed
        date next_due
        text description
        boolean is_active*
        timestamptz deleted_at
    }
    MAINTENANCE-RECORDS {  %% 🔒RLS 📊IDX:6
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        uuid vehicle_id* FK
        uuid maintenance_type_id* FK
        date performed_date*
        text description
        decimal cost
        integer mileage_at_service
        varchar service_provider
        varchar invoice_number
        timestamptz deleted_at
    }
    FUEL-LOGS {  %% 🔒RLS 📊IDX:5
        uuid id PK
        timestamptz created_at*
        timestamptz updated_at*
        uuid vehicle_id* FK
        date date*
        decimal amount*
        decimal cost*
        decimal price_per_unit*
        integer mileage
        varchar location
        varchar receipt_number
        timestamptz deleted_at
    }
    LOCATION-LOGS {  %% 🔒RLS 📊IDX:5
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
        decimal altitude
    }

    COMPANIES ||--|{ MANAGERS : company [CASCADE]
    COMPANIES ||--|{ DRIVERS : company [CASCADE]
    COMPANIES ||--|{ VEHICLES : company [CASCADE]
    VEHICLE-TYPES ||--|{ VEHICLES : vehicle_type
    DRIVERS ||--|{ VEHICLE-ASSIGNMENTS : driver [CASCADE]
    VEHICLES ||--|{ VEHICLE-ASSIGNMENTS : vehicle [CASCADE]
    VEHICLES ||--|{ MAINTENANCE-SCHEDULES : vehicle [CASCADE]
    MAINTENANCE-TYPES ||--|{ MAINTENANCE-SCHEDULES : maintenance_type
    VEHICLES ||--|{ MAINTENANCE-RECORDS : vehicle [CASCADE]
    MAINTENANCE-TYPES ||--|{ MAINTENANCE-RECORDS : maintenance_type
    VEHICLES ||--|{ FUEL-LOGS : vehicle [CASCADE]
    VEHICLES ||--|{ LOCATION-LOGS : vehicle [CASCADE]
```

# Schema Summary

**Tables:** 11
**Columns:** 118
**Indexes:** 55
**Foreign Keys:** 12

## Security
**Tables with PII:** companies, managers, drivers
**Tables with RLS:** companies, managers, drivers, vehicles, vehicle_assignments, maintenance_schedules, maintenance_records, fuel_logs, location_logs

## Tables Overview
- **companies** (9 cols, 0 FKs, 3 indexes)
- **vehicle_types** (8 cols, 0 FKs, 3 indexes)
- **maintenance_types** (8 cols, 0 FKs, 2 indexes)
- **managers** (11 cols, 1 FKs, 5 indexes)
- **drivers** (11 cols, 1 FKs, 5 indexes)
- **vehicles** (14 cols, 2 FKs, 8 indexes)
- **vehicle_assignments** (10 cols, 2 FKs, 7 indexes)
- **maintenance_schedules** (12 cols, 2 FKs, 6 indexes)
- **maintenance_records** (12 cols, 2 FKs, 6 indexes)
- **fuel_logs** (12 cols, 1 FKs, 5 indexes)
- **location_logs** (11 cols, 1 FKs, 5 indexes)

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
