"""
检查数据库中已同步订单的时间分布
"""
import sqlite3
from datetime import datetime

conn = sqlite3.connect('shopee_orders.db')
c = conn.cursor()

print("="*80)
print("数据库中订单时间分布分析")
print("="*80)

# 获取所有订单的创建时间
c.execute('SELECT order_sn, create_time FROM orders ORDER BY create_time')
rows = c.fetchall()

if len(rows) == 0:
    print("数据库中没有订单")
else:
    print(f"\n总订单数: {len(rows)}")
    
    # 显示前10个和后10个订单
    print("\n最早的10个订单:")
    for i, row in enumerate(rows[:10], 1):
        dt = datetime.fromtimestamp(row[1])
        print(f"  {i}. {row[0]} - {dt} ({row[1]})")
    
    print("\n最新的10个订单:")
    for i, row in enumerate(rows[-10:], 1):
        dt = datetime.fromtimestamp(row[1])
        print(f"  {len(rows)-10+i}. {row[0]} - {dt} ({row[1]})")
    
    # 检查2025年11月的订单
    print("\n2025年11月的订单:")
    nov_start = int(datetime(2025, 11, 1, 0, 0, 0).timestamp())
    nov_end = int(datetime(2025, 12, 1, 0, 0, 0).timestamp())
    
    c.execute('SELECT order_sn, create_time FROM orders WHERE create_time >= ? AND create_time < ? ORDER BY create_time', 
              (nov_start, nov_end))
    nov_rows = c.fetchall()
    
    print(f"  总数: {len(nov_rows)}")
    if nov_rows:
        print("\n  所有11月订单:")
        for row in nov_rows:
            dt = datetime.fromtimestamp(row[1])
            print(f"    {row[0]} - {dt}")
    
    # 检查目标订单前后的订单
    target_time = 1764432435  # 2025-11-30 00:07:15
    print(f"\n目标订单时间: {datetime.fromtimestamp(target_time)}")
    
    # 查找目标时间前后1天的订单
    time_before = target_time - 86400
    time_after = target_time + 86400
    
    c.execute('SELECT order_sn, create_time FROM orders WHERE create_time >= ? AND create_time <= ? ORDER BY create_time', 
              (time_before, time_after))
    nearby_rows = c.fetchall()
    
    print(f"\n目标订单前后1天的订单 ({len(nearby_rows)}个):")
    for row in nearby_rows:
        dt = datetime.fromtimestamp(row[1])
        is_target = " ← 目标订单" if row[0] == '2511303TK11A2K' else ""
        print(f"    {row[0]} - {dt}{is_target}")
    
    # 检查时间间隙
    print("\n" + "="*80)
    print("检查时间间隙（是否有大于1天的间隙）")
    print("="*80)
    
    gaps = []
    for i in range(1, len(rows)):
        gap = rows[i][1] - rows[i-1][1]
        if gap > 86400:  # 大于1天
            gaps.append((rows[i-1], rows[i], gap))
    
    if gaps:
        print(f"\n发现 {len(gaps)} 个大于1天的时间间隙:")
        for prev, next, gap in gaps:
            prev_dt = datetime.fromtimestamp(prev[1])
            next_dt = datetime.fromtimestamp(next[1])
            gap_days = gap / 86400
            print(f"\n  间隙: {gap_days:.2f} 天")
            print(f"    前一个: {prev[0]} - {prev_dt}")
            print(f"    后一个: {next[0]} - {next_dt}")
            
            # 检查目标订单是否在这个间隙中
            if prev[1] < target_time < next[1]:
                print(f"    ⚠️  目标订单 2511303TK11A2K 可能在这个间隙中！")
    else:
        print("\n没有发现大于1天的时间间隙")

conn.close()
