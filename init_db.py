import sys
from pathlib import Path
import sqlite3

# Add backend to sys.path
BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR / "backend"
sys.path.append(str(BACKEND_DIR))

# Add token_manager path (backend/test/shop_test)
TOKEN_MANAGER_DIR = BACKEND_DIR / "test" / "shop_test"
sys.path.append(str(TOKEN_MANAGER_DIR))

from shared import get_db_connection, init_db_tables

print("Initializing database tables...")
try:
    conn = get_db_connection()
    init_db_tables(conn)
    conn.close()
    print("Database tables initialized successfully.")
except Exception as e:
    print(f"Error initializing tables: {e}")
