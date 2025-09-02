# Bike Taxi Booking Platform

This repository contains a fullstack bike taxi booking platform. This backend (Django + DRF) handles:
- User registration/login
- Ride booking and driver matching
- Real-time ride tracking (simulated via pings)
- Payment records and capture simulation
- API docs at /docs and /redoc

Quickstart:
- Install requirements: pip install -r bike_taxi_backend/requirements.txt
- Run migrations: python bike_taxi_backend/manage.py migrate
- Start server: python bike_taxi_backend/manage.py runserver 0.0.0.0:8000

Key endpoints (all under /api/):
- GET /api/health/
- POST /api/auth/register
- POST /api/auth/login
- GET /api/auth/me
- POST /api/rides/ (create ride)
- POST /api/rides/{id}/action (match|start|complete|cancel)
- POST /api/rides/{id}/ping (driver location ping)
- GET /api/payments/
- POST /api/payments/{id}/capture

OpenAPI JSON: /openapi.json
Swagger UI: /docs
Redoc: /redoc