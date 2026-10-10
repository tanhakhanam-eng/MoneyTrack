# MoneyTrack

MoneyTrack is a mobile-first business workflow for home-based sellers in Bangladesh. This repository starts with the core business foundation: secure authentication, business-scoped data, product/customer management, and order dashboard APIs.

## Stack

- Frontend: Next.js + TypeScript + Tailwind
- Backend: FastAPI + SQLAlchemy + PostgreSQL-ready configuration
- Database: PostgreSQL-compatible SQLAlchemy models with SQLite fallback for local development

## Repository structure

- backend: FastAPI API and data models
- frontend: Next.js app shell
- docs: product planning and implementation notes

## Quick start

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Notes

This MVP focuses on the business-critical flow: register a user, create a business, add products/customers, create orders, track payments, and compute dashboard numbers. The app is intentionally designed around correct financial logic rather than superficial visual complexity.
