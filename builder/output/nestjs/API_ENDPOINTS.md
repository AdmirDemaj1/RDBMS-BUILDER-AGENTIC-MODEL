# API Endpoints Documentation


## Auth

### POST `/api/auth/login`

Manager authentication

---


## Companies

### GET `/api/companies/:companyId/vehicles`

Get company fleet vehicles

---


## Vehicles

### POST `/api/vehicles/:vehicleId/locations`

Record real-time GPS location

---

### GET `/api/vehicles/:vehicleId/current-location`

Get current vehicle location

---

### POST `/api/vehicles/:vehicleId/fuel-logs`

Record fuel consumption

---

### POST `/api/vehicles/:vehicleId/maintenance`

Log maintenance activity

---

### PUT `/api/vehicles/:vehicleId/driver`

Assign driver to vehicle

---


## Reports

### GET `/api/reports/fleet-performance`

Generate fleet performance reports

---


## Vehicles

### GET `/api/vehicles/:vehicleId/maintenance`

Get vehicle maintenance history

---


## Companies

### GET `/api/companies/:companyId/drivers`

Get company drivers list

---

