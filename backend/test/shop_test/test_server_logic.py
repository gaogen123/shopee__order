
import sys
import os
import json
import sqlite3

# Import server code logic directly
# We need to mock app deps or import specific functions.
# importing server might run the app if not careful.
# But server.py has if __name__ == "__main__": uvicorn... so safe.

sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# We need to override token_manager path probably?
# backend/server.py imports 'backend.token_manager' or 'token_manager'?
# It imports 'token_manager' assuming cwd is backend? No, `from token_manager import`.
# If I run from root, I need to ensure backend is in path.

from backend.server import fetch_escrow_detail, save_order_to_db, init_db_tables, fetch_order_from_api

# Define DB connection manually
def get_db_connection():
    db_paths = ['shopee_orders.db', 'backend/shopee_orders.db', 'orders.db']
    for p in db_paths:
        if os.path.exists(p):
            return sqlite3.connect(p)
    return sqlite3.connect('shopee_orders.db')

def update_test():
    shop_id = 494829323
    order_sn = "2512114B1GNREJ"
    
    print("--- Testing fetch_escrow_detail ---")
    escrow_data = fetch_escrow_detail(shop_id, order_sn)
    
    if escrow_data:
        print("Fetch successful!")
        print(f"Keys in result: {list(escrow_data.keys())}")
        print(f"ICMS: {escrow_data.get('icms_tax_amount')}")
        print(f"Discount Coins: {escrow_data.get('discount_from_coin')}")
        
        # Save to DB
        conn = get_db_connection()
        init_db_tables(conn)
        
        # We need generic order data too for save_order_to_db constraint?
        # save_order_to_db(conn, shop_id, order_data, escrow_data)
        # It does INSERT OR IGNORE.
        # So we need order_data.
        # Let's fetch order too.
        order_data = fetch_order_from_api(shop_id, order_sn)
        if order_data:
            save_order_to_db(conn, shop_id, order_data, escrow_data)
            print("Saved to DB.")
            conn.commit()
        else:
            print("Failed to fetch order data.")
        conn.close()
    else:
        print("Fetch failed (None returned).")

if __name__ == "__main__":
    update_test()
