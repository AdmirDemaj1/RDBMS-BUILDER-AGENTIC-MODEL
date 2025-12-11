# API Endpoints Documentation


## Auth

### POST `/api/auth/login`

Authenticate user with username/email and password

**Request Body**: LoginDto (username/email, password)

**Response**: JWT access token, refresh token, user profile

---

### POST `/api/auth/refresh`

Refresh expired JWT token using refresh token

**Request Body**: RefreshTokenDto

**Response**: New JWT access token

---

### POST `/api/auth/logout`

Invalidate user session and tokens

**Response**: Success confirmation

---

### GET `/api/auth/profile`

Get current user profile information

**Response**: User profile with company and role details

---


## Companies

### POST `/api/companies`

Register a new company in the system

**Request Body**: CreateCompanyDto (name, address, phone, email, registration_number)

**Response**: Created company details

---

### GET `/api/companies/:id`

Get company details by ID

**Response**: Company profile information

---

### PUT `/api/companies/:id`

Update company information

**Request Body**: UpdateCompanyDto

**Response**: Updated company details

---

### GET `/api/companies/:id/dashboard`

Get company dashboard with fleet overview statistics

**Response**: Dashboard data with vehicle count, active drivers, maintenance alerts

---


## Users

### POST `/api/users`

Create a new user account

**Request Body**: CreateUserDto (username, email, first_name, last_name, role, company_id, driver_id?)

**Response**: Created user details

---

### GET `/api/users`

Get paginated list of users within company

**Response**: Paginated user list with filtering options

---

### GET `/api/users/:id`

Get user details by ID

**Response**: User profile information

---

### PUT `/api/users/:id`

Update user information

**Request Body**: UpdateUserDto

**Response**: Updated user details

---

### PATCH `/api/users/:id/status`

Activate or deactivate user account

**Request Body**: UpdateUserStatusDto (is_active)

**Response**: Updated user status

---


## Vehicles

### POST `/api/vehicles`

Register a new vehicle in the fleet

**Request Body**: CreateVehicleDto (company_id, vehicle_type_id, make, model, year, license_plate, vin, mileage)

**Response**: Created vehicle details

---

### GET `/api/vehicles`

Get paginated list of vehicles with filtering and sorting

**Response**: Paginated vehicle list with company and type details

---

### GET `/api/vehicles/:id`

Get detailed vehicle information

**Response**: Vehicle details with current driver assignment and maintenance status

---

### PUT `/api/vehicles/:id`

Update vehicle information

**Request Body**: UpdateVehicleDto

**Response**: Updated vehicle details

---

### DELETE `/api/vehicles/:id`

Remove vehicle from fleet (soft delete)

**Response**: Deletion confirmation

---


## Vehicle Types

### GET `/api/vehicle-types`

Get list of available vehicle types

**Response**: List of vehicle types with descriptions

---

### POST `/api/vehicle-types`

Create new vehicle type

**Request Body**: CreateVehicleTypeDto (type_name, description)

**Response**: Created vehicle type

---


## Drivers

### POST `/api/drivers`

Register a new driver

**Request Body**: CreateDriverDto (company_id, first_name, last_name, license_number, phone, email, hire_date)

**Response**: Created driver details

---

### GET `/api/drivers`

Get paginated list of drivers with filtering

**Response**: Paginated driver list with current vehicle assignments

---

### GET `/api/drivers/:id`

Get driver details with assignment history

**Response**: Driver profile with current and historical vehicle assignments

---

### PUT `/api/drivers/:id`

Update driver information

**Request Body**: UpdateDriverDto

**Response**: Updated driver details

---


## Driver Assignments

### POST `/api/driver-assignments`

Assign driver to vehicle

**Request Body**: CreateDriverAssignmentDto (vehicle_id, driver_id, start_date)

**Response**: Created assignment details

---

### PATCH `/api/driver-assignments/:id/end`

End current driver assignment

**Request Body**: EndAssignmentDto (end_date)

**Response**: Updated assignment with end date

---

### GET `/api/driver-assignments/history/:vehicleId`

Get assignment history for a specific vehicle

**Response**: List of historical driver assignments

---


## Maintenance Schedules

### POST `/api/maintenance-schedules`

Schedule maintenance for a vehicle

**Request Body**: CreateMaintenanceScheduleDto (vehicle_id, maintenance_type_id, description, scheduled_date, due_date, mileage_interval)

**Response**: Created maintenance schedule

---

### GET `/api/maintenance-schedules`

Get maintenance schedules with filtering by vehicle, date range, completion status

**Response**: Paginated maintenance schedules list

---

### GET `/api/maintenance-schedules/overdue`

Get overdue maintenance schedules

**Response**: List of overdue maintenance items

---

### PATCH `/api/maintenance-schedules/:id/complete`

Mark maintenance schedule as completed

**Request Body**: CompleteMaintenanceDto (completion_date, notes)

**Response**: Updated maintenance schedule

---


## Maintenance Types

### GET `/api/maintenance-types`

Get list of maintenance types

**Response**: List of maintenance types with default intervals

---

### POST `/api/maintenance-types`

Create new maintenance type

**Request Body**: CreateMaintenanceTypeDto (type_name, description, default_interval)

**Response**: Created maintenance type

---


## Fuel Logs

### POST `/api/fuel-logs`

Record fuel purchase/consumption

**Request Body**: CreateFuelLogDto (vehicle_id, date, amount, cost, odometer, fuel_type, location)

**Response**: Created fuel log entry

---

### GET `/api/fuel-logs`

Get fuel logs with filtering by vehicle, date range, fuel type

**Response**: Paginated fuel logs list

---

### GET `/api/fuel-logs/vehicle/:vehicleId`

Get fuel consumption history for specific vehicle

**Response**: Vehicle fuel consumption records

---

### GET `/api/fuel-logs/analytics/:vehicleId`

Get fuel consumption analytics for vehicle

**Response**: Fuel efficiency metrics, cost analysis, consumption trends

---

### PUT `/api/fuel-logs/:id`

Update fuel log entry

**Request Body**: UpdateFuelLogDto

**Response**: Updated fuel log

---


## Location Tracking

### POST `/api/location-tracking`

Record vehicle GPS location data

**Request Body**: CreateLocationTrackingDto (vehicle_id, latitude, longitude, timestamp, speed, heading, accuracy)

**Response**: Created location record

---

### GET `/api/location-tracking/current/:vehicleId`

Get current location of specific vehicle

**Response**: Latest GPS coordinates and movement data

---

### GET `/api/location-tracking/history/:vehicleId`

Get location history for vehicle within date range

**Response**: Historical GPS tracking data

---

### GET `/api/location-tracking/fleet-map`

Get current locations of all vehicles in company fleet

**Response**: Real-time fleet location data for map display

---

### GET `/api/location-tracking/route/:vehicleId`

Get vehicle route for specific date range

**Response**: Route data with waypoints and timestamps

---


## Reports

### GET `/api/reports/fleet-performance`

Generate comprehensive fleet performance report

**Response**: Fleet utilization, fuel efficiency, maintenance costs, driver performance metrics

---

### GET `/api/reports/vehicle-utilization`

Generate vehicle utilization report

**Response**: Vehicle usage statistics, idle time, mileage reports

---

### GET `/api/reports/fuel-consumption`

Generate fuel consumption analysis report

**Response**: Fuel costs, efficiency trends, consumption by vehicle/driver

---

### GET `/api/reports/maintenance-costs`

Generate maintenance cost analysis report

**Response**: Maintenance expenses, upcoming schedules, cost per vehicle

---

### GET `/api/reports/driver-performance`

Generate driver performance report

**Response**: Driver efficiency metrics, fuel consumption, route optimization

---

### POST `/api/reports/custom`

Generate custom report with specified parameters

**Request Body**: CustomReportDto (report_type, date_range, filters, metrics)

**Response**: Custom report data based on specified criteria

---

