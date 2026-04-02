
import sqlite3
import pandas as pd
from datetime import datetime

# 连接数据库
conn = sqlite3.connect("d:/code/shopee__order/shopee_orders.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("\n=== DEBUG: Check estimated_revenue Values ===")

# 1. 检查是否有数据
cursor.execute("SELECT COUNT(*), COUNT(estimated_revenue), SUM(estimated_revenue) FROM orders")
row = cursor.fetchone()
print(f"Total Orders: {row[0]}")
print(f"Orders with Revenue: {row[1]}")
print(f"Total Revenue Sum: {row[2]}")

# 2. 检查最近30天的每日数据
print("\n=== DEBUG: Daily Revenue (Last 30 Days) ===")
cursor.execute("""
    SELECT 
        DATE(create_time, 'unixepoch', 'localtime') as date,
        COUNT(*) as cnt,
        SUM(estimated_revenue) as rev,
        SUM(total_cost) as cost,
        SUM(estimated_profit) as prof
    FROM orders 
    GROUP BY date
    ORDER BY date DESC
    LIMIT 10
""")
rows = cursor.fetchall()
for r in rows:
    print(f"Date: {r['date']}, Count: {r['cnt']}, Rev: {r['rev']}, Cost: {r['cost']}, Prof: {r['prof']}")

conn.close()
