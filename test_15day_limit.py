"""
简化版诊断 - 重点测试15天范围限制
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).resolve().parent
TEST_DIR = BASE_DIR / "backend" / "test" / "shop_test"
sys.path.append(str(TEST_DIR))

from token_manager import get_valid_token, PARTNER_ID, PARTNER_KEY, HOST
import requests
import time
import hmac
import hashlib

def generate_shop_sign(path, timestamp, access_token, shop_id):
    base_string = f"{PARTNER_ID}{path}{timestamp}{access_token}{shop_id}"
    return hmac.new(
        PARTNER_KEY.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def test_order_in_list(shop_id, time_from, time_to, test_name):
    """测试订单列表API"""
    print(f"\n{test_name}")
    print(f"  开始: {datetime.fromtimestamp(time_from)}")
    print(f"  结束: {datetime.fromtimestamp(time_to)}")
    print(f"  天数: {(time_to - time_from) / 86400:.1f} 天")
    
    token = get_valid_token(shop_id)
    if not token:
        print("  ❌ 无法获取token")
        return []
    
    path = "/api/v2/order/get_order_list"
    timestamp = int(time.time())
    sign = generate_shop_sign(path, timestamp, token, shop_id)
    url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&access_token={token}&shop_id={shop_id}&sign={sign}"
    
    params = {
        "time_range_field": "create_time",
        "time_from": time_from,
        "time_to": time_to,
        "page_size": 100
    }
    
    try:
        resp = requests.get(url, params=params, timeout=30)
        data = resp.json()
        
        if "error" in data and data["error"]:
            print(f"  ❌ API错误: {data.get('message')}")
            return []
        
        order_list = data.get("response", {}).get("order_list", [])
        order_sns = [o.get('order_sn') for o in order_list]
        
        print(f"  ✓ 成功获取 {len(order_sns)} 个订单")
        
        # 检查目标订单
        target = "2511303TK11A2K"        
        if target in order_sns:
            print(f"  ✅ 找到目标订单 {target}!")
        else:
            print(f"  未找到目标订单 {target}")
        
        return order_sns
        
    except Exception as e:
        print(f"  ❌ 异常: {e}")
        return []

if __name__ == "__main__":
    SHOP_ID = 494829323
    ORDER_TIMESTAMP = 1764432435  # 2025-11-30 00:07:15 本地时间
    
    print("="*70)
    print("测试Shopee API的15天限制")
    print("="*70)
    print(f"\n目标订单: 2511303TK11A2K")
    print(f"订单时间: {datetime.fromtimestamp(ORDER_TIMESTAMP)}")
    
    # 测试1: 15天范围（应该成功）
    end_time = int(datetime(2025, 12, 1, 0, 0, 0).timestamp())
    start_time_15days = end_time - (15 * 86400)
    test_order_in_list(SHOP_ID, start_time_15days, end_time, "测试1: 15天范围 (2025-11-16 到 2025-12-01)")
    
    time.sleep(1)
    
    # 测试2: 订单所在的15天窗口
    # 从 2025-11-29 到 2025-12-14
    order_start = int(datetime(2025, 11, 29, 0, 0, 0).timestamp())
    order_end = order_start + (15 * 86400)
    test_order_in_list(SHOP_ID, order_start, order_end, "测试2: 订单日期开始的15天 (2025-11-29 到 2025-12-14)")
    
    time.sleep(1)
    
    # 测试3: 从2025-11-15开始的15天
    start_nov15 = int(datetime(2025, 11, 15, 0, 0, 0).timestamp())
    end_nov30 = int(datetime(2025, 11, 30, 23, 59, 59).timestamp())
    test_order_in_list(SHOP_ID, start_nov15, end_nov30, "测试3: 2025-11-15 到 2025-11-30")
    
    time.sleep(1)
    
    # 测试4: 从2025-11-20开始的15天
    start_nov20 = int(datetime(2025, 11, 20, 0, 0, 0).timestamp())
    end_dec5 = int(datetime(2025, 12, 5, 0, 0, 0).timestamp())
    test_order_in_list(SHOP_ID, start_nov20, end_dec5, "测试4: 2025-11-20 到 2025-12-05")
    
    print("\n" + "="*70)
    print("测试完成")
    print("="*70)
