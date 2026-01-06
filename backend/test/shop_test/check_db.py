
import sqlite3
import json

DB_FILE = 'd:\\code\\Shopee_Order\\shopee_orders.db'

def check_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 1. 检查表结构
    print("Checking 'orders' table info:")
    c.execute("PRAGMA table_info(orders)")
    columns = c.fetchall()
    found_escrow = False
    for col in columns:
        print(col)
        if col[1] == 'escrow_data':
            found_escrow = True
            
    if not found_escrow:
        print("ERROR: 'escrow_data' column NOT found!")
    else:
        print("SUCCESS: 'escrow_data' column exists.")

    # 2. 检查特定订单的数据
    order_sn = "2601069NC34KCU"
    print(f"\nChecking data for order {order_sn}:")
    c.execute("SELECT escrow_data FROM orders WHERE order_sn = ?", (order_sn,))
    row = c.fetchone()
    
    if row:
        escrow_raw = row[0]
        if escrow_raw:
            print(f"Escrow Data Length: {len(escrow_raw)}")
            try:
                data = json.loads(escrow_raw)
                print("shopee_shipping_rebate:", data.get('shopee_shipping_rebate'))
            except Exception as e:
                print(f"JSON Parse Error: {e}")
                print(escrow_raw)
        else:
            print("Escrow Data is NULL or Empty")
    else:
        print("Order not found in DB")

    conn.close()

if __name__ == "__main__":
    check_db()
