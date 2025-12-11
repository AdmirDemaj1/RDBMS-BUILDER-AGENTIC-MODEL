# ERD

```mermaid
# Entity Relationship Diagram

```mermaid
erDiagram
    COMPANIES {  %% 🔒RLS ⚠️PII:3 📊IDX:2
        uuid id* PK
        varchar name*
        text address 🔐
        varchar phone 🔐
        varchar email 🔐
        varchar registration_number UK
        timestamptz created_at*
        timestamptz updated_at*
    }
    VEHICLE-TYPES {  %% 📊IDX:1
        uuid id* PK
        varchar type_name* UK
        text description
        timestamptz created_at*
        timestamptz updated_at*
    }
    MAINTENANCE-TYPES {  %% 📊IDX:1
        uuid id* PK
        varchar type_name* UK
        text description
        integer default_interval
        timestamptz created_at*
        timestamptz updated_at*
    }
    VEHICLES {  %% 🔒RLS 📊IDX:5
        uuid id* PK
        uuid company_id* FK
        uuid vehicle_type_id* FK
        varchar make*
        varchar model*
        integer year*
        varchar license_plate* UK
        varchar vin* UK
        integer mileage
        timestamptz created_at*
        timestamptz updated_at*
    }
    DRIVERS {  %% 🔒RLS ⚠️PII:5 📊IDX:4
        uuid id* PK
        uuid company_id* FK
        varchar first_name* 🔐
        varchar last_name* 🔐
        varchar license_number* UK🔐
        varchar phone 🔐
        varchar email 🔐
        date hire_date*
        timestamptz created_at*
        timestamptz updated_at*
    }
    USERS {  %% 🔒RLS ⚠️PII:3 📊IDX:6
        uuid id* PK
        uuid company_id* FK
        uuid driver_id FK
        varchar username* UK
        varchar email* UK🔐
        varchar first_name* 🔐
        varchar last_name* 🔐
        varchar role*
        boolean is_active*
        timestamptz created_at*
        timestamptz updated_at*
    }
    DRIVER-ASSIGNMENTS {  %% 🔒RLS 📊IDX:6
        uuid id* PK
        uuid vehicle_id* FK
        uuid driver_id* FK
        date start_date*
        date end_date
        boolean is_active*
        timestamptz created_at*
        timestamptz updated_at*
    }
    MAINTENANCE-SCHEDULES {  %% 🔒RLS 📊IDX:6
        uuid id* PK
        uuid vehicle_id* FK
        uuid maintenance_type_id* FK
        text description
        date scheduled_date*
        date due_date*
        boolean is_completed*
        integer mileage_interval
        timestamptz created_at*
        timestamptz updated_at*
    }
    FUEL-LOGS {  %% 🔒RLS 📊IDX:5
        uuid id* PK
        uuid vehicle_id* FK
        date date*
        decimal amount*
        decimal cost*
        integer odometer*
        varchar fuel_type*
        varchar location
        timestamptz created_at*
        timestamptz updated_at*
    }
    LOCATION-TRACKINGS {  %% 🔒RLS 📊IDX:4
        uuid id* PK
        uuid vehicle_id* FK
        decimal latitude*
        decimal longitude*
        timestamptz timestamp*
        decimal speed
        decimal heading
        decimal accuracy
        timestamptz created_at*
        timestamptz updated_at*
    }

    COMPANIES ||--|{ VEHICLES : company [CASCADE]
    VEHICLE-TYPES ||--|{ VEHICLES : vehicle_type
    COMPANIES ||--|{ DRIVERS : company [CASCADE]
    COMPANIES ||--|{ USERS : company [CASCADE]
    DRIVERS ||--o| USERS : driver
    VEHICLES ||--|{ DRIVER-ASSIGNMENTS : vehicle [CASCADE]
    DRIVERS ||--|{ DRIVER-ASSIGNMENTS : driver [CASCADE]
    VEHICLES ||--|{ MAINTENANCE-SCHEDULES : vehicle [CASCADE]
    MAINTENANCE-TYPES ||--|{ MAINTENANCE-SCHEDULES : maintenance_type
    VEHICLES ||--|{ FUEL-LOGS : vehicle [CASCADE]
    VEHICLES ||--|{ LOCATION-TRACKINGS : vehicle [CASCADE]
```

# Schema Summary

**Tables:** 10
**Columns:** 89
**Indexes:** 40
**Foreign Keys:** 11

## Security
**Tables with PII:** companies, drivers, users
**Tables with RLS:** companies, vehicles, drivers, users, driver_assignments, maintenance_schedules, fuel_logs, location_trackings

## Tables Overview
- **companies** (8 cols, 0 FKs, 2 indexes)
- **vehicle_types** (5 cols, 0 FKs, 1 indexes)
- **maintenance_types** (6 cols, 0 FKs, 1 indexes)
- **vehicles** (11 cols, 2 FKs, 5 indexes)
- **drivers** (10 cols, 1 FKs, 4 indexes)
- **users** (11 cols, 2 FKs, 6 indexes)
- **driver_assignments** (8 cols, 2 FKs, 6 indexes)
- **maintenance_schedules** (10 cols, 2 FKs, 6 indexes)
- **fuel_logs** (10 cols, 1 FKs, 5 indexes)
- **location_trackings** (10 cols, 1 FKs, 4 indexes)

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
