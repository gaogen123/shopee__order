"""
检查订单预估收入的计算方式
"""
import sqlite3
import json

order_sn = '2601069NC34KCU'

conn = sqlite3.connect('shopee_orders.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute('''
    SELECT raw_data, escrow_data, total_cost, estimated_revenue, exchange_rate, estimated_profit, estimated_shipping_fee
    FROM orders WHERE order_sn = ?
''', (order_sn,))
row = c.fetchone()

if not row:
    print(f"订单 {order_sn} 不存在")
else:
    print("=" * 60)
    print(f"订单号: {order_sn}")
    print("=" * 60)
    
    # 解析原始订单数据
    rd = json.loads(row['raw_data']) if row['raw_data'] else {}
    print("\n【原始订单数据】")
    print(f"  total_amount (订单总额): {rd.get('total_amount')}")
    print(f"  estimated_shipping_fee (预估运费): {rd.get('estimated_shipping_fee')}")
    
    # 计算商品总额
    items = rd.get('item_list', [])
    item_total = sum(item.get('model_discounted_price', 0) * item.get('model_quantity_purchased', 0) for item in items)
    print(f"  商品总额 (计算): {item_total}")
    
    # 解析托管数据
    ed = json.loads(row['escrow_data']) if row['escrow_data'] else {}
    print("\n【托管数据 (escrow_info) - 来自 get_escrow_detail API】")
    print(f"  order_income_amount (订单收入金额): {ed.get('order_income_amount')}")
    print(f"  escrow_amount (托管金额): {ed.get('escrow_amount')}")
    print(f"  estimated_shipping_fee (预估运费): {ed.get('estimated_shipping_fee')}")
    print(f"  actual_shipping_fee (实际运费): {ed.get('actual_shipping_fee')}")
    print(f"  commission_fee (佣金): {ed.get('commission_fee')}")
    print(f"  service_fee (服务费): {ed.get('service_fee')}")
    print(f"  seller_transaction_fee (交易手续费): {ed.get('seller_transaction_fee')}")
    print(f"  buyer_total_amount (买家支付总额): {ed.get('buyer_total_amount')}")
    print(f"  original_price (原价): {ed.get('original_price')}")
    print(f"  shopee_shipping_rebate (Shopee运费补贴): {ed.get('shopee_shipping_rebate')}")
    
    # 计算费用
    commission = float(ed.get('commission_fee', 0))
    service = float(ed.get('service_fee', 0))
    transaction = float(ed.get('seller_transaction_fee', 0))
    total_fees = commission + service + transaction
    
    print("\n【费用计算】")
    print(f"  佣金: {commission}")
    print(f"  服务费: {service}")
    print(f"  交易手续费: {transaction}")
    print(f"  总费用 = 佣金 + 服务费 + 交易手续费 = {total_fees}")
    
    print("\n【预估订单收入的计算逻辑】")
    print("前端 OrderDetail.tsx 第 199 行的计算公式:")
    print("  如果 escrow_info.order_income_amount 存在:")
    print("    → 预估订单收入 = order_income_amount")
    print("  否则:")
    print("    → 预估订单收入 = (商品总额 + 预估运费净额) - 总费用")
    print("      其中预估运费净额 = estimated_shipping_fee - actual_shipping_fee")
    
    order_income_amount = ed.get('order_income_amount')
    if order_income_amount is not None:
        print(f"\n✅ 预估订单收入 (使用 order_income_amount): {order_income_amount}")
    else:
        est_ship = float(ed.get('estimated_shipping_fee', 0)) - float(ed.get('actual_shipping_fee', 0))
        calculated_revenue = (item_total + est_ship) - total_fees
        print(f"\n⚠️ order_income_amount 不存在，使用备用计算:")
        print(f"  预估订单收入 = ({item_total} + {est_ship}) - {total_fees} = {calculated_revenue}")
    
    print("\n【数据库存储的计算值】")
    print(f"  estimated_revenue: {row['estimated_revenue']}")
    print(f"  exchange_rate: {row['exchange_rate']}")
    print(f"  estimated_profit: {row['estimated_profit']}")
    print(f"  total_cost: {row['total_cost']}")
    print(f"  estimated_shipping_fee (订单表): {row['estimated_shipping_fee']}")

conn.close()
