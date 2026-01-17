# MySQL Migration Guide

The project has been migrated from SQLite to local MySQL.

## Database Configuration

- **Host**: localhost
- **User**: root
- **Password**: (empty)
- **Database**: `shopee_orders`

## Changes Made

1.  **Dependencies**: Installed `mysql-connector-python`.
2.  **Database Creation**: Created `shopee_orders` database in local MySQL.
3.  **Code Updates**:
    -   Updated `backend/shared.py` to connect to MySQL.
    -   Updated SQL syntax in `backend/shared.py`, `backend/routers/orders.py`, and `backend/routers/mappings.py`.
    -   Replaced `?` placeholders with `%s`.
    -   Replaced `ON CONFLICT` with `ON DUPLICATE KEY UPDATE`.
    -   Replaced SQLite-specific date functions with MySQL equivalents.

## Verification

The backend server has been restarted and is successfully connected to the MySQL database.
The tables have been initialized automatically.

## Next Steps

Since this is a new database, the order list will be empty.
Please use the **"Sync Orders"** feature in the frontend to populate the database with data from Shopee API.
