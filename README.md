# Billora — Smart Billing & Retail Management System System

A full-stack billing system built using Flask, MySQL, and JavaScript.

## Features
- Product management (Add/Edit/Delete)
- Real-time cart system
- GST calculation
- PDF invoice generation
- Billing history
- Stock management
- Customer loyalty balances: earn one point per ₹100 of final spend; redeem one point as ₹1.
- Server-validated discounts (cashiers up to ₹100; administrators can approve larger discounts).
- Cash, UPI, card, bank-transfer, and split payments with an exact-total check.
- Administrator audit log for checkouts and key customer/product/team changes.
  

## Tech Stack
- Python (Flask)
- MySQL
- HTML, CSS, JavaScript
- ReportLab (PDF generation)

## First-time login setup

1. Install dependencies with `pip install -r requirements.txt`.
2. Create a local `.env` file with your Aiven MySQL connection details (`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASS`, `DB_NAME`) and a long random `SECRET_KEY`. Never commit `.env`.
3. Start the app with `python app.py`.
4. Open `/register` once to create the first account. Use a password of at least 10 characters. The registration route automatically closes after the first account exists.
5. Sign in at `/login`. Billing, products, billing history, and their API routes require an authenticated session.

The app creates and upgrades its supporting tables automatically when the login/setup page is first opened. The first user is an administrator; administrators can add cashiers, manage inventory/customers, and access reports. Cashiers can bill and view billing history. Existing products and bills are retained, with optional customer and cashier references added to bills. If automatic migration is unavailable, run `migrations/001_reporting_and_roles.sql` once after reviewing it (skip statements for columns/tables already present).

## Billora upgrade

1. Back up the database first.
2. Copy `.env.example` to `.env` and enter local credentials; never add the real `.env` to source control or a shared ZIP.
3. Install packages with `pip install -r requirements.txt`, then start with `python app.py`. The login/setup page runs the additive upgrade automatically.
4. If the application cannot access the database during startup, review and run `migrations/002_loyalty_payments_audit.sql` once. Do not run it again on a database that already has these columns/tables.

### Changelog — Billora

- Added loyalty points, promotional discount validation, and receipt details.
- Added auditable, exact-total split payments.
- Added administrator-only activity history and local AI Retail Assistant views.
- Preserved server-side product/stock/GST validation, customer/product search, PDF receipts, and admin/cashier access rules.

### Reporting and inventory

- **Analytics** summarizes the last 30 days of invoices and best-selling products.
- **Inventory alerts** uses `LOW_STOCK_THRESHOLD` (default `5`) and gives a sales-based reorder suggestion.
- **Forecast** estimates 30-day demand from the previous 30 days' average sales.
- **Sales reports** can be filtered by date and exported as CSV.
