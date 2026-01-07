"""
测试特定订单是否可以从Shopee API获取
"""
import sys
from pathlib import Path

# 添加路径以导入token_manager
BASE_DIR = Path(__file__).resolve().parent
TEST_DIR = BASE_DIR / "backend" / "test" / "shop_test"
sys.path.append(str(TEST_DIR))

from token_manager import get_valid_token, PARTNER_ID, PARTNER_KEY, HOST
import requests
import time
import hmac
import hashlib
import json

def generate_shop_sign(path, timestamp, access_token, shop_id):
    base_string = f"{PARTNER_ID}{path}{timestamp}{access_token}{shop_id}"
    return hmac.new(
        PARTNER_KEY.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def test_order_detail(shop_id, order_sn):
    """测试从API获取订单详情"""
    print(f"\n=== 测试获取订单 {order_sn} ===")
    print(f"店铺ID: {shop_id}")
    
    token = get_valid_token(shop_id)
    if not token:
        print("❌ 无法获取有效token")
        return None
    
    print(f"✓ Token获取成功")
    
    path = "/api/v2/order/get_order_detail"
    timestamp = int(time.time())
    sign = generate_shop_sign(path, timestamp, token, shop_id)
    
    url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&access_token={token}&shop_id={shop_id}&sign={sign}"
    
    fields = [
        "order_sn", "order_status", "total_amount", "currency", 
        "create_time", "pay_time", "shipping_carrier", "payment_method",
        "estimated_shipping_fee", "actual_shipping_fee",
        "buyer_username", "recipient_address", "item_list"
    ]
    
    params = {
        "order_sn_list": order_sn,
        "response_optional_fields": ",".join(fields)
    }
    
    try:
        print(f"发送API请求...")
        resp = requests.get(url, params=params, timeout=30)
        data = resp.json()
        
        print(f"\nAPI响应:")
        print(f"状态码: {resp.status_code}")
        
        if "error" in data and data["error"]:
            print(f"❌ API错误: {data.get('message')}")
            print(f"完整响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
            return None
        
        order_list = data.get("response", {}).get("order_list", [])
        if order_list:
            order = order_list[0]
            print(f"✓ 成功获取订单")
            print(f"\n订单信息:")
            print(f"  订单号: {order.get('order_sn')}")
            print(f"  创建时间戳: {order.get('create_time')}")
            if order.get('create_time'):
                from datetime import datetime
                create_dt = datetime.fromtimestamp(order.get('create_time'))
                print(f"  创建时间: {create_dt}")
            print(f"  订单状态: {order.get('order_status')}")
            print(f"  订单金额: {order.get('total_amount')} {order.get('currency')}")
            print(f"  买家: {order.get('buyer_username')}")
            print(f"\n完整数据:")
            print(json.dumps(order, indent=2, ensure_ascii=False))
            return order
        else:
            print(f"❌ 订单不存在于API响应中")
            print(f"完整响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
            return None
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_order_in_list(shop_id, time_from, time_to):
    """测试订单是否出现在订单列表中"""
    from datetime import datetime
    print(f"\n=== 测试订单列表查询 ===")
    print(f"时间范围: {datetime.fromtimestamp(time_from)} 至 {datetime.fromtimestamp(time_to)}")
    
    token = get_valid_token(shop_id)
    if not token:
        print("❌ 无法获取有效token")
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
            print(f"❌ API错误: {data.get('message')}")
            return []
        
        order_list = data.get("response", {}).get("order_list", [])
        print(f"✓ 获取到 {len(order_list)} 个订单")
        
        # 查找特定订单
        for order in order_list:
            print(f"  - {order.get('order_sn')}")
        
        return [o.get('order_sn') for o in order_list]
        
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return []

if __name__ == "__main__":
    # 测试参数
    SHOP_ID = 494829323  # 你的店铺ID
    ORDER_SN = "2511303TK11A2K"
    
    # 2025-11-30的时间范围
    from datetime import datetime
    time_from = int(datetime(2025, 11, 30, 0, 0, 0).timestamp())
    time_to = int(datetime(2025, 12, 1, 0, 0, 0).timestamp())
    
    # 测试1: 直接获取订单详情
    order = test_order_detail(SHOP_ID, ORDER_SN)
    
    # 测试2: 查看订单是否在列表中
    print("\n" + "="*60)
    order_sns = test_order_in_list(SHOP_ID, time_from, time_to)
    
    if ORDER_SN in order_sns:
        print(f"\n✓ 订单 {ORDER_SN} 在订单列表中")
    else:
        print(f"\n❌ 订单 {ORDER_SN} 不在订单列表中")
