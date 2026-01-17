"""
订单管理路由模块

提供订单相关的所有API接口，包括：
- 订单详情查询
- 订单成本更新
- 商品成本更新
- 订单列表查询
- 订单统计信息

作者: AI Assistant
创建时间: 2025-01-09
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
import json
import time

# 导入共享函数，避免循环依赖
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from shared import get_db_connection, init_db_tables, fetch_order_from_api, fetch_escrow_detail, save_order_to_db

# 创建路由器实例，所有路由都以 /api 开头
router = APIRouter()

class CostUpdate(BaseModel):
    """订单成本更新模型"""
    cost: float | None = None  # 订单总成本（遗留字段）
    total_cost: float | None = None  # 订单总成本
    # 注意：purchase_cost 和 domestic_shipping_cost 现在在商品级别，通过 ItemCostUpdate 更新

class ItemCostUpdate(BaseModel):
    """商品成本更新模型"""
    item_id: int  # 商品ID
    model_id: int = 0  # 型号ID，默认为0
    sourcing_price: float = 0  # 采购价
    purchase_cost: float = 0  # 采购成本
    domestic_shipping_cost: float = 0  # 国内物流成本

@router.get("/api/order/{order_sn}")
def get_order(order_sn: str, shop_id: int = Query(494829323, description="Shop ID to fetch order from")):
    """
    获取单个订单的详细信息

    Args:
        order_sn (str): 订单编号
        shop_id (int): 店铺ID，默认值为494829323

    Returns:
        dict: 包含订单详情、财务信息和成本信息的字典

    Raises:
        HTTPException: 当订单不存在时返回404错误
    """
    print(f"从数据库读取订单 {order_sn} (跳过API调用)...")

    # 建立数据库连接并初始化表结构
    conn = get_db_connection()
    init_db_tables(conn)

    # 从数据库查询订单数据
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT raw_data, escrow_data, total_cost, estimated_revenue, exchange_rate, estimated_profit, refund_amount
        FROM orders
        WHERE order_sn = %s
    """, (order_sn,))
    row = cursor.fetchone()

    result_data = {}

    # 解析数据库中的订单数据
    if row and row['raw_data']:
        # 解析原始订单数据
        result_data = json.loads(row['raw_data'])

        # 添加托管数据（财务信息）
        if row['escrow_data']:
            result_data['escrow_info'] = json.loads(row['escrow_data'])

        # 添加订单总成本信息到响应中
        result_data['total_cost'] = row['total_cost'] if row['total_cost'] is not None else 0
        
        # 添加预估收入、汇率和预估利润到响应中
        result_data['estimated_revenue'] = row['estimated_revenue'] if row['estimated_revenue'] is not None else 0
        result_data['exchange_rate'] = row['exchange_rate'] if row['exchange_rate'] is not None else 0
        result_data['estimated_profit'] = row['estimated_profit'] if row['estimated_profit'] is not None else 0
        result_data['refund_amount'] = row['refund_amount'] if row['refund_amount'] is not None else 0
    else:
        # 订单不存在，关闭连接并返回404错误
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")

    # 处理财务信息，计算各项费用
    # 公式：费用 = 佣金 + 服务费 + 交易手续费
    if 'escrow_info' in result_data and result_data['escrow_info']:
        ei = result_data['escrow_info']

        # 提取各项费用
        commission = float(ei.get('commission_fee', 0))      # 佣金
        service = float(ei.get('service_fee', 0))           # 服务费
        transaction = float(ei.get('seller_transaction_fee', 0))  # 交易手续费

        # 构建财务信息字典
        result_data['financials'] = {
            'estimated_shipping_fee': ei.get('estimated_shipping_fee'),  # 预估运费
            'commission_fee': commission,                    # 佣金费用
            'service_fee': service,                         # 服务费用
            'seller_transaction_fee': transaction,          # 交易手续费
            'original_price': ei.get('original_price'),     # 原价
            'buyer_total_amount': ei.get('buyer_total_amount'),  # 买家支付总额
            'shopee_shipping_rebate': ei.get('shopee_shipping_rebate', 0),  # Shopee运费补贴
            'total_fees': commission + service + transaction  # 总费用
        }

    # 合并商品成本信息
    cursor.execute("""
        SELECT item_id, model_id, sourcing_price
        FROM order_item_costs
        WHERE order_sn = %s
    """, (order_sn,))
    cost_rows = cursor.fetchall()

    # 构建成本映射表
    cost_map = {}
    for cr in cost_rows:
        mid = cr['model_id'] if cr['model_id'] else 0
        key = f"{cr['item_id']}_{mid}"
        cost_map[key] = cr['sourcing_price']

    # 为每个商品添加采购价格
    if 'item_list' in result_data:
        for item in result_data['item_list']:
             mid = item.get('model_id', 0)
             key = f"{item.get('item_id')}_{mid}"
             item['sourcing_price'] = cost_map.get(key, 0)

    # 从用户成本表获取商品成本信息
    cursor.execute("""
        SELECT item_id, model_id, purchase_cost, domestic_shipping_cost
        FROM order_item_user_costs
        WHERE order_sn = %s
    """, (order_sn,))
    user_cost_rows = cursor.fetchall()

    # 构建用户成本映射表
    user_cost_map = {}
    for ucr in user_cost_rows:
        mid = ucr['model_id'] if ucr['model_id'] else 0
        key = f"{ucr['item_id']}_{mid}"
        user_cost_map[key] = {
            'purchase_cost': ucr['purchase_cost'] or 0,
            'domestic_shipping_cost': ucr['domestic_shipping_cost'] or 0
        }

    # 为每个商品添加用户记录的成本
    if 'item_list' in result_data:
        for item in result_data['item_list']:
            mid = item.get('model_id', 0)
            key = f"{item.get('item_id')}_{mid}"
            user_costs = user_cost_map.get(key, {'purchase_cost': 0, 'domestic_shipping_cost': 0})
            item['purchase_cost'] = user_costs['purchase_cost']
            item['domestic_shipping_cost'] = user_costs['domestic_shipping_cost']

    # 关闭数据库连接
    conn.close()
    return result_data

@router.post("/api/order/{order_sn}/cost")
def update_order_cost(order_sn: str, update: CostUpdate):
    """
    更新订单的成本信息

    Args:
        order_sn (str): 订单编号
        update (CostUpdate): 要更新的成本信息

    Returns:
        dict: 包含更新状态和更新字段的响应
    """
    # 建立数据库连接
    conn = get_db_connection()
    c = conn.cursor(dictionary=True)

    # 根据提供的更新数据更新相应的字段
    if update.cost is not None:
        c.execute("UPDATE orders SET cost = %s WHERE order_sn = %s", (update.cost, order_sn))

    # 注意：purchase_cost 和 domestic_shipping_cost 现在在商品级别，通过 update_item_costs 更新
    # 这里只更新订单级别的 total_cost
    if update.total_cost is not None:
        # 获取当前订单的预估收入和汇率
        c.execute("SELECT estimated_revenue, exchange_rate FROM orders WHERE order_sn = %s", (order_sn,))
        row = c.fetchone()
        
        if row:
            estimated_revenue = row['estimated_revenue'] or 0
            exchange_rate = row['exchange_rate'] or 1.0
            
            # 重新计算预估利润
            revenue_in_rmb = estimated_revenue * exchange_rate
            estimated_profit = revenue_in_rmb - update.total_cost
            
            # 更新 total_cost 和 estimated_profit
            c.execute("""
                UPDATE orders 
                SET total_cost = %s, estimated_profit = %s 
                WHERE order_sn = %s
            """, (update.total_cost, estimated_profit, order_sn))
        else:
            # 如果订单不存在，只更新 total_cost
            c.execute("UPDATE orders SET total_cost = %s WHERE order_sn = %s", (update.total_cost, order_sn))

    # 提交事务
    conn.commit()
    conn.close()

    # 返回更新成功的响应
    return {"status": "success", "updated": update.dict(exclude_unset=True)}

@router.post("/api/order/{order_sn}/items/cost")
def update_item_costs(order_sn: str, updates: list[ItemCostUpdate]):
    """
    批量更新订单中商品的成本信息

    Args:
        order_sn (str): 订单编号
        updates (list[ItemCostUpdate]): 要更新的商品成本信息列表

    Returns:
        dict: 更新成功的响应
    """
    # 建立数据库连接
    conn = get_db_connection()
    c = conn.cursor(dictionary=True)

    # 处理每个商品的成本更新
    for u in updates:
        # 更新 order_item_costs 表（遗留表，用于兼容性）
        c.execute("""
            INSERT INTO order_item_costs (order_sn, item_id, model_id, sourcing_price)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE sourcing_price=VALUES(sourcing_price)
        """, (order_sn, u.item_id, u.model_id, u.sourcing_price))

        # 更新 order_item_user_costs 表中的采购成本和国内物流成本
        c.execute("""
            INSERT INTO order_item_user_costs (order_sn, item_id, model_id, purchase_cost, domestic_shipping_cost, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                purchase_cost=VALUES(purchase_cost),
                domestic_shipping_cost=VALUES(domestic_shipping_cost),
                updated_at=VALUES(updated_at)
        """, (order_sn, u.item_id, u.model_id, u.purchase_cost, u.domestic_shipping_cost, int(time.time())))

    # 计算新的订单总成本
    # 关联 order_items 表获取数量，关联 order_item_user_costs 表获取最新成本
    c.execute("""
        SELECT SUM((COALESCE(ouic.purchase_cost, 0) + COALESCE(ouic.domestic_shipping_cost, 0)) * oi.model_quantity_purchased)
        FROM order_items oi
        LEFT JOIN order_item_user_costs ouic ON oi.order_sn = ouic.order_sn 
            AND oi.item_id = ouic.item_id 
            AND oi.model_id = ouic.model_id
        WHERE oi.order_sn = %s
    """, (order_sn,))
    
    new_total_cost = c.fetchone()['SUM((COALESCE(ouic.purchase_cost, 0) + COALESCE(ouic.domestic_shipping_cost, 0)) * oi.model_quantity_purchased)'] or 0
    
    # 获取预估收入和汇率
    c.execute("SELECT estimated_revenue, exchange_rate FROM orders WHERE order_sn = %s", (order_sn,))
    order_row = c.fetchone()
    
    if order_row:
        estimated_revenue = order_row['estimated_revenue'] or 0
        exchange_rate = order_row['exchange_rate'] or 0
        
        # 计算预估利润
        # 利润 = (预估收入 * 汇率) - 总成本
        estimated_profit = (estimated_revenue * exchange_rate) - new_total_cost
        
        # 更新 orders 表中的 total_cost 和 estimated_profit
        c.execute("""
            UPDATE orders 
            SET total_cost = %s, estimated_profit = %s
            WHERE order_sn = %s
        """, (new_total_cost, estimated_profit, order_sn))

    # 提交事务
    conn.commit()
    conn.close()

    return {"status": "success", "new_total_cost": new_total_cost, "new_estimated_profit": estimated_profit if order_row else 0}

@router.get("/api/orders")
def get_orders(
    status: str = Query(None),
    keyword: str = Query(None),
    shop_id: int = Query(None, description="店铺ID筛选，可选"),
    site_id: str = Query(None, description="站点ID筛选，可选"),
    time_from: int = Query(None, description="创建时间起始时间戳(Unix)，可选"),
    time_to: int = Query(None, description="创建时间结束时间戳(Unix)，可选"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=10000)
):
    """
    获取订单列表，支持分页、状态筛选和关键词搜索

    Args:
        status (str, optional): 订单状态筛选 ('UNPAID', 'READY_TO_SHIP', 'SHIPPED', 'COMPLETED', 'CANCELLED', 'ALL')
        keyword (str, optional): 搜索关键词，会在订单号和买家用户名中进行模糊匹配
        page (int): 页码，从1开始，默认值为1
        limit (int): 每页显示数量，范围1-100，默认值为20

    Returns:
        dict: 包含总数、分页信息和订单列表的响应
    """
    # 建立数据库连接
    conn = get_db_connection()
    c = conn.cursor(dictionary=True)

    # 构建查询条件
    where_clauses = []
    params = []

    # 店铺ID筛选条件
    if shop_id is not None:
        where_clauses.append("shop_id = %s")
        params.append(shop_id)

    # 站点ID筛选条件
    if site_id is not None and site_id != 'all':
        # 导入店铺配置来获取站点下的店铺ID列表
        import sys
        from pathlib import Path
        TEST_DIR = Path(__file__).resolve().parent.parent / "test" / "shop_test"
        if str(TEST_DIR) not in sys.path:
            sys.path.append(str(TEST_DIR))

        from token_manager import ALL_SHOPS

        # 获取指定站点下的所有店铺ID
        site_shop_ids = []
        for shop in ALL_SHOPS:
            if shop.get('region') == site_id:
                site_shop_ids.append(shop['id'])

        if site_shop_ids:
            placeholders = ','.join(['%s'] * len(site_shop_ids))
            where_clauses.append(f"shop_id IN ({placeholders})")
            params.extend(site_shop_ids)
        else:
            # 如果站点下没有店铺，返回空结果
            return {
                "total": 0,
                "page": page,
                "limit": limit,
                "orders": []
            }

    # 状态筛选条件
    if status and status != 'ALL':
        if status == 'CANCELLED':
            # 取消状态包括 'CANCELLED' 和 'TO_RETURN'
            where_clauses.append("order_status IN ('CANCELLED', 'TO_RETURN')")
        else:
            # 其他状态直接匹配
            where_clauses.append("order_status = %s")
            params.append(status)

    # 时间范围筛选条件
    if time_from is not None:
        where_clauses.append("create_time >= %s")
        params.append(time_from)
    if time_to is not None:
        where_clauses.append("create_time <= %s")
        params.append(time_to)

    # 关键词搜索条件（订单号或买家用户名）
    if keyword:
        where_clauses.append("(order_sn LIKE %s OR buyer_username LIKE %s)")
        params.append(f"%{keyword}%")
        params.append(f"%{keyword}%")

    # 构建WHERE子句
    where_str = " AND ".join(where_clauses) if where_clauses else "1=1"

    # 查询总记录数
    c.execute(f"SELECT count(*) as cnt FROM orders WHERE {where_str}", params)
    total = c.fetchone()['cnt']

    # 构建分页查询语句 - 包含 estimated_revenue, exchange_rate, estimated_profit
    query = f"""
        SELECT raw_data, order_sn, order_status, total_amount, currency, create_time,
               buyer_username, shop_id, estimated_shipping_fee, total_cost, escrow_data,
               estimated_revenue, exchange_rate, estimated_profit, refund_amount
        FROM orders
        WHERE {where_str}
        ORDER BY create_time DESC
        LIMIT %s OFFSET %s
    """
    # 添加分页参数
    params.append(limit)  # 每页数量
    params.append((page - 1) * limit)  # 偏移量

    # 执行分页查询
    c.execute(query, params)
    rows = c.fetchall()

    # 处理查询结果，构建订单列表
    orders = []
    for r in rows:
        order = {}

        # 解析数据库中的原始订单数据
        if r['raw_data']:
            try:
                order = json.loads(r['raw_data'])
            except:
                # 如果解析失败，使用空字典
                pass

        # 确保关键字段有值（后备机制）
        order['order_sn'] = r['order_sn']
        order['order_status'] = r['order_status']
        order['buyer_username'] = r['buyer_username'] if r['buyer_username'] else (order.get('buyer_username', ''))
        order['total_amount'] = r['total_amount']
        order['shop_id'] = r['shop_id']
        order['estimated_shipping_fee'] = r['estimated_shipping_fee']
        order['create_time'] = r['create_time']
        order['total_cost'] = r['total_cost'] or 0  # 订单级别的采购总成本
        
        # 调试日志
        if order['order_sn'] == '2601069NC34KCU':
            print(f"DEBUG API: {order['order_sn']} - DB Revenue: {r['estimated_revenue']}, Profit: {r['estimated_profit']}")
        
        # 直接从数据库获取预估收入、汇率和预估利润（后端计算存储）
        order['estimated_revenue'] = r['estimated_revenue'] if r['estimated_revenue'] is not None else 0
        order['exchange_rate'] = r['exchange_rate'] if r['exchange_rate'] is not None else 0
        order['estimated_profit'] = r['estimated_profit'] if r['estimated_profit'] is not None else 0
        order['refund_amount'] = r['refund_amount'] if r['refund_amount'] is not None else 0

        # 从托管数据计算财务信息
        escrow_info = {}
        if r['escrow_data']:
            try:
                escrow_info = json.loads(r['escrow_data'])
            except:
                # 如果解析失败，使用空字典
                pass

        # 计算各项费用（如果没有托管数据，默认为0）
        commission = float(escrow_info.get('commission_fee', 0))      # 佣金
        service = float(escrow_info.get('service_fee', 0))           # 服务费
        transaction = float(escrow_info.get('seller_transaction_fee', 0))  # 交易手续费
        total_fees = commission + service + transaction

        # 计算订单收入（优先级：API直接提供 > 买家支付总额-费用 > 订单总额）
        order_income = escrow_info.get('order_income_amount')
        # if order_income is None:
        #     # 如果没有直接的收入字段，使用买家支付总额减去费用
        #     if escrow_info.get('buyer_total_amount'):
        #         order_income = float(escrow_info.get('buyer_total_amount')) - total_fees
        #     else:
        #         # 最后的备选方案：使用订单总额
        #         order_income = r['total_amount']

        # 构建财务信息字典
        order['financials'] = {
            'total_fees': total_fees,                               # 总费用
            'order_income': order_income,                          # 订单收入
            'commission_fee': commission,                          # 佣金费用
            'service_fee': service,                               # 服务费用
            'seller_transaction_fee': transaction,                # 交易手续费
            'buyer_paid_shipping': escrow_info.get('buyer_paid_shipping_fee', 0),  # 买家支付运费
            'shopee_shipping_rebate': escrow_info.get('shopee_shipping_rebate', 0), # Shopee运费补贴
            'actual_shipping_fee': escrow_info.get('actual_shipping_fee', 0)       # 实际运费
        }

        # 获取订单商品信息
        c.execute("""
            SELECT item_id, order_item_id, item_name, model_id, model_name, model_sku, model_quantity_purchased,
                   model_discounted_price, image_info
            FROM order_items
            WHERE order_sn = %s
        """, (r['order_sn'],))
        items_rows = c.fetchall()

        # 获取商品成本信息
        c.execute("""
            SELECT item_id, model_id, purchase_cost, domestic_shipping_cost
            FROM order_item_user_costs
            WHERE order_sn = %s
        """, (r['order_sn'],))
        cost_rows = c.fetchall()

        # 构建成本映射表
        cost_map = {}
        for cost_row in cost_rows:
            mid = cost_row['model_id'] if cost_row['model_id'] else 0
            key = f"{cost_row['item_id']}_{mid}"
            cost_map[key] = {
                'purchase_cost': cost_row['purchase_cost'] or 0,
                'domestic_shipping_cost': cost_row['domestic_shipping_cost'] or 0
            }

        # 将数据库中的商品信息转换为字典格式
        items_from_db = []
        for item_row in items_rows:
            mid = item_row['model_id'] if item_row['model_id'] else 0
            key = f"{item_row['item_id']}_{mid}"
            costs = cost_map.get(key, {'purchase_cost': 0, 'domestic_shipping_cost': 0})

            items_from_db.append({
                'item_id': item_row['item_id'],                           # 商品ID
                'order_item_id': item_row['order_item_id'],               # 订单项ID
                'item_name': item_row['item_name'],                       # 商品名称
                'model_id': item_row['model_id'],                         # 型号ID
                'model_name': item_row['model_name'],                     # 型号名称
                'model_sku': item_row['model_sku'],                       # SKU
                'model_quantity_purchased': item_row['model_quantity_purchased'],  # 购买数量
                'model_discounted_price': item_row['model_discounted_price'],      # 折后价格
                'image_info': json.loads(item_row['image_info']) if item_row['image_info'] else None,  # 图片信息
                'purchase_cost': costs['purchase_cost'],                  # 采购成本
                'domestic_shipping_cost': costs['domestic_shipping_cost'], # 国内物流成本
            })

        # 如果数据库中有商品信息，使用数据库中的数据（包含成本信息）
        if items_from_db:
            order['item_list'] = items_from_db

        # 将处理好的订单添加到结果列表
        orders.append(order)

    # 关闭数据库连接
    conn.close()

    # 返回分页结果
    return {
        "total": total,     # 总记录数
        "page": page,       # 当前页码
        "limit": limit,     # 每页数量
        "orders": orders    # 订单列表
    }

@router.get("/api/orders/stats")
def get_order_stats(
    shop_id: int = Query(None, description="店铺ID筛选，可选"),
    site_id: str = Query(None, description="站点ID筛选，可选"),
    status: str = Query(None, description="订单状态筛选，可选"),
    start_time: int = Query(None, description="创建时间起始时间戳(Unix)，可选"),
    end_time: int = Query(None, description="创建时间结束时间戳(Unix)，可选")
):
    """
    获取订单统计信息，按照前端友好的状态分组统计订单数量

    支持按店铺ID、站点ID、状态和创建时间范围进行筛选，用于生成订单状态分布图表

    Args:
        shop_id (int, optional): 店铺ID，用于筛选特定店铺的订单统计
        site_id (str, optional): 站点ID，用于筛选特定站点的订单统计
        status (str, optional): 订单状态，用于筛选特定状态的订单
        start_time (int, optional): Unix时间戳，筛选创建时间大于等于此时间的订单
        end_time (int, optional): Unix时间戳，筛选创建时间小于等于此时间的订单

    Returns:
        dict: 包含分组统计和原始状态分布的响应
            - counts: 按前端状态分组的统计结果
            - raw_breakdown: 原始状态分布统计
    """
    # 建立数据库连接并初始化表结构
    conn = get_db_connection()
    init_db_tables(conn)
    c = conn.cursor(dictionary=True)

    # 构建查询条件
    where_clauses = []
    params = []

    # 站点筛选条件 - 需要通过shop_id间接实现
    if site_id is not None and site_id != 'all':
        # 导入店铺配置来获取站点下的店铺ID列表
        import sys
        from pathlib import Path
        TEST_DIR = Path(__file__).resolve().parent.parent / "test" / "shop_test"
        if str(TEST_DIR) not in sys.path:
            sys.path.append(str(TEST_DIR))

        from token_manager import ALL_SHOPS

        # 获取指定站点下的所有店铺ID
        site_shop_ids = []
        for shop in ALL_SHOPS:
            if shop.get('region') == site_id:
                site_shop_ids.append(shop['id'])

        if site_shop_ids:
            placeholders = ','.join(['%s'] * len(site_shop_ids))
            where_clauses.append(f"shop_id IN ({placeholders})")
            params.extend(site_shop_ids)
        else:
            # 如果站点下没有店铺，返回空结果
            return {
                "counts": {
                    "all": 0, "pending": 0, "processing": 0, "shipped": 0,
                    "completed": 0, "cancelled": 0, "other": 0
                },
                "raw_breakdown": {}
            }

    # 店铺筛选条件
    if shop_id is not None:
        where_clauses.append("shop_id = %s")
        params.append(shop_id)

    # 状态筛选条件 - 直接使用Shopee原始状态
    if status is not None and status != 'all':
        where_clauses.append("order_status = %s")
        params.append(status)

    # 时间范围筛选条件
    if start_time is not None:
        where_clauses.append("create_time >= %s")
        params.append(start_time)
    if end_time is not None:
        where_clauses.append("create_time <= %s")
        params.append(end_time)

    # 构建WHERE子句
    where_str = " AND ".join(where_clauses) if where_clauses else "1=1"

    # 查询总订单数
    c.execute(f"SELECT count(*) as cnt FROM orders WHERE {where_str}", params)
    total = c.fetchone()['cnt']

    # 按订单状态分组统计数量
    c.execute(f"SELECT order_status, count(*) as cnt FROM orders WHERE {where_str} GROUP BY order_status", params)
    rows = c.fetchall()

    # 直接返回Shopee原始状态的统计
    status_counts = {}

    # 处理统计结果
    for r in rows:
        # 获取原始状态和数量
        raw_status = r['order_status'] if r['order_status'] is not None else 'UNKNOWN'
        cnt = r['cnt'] if 'cnt' in r.keys() else r[1]

        # 记录每个原始状态的数量
        status_counts[raw_status] = cnt

    # 统计退货退款（已完成）订单数量 - refund_amount > 0 的订单
    c.execute(f"SELECT count(*) as cnt FROM orders WHERE {where_str} AND refund_amount > 0", params)
    refund_completed_count = c.fetchone()['cnt']

    # 关闭数据库连接
    conn.close()

    # 返回统计结果
    return {
        "total": total,             # 总订单数
        "status_counts": status_counts,  # 各状态订单数
        "refund_completed": refund_completed_count  # 退货退款（已完成）订单数
    }

@router.get("/api/dashboard/financials")
def get_dashboard_financials(
    shop_id: int = Query(None, description="店铺ID筛选，可选"),
    site_id: str = Query(None, description="站点ID筛选，可选"),
    status: str = Query(None, description="订单状态筛选，可选"),
    start_time: int = Query(None, description="创建时间起始时间戳(Unix)，可选"),
    end_time: int = Query(None, description="创建时间结束时间戳(Unix)，可选")
):
    """
    获取仪表板财务统计信息，包括销售额、成本、利润等

    Args:
        shop_id (int, optional): 店铺ID，用于筛选特定店铺的财务统计
        site_id (str, optional): 站点ID，用于筛选特定站点的财务统计
        status (str, optional): 订单状态，用于筛选特定状态的订单
        start_time (int, optional): Unix时间戳，筛选创建时间大于等于此时间的订单
        end_time (int, optional): Unix时间戳，筛选创建时间小于等于此时间的订单

    Returns:
        dict: 包含财务统计数据的响应
    """
    # 建立数据库连接并初始化表结构
    conn = get_db_connection()
    init_db_tables(conn)
    c = conn.cursor(dictionary=True)

    # 构建查询条件
    where_clauses = []
    params = []

    # 站点筛选条件 - 需要通过shop_id间接实现
    if site_id is not None and site_id != 'all':
        # 导入店铺配置来获取站点下的店铺ID列表
        import sys
        from pathlib import Path
        TEST_DIR = Path(__file__).resolve().parent.parent / "test" / "shop_test"
        if str(TEST_DIR) not in sys.path:
            sys.path.append(str(TEST_DIR))

        from token_manager import ALL_SHOPS

        # 获取指定站点下的所有店铺ID
        site_shop_ids = []
        for shop in ALL_SHOPS:
            if shop.get('region') == site_id:
                site_shop_ids.append(shop['id'])

        if site_shop_ids:
            placeholders = ','.join(['%s'] * len(site_shop_ids))
            where_clauses.append(f"o.shop_id IN ({placeholders})")
            params.extend(site_shop_ids)
        else:
            # 如果站点下没有店铺，返回空结果
            return {
                "financials": {"sales": 0, "cost": 0, "profit": 0, "margin": 0},
                "summary": {"total_orders": 0, "avg_order_value": 0, "orders_with_cost": 0, "items_with_cost": 0, "total_items": 0},
                "history": []
            }

    # 店铺筛选条件
    if shop_id is not None:
        where_clauses.append("o.shop_id = %s")
        params.append(shop_id)

    # 状态筛选条件 - 直接使用Shopee原始状态
    if status is not None and status != 'all':
        where_clauses.append("o.order_status = %s")
        params.append(status)

    # 时间范围筛选条件
    if start_time is not None:
        where_clauses.append("o.create_time >= %s")
        params.append(start_time)
    if end_time is not None:
        where_clauses.append("o.create_time <= %s")
        params.append(end_time)

    # 构建WHERE子句
    where_str = " AND ".join(where_clauses) if where_clauses else "1=1"

    # 计算财务统计
    # 1. 总销售额 (商品总额 = 所有商品的价格总和)
    c.execute(f"""
        SELECT
            SUM(oi.model_discounted_price * oi.model_quantity_purchased) as total_sales,
            COUNT(DISTINCT o.order_sn) as order_count,
            AVG(oi.model_discounted_price * oi.model_quantity_purchased) as avg_item_value
        FROM orders o
        JOIN order_items oi ON o.order_sn = oi.order_sn
        WHERE {where_str}
    """, params)
    sales_row = c.fetchone()
    total_sales = sales_row['total_sales'] or 0
    order_count = sales_row['order_count'] or 0
    avg_order_value = sales_row['avg_item_value'] or 0

    # 2. 总成本、总利润、总收入
    # 用户要求：总收入显示为当地币 (SUM estimated_revenue)
    # 利润率=总利润(RMB) / 总收入(RMB)
    c.execute(f"""
        SELECT
            SUM(COALESCE(o.total_cost, 0)) as total_cost,
            SUM(COALESCE(o.estimated_profit, 0)) as total_profit,
            SUM(COALESCE(o.estimated_revenue, 0)) as total_revenue_local,
            SUM(COALESCE(o.estimated_revenue * COALESCE(o.exchange_rate, 1), 0)) as total_revenue_rmb
        FROM orders o
        WHERE {where_str}
    """, params)
    
    financial_row = c.fetchone()
    total_cost = financial_row['total_cost'] or 0
    total_profit = financial_row['total_profit'] or 0
    total_revenue_local = financial_row['total_revenue_local'] or 0
    total_revenue_rmb = financial_row['total_revenue_rmb'] or 0

    # 3. 计算利润率 (Profit/Revenue(RMB))
    profit_margin = (total_profit / total_revenue_rmb * 100) if total_revenue_rmb > 0 else 0

    # 4. 成本录入统计
    c.execute(f"""
        SELECT
            COUNT(DISTINCT CASE WHEN o.total_cost > 0 THEN o.order_sn END) as orders_with_cost,
            COUNT(DISTINCT o.order_sn) as total_orders,
            COUNT(DISTINCT CASE WHEN ouic.purchase_cost > 0 THEN CONCAT(o.order_sn, '-', ouic.item_id) END) as items_with_cost,
            COUNT(DISTINCT CONCAT(o.order_sn, '-', oi.item_id)) as total_items
        FROM orders o
        LEFT JOIN order_items oi ON o.order_sn = oi.order_sn
        LEFT JOIN order_item_user_costs ouic ON o.order_sn = ouic.order_sn
            AND oi.item_id = ouic.item_id
            AND oi.model_id = ouic.model_id
        WHERE {where_str}
    """, params)
    cost_stats = c.fetchone()
    orders_with_cost = cost_stats['orders_with_cost'] or 0
    total_orders = cost_stats['total_orders'] or 0
    items_with_cost = cost_stats['items_with_cost'] or 0
    total_items = cost_stats['total_items'] or 0

    # 5. 历史趋势数据 (按日期分组)
    # 为避免 Join 导致的 Cost/Profit 重复计算，我们将查询分为两步：
    
    # 5.1 获取每日成本、利润和订单数 (Order Level)
    c.execute(f"""
        SELECT
            DATE(FROM_UNIXTIME(o.create_time)) as date,
            COUNT(*) as order_count,
            SUM(COALESCE(o.total_cost, 0)) as daily_cost,
            SUM(COALESCE(o.estimated_profit, 0)) as daily_profit,
            SUM(COALESCE(o.estimated_revenue, 0)) as daily_revenue
        FROM orders o
        WHERE {where_str}
        GROUP BY DATE(FROM_UNIXTIME(o.create_time))
    """, params)
    
    financial_map = {}
    for row in c.fetchall():
        # MySQL Connector 可能返回 datetime.date 对象，转换为字符串
        date_key = str(row['date'])
        financial_map[date_key] = {
            'order_count': row['order_count'],
            'daily_cost': row['daily_cost'],
            'daily_profit': row['daily_profit'],
            'daily_revenue': row['daily_revenue']
        }

    # 5.2 获取每日销售额 (Item Level - 商品总额)
    c.execute(f"""
        SELECT
            DATE(FROM_UNIXTIME(o.create_time)) as date,
            SUM(oi.model_discounted_price * oi.model_quantity_purchased) as daily_sales
        FROM orders o
        JOIN order_items oi ON o.order_sn = oi.order_sn
        WHERE {where_str}
        GROUP BY DATE(FROM_UNIXTIME(o.create_time))
    """, params)
    
    sales_map = {}
    for row in c.fetchall():
        date_key = str(row['date'])
        sales_map[date_key] = row['daily_sales']

    # 5.3 合并数据
    # 5.3 合并数据 - 生成完整日期范围
    from datetime import datetime, timedelta
    
    start_dt = datetime.fromtimestamp(start_time) if start_time else (datetime.now() - timedelta(days=29))
    end_dt = datetime.fromtimestamp(end_time - 86400) if end_time else datetime.now() # end_time passed from frontend includes next day buffer
    
    # 确保日期范围按天遍历
    history_data = []
    current_dt = start_dt
    while current_dt <= end_dt:
        date_str = current_dt.strftime('%Y-%m-%d')
        
        fin = financial_map.get(date_str, {})
        sale = sales_map.get(date_str, 0)
        
        daily_cost = fin.get('daily_cost', 0)
        daily_profit = fin.get('daily_profit', 0)
        daily_revenue = fin.get('daily_revenue', 0)
        
        history_data.append({
            'date': date_str,
            'sales': sale or 0,
            'revenue': daily_revenue or 0,
            'cost': daily_cost or 0,
            'profit': daily_profit or 0
        })
        
        current_dt += timedelta(days=1)
    
    # 无需再反转或切片，直接返回完整正序列表

    # Debug log to check revenue data
    if history_data:
        print(f"DEBUG: First history item: {history_data[0]}")

    # 关闭数据库连接
    conn.close()

    # 返回财务统计结果
    return {
        "financials": {
            "sales": total_sales,
            "revenue": total_revenue_local,
            "revenue_rmb": total_revenue_rmb,
            "cost": total_cost,
            "profit": total_profit,
            "margin": profit_margin
        },
        "summary": {
            "total_orders": order_count,
            "avg_order_value": avg_order_value,
            "orders_with_cost": orders_with_cost,
            "total_orders": total_orders,
            "items_with_cost": items_with_cost,
            "total_items": total_items
        },
        "history": history_data
    }
