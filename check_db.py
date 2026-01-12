import sqlite3
import os

# 检查数据库文件是否存在
db_path = 'shopee_orders.db'
if not os.path.exists(db_path):
    print("数据库文件不存在")
    exit()

conn = sqlite3.connect(db_path)
c = conn.cursor()

# 检查orders表结构
print("orders表结构:")
c.execute('PRAGMA table_info(orders)')
columns = c.fetchall()
for col in columns:
    print(f"  {col[1]}: {col[2]}")

# 检查是否存在预估收入、汇率和利润字段
required_columns = ['estimated_revenue', 'exchange_rate', 'estimated_profit']
missing_columns = []

for col_name in required_columns:
    if not any(col[1] == col_name for col in columns):
        missing_columns.append(col_name)

if missing_columns:
    print(f"\n缺少以下字段: {missing_columns}")
    # 添加缺失的字段
    for col in missing_columns:
        try:
            if col == 'estimated_revenue':
                c.execute(f'ALTER TABLE orders ADD COLUMN {col} REAL DEFAULT 0')
                print(f"添加字段: {col}")
            elif col == 'exchange_rate':
                c.execute(f'ALTER TABLE orders ADD COLUMN {col} REAL DEFAULT 1.0')
                print(f"添加字段: {col}")
            elif col == 'estimated_profit':
                c.execute(f'ALTER TABLE orders ADD COLUMN {col} REAL DEFAULT 0')
                print(f"添加字段: {col}")
        except Exception as e:
            print(f"添加字段 {col} 失败: {e}")
    conn.commit()
else:
    print("\n所有需要的字段都已存在")

conn.close()
