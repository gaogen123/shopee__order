
import sqlite3
import json

def check_data():
    conn = sqlite3.connect('shopee_orders.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Check schema
    c.execute("PRAGMA table_info(orders)")
    columns = [row['name'] for row in c.fetchall()]
    print(f"Columns in orders: {columns}")
    
    if 'estimated_profit' not in columns or 'total_cost' not in columns:
        print("MISSING COLUMNS!")
        return

    # Inspect count
    c.execute("SELECT COUNT(*) as cnt, SUM(total_cost) as sum_cost FROM orders WHERE order_status = 'TO_CONFIRM_RECEIVE'")
    row = c.fetchone()
    print(f"\nStats for TO_CONFIRM_RECEIVE:")
    print(dict(row))
        
    # Check sums
    c.execute("SELECT SUM(total_cost), SUM(estimated_profit) FROM orders")
    sums = c.fetchone()
    print(f"\nSums: Cost={sums[0]}, Profit={sums[1]}")

    conn.close()

if __name__ == "__main__":
    check_data()
