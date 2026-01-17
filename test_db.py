import sqlite3
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "shopee_orders.db"

print(f"Attempting to connect to {DB_FILE}")
print(f"Parent directory: {BASE_DIR}")
print(f"Parent directory exists: {BASE_DIR.exists()}")
print(f"Parent directory is writable: {os.access(BASE_DIR, os.W_OK)}")

try:
    conn = sqlite3.connect(str(DB_FILE))
    print("Connection successful")
    conn.close()
    print("Connection closed")
except Exception as e:
    print(f"Error: {e}")
