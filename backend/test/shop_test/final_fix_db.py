
import sys
import os
import json
import sqlite3

# Import server code logic
sys.path.append(os.getcwd())
try:
    from backend.server import fetch_escrow_detail
except ImportError:
    sys.path.append(os.path.join(os.getcwd(), 'backend'))
    from server import fetch_escrow_detail

def fix_db():
    shop_id = 494829323
    order_sn = "2512114B1GNREJ"
    
    # 1. Fetch Fresh Data (with merge logic)
    print("Fetching merged escrow data...")
    escrow_data = fetch_escrow_detail(shop_id, order_sn)
    
    if not escrow_data:
        print("Failed to fetch escrow data")
        return

    print(f"Fetched Data ICMS: {escrow_data.get('icms_tax_amount')}")
    
    # 2. Connect DB
    db_paths = ['shopee_orders.db', 'backend/shopee_orders.db', 'orders.db']
    db_path = None
    for p in db_paths:
        if os.path.exists(p):
            db_path = p
            break
            
    if not db_path:
        db_path = 'shopee_orders.db'

    print(f"Connecting to {db_path}...")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # 3. Explicit Update
    json_str = json.dumps(escrow_data)
    c.execute("UPDATE orders SET escrow_data=? WHERE order_sn=?", (json_str, order_sn))
    
    if c.rowcount == 0:
        print("Order not found in DB! Needs insert.")
    else:
        print(f"Updated {c.rowcount} row(s).")
        conn.commit()
        
    # 4. Verify
    c.execute("SELECT escrow_data FROM orders WHERE order_sn=?", (order_sn,))
    row = c.fetchone()
    if row:
        stored = json.loads(row[0])
        print(f"Stored Data ICMS: {stored.get('icms_tax_amount')}")
        print(f"Stored Data Coin Discount: {stored.get('discount_from_coin')}")
    
    conn.close()

if __name__ == "__main__":
    fix_db()
