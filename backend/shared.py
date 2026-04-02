import mysql.connector
from pathlib import Path

# 共享数据库和工具函数
BASE_DIR = Path(__file__).resolve().parent
# DB_FILE 不再用于连接，但保留作为参考
# 我们现在切换到了 MySQL 服务器

def get_db_connection():
    """获取数据库连接"""
    # 连接到 MySQL 数据库 (支持环境变量配置，用于 Docker 部署)
    import os
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = int(os.getenv("DB_PORT", 3306))
    db_user = os.getenv("DB_USER", "root")
    db_password = os.getenv("DB_PASSWORD", "")
    db_name = os.getenv("DB_NAME", "shopee_orders")

    conn = mysql.connector.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_password,
        database=db_name
    )
    return conn

def init_db_tables(conn):
    """初始化数据库表结构"""
    c = conn.cursor(dictionary=True)
    
    # 辅助函数：检查列是否存在
    def column_exists(table, column):
        try:
            c.execute(f"SHOW COLUMNS FROM {table} LIKE '{column}'")
            return c.fetchone() is not None
        except mysql.connector.Error:
            return False

    # 检查 escrow_data 列是否存在，如果不存在则添加（简单的迁移逻辑）
    if not column_exists('orders', 'escrow_data'):
        try:
            c.execute("ALTER TABLE orders ADD COLUMN escrow_data TEXT")
        except:
            pass 

    # 检查 estimated_shipping_fee 列是否存在
    if not column_exists('orders', 'estimated_shipping_fee'):
        try:
            c.execute("ALTER TABLE orders ADD COLUMN estimated_shipping_fee DOUBLE")
        except:
            pass

    # 检查 total_cost 列是否存在
    if not column_exists('orders', 'total_cost'):
        try:
            c.execute("ALTER TABLE orders ADD COLUMN total_cost DOUBLE DEFAULT 0")
        except:
            pass

    # 检查 refund_amount 列是否存在
    if not column_exists('orders', 'refund_amount'):
        try:
            c.execute("ALTER TABLE orders ADD COLUMN refund_amount DECIMAL(10, 2) DEFAULT 0.00")
        except:
            pass

    # 创建订单主表
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_sn VARCHAR(255) PRIMARY KEY COMMENT '订单编号',
            shop_id BIGINT COMMENT '店铺ID',
            order_status VARCHAR(50) COMMENT '订单状态',
            total_amount DOUBLE COMMENT '订单总金额',
            estimated_shipping_fee DOUBLE COMMENT '预估运费',
            cost DOUBLE DEFAULT 0 COMMENT '成本（旧字段）',
            currency VARCHAR(10) COMMENT '货币类型',
            create_time BIGINT COMMENT '创建时间戳',
            pay_time BIGINT COMMENT '支付时间戳',
            shipping_carrier VARCHAR(100) COMMENT '物流承运商',
            payment_method VARCHAR(50) COMMENT '支付方式',
            buyer_username VARCHAR(100) COMMENT '买家用户名',
            recipient_address TEXT COMMENT '收件人地址（JSON）',
            raw_data TEXT COMMENT '原始API数据（JSON）',
            escrow_data TEXT COMMENT '托管/财务数据（JSON）',
            updated_at BIGINT COMMENT '更新时间戳',
            estimated_revenue DOUBLE COMMENT '预估收入',
            exchange_rate DOUBLE COMMENT '汇率',
            estimated_profit DOUBLE COMMENT '预估利润',
            total_cost DOUBLE DEFAULT 0 COMMENT '总成本',
            refund_amount DECIMAL(10, 2) DEFAULT 0.00 COMMENT '退款金额'
        ) COMMENT='订单主表'
    ''')
    
    # 创建订单商品表
    c.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
            order_sn VARCHAR(255) COMMENT '关联订单编号',
            item_id BIGINT COMMENT '商品ID',
            order_item_id BIGINT COMMENT '订单项ID',
            item_name TEXT COMMENT '商品名称',
            model_id BIGINT COMMENT '型号ID',
            model_name TEXT COMMENT '型号名称',
            model_sku VARCHAR(100) COMMENT 'SKU',
            model_quantity_purchased INT COMMENT '购买数量',
            model_discounted_price DOUBLE COMMENT '折后价格',
            image_info TEXT COMMENT '图片信息（JSON）',
            FOREIGN KEY(order_sn) REFERENCES orders(order_sn)
        ) COMMENT='订单商品表'
    ''')

    # 检查 order_items 表的新增列
    if not column_exists('order_items', 'model_id'):
        try:
            c.execute("ALTER TABLE order_items ADD COLUMN model_id BIGINT")
        except:
            pass

    if not column_exists('order_items', 'model_sku'):
        try:
            c.execute("ALTER TABLE order_items ADD COLUMN model_sku VARCHAR(100)")
        except:
            pass

    if not column_exists('order_items', 'order_item_id'):
        try:
            c.execute("ALTER TABLE order_items ADD COLUMN order_item_id BIGINT")
        except:
            pass

    # 创建成本映射表（管理端配置）
    c.execute('''
        CREATE TABLE IF NOT EXISTS cost_mappings (
            id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
            site_id VARCHAR(50) COMMENT '站点ID',
            shop_id VARCHAR(50) COMMENT '店铺ID',
            item_id BIGINT COMMENT '商品ID',
            sku_id VARCHAR(100) COMMENT 'SKU ID',
            product_name TEXT COMMENT '商品名称',
            purchase_cost DOUBLE DEFAULT 0 COMMENT '采购成本',
            domestic_shipping_cost DOUBLE DEFAULT 0 COMMENT '国内物流成本',
            created_at BIGINT COMMENT '创建时间',
            UNIQUE(site_id, shop_id, item_id, sku_id)
        ) COMMENT='成本映射表（管理端配置）'
    ''')

    # 创建订单项成本表（旧表，保留兼容性）
    c.execute('''
        CREATE TABLE IF NOT EXISTS order_item_costs (
            order_sn VARCHAR(255) COMMENT '订单编号',
            item_id BIGINT COMMENT '商品ID',
            model_id BIGINT DEFAULT 0 COMMENT '型号ID',
            sourcing_price DOUBLE COMMENT '采购价',
            PRIMARY KEY (order_sn, item_id, model_id)
        ) COMMENT='订单项成本表（旧表）'
    ''')

    # 创建订单项用户成本表（实际使用）
    # 与管理表 cost_mappings 区分开，这是具体到某个订单的快照
    c.execute('''
        CREATE TABLE IF NOT EXISTS order_item_user_costs (
            order_sn VARCHAR(255) COMMENT '订单编号',
            item_id BIGINT COMMENT '商品ID',
            model_id BIGINT DEFAULT 0 COMMENT '型号ID',
            purchase_cost DOUBLE DEFAULT 0 COMMENT '采购成本',
            domestic_shipping_cost DOUBLE DEFAULT 0 COMMENT '国内物流成本',
            updated_at BIGINT DEFAULT 0 COMMENT '更新时间',
            PRIMARY KEY (order_sn, item_id, model_id)
        ) COMMENT='订单项用户成本表（实际使用）'
    ''')

    # 创建 Shopee 全球商品类目表
    c.execute('''
        CREATE TABLE IF NOT EXISTS shopee_global_categories (
            category_id BIGINT PRIMARY KEY COMMENT '类目ID',
            parent_category_id BIGINT COMMENT '父类目ID',
            original_category_name VARCHAR(255) COMMENT '原始类目名称(英文)',
            display_category_name VARCHAR(255) COMMENT '展示类目名称(本地语言)',
            has_children BOOLEAN COMMENT '是否有子类目',
            updated_at BIGINT COMMENT '更新时间'
        ) COMMENT='Shopee全球商品类目表'
    ''')
    conn.commit()
    c.close()

# Import token manager functions (will be available after token_manager is in path)
def get_valid_token(shop_id):
    # Import here to avoid circular imports
    import sys
    from pathlib import Path
    TEST_DIR = Path(__file__).resolve().parent / "test" / "shop_test"
    if str(TEST_DIR) not in sys.path:
        sys.path.append(str(TEST_DIR))

    from token_manager import get_valid_token as _get_valid_token
    return _get_valid_token(shop_id)

# Import required modules for shared functions
import json
import time
import sqlite3
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import hmac
import hashlib

# Create global session (same as in server.py)
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "POST"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
api_session = requests.Session()
api_session.mount("http://", adapter)
api_session.mount("https://", adapter)

# Import constants
from token_manager import PARTNER_ID, PARTNER_KEY, HOST

def generate_shop_sign(path, timestamp, access_token, shop_id):
    base_string = f"{PARTNER_ID}{path}{timestamp}{access_token}{shop_id}"
    return hmac.new(
        PARTNER_KEY.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def fetch_order_from_api(shop_id, order_sn):
    token = get_valid_token(shop_id)
    if not token:
        print(f"Failed to get token for shop {shop_id}")
        return None

    path = "/api/v2/order/get_order_detail"
    timestamp = int(time.time())
    sign = generate_shop_sign(path, timestamp, token, shop_id)

    url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&access_token={token}&shop_id={shop_id}&sign={sign}"

    fields = [
        "order_sn", "order_status", "total_amount", "currency",
        "create_time", "pay_time", "shipping_carrier", "payment_method",
        "estimated_shipping_fee", "actual_shipping_fee",
        "buyer_username", "recipient_address", "item_list", "note", "invoice_data",
        "buyer_user_id", "message_to_seller"
    ]

    params = {
        "order_sn_list": order_sn,
        "response_optional_fields": ",".join(fields)
    }

    try:
        # 使用带重试机制的session，并设置30秒超时
        resp = api_session.get(url, params=params, timeout=30)
        data = resp.json()
        if "error" in data and data["error"]:
            print(f"API Error (Order): {data['message']}")
            return None
        order_list = data.get("response", {}).get("order_list", [])
        return order_list[0] if order_list else None
    except Exception as e:
        print(f"Network Exception (Order): {e}")
        return None

def fetch_escrow_detail(shop_id, order_sn):
    token = get_valid_token(shop_id)
    if not token:
        return None

    path = "/api/v2/payment/get_escrow_detail"
    timestamp = int(time.time())
    sign = generate_shop_sign(path, timestamp, token, shop_id)

    url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&access_token={token}&shop_id={shop_id}&sign={sign}&order_sn={order_sn}"

    try:
        # 使用带重试机制的session，并设置30秒超时
        resp = api_session.get(url, timeout=30)
        data = resp.json()
        if "error" in data and data["error"]:
            print(f"API Error (Escrow Single): {data.get('message')}")
            return None

        response_data = data.get("response", {})
        order_income = response_data.get("order_income", {})
        buyer_payment = response_data.get("buyer_payment_info", {})

        # Merge logic: buyer_payment_info contains the accurate tax breakdown (ICMS, etc.)
        # so we merge it into order_income.
        merged = order_income.copy()
        merged.update(buyer_payment)

        # Lift item-level field 'discount_from_coin' and 'discount_from_voucher_shopee' to root
        # as user requested these specific keys which are found in 'items' list.
        items = order_income.get("items", [])
        total_coins = 0.0
        total_shopee_voucher = 0.0
        total_seller_discount = 0.0

        for item in items:
            total_coins += float(item.get("discount_from_coin", 0))
            total_shopee_voucher += float(item.get("discount_from_voucher_shopee", 0))
            total_seller_discount += float(item.get("seller_discount", 0))

        merged["discount_from_coin"] = total_coins
        merged["discount_from_voucher_shopee"] = total_shopee_voucher
        merged["seller_discount"] = total_seller_discount

        return merged
    except Exception as e:
        print(f"Network Exception (Escrow Single): {e}")
        return None

def save_order_to_db(conn, shop_id, order, escrow_data=None):
    """
    保存订单数据到数据库
    
    Args:
        conn: 数据库连接对象
        shop_id: 店铺ID
        order: 订单详情数据 (字典)
        escrow_data: 托管/财务数据 (字典，可选)
    """
    c = conn.cursor(dictionary=True)

    # 准备 escrow_data 字符串
    escrow_json = json.dumps(escrow_data) if escrow_data else None

    # 提取预估运费 (优先使用 escrow 数据)
    est_ship = 0
    refund_amount = 0.0
    if escrow_data:
         est_ship = escrow_data.get('estimated_shipping_fee', 0)
         # 提取退款金额 (优先使用 refund_amount_to_buyer，如果没有则检查 seller_return_refund)
         val = escrow_data.get('refund_amount_to_buyer')
         if val is None:
             # seller_return_refund 通常是负数，取绝对值
             val = abs(float(escrow_data.get('seller_return_refund', 0) or 0))
         
         refund_amount = float(val or 0)
    else:
         est_ship = order.get('estimated_shipping_fee', 0)

    # ====== 计算预估订单收入 (estimated_revenue) ======
    # 汇率配置
    EXCHANGE_RATES = {
        'BRL': 1.24, 'USD': 7.2, 'SGD': 5.3, 'MYR': 1.6,
        'PHP': 0.13, 'IDR': 0.00046, 'THB': 0.2, 'VND': 0.00029, 'TWD': 0.23,
        'CNY': 1.0
    }
    currency = order.get('currency', 'BRL')
    exchange_rate = EXCHANGE_RATES.get(currency, 1.0)

    # 计算预估收入 - 直接使用 Shopee 返回的 escrow_amount
    estimated_revenue = 0
    if escrow_data:
        escrow_amount = escrow_data.get('escrow_amount')
        if escrow_amount is not None:
            estimated_revenue = float(escrow_amount)
    
    # 获取现有成本来计算利润（如果存在）
    c.execute("SELECT total_cost FROM orders WHERE order_sn = %s", (order.get('order_sn'),))
    existing = c.fetchone()
    total_cost = existing['total_cost'] if existing and existing['total_cost'] else 0
    
    # 计算预估利润 = 预估收入(原币种) * 汇率 - 总成本(人民币)
    revenue_in_rmb = estimated_revenue * exchange_rate
    estimated_profit = revenue_in_rmb - total_cost

    # 插入或更新订单数据 (Upsert)
    c.execute('''
        INSERT INTO orders (
            order_sn, shop_id, order_status, total_amount, estimated_shipping_fee, currency,
            create_time, pay_time, shipping_carrier, payment_method,
            buyer_username, recipient_address, raw_data, escrow_data, updated_at,
            estimated_revenue, exchange_rate, estimated_profit, refund_amount
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            order_status=VALUES(order_status),
            total_amount=VALUES(total_amount),
            estimated_shipping_fee=VALUES(estimated_shipping_fee),
            create_time=VALUES(create_time),
            pay_time=VALUES(pay_time),
            raw_data=VALUES(raw_data),
            escrow_data=COALESCE(VALUES(escrow_data), orders.escrow_data),
            updated_at=VALUES(updated_at),
            estimated_revenue=VALUES(estimated_revenue),
            exchange_rate=VALUES(exchange_rate),
            estimated_profit=VALUES(estimated_profit),
            refund_amount=VALUES(refund_amount)
    ''', (
        order.get('order_sn'),
        shop_id,
        order.get('order_status'),
        order.get('total_amount'),
        est_ship,
        order.get('currency'),
        order.get('create_time'),
        order.get('pay_time'),
        order.get('shipping_carrier'),
        order.get('payment_method'),
        order.get('buyer_username'),
        json.dumps(order.get('recipient_address', {})),
        json.dumps(order),
        escrow_json,
        int(time.time()),
        estimated_revenue,
        exchange_rate,
        estimated_profit,
        refund_amount
    ))

    # 保存订单项 - 删除并重新插入（不再包含成本字段）
    c.execute('DELETE FROM order_items WHERE order_sn = %s', (order.get('order_sn'),))
    for item in order.get('item_list', []):
        item_id = item.get('item_id')
        model_id = item.get('model_id', 0)

        c.execute('''
            INSERT INTO order_items (
                order_sn, item_id, order_item_id, item_name, model_id, model_name, model_sku,
                model_quantity_purchased, model_discounted_price, image_info
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            order.get('order_sn'),
            item_id,
            item.get('order_item_id'),  # 添加 order_item_id
            item.get('item_name'),
            model_id,
            item.get('model_name'),
            item.get('model_sku'),
            item.get('model_quantity_purchased'),
            item.get('model_discounted_price'),
            json.dumps(item.get('image_info', {}))
        ))

    # 确保用户成本记录表中存在该订单的所有商品记录（如果不存在）
    # 这保证了前端可以查询到所有商品的成本字段
    for item in order.get('item_list', []):
        item_id = item.get('item_id')
        model_id = item.get('model_id', 0)

        c.execute('''
            INSERT INTO order_item_user_costs (
                order_sn, item_id, model_id, purchase_cost, domestic_shipping_cost, updated_at
            ) VALUES (%s, %s, %s, 0, 0, %s)
            ON DUPLICATE KEY UPDATE order_sn=order_sn
        ''', (
            order.get('order_sn'),
            item_id,
            model_id,
            int(time.time())
        ))
    conn.commit()
    c.close()
