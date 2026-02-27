# Inventory Pro

A production-style inventory management web app built with Django + PostgreSQL.
Designed as a portfolio project showcasing authentication, role-based access, audit logging, reporting, and transaction-safe stock management.

## Live Demo
- URL: https://inventory-pro-6dcu.onrender.com
- Demo account:
  - Username : staff_user
  - Password : inventory-DEMO

## Features
- Authentication (login/logout)
- Role-based access (Admin vs Staff)
- Products CRUD (name, SKU, category, cost, price, qty, reorder level)
- Stock IN/OUT transactions with full history
- Dashboard: low stock + top movers
- Reports export: CSV + PDF
- Audit logs (resume feature)

## Tech Stack
- Backend: Django
- Database: PostgreSQL (Docker locally, Render in production)
- Deployment: Render
- PDF Export: ReportLab
- Auth/Roles: Django auth + Groups

## Screenshots
-----

## Local Setup (Windows)
### Prereqs
- Python 3.12+
- Docker Desktop
- Git

### Run locally
```bash
cd backend
.\.venv\Scripts\Activate.ps1
docker compose up -d
python manage.py migrate
python manage.py runserver