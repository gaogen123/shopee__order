
import sqlite3
import json
import os

# Try probable locations for the db
db_paths = ['shopee_orders.db', 'backend/shopee_orders.db', 'orders.db']
db_path = None
for p in db_paths:
    if os.path.exists(p):
        db_path = p
        break

if not db_path:
    print("Could not find orders.db")
    exit(1)

print(f"Checking DB: {db_path}")
conn = sqlite3.connect(db_path)
c = conn.cursor()
order_sn = '2512114B1GNREJ'

c.execute("SELECT escrow_data FROM orders WHERE order_sn=?", (order_sn,))
row = c.fetchone()

if row and row[0]:
    try:
        escrow = json.loads(row[0])
        print("--- DB Escrow Data ---")
        print(json.dumps(escrow, indent=2))
        
        print("\n--- Key Check ---")
        print(f"icms_tax_amount: {escrow.get('icms_tax_amount')}")
        print(f"discount_from_coin: {escrow.get('discount_from_coin')}")
        
    except json.JSONDecodeError:
        print("❌ JSON Decode Error for escrow_data")
else:
    print(f"❌ Order {order_sn} not found or no escrow_data")

conn.close()
