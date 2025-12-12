# API Endpoints Documentation


## Auth

### POST `/api/auth/login`

Manager authentication

---


## Vehicles

### GET `/api/vehicles`

Get company vehicles with filters

---

### POST `/api/vehicles/:vehicleId/locations`

Record real-time GPS location

---

### GET `/api/vehicles/:vehicleId/current-location`

Get current vehicle location

---


## Drivers

### POST `/api/drivers/:id/assign-vehicle`

Assign driver to vehicle

---


## Vehicles

### POST `/api/vehicles/:vehicleId/maintenance`

Log maintenance record

---

### POST `/api/vehicles/:vehicleId/fuel-logs`

Record fuel consumption

---


## Reports

### GET `/api/reports/fleet-performance`

Generate fleet performance report

---

### GET `/api/reports/fuel-consumption`

Generate fuel consumption report

---

### GET `/api/reports/maintenance-summary`

Generate maintenance summary report

---

