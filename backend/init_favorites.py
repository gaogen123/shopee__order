
import sys
import os
from pathlib import Path

# Add project root to sys.path to find shared.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import get_db_connection

def init_fav_table():
    conn = get_db_connection()
    c = conn.cursor()
    print("Creating selection_favorites table in shopee_orders...")
    c.execute("""
    CREATE TABLE IF NOT EXISTS selection_favorites (
        product_id INT PRIMARY KEY,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()
    print("Table selection_favorites created successfully or already exists.")

if __name__ == "__main__":
    init_fav_table()
