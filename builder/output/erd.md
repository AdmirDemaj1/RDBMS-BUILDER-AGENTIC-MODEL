# ERD

```mermaid
# Entity Relationship Diagram

```mermaid
erDiagram
    COMPANIES {  %% ⚠️PII:2
        uuid id* PK
        timestamptz created_at*
        timestamptz updated_at*
        timestamptz deleted_at
        varchar name*
        varchar address*
        varchar contact_email* 🔐
        varchar contact_phone* 🔐
        varchar registration_number*
    }
    VEHICLE-TYPES {
        uuid id* PK
        timestamptz created_at*
        timestamptz updated_at*
        timestamptz deleted_at
        varchar type_name*
        varchar description
        decimal fuel_capacity
        decimal max_weight
    }
    VEHICLES {  %% 📊IDX:2
        uuid id* PK
        timestamptz created_at*
        timestamptz updated_at*
        timestamptz deleted_at
        uuid company_id* FK
        uuid vehicle_type_id* FK
        varchar make*
        varchar model*
        varchar year*
        varchar license_plate* UK
        varchar vin* UK
        decimal current_mileage*
    }
    DRIVERS {  %% ⚠️PII:5 📊IDX:2
        uuid id* PK
        timestamptz created_at*
        timestamptz updated_at*
        timestamptz deleted_at
        uuid company_id* FK
        uuid vehicle_id FK
        varchar first_name* 🔐
        varchar last_name* 🔐
        varchar license_number* UK🔐
        timestamptz license_expiry_date*
        varchar contact_phone* 🔐
        varchar email* 🔐
    }
    MANAGERS {  %% ⚠️PII:3 📊IDX:1
        uuid id* PK
        timestamptz created_at*
        timestamptz updated_at*
        timestamptz deleted_at
        uuid company_id* FK
        varchar first_name* 🔐
        varchar last_name* 🔐
        varchar email* 🔐
        varchar access_level*
        varchar department*
    }
    MAINTENANCE-LOGS {  %% 📊IDX:1
        uuid id* PK
        timestamptz created_at*
        timestamptz updated_at*
        timestamptz deleted_at
        uuid vehicle_id* FK
        timestamptz maintenance_date*
        varchar description*
        decimal cost*
        varchar service_provider*
        decimal mileage_at_service*
        decimal next_service_due
    }
    FUEL-LOGS {  %% 📊IDX:1
        uuid id* PK
        timestamptz created_at*
        timestamptz updated_at*
        timestamptz deleted_at
        uuid vehicle_id* FK
        timestamptz fuel_date*
        decimal amount*
        decimal cost*
        varchar fuel_type*
        varchar location*
        decimal mileage_at_fueling*
    }
    LOCATION-TRACKINGS {  %% 📊IDX:1
        uuid id* PK
        timestamptz created_at*
        timestamptz updated_at*
        timestamptz deleted_at
        uuid vehicle_id* FK
        decimal latitude*
        decimal longitude*
        timestamptz timestamp*
        decimal speed
        decimal heading
        decimal accuracy
    }

    COMPANIES ||--|{ VEHICLES : company
    VEHICLE-TYPES ||--|{ VEHICLES : vehicle_type
    COMPANIES ||--|{ DRIVERS : company
    VEHICLES ||--o{ DRIVERS : vehicle
    COMPANIES ||--|{ MANAGERS : company
    VEHICLES ||--|{ MAINTENANCE-LOGS : vehicle
    VEHICLES ||--|{ FUEL-LOGS : vehicle
    VEHICLES ||--|{ LOCATION-TRACKINGS : vehicle
```

# Schema Summary

**Tables:** 8
**Columns:** 84
**Indexes:** 8
**Foreign Keys:** 8

## Security
**Tables with PII:** companies, drivers, managers
**Tables with RLS:** None

## Tables Overview
- **companies** (9 cols, 0 FKs, 0 indexes)
- **vehicle_types** (8 cols, 0 FKs, 0 indexes)
- **vehicles** (12 cols, 2 FKs, 2 indexes)
- **drivers** (12 cols, 2 FKs, 2 indexes)
- **managers** (10 cols, 1 FKs, 1 indexes)
- **maintenance_logs** (11 cols, 1 FKs, 1 indexes)
- **fuel_logs** (11 cols, 1 FKs, 1 indexes)
- **location_trackings** (11 cols, 1 FKs, 1 indexes)

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
