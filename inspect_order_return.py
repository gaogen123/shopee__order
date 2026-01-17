import sys
import os
from pathlib import Path

# 添加后端目录到 sys.path
sys.path.append(os.path.join(os.getcwd(), 'backend'))
sys.path.append(os.path.join(os.getcwd(), 'backend', 'test', 'shop_test'))

from shared import fetch_order_from_api, fetch_escrow_detail

ORDER_SN = "2511086UM68HYU"
SHOP_ID = 494829323

def inspect_order_details():
    print(f"正在获取店铺 {SHOP_ID} 订单 {ORDER_SN} 的详细信息...")
    
    # 1. 获取订单详情
    order = fetch_order_from_api(SHOP_ID, ORDER_SN)
    if order:
        print("\n--- 订单 API 数据 ---")
        print(f"状态: {order.get('order_status')}")
        print(f"取消原因: {order.get('cancel_reason')}")
        print(f"买家取消原因: {order.get('buyer_cancel_reason')}")
        # 检查退货/退款相关字段（尽管通常在单独的 API 中）
        # 打印相关键值
        keys_to_check = ['order_status', 'cancel_reason', 'buyer_cancel_reason', 'cancel_by', 'fulfillment_flag', 'pay_time', 'update_time']
        for k in keys_to_check:
            print(f"{k}: {order.get(k)}")
    else:
        print("❌ 获取订单数据失败。")

    # 2. 获取托管/财务详情
    print("\n--- 托管/财务数据 ---")
    escrow = fetch_escrow_detail(SHOP_ID, ORDER_SN)
    if escrow:
        import json
        print(json.dumps(escrow, indent=2, ensure_ascii=False))
    else:
        print("⚠️ 未找到托管详情。")

    # 3. 检查退货列表（可选 - 需要实现退货 API）
    # Shopee 有单独的 get_return_list API。
    # 目前，让我们看看是否可以从订单状态或财务数据中推断出来。

if __name__ == "__main__":
    inspect_order_details()
