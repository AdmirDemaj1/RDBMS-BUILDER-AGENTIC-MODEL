# ERD

```mermaid
# Entity Relationship Diagram

```mermaid
erDiagram
    COMPANIES {  %% 🔒RLS ⚠️PII:3 📊IDX:2
        uuid id PK
        varchar name*
        text address 🔐
        varchar contact_email 🔐
        varchar contact_phone 🔐
        varchar registration_number UK
        timestamptz created_at*
        timestamptz updated_at*
    }
    VEHICLE-TYPES {  %% 📊IDX:1
        uuid id PK
        varchar type_name* UK
        text description
        decimal fuel_capacity
        decimal max_load_capacity
        timestamptz created_at*
        timestamptz updated_at*
    }
    VEHICLES {  %% 🔒RLS 📊IDX:4
        uuid id PK
        uuid company_id* FK
        uuid vehicle_type_id* FK
        varchar make*
        varchar model*
        integer year*
        varchar license_plate* UK
        varchar vin UK
        decimal current_mileage*
        timestamptz created_at*
        timestamptz updated_at*
    }
    DRIVERS {  %% 🔒RLS ⚠️PII:5 📊IDX:5
        uuid id PK
        uuid company_id* FK
        uuid vehicle_id FK
        varchar first_name* 🔐
        varchar last_name* 🔐
        varchar license_number* UK🔐
        date license_expiry_date*
        varchar contact_phone 🔐
        varchar email 🔐
        timestamptz created_at*
        timestamptz updated_at*
    }
    MANAGERS {  %% 🔒RLS ⚠️PII:3 📊IDX:3
        uuid id PK
        uuid company_id* FK
        varchar first_name* 🔐
        varchar last_name* 🔐
        varchar email* UK🔐
        varchar access_level*
        varchar department
        timestamptz created_at*
        timestamptz updated_at*
    }
    MAINTENANCE-LOGS {  %% 🔒RLS 📊IDX:3
        uuid id PK
        uuid vehicle_id* FK
        date maintenance_date*
        text description*
        decimal cost*
        varchar service_provider
        decimal mileage_at_service*
        decimal next_service_due
        timestamptz created_at*
        timestamptz updated_at*
    }
    FUEL-LOGS {  %% 🔒RLS 📊IDX:3
        uuid id PK
        uuid vehicle_id* FK
        date fuel_date*
        decimal amount*
        decimal cost*
        decimal price_per_unit*
        varchar location
        decimal mileage_at_fueling*
        varchar fuel_type*
        timestamptz created_at*
        timestamptz updated_at*
    }
    LOCATION-TRACKINGS {  %% 🔒RLS 📊IDX:3
        uuid id PK
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
    VEHICLES ||--o| DRIVERS : vehicle
    COMPANIES ||--|{ MANAGERS : company [CASCADE]
    VEHICLES ||--|{ MAINTENANCE-LOGS : vehicle [CASCADE]
    VEHICLES ||--|{ FUEL-LOGS : vehicle [CASCADE]
    VEHICLES ||--|{ LOCATION-TRACKINGS : vehicle [CASCADE]
```

# Schema Summary

**Tables:** 8
**Columns:** 77
**Indexes:** 24
**Foreign Keys:** 8

## Security
**Tables with PII:** companies, drivers, managers
**Tables with RLS:** companies, vehicles, drivers, managers, maintenance_logs, fuel_logs, location_trackings

## Tables Overview
- **companies** (8 cols, 0 FKs, 2 indexes)
- **vehicle_types** (7 cols, 0 FKs, 1 indexes)
- **vehicles** (11 cols, 2 FKs, 4 indexes)
- **drivers** (11 cols, 2 FKs, 5 indexes)
- **managers** (9 cols, 1 FKs, 3 indexes)
- **maintenance_logs** (10 cols, 1 FKs, 3 indexes)
- **fuel_logs** (11 cols, 1 FKs, 3 indexes)
- **location_trackings** (10 cols, 1 FKs, 3 indexes)

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
