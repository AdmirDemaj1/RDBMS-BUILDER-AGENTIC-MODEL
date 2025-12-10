# API Endpoints Documentation


## Auth

### POST `/api/auth/login`

Manager login with email and password

**Request Body**: LoginDto with email and password

**Response**: JWT access token and refresh token

---

### POST `/api/auth/refresh`

Refresh JWT access token using refresh token

**Request Body**: RefreshTokenDto

**Response**: New JWT access token

---

### POST `/api/auth/logout`

Logout and invalidate tokens

**Response**: Success confirmation

---

### GET `/api/auth/profile`

Get current manager profile information

**Response**: Manager profile data

---


## Companies

### POST `/api/companies`

Register a new fleet management company

**Request Body**: CreateCompanyDto with name, address, phone, email, registration_number

**Response**: Created company details

---

### GET `/api/companies/:id`

Get company details by ID

**Response**: Company information

---

### PUT `/api/companies/:id`

Update company information

**Request Body**: UpdateCompanyDto

**Response**: Updated company details

---

### DELETE `/api/companies/:id`

Soft delete a company

**Response**: Deletion confirmation

---


## Managers

### POST `/api/managers`

Create a new manager for a company

**Request Body**: CreateManagerDto with company_id, personal info, department, access_level

**Response**: Created manager details

---

### GET `/api/managers`

Get paginated list of managers with filtering by company, department, access_level

**Response**: Paginated manager list

---

### GET `/api/managers/:id`

Get manager details by ID

**Response**: Manager information

---

### PUT `/api/managers/:id`

Update manager information

**Request Body**: UpdateManagerDto

**Response**: Updated manager details

---

### DELETE `/api/managers/:id`

Soft delete a manager

**Response**: Deletion confirmation

---


## Drivers

### POST `/api/drivers`

Add a new driver to a company

**Request Body**: CreateDriverDto with company_id, personal info, license_number, hire_date

**Response**: Created driver details

---

### GET `/api/drivers`

Get paginated list of drivers with filtering by company, hire_date range

**Response**: Paginated driver list

---

### GET `/api/drivers/:id`

Get driver details by ID

**Response**: Driver information

---

### PUT `/api/drivers/:id`

Update driver information

**Request Body**: UpdateDriverDto

**Response**: Updated driver details

---

### DELETE `/api/drivers/:id`

Soft delete a driver

**Response**: Deletion confirmation

---

### GET `/api/drivers/:id/assignments`

Get driver's vehicle assignment history

**Response**: List of vehicle assignments

---


## Vehicle Types

### POST `/api/vehicle-types`

Create a new vehicle type

**Request Body**: CreateVehicleTypeDto with type_name, description, fuel_type, capacity

**Response**: Created vehicle type details

---

### GET `/api/vehicle-types`

Get list of all vehicle types with filtering by fuel_type

**Response**: List of vehicle types

---

### GET `/api/vehicle-types/:id`

Get vehicle type details by ID

**Response**: Vehicle type information

---

### PUT `/api/vehicle-types/:id`

Update vehicle type information

**Request Body**: UpdateVehicleTypeDto

**Response**: Updated vehicle type details

---

### DELETE `/api/vehicle-types/:id`

Soft delete a vehicle type

**Response**: Deletion confirmation

---


## Vehicles

### POST `/api/vehicles`

Add a new vehicle to company fleet

**Request Body**: CreateVehicleDto with company_id, vehicle_type_id, make, model, year, license_plate, vin, purchase_date

**Response**: Created vehicle details

---

### GET `/api/vehicles`

Get paginated list of vehicles with filtering by company, status, make, model, year

**Response**: Paginated vehicle list

---

### GET `/api/vehicles/:id`

Get vehicle details by ID

**Response**: Vehicle information with current assignment

---

### PUT `/api/vehicles/:id`

Update vehicle information

**Request Body**: UpdateVehicleDto

**Response**: Updated vehicle details

---

### PATCH `/api/vehicles/:id/status`

Update vehicle status (active, maintenance, retired)

**Request Body**: UpdateVehicleStatusDto

**Response**: Updated vehicle status

---

### DELETE `/api/vehicles/:id`

Soft delete a vehicle

**Response**: Deletion confirmation

---


## Vehicle Assignments

### POST `/api/vehicle-assignments`

Assign a driver to a vehicle

**Request Body**: CreateVehicleAssignmentDto with driver_id, vehicle_id, assignment_date, notes

**Response**: Created assignment details

---

### GET `/api/vehicle-assignments`

Get paginated list of assignments with filtering by driver, vehicle, active status

**Response**: Paginated assignment list

---

### GET `/api/vehicle-assignments/active`

Get all currently active vehicle assignments

**Response**: List of active assignments

---

### PATCH `/api/vehicle-assignments/:id/end`

End a vehicle assignment

**Request Body**: EndAssignmentDto with end_date and notes

**Response**: Updated assignment with end_date

---

### GET `/api/vehicle-assignments/:id`

Get assignment details by ID

**Response**: Assignment information

---


## Maintenance Types

### POST `/api/maintenance-types`

Create a new maintenance type

**Request Body**: CreateMaintenanceTypeDto with type_name, description, estimated_cost, estimated_duration

**Response**: Created maintenance type details

---

### GET `/api/maintenance-types`

Get list of all maintenance types

**Response**: List of maintenance types

---

### GET `/api/maintenance-types/:id`

Get maintenance type details by ID

**Response**: Maintenance type information

---

### PUT `/api/maintenance-types/:id`

Update maintenance type information

**Request Body**: UpdateMaintenanceTypeDto

**Response**: Updated maintenance type details

---

### DELETE `/api/maintenance-types/:id`

Soft delete a maintenance type

**Response**: Deletion confirmation

---


## Maintenance

### POST `/api/maintenance/schedules`

Create a maintenance schedule for a vehicle

**Request Body**: CreateMaintenanceScheduleDto with vehicle_id, maintenance_type_id, intervals, description

**Response**: Created schedule details

---

### GET `/api/maintenance/schedules`

Get paginated maintenance schedules with filtering by vehicle, due date, active status

**Response**: Paginated schedule list

---

### GET `/api/maintenance/schedules/due`

Get maintenance schedules due within specified days

**Response**: List of due maintenance schedules

---

### POST `/api/maintenance/records`

Record completed maintenance activity

**Request Body**: CreateMaintenanceRecordDto with vehicle_id, maintenance_type_id, performed_date, cost, description

**Response**: Created maintenance record

---

### GET `/api/maintenance/records`

Get paginated maintenance records with filtering by vehicle, date range, service provider

**Response**: Paginated maintenance records

---

### GET `/api/maintenance/vehicles/:vehicleId/history`

Get complete maintenance history for a vehicle

**Response**: Vehicle maintenance history

---

### PUT `/api/maintenance/schedules/:id`

Update maintenance schedule

**Request Body**: UpdateMaintenanceScheduleDto

**Response**: Updated schedule details

---


## Fuel Logs

### POST `/api/fuel-logs`

Record fuel purchase/consumption for a vehicle

**Request Body**: CreateFuelLogDto with vehicle_id, date, amount, cost, price_per_unit, mileage, location

**Response**: Created fuel log entry

---

### GET `/api/fuel-logs`

Get paginated fuel logs with filtering by vehicle, date range, location

**Response**: Paginated fuel log list

---

### GET `/api/fuel-logs/vehicles/:vehicleId`

Get fuel consumption history for a specific vehicle

**Response**: Vehicle fuel history

---

### GET `/api/fuel-logs/analytics/consumption`

Get fuel consumption analytics by vehicle, time period

**Response**: Fuel consumption analytics data

---

### GET `/api/fuel-logs/analytics/costs`

Get fuel cost analytics and trends

**Response**: Fuel cost analytics data

---

### PUT `/api/fuel-logs/:id`

Update fuel log entry

**Request Body**: UpdateFuelLogDto

**Response**: Updated fuel log details

---

### DELETE `/api/fuel-logs/:id`

Soft delete a fuel log entry

**Response**: Deletion confirmation

---


## Location Logs

### POST `/api/location-logs`

Record GPS location data for a vehicle

**Request Body**: CreateLocationLogDto with vehicle_id, timestamp, latitude, longitude, speed, heading

**Response**: Created location log entry

---

### POST `/api/location-logs/batch`

Bulk insert multiple location records

**Request Body**: Array of CreateLocationLogDto

**Response**: Batch insert confirmation

---

### GET `/api/location-logs/vehicles/:vehicleId/current`

Get current/latest location of a vehicle

**Response**: Current vehicle location

---

### GET `/api/location-logs/vehicles/:vehicleId/history`

Get location history for a vehicle within date range

**Response**: Vehicle location history

---

### GET `/api/location-logs/vehicles/:vehicleId/route`

Get route/path taken by vehicle for a specific date

**Response**: Vehicle route data

---

### GET `/api/location-logs/fleet/live`

Get live locations of all vehicles in fleet

**Response**: Fleet live location data

---


## Reports

### GET `/api/reports/fleet-overview`

Generate comprehensive fleet overview report

**Response**: Fleet overview analytics

---

### GET `/api/reports/vehicle-utilization`

Generate vehicle utilization report by date range

**Response**: Vehicle utilization analytics

---

### GET `/api/reports/maintenance-costs`

Generate maintenance cost analysis report

**Response**: Maintenance cost analytics

---

### GET `/api/reports/fuel-efficiency`

Generate fuel efficiency report by vehicle and time period

**Response**: Fuel efficiency analytics

---

### GET `/api/reports/driver-performance`

Generate driver performance report including assignments and vehicle usage

**Response**: Driver performance analytics

---

### POST `/api/reports/custom`

Generate custom report based on specified parameters

**Request Body**: CustomReportDto with report parameters and filters

**Response**: Custom report data

---

### GET `/api/reports/export/:reportType`

Export report data in specified format (PDF, Excel, CSV)

**Response**: Report file download

---

