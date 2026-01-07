import sqlite3
from datetime import datetime

# 连接到数据库
conn = sqlite3.connect('shopee_orders.db')
c = conn.cursor()

# 1. 检查特定订单是否存在
order_sn = '2511303TK11A2K'
c.execute('SELECT order_sn, create_time, shop_id, order_status FROM orders WHERE order_sn = ?', (order_sn,))
result = c.fetchone()

print(f'=== 查询订单 {order_sn} ===')
if result:
    create_dt = datetime.fromtimestamp(result[1])
    print(f'订单号: {result[0]}')
    print(f'创建时间: {create_dt} (时间戳: {result[1]})')
    print(f'店铺ID: {result[2]}')
    print(f'订单状态: {result[3]}')
else:
    print(f'❌ 订单不存在于数据库中')

print()

# 2. 搜索包含类似订单号的订单
print('=== 搜索包含 "2511303" 的订单 ===')
c.execute('SELECT order_sn, create_time, shop_id FROM orders WHERE order_sn LIKE ? ORDER BY create_time DESC', ('%2511303%',))
rows = c.fetchall()
if rows:
    for r in rows:
        create_dt = datetime.fromtimestamp(r[1])
        print(f'  订单号: {r[0]}, 创建时间: {create_dt}, 店铺ID: {r[2]}')
else:
    print('  无相关订单')

print()

# 3. 统计2025-11-01及之后的订单数量
# 2025-11-01 00:00:00 UTC+8 的时间戳
time_from = int(datetime(2025, 11, 1, 0, 0, 0).timestamp())
print(f'=== 2025-11-01 之后的订单统计 ===')
print(f'时间戳起始: {time_from} ({datetime.fromtimestamp(time_from)})')

c.execute('SELECT COUNT(*) FROM orders WHERE create_time >= ?', (time_from,))
count = c.fetchone()[0]
print(f'订单总数: {count}')

# 4. 检查最新的几个订单
print()
print('=== 最近的10个订单 ===')
c.execute('SELECT order_sn, create_time, shop_id, order_status FROM orders ORDER BY create_time DESC LIMIT 10')
rows = c.fetchall()
for r in rows:
    create_dt = datetime.fromtimestamp(r[1])
    print(f'  订单号: {r[0]}, 创建时间: {create_dt}, 店铺ID: {r[2]}, 状态: {r[3]}')

conn.close()
