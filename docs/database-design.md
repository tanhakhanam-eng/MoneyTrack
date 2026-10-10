# Database design notes

The backend uses SQLAlchemy models that are PostgreSQL-ready and can run against SQLite for local development.

Key design choices:

- business_id on all tenant-owned tables
- user and business membership table for scoping
- historical order snapshots for unit_cost_p and unit_price_p
- separate payment and cashbook records to avoid double-counting
- stock movement tracking for inventory changes and cancellations
