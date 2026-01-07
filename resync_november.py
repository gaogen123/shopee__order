"""
重新同步2025年11月的订单（缺失的订单）
"""
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
TEST_DIR = BASE_DIR / "backend" / "test" / "shop_test"
sys.path.append(str(TEST_DIR))

from token_manager import get_valid_token
import sqlite3
import requests

# 导入server.py中的函数
sys.path.append(str(BASE_DIR / "backend"))
from server import (
    fetch_order_list_from_api, 
    fetch_order_from_api, 
    fetch_escrow_detail,
    save_order_to_db,
    get_db_connection
)

def resync_november_orders(shop_id):
    """重新同步2025年11月的订单"""
    
    print("="*80)
    print("重新同步2025年11月订单")
    print("="*80)
    
    # 11月的时间范围
    nov_start = int(datetime(2025, 11, 1, 0, 0, 0).timestamp())
    nov_end = int(datetime(2025, 12, 1, 0, 0, 0).timestamp())
    
    print(f"\n同步范围:")
    print(f"  开始: {datetime.fromtimestamp(nov_start)}")
    print(f"  结束: {datetime.fromtimestamp(nov_end)}")
    print(f"  天数: {(nov_end - nov_start) / 86400} 天")
    print(f"  店铺ID: {shop_id}")
    
    # 获取订单列表
    print(f"\n步骤 1: 从API获取订单列表...")
    order_sns = fetch_order_list_from_api(shop_id, nov_start, nov_end)
    
    print(f"✓ 获取到 {len(order_sns)} 个订单")
    
    if not order_sns:
        print("\n❌ 没有找到任何订单")
        return
    
    # 显示订单列表
    print(f"\n订单列表:")
    for i, sn in enumerate(order_sns, 1):
        is_target = " ← 目标订单" if sn == "2511303TK11A2K" else ""
        print(f"  {i}. {sn}{is_target}")
    
    # 检查目标订单是否在列表中
    target_order = "2511303TK11A2K"
    if target_order in order_sns:
        print(f"\n✅ 找到目标订单 {target_order}!")
    else:
        print(f"\n⚠️  目标订单 {target_order} 不在列表中")
    
    # 同步订单详情
    print(f"\n步骤 2: 同步订单详情到数据库...")
    
    conn = get_db_connection()
    success_count = 0
    error_count = 0
    
    for i, sn in enumerate(order_sns, 1):
        try:
            print(f"  [{i}/{len(order_sns)}] 正在同步 {sn}...", end=" ")
            
            # 获取订单详情
            order_data = fetch_order_from_api(shop_id, sn)
            if not order_data:
                print("❌ 获取订单详情失败")
                error_count += 1
                continue
            
            # 获取escrow详情
            escrow_data = fetch_escrow_detail(shop_id, sn)
            
            # 保存到数据库
            save_order_to_db(conn, shop_id, order_data, escrow_data)
            
            print("✓")
            success_count += 1
            
        except Exception as e:
            print(f"❌ 错误: {e}")
            error_count += 1
            continue
    
    conn.close()
    
    print(f"\n" + "="*80)
    print("同步完成")
    print("="*80)
    print(f"成功: {success_count} 个订单")
    print(f"失败: {error_count} 个订单")
    print(f"总计: {len(order_sns)} 个订单")
    
    # 验证目标订单是否已同步
    print(f"\n步骤 3: 验证目标订单...")
    conn = sqlite3.connect(str(BASE_DIR / "shopee_orders.db"))
    c = conn.cursor()
    c.execute('SELECT order_sn, create_time FROM orders WHERE order_sn = ?', (target_order,))
    result = c.fetchone()
    
    if result:
        dt = datetime.fromtimestamp(result[1])
        print(f"✅ 目标订单 {target_order} 已成功同步!")
        print(f"   创建时间: {dt}")
    else:
        print(f"❌ 目标订单 {target_order} 仍未在数据库中")
    
    conn.close()

if __name__ == "__main__":
    SHOP_ID = 494829323  # 你的店铺ID
    
    # 确认执行
    print("⚠️  这将重新同步2025年11月的所有订单")
    print("如果订单已存在，将会更新它们")
    print("\n按回车继续，或Ctrl+C取消...")
    try:
        input()
    except KeyboardInterrupt:
        print("\n\n已取消")
        sys.exit(0)
    
    resync_november_orders(SHOP_ID)
