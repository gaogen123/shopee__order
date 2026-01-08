import sys
from pathlib import Path
import threading
import uuid
import time

# Add the test/shop_test directory to sys.path to import token_manager
# Assuming server.py is in backend/ and token_manager is in backend/test/shop_test/
BASE_DIR = Path(__file__).resolve().parent
TEST_DIR = BASE_DIR / "test" / "shop_test"
sys.path.append(str(TEST_DIR))

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import json
import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import hmac
import hashlib
from token_manager import get_valid_token, PARTNER_ID, PARTNER_KEY, HOST, ALL_SHOPS

# 配置requests重试策略和SSL超时设置
def create_session_with_retries():
    """创建带有重试机制的requests session"""
    session = requests.Session()
    
    # 配置重试策略：总共重试3次，对于连接错误、读取错误、超时等进行重试
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,  # 重试间隔：1s, 2s, 4s
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

# 创建全局session
api_session = create_session_with_retries()

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = BASE_DIR.parent / "shopee_orders.db"

# --- Helper Functions (Ported from single_order_implementation.py) ---

def get_db_connection():
    # Ensure DB file exists or create it if not (sqlite3 connects creates it, but we need tables)
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    return conn

def init_db_tables(conn):
    c = conn.cursor()
    
    # 1. Create Tables First (ensure latest schema is used for new tables)
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_sn TEXT PRIMARY KEY,
            shop_id INTEGER,
            order_status TEXT,
            total_amount REAL,
            estimated_shipping_fee REAL,
            cost REAL DEFAULT 0,
            purchase_cost REAL DEFAULT 0,
            domestic_shipping_cost REAL DEFAULT 0,
            total_cost REAL DEFAULT 0,
            currency TEXT,
            create_time INTEGER,
            pay_time INTEGER,
            shipping_carrier TEXT,
            payment_method TEXT,
            buyer_username TEXT,
            recipient_address TEXT,
            raw_data TEXT,
            escrow_data TEXT,
            updated_at INTEGER
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_sn TEXT,
            item_id INTEGER,
            item_name TEXT,
            model_id INTEGER,
            model_name TEXT,
            model_sku TEXT,
            model_quantity_purchased INTEGER,
            model_discounted_price REAL,
            image_info TEXT,
            purchase_cost REAL DEFAULT 0,
            domestic_shipping_cost REAL DEFAULT 0,
            FOREIGN KEY(order_sn) REFERENCES orders(order_sn)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS cost_mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id TEXT,
            shop_id TEXT,
            item_id INTEGER,
            sku_id TEXT,
            product_name TEXT,
            purchase_cost REAL DEFAULT 0,
            domestic_shipping_cost REAL DEFAULT 0,
            created_at INTEGER,
            UNIQUE(site_id, shop_id, item_id, sku_id)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS order_item_costs (
            order_sn TEXT,
            item_id INTEGER,
            model_id INTEGER DEFAULT 0,
            sourcing_price REAL,
            PRIMARY KEY (order_sn, item_id, model_id)
        )
    ''')

    # 2. Migrations (Check for columns and add if missing - for existing DBs)
    # This ensures that even if the table existed with an old schema, we add new columns.
    
    migrations = [
        ("orders", "escrow_data", "TEXT"),
        ("orders", "estimated_shipping_fee", "REAL"),
        ("orders", "purchase_cost", "REAL DEFAULT 0"),
        ("orders", "domestic_shipping_cost", "REAL DEFAULT 0"),
        ("orders", "total_cost", "REAL DEFAULT 0"),
        ("order_items", "model_id", "INTEGER"),
        ("order_items", "model_sku", "TEXT"),
        ("order_items", "purchase_cost", "REAL DEFAULT 0"),
        ("order_items", "domestic_shipping_cost", "REAL DEFAULT 0"),
    ]
    
    for table, col, dtype in migrations:
        try:
            c.execute(f"SELECT {col} FROM {table} LIMIT 1")
        except sqlite3.OperationalError:
            try:
                print(f"Migrating {table}: Adding {col}...")
                c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {dtype}")
            except Exception as e:
                print(f"Migration Error ({table}.{col}): {e}")

    conn.commit()

def generate_shop_sign(path, timestamp, access_token, shop_id):
    base_string = f"{PARTNER_ID}{path}{timestamp}{access_token}{shop_id}"
    return hmac.new(
        PARTNER_KEY.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def save_order_to_db(conn, shop_id, order, escrow_data=None):
    c = conn.cursor()
    
    # Prepare escrow_data string
    escrow_json = json.dumps(escrow_data) if escrow_data else None
    
    # Extract estimated shipping fee (priority to escrow data)
    est_ship = 0
    if escrow_data and 'estimated_shipping_fee' in escrow_data:
         est_ship = escrow_data.get('estimated_shipping_fee', 0)
    else:
         est_ship = order.get('estimated_shipping_fee', 0)
    
    # Upsert with new column
    c.execute('''
        INSERT INTO orders (
            order_sn, shop_id, order_status, total_amount, estimated_shipping_fee, currency, 
            create_time, pay_time, shipping_carrier, payment_method, 
            buyer_username, recipient_address, raw_data, escrow_data, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(order_sn) DO UPDATE SET
            order_status=excluded.order_status,
            total_amount=excluded.total_amount,
            estimated_shipping_fee=excluded.estimated_shipping_fee,
            create_time=excluded.create_time,
            pay_time=excluded.pay_time,
            raw_data=excluded.raw_data,
            escrow_data=COALESCE(excluded.escrow_data, orders.escrow_data),
            updated_at=excluded.updated_at
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
        int(time.time())
    ))
    
    # 在删除订单项之前，先保存现有的成本数据
    # 这样可以防止再次同步订单时丢失用户手动输入的成本信息
    c.execute('''
        SELECT item_id, model_id, purchase_cost, domestic_shipping_cost 
        FROM order_items 
        WHERE order_sn = ?
    ''', (order.get('order_sn'),))
    
    existing_costs = {}
    for row in c.fetchall():
        item_id = row[0]
        model_id = row[1] if row[1] else 0
        key = f"{item_id}_{model_id}"
        existing_costs[key] = {
            'purchase_cost': row[2] if row[2] else 0,
            'domestic_shipping_cost': row[3] if row[3] else 0
        }
    
    # Save Items - 删除并重新插入，但保留成本数据
    c.execute('DELETE FROM order_items WHERE order_sn = ?', (order.get('order_sn'),))
    
    total_order_purchase_cost = 0.0
    total_order_domestic_shipping_cost = 0.0
    
    for item in order.get('item_list', []):
        item_id = item.get('item_id')
        model_id = item.get('model_id', 0)
        model_sku = item.get('model_sku', '') or '' # Ensure string
        key = f"{item_id}_{model_id}"
        
        # 1. 尝试获取现有成本 (Priority 1: Existing on this order item)
        costs = existing_costs.get(key)
        
        purchase_cost = 0.0
        domestic_shipping_cost = 0.0
        
        if costs and (costs['purchase_cost'] > 0 or costs['domestic_shipping_cost'] > 0):
             purchase_cost = costs['purchase_cost']
             domestic_shipping_cost = costs['domestic_shipping_cost']
        else:
             # 2. 如果没有现有成本，尝试从映射表中查找 (Priority 2: Global Mapping)
             # Note: shop_id in DB is usually stored as string or int, ensure consistency.
             # cost_mappings uses TEXT for shop_id.
             c.execute('''
                 SELECT purchase_cost, domestic_shipping_cost 
                 FROM cost_mappings 
                 WHERE shop_id = ? AND item_id = ? AND sku_id = ?
             ''', (str(shop_id), item_id, model_sku))
             mapping = c.fetchone()
             if mapping:
                 purchase_cost = mapping[0]
                 domestic_shipping_cost = mapping[1]
        
        # Keep track for total
        qty = item.get('model_quantity_purchased', 1)
        total_order_purchase_cost += (purchase_cost * qty)
        total_order_domestic_shipping_cost += (domestic_shipping_cost * qty)

        c.execute('''
            INSERT INTO order_items (
                order_sn, item_id, item_name, model_id, model_name, model_sku,
                model_quantity_purchased, model_discounted_price, image_info,
                purchase_cost, domestic_shipping_cost
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            order.get('order_sn'),
            item_id,
            item.get('item_name'),
            model_id,
            item.get('model_name'),
            model_sku,
            item.get('model_quantity_purchased'),
            item.get('model_discounted_price'),
            json.dumps(item.get('image_info', {})),
            purchase_cost, 
            domestic_shipping_cost
        ))
    
    # Update Order Level Costs
    total_cost = total_order_purchase_cost + total_order_domestic_shipping_cost
    c.execute('''
        UPDATE orders 
        SET purchase_cost = ?, domestic_shipping_cost = ?, total_cost = ?
        WHERE order_sn = ?
    ''', (total_order_purchase_cost, total_order_domestic_shipping_cost, total_cost, order.get('order_sn')))
    
    conn.commit()

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

@app.get("/api/order/{order_sn}")
def get_order(order_sn: str, shop_id: int = Query(494829323, description="Shop ID to fetch order from")):
    print(f"Reading order {order_sn} from DB (API skipped)...")
    
    conn = get_db_connection()
    init_db_tables(conn)
    
    # Always read from DB to return to client
    cursor = conn.cursor()
    cursor.execute("SELECT raw_data, escrow_data, purchase_cost, domestic_shipping_cost, total_cost FROM orders WHERE order_sn = ?", (order_sn,))
    row = cursor.fetchone()
    
    result_data = {}
    
    if row and row['raw_data']:
        result_data = json.loads(row['raw_data'])
        if row['escrow_data']:
            result_data['escrow_info'] = json.loads(row['escrow_data'])
        # Add cost to response
        result_data['purchase_cost'] = row['purchase_cost'] if row['purchase_cost'] is not None else 0
        result_data['domestic_shipping_cost'] = row['domestic_shipping_cost'] if row['domestic_shipping_cost'] is not None else 0
        result_data['total_cost'] = row['total_cost'] if row['total_cost'] is not None else 0
    else:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")

    # 3. Enhance response with requested fields from Escrow data
    # "费用=佣金+服务费+交易手续费"
    if 'escrow_info' in result_data and result_data['escrow_info']:
        ei = result_data['escrow_info']
        
        commission = float(ei.get('commission_fee', 0))
        service = float(ei.get('service_fee', 0))
        transaction = float(ei.get('seller_transaction_fee', 0))
        
        result_data['financials'] = {
            'estimated_shipping_fee': ei.get('estimated_shipping_fee'),
            'commission_fee': commission,
            'service_fee': service,
            'seller_transaction_fee': transaction,
            'original_price': ei.get('original_price'),
            'buyer_total_amount': ei.get('buyer_total_amount'),
            'shopee_shipping_rebate': ei.get('shopee_shipping_rebate', 0),
            'total_fees': commission + service + transaction
        }

    # Merge Item Costs from order_items (Source of Truth)
    cursor.execute("SELECT item_id, model_id, purchase_cost FROM order_items WHERE order_sn = ?", (order_sn,))
    cost_rows = cursor.fetchall()
    cost_map = {}
    for cr in cost_rows:
        mid = cr['model_id'] if cr['model_id'] else 0
        key = f"{cr['item_id']}_{mid}"
        cost_map[key] = cr['purchase_cost']

    if 'item_list' in result_data:
        for item in result_data['item_list']:
             mid = item.get('model_id', 0)
             key = f"{item.get('item_id')}_{mid}"
             item['sourcing_price'] = cost_map.get(key, 0)
    
    conn.close()
    return result_data

class CostUpdate(BaseModel):
    cost: float | None = None
    purchase_cost: float | None = None
    domestic_shipping_cost: float | None = None
    total_cost: float | None = None

@app.post("/api/order/{order_sn}/cost")
def update_order_cost(order_sn: str, update: CostUpdate):
    conn = get_db_connection()
    c = conn.cursor()
    
    if update.cost is not None:
        c.execute("UPDATE orders SET cost = ? WHERE order_sn = ?", (update.cost, order_sn))
        
    if update.purchase_cost is not None:
        c.execute("UPDATE orders SET purchase_cost = ? WHERE order_sn = ?", (update.purchase_cost, order_sn))
        
    if update.domestic_shipping_cost is not None:
        c.execute("UPDATE orders SET domestic_shipping_cost = ? WHERE order_sn = ?", (update.domestic_shipping_cost, order_sn))

    if update.total_cost is not None:
        c.execute("UPDATE orders SET total_cost = ? WHERE order_sn = ?", (update.total_cost, order_sn))
        
    conn.commit()
    conn.close()
    return {"status": "success", "updated": update.dict(exclude_unset=True)}

class ItemCostUpdate(BaseModel):
    item_id: int
    model_id: int = 0
    sourcing_price: float = 0
    purchase_cost: float = 0
    domestic_shipping_cost: float = 0

@app.post("/api/order/{order_sn}/items/cost")
def update_item_costs(order_sn: str, updates: list[ItemCostUpdate]):
    conn = get_db_connection()
    c = conn.cursor()
    for u in updates:
        # Update order_item_costs table (legacy - keep for compatibility)
        c.execute("""
            INSERT INTO order_item_costs (order_sn, item_id, model_id, sourcing_price)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(order_sn, item_id, model_id) DO UPDATE SET sourcing_price=excluded.sourcing_price
        """, (order_sn, u.item_id, u.model_id, u.sourcing_price))
        
        # Update order_items table with purchase_cost and domestic_shipping_cost
        # FIX: Include model_id in the where clause to target specific variation
        c.execute("""
            UPDATE order_items 
            SET purchase_cost = ?, domestic_shipping_cost = ?
            WHERE order_sn = ? AND item_id = ? AND model_id = ?
        """, (u.purchase_cost, u.domestic_shipping_cost, order_sn, u.item_id, u.model_id))
        
    # Recalculate Order Totals
    c.execute("""
        SELECT SUM(purchase_cost * model_quantity_purchased) as total_purchase,
               SUM(domestic_shipping_cost * model_quantity_purchased) as total_shipping
        FROM order_items
        WHERE order_sn = ?
    """, (order_sn,))
    
    row = c.fetchone()
    total_purchase = row[0] if row[0] else 0.0
    total_shipping = row[1] if row[1] else 0.0
    total_cost = total_purchase + total_shipping
    
    c.execute("""
        UPDATE orders 
        SET purchase_cost = ?, domestic_shipping_cost = ?, total_cost = ?
        WHERE order_sn = ?
    """, (total_purchase, total_shipping, total_cost, order_sn))

    conn.commit()
    conn.close()
    return {"status": "success", "total_cost": total_cost}

@app.get("/api/orders")
def get_orders(
    status: str = Query(None),
    keyword: str = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    time_from: int = Query(None),
    time_to: int = Query(None),
    shop_id: str = Query(None),
    site_id: str = Query(None)
):
    conn = get_db_connection()
    c = conn.cursor()
    print(f"DEBUG: get_orders params - time_from: {time_from}, time_to: {time_to}, status: {status}, site_id: {site_id}, shop_id: {shop_id}")
    
    where_clauses = ["1=1"]
    params = []
    
    if status and status != 'ALL':
        if status == 'CANCELLED':
             where_clauses.append("order_status IN ('CANCELLED', 'TO_RETURN')")
        else:
             where_clauses.append("order_status = ?")
             params.append(status)
        
    if keyword:
        where_clauses.append("(order_sn LIKE ? OR buyer_username LIKE ?)")
        params.append(f"%{keyword}%")
        params.append(f"%{keyword}%")
        
    if time_from:
        where_clauses.append("create_time >= ?")
        params.append(time_from)
        
    if time_to:
        where_clauses.append("create_time <= ?")
        params.append(time_to)
        
    if shop_id and shop_id != 'all':
        where_clauses.append("shop_id = ?")
        params.append(shop_id)
    
    if site_id and site_id != 'all':
        # Find all shops in this site
        site_shop_ids = [str(s['id']) for s in ALL_SHOPS if s.get('region') == site_id]
        if site_shop_ids:
            placeholders = ','.join(['?'] * len(site_shop_ids))
            where_clauses.append(f"shop_id IN ({placeholders})")
            params.extend(site_shop_ids)
        else:
            # Site has no shops, return nothing
            where_clauses.append("1=0")
        
    where_str = " AND ".join(where_clauses)
    
    # Count
    c.execute(f"SELECT count(*) FROM orders WHERE {where_str}", params)
    total = c.fetchone()[0]
    
    # Fetch orders (Added escrow_data)
    query = f"SELECT raw_data, order_sn, order_status, total_amount, currency, create_time, buyer_username, shop_id, estimated_shipping_fee, total_cost, escrow_data FROM orders WHERE {where_str} ORDER BY create_time DESC LIMIT ? OFFSET ?"
    params.append(limit)
    params.append((page - 1) * limit)
    
    c.execute(query, params)
    rows = c.fetchall()
    
    orders = []
    for r in rows:
        order = {}
        if r['raw_data']:
             try:
                order = json.loads(r['raw_data'])
             except:
                pass
        # Ensure fallback
        order['order_sn'] = r['order_sn']
        order['order_status'] = r['order_status']
        order['buyer_username'] = r['buyer_username'] if r['buyer_username'] else (order.get('buyer_username', ''))
        order['total_amount'] = r['total_amount']
        order['shop_id'] = r['shop_id']
        order['estimated_shipping_fee'] = r['estimated_shipping_fee']
        order['create_time'] = r['create_time']
        order['total_cost'] = r['total_cost'] or 0  # 采购总成本（订单级别）
        
        # Calculate Financials from Escrow Data
        escrow_info = {}
        if r['escrow_data']:
            try:
                escrow_info = json.loads(r['escrow_data'])
            except:
                pass
        
        # Default financials (0 if no escrow data yet)
        commission = float(escrow_info.get('commission_fee', 0))
        service = float(escrow_info.get('service_fee', 0))
        transaction = float(escrow_info.get('seller_transaction_fee', 0))
        total_fees = commission + service + transaction
        
        # Calculate Order Income (Revenue)
        # Priority: order_income_amount (direct from API) > buyer_total_amount - fees (fallback approximation)
        order_income = escrow_info.get('order_income_amount')
        if order_income is None:
             # Fallback if specific field missing but we have others
             if escrow_info.get('buyer_total_amount'):
                 order_income = float(escrow_info.get('buyer_total_amount')) - total_fees
             else:
                 order_income = r['total_amount'] # Fallback to total amount
        
        order['financials'] = {
            'total_fees': total_fees,
            'order_income': order_income,
            'commission_fee': commission,
            'service_fee': service,
            'seller_transaction_fee': transaction,
            'buyer_paid_shipping': escrow_info.get('buyer_paid_shipping_fee', 0), # Potentially available
            'shopee_shipping_rebate': escrow_info.get('shopee_shipping_rebate', 0),
            'actual_shipping_fee': escrow_info.get('actual_shipping_fee', 0)
        }
        
        # Fetch order items with costs
        c.execute("""
            SELECT item_id, item_name, model_id, model_name, model_sku, model_quantity_purchased, 
                   model_discounted_price, image_info, purchase_cost, domestic_shipping_cost
            FROM order_items 
            WHERE order_sn = ?
        """, (r['order_sn'],))
        items_rows = c.fetchall()
        
        # Merge with raw_data item_list or create new items
        items_from_db = []
        for item_row in items_rows:
            items_from_db.append({
                'item_id': item_row['item_id'],
                'item_name': item_row['item_name'],
                'model_id': item_row['model_id'],
                'model_name': item_row['model_name'],
                'model_sku': item_row['model_sku'],
                'model_quantity_purchased': item_row['model_quantity_purchased'],
                'model_discounted_price': item_row['model_discounted_price'],
                'image_info': json.loads(item_row['image_info']) if item_row['image_info'] else None,
                'purchase_cost': item_row['purchase_cost'] or 0,
                'domestic_shipping_cost': item_row['domestic_shipping_cost'] or 0,
            })
        
        # If we have items from DB, use them; otherwise fallback to raw_data
        if items_from_db:
            order['item_list'] = items_from_db
        
        orders.append(order)
             
    conn.close()
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "orders": orders
    }

def fetch_order_list_from_api(shop_id, time_from, time_to):
    token = get_valid_token(shop_id)
    if not token:
        print("Error: No valid token for shop", shop_id)
        return []

    path = "/api/v2/order/get_order_list"
    timestamp = int(time.time())
    all_order_sns = []
    
    # Shopee API v2 limits get_order_list to a max of 15 days (1,296,000 seconds)
    MAX_RANGE = 15 * 24 * 3600
    
    # Split the requested time range into 15-day chunks
    current_from = time_from
    while current_from < time_to:
        current_to = min(current_from + MAX_RANGE, time_to)
        
        cursor = ""
        while True:
            sign = generate_shop_sign(path, timestamp, token, shop_id)
            url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&access_token={token}&shop_id={shop_id}&sign={sign}"
            
            params = {
                "time_range_field": "create_time",
                "time_from": current_from,
                "time_to": current_to,
                "page_size": 100,
                "cursor": cursor
            }
            
            try:
                # 使用带重试机制的session，并设置30秒超时
                resp = api_session.get(url, params=params, timeout=30)
                data = resp.json()
                if "error" in data and data["error"]:
                    msg = data.get("message", "Unknown error")
                    print(f"API Error (Order List segment {current_from}-{current_to}): {msg}")
                    # If it's a critical error (like token), we stop everything
                    if "token" in msg.lower():
                        return all_order_sns # Return what we have
                    break
                
                response_data = data.get("response", {})
                order_list = response_data.get("order_list", [])
                for o in order_list:
                    if o["order_sn"] not in all_order_sns:
                        all_order_sns.append(o["order_sn"])
                
                if not response_data.get("more", False):
                    break
                cursor = response_data.get("next_cursor", "")
            except Exception as e:
                print(f"Error fetching order list segment: {e}")
                break
        
        current_from = current_to  # 移动到下一个时间段（无缝连接，避免遗漏订单）

    return all_order_sns

class SyncRequest(BaseModel):
    time_from: int
    time_to: int
    shop_id: int = 494829323 # 默认店铺ID

@app.get("/api/sync/get_order_sns")
def get_order_sns_to_sync(time_from: int, time_to: int, shop_id: int = 494829323):
    order_sns = fetch_order_list_from_api(shop_id, time_from, time_to)
    return {"order_sns": order_sns}

class SingleSyncRequest(BaseModel):
    order_sn: str
    shop_id: int = 494829323

# --- Background Sync Task Management ---
SYNC_TASKS = {} # task_id -> {status, current, total, count, error}

def run_sync_task(task_id, shop_id, time_from, time_to):
    try:
        order_sns = fetch_order_list_from_api(shop_id, time_from, time_to)
        total = len(order_sns)
        SYNC_TASKS[task_id] = {"task_id": task_id, "status": "running", "current": 0, "total": total, "count": 0}
        
        count = 0
        conn = get_db_connection()
        for i, sn in enumerate(order_sns):
            order_data = fetch_order_from_api(shop_id, sn)
            if order_data:
                escrow_data = fetch_escrow_detail(shop_id, sn)
                save_order_to_db(conn, shop_id, order_data, escrow_data)
                count += 1
            SYNC_TASKS[task_id]["current"] = i + 1
            SYNC_TASKS[task_id]["count"] = count
            
        conn.close()
        SYNC_TASKS[task_id]["status"] = "completed"
    except Exception as e:
        print(f"Sync Task Error: {e}")
        SYNC_TASKS[task_id]["status"] = "failed"
        SYNC_TASKS[task_id]["error"] = str(e)

@app.post("/api/sync_orders")
def sync_orders(req: SyncRequest):
    task_id = str(uuid.uuid4())
    SYNC_TASKS[task_id] = {"task_id": task_id, "status": "starting", "current": 0, "total": 0, "count": 0}
    
    thread = threading.Thread(target=run_sync_task, args=(task_id, req.shop_id, req.time_from, req.time_to))
    thread.start()
    
    return {"status": "accepted", "task_id": task_id}

class BatchSyncItem(BaseModel):
    order_sn: str
    shop_id: int

class BatchSyncRequest(BaseModel):
    items: List[BatchSyncItem]

def run_batch_sync_task(task_id, items):
    total = len(items)
    SYNC_TASKS[task_id] = {"task_id": task_id, "status": "running", "current": 0, "total": total, "count": 0}
    
    count = 0
    conn = get_db_connection()
    for i, item in enumerate(items):
        try:
            shop_id = item.shop_id
            sn = item.order_sn
            order_data = fetch_order_from_api(shop_id, sn)
            if order_data:
                escrow_data = fetch_escrow_detail(shop_id, sn)
                save_order_to_db(conn, shop_id, order_data, escrow_data)
                count += 1
        except Exception as e:
            print(f"Batch Sync Error for {item.order_sn}: {e}")
        
        SYNC_TASKS[task_id]["current"] = i + 1
        SYNC_TASKS[task_id]["count"] = count
        
    conn.close()
    SYNC_TASKS[task_id]["status"] = "completed"

@app.post("/api/sync_batch")
def sync_batch(req: BatchSyncRequest):
    task_id = str(uuid.uuid4())
    SYNC_TASKS[task_id] = {"task_id": task_id, "status": "starting", "current": 0, "total": 0, "count": 0}
    
    thread = threading.Thread(target=run_batch_sync_task, args=(task_id, req.items))
    thread.start()
    
    return {"status": "accepted", "task_id": task_id}

@app.get("/api/sync/status/{task_id}")
def get_sync_status(task_id: str):
    if task_id not in SYNC_TASKS:
        raise HTTPException(status_code=404, detail="Task not found")
    return SYNC_TASKS[task_id]

@app.post("/api/sync/order")
def sync_single_order(req: SingleSyncRequest):
    order_data = fetch_order_from_api(req.shop_id, req.order_sn)
    if order_data:
        escrow_data = fetch_escrow_detail(req.shop_id, req.order_sn)
        conn = get_db_connection()
        save_order_to_db(conn, req.shop_id, order_data, escrow_data)
        conn.close()
        return {"status": "success"}
    return {"status": "error", "message": "Failed to fetch order data"}

@app.get("/api/shops")
def get_shops_endpoint():
    """
    Return the list of configured shops, grouping them by Region (as 'sites').
    """
    formatted_shops = []
    regions = set()
    
    for shop in ALL_SHOPS:
        region = shop.get('region', 'Unknown')
        regions.add(region)
        
        formatted_shops.append({
            "value": str(shop['id']),
            "label": shop['name'],
            "siteId": region, # Use region as the siteId for filtering
            "region": region
        })
    
    # Sort regions
    sorted_regions = sorted(list(regions))
    
    # Build sites list from regions
    formatted_sites = [{ "value": "all", "label": "全部站点" }]
    for r in sorted_regions:
        formatted_sites.append({
            "value": r,
            "label": r 
        })
    
    return {
        "shops": formatted_shops,
        "sites": formatted_sites
    }

class MappingBase(BaseModel):
    site_id: str
    shop_id: str
    item_id: int
    sku_id: str | None = None
    product_name: str
    purchase_cost: float
    domestic_shipping_cost: float

class MappingCreate(MappingBase):
    pass

class Mapping(MappingBase):
    id: int
    created_at: int

@app.post("/api/mappings/save")
def save_mapping(mapping: MappingCreate):
    conn = get_db_connection()
    c = conn.cursor()
    
    # Upsert mapping
    c.execute("""
        INSERT INTO cost_mappings (
            site_id, shop_id, item_id, sku_id, product_name, 
            purchase_cost, domestic_shipping_cost, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(site_id, shop_id, item_id, sku_id) DO UPDATE SET
            purchase_cost=excluded.purchase_cost,
            domestic_shipping_cost=excluded.domestic_shipping_cost,
            product_name=excluded.product_name,
            created_at=excluded.created_at
    """, (
        mapping.site_id, mapping.shop_id, mapping.item_id, mapping.sku_id or "", mapping.product_name,
        mapping.purchase_cost, mapping.domestic_shipping_cost, int(time.time())
    ))
    
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.get("/api/mappings")
def get_mappings():
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM cost_mappings ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    
    mappings = []
    for r in rows:
        mappings.append({
            "id": r["id"],
            "siteId": r["site_id"],
            "shopId": r["shop_id"],
            "productId": str(r["item_id"]),
            "productName": r["product_name"],
            "sku": r["sku_id"],
            "purchaseCost": r["purchase_cost"],
            "domesticShippingCost": r["domestic_shipping_cost"],
            "createdAt": r["created_at"]
        })
    return mappings

@app.get("/api/dashboard/stats")
def get_dashboard_stats(
    time_from: int = Query(None),
    time_to: int = Query(None),
    shop_id: str = Query(None),
    site_id: str = Query(None),
    status: str = Query(None)
):
    conn = get_db_connection()
    c = conn.cursor()
    
    where_clauses = ["1=1"]
    params = []
    
    if time_from:
        where_clauses.append("create_time >= ?")
        params.append(time_from)
        
    if time_to:
        where_clauses.append("create_time <= ?")
        params.append(time_to)
        
    if shop_id and shop_id != 'all':
        where_clauses.append("shop_id = ?")
        params.append(shop_id)
        
    if site_id and site_id != 'all':
        # Find all shops in this site
        site_shop_ids = [str(s['id']) for s in ALL_SHOPS if s.get('region') == site_id]
        if site_shop_ids:
            placeholders = ','.join(['?'] * len(site_shop_ids))
            where_clauses.append(f"shop_id IN ({placeholders})")
            params.extend(site_shop_ids)
        else:
            # Site has no shops, return nothing
            where_clauses.append("1=0")

    if status and status != 'all':
        if status == 'CANCELLED':
             where_clauses.append("order_status IN ('CANCELLED', 'TO_RETURN')")
        else:
             where_clauses.append("order_status = ?")
             params.append(status)
        
    where_str = " AND ".join(where_clauses)
    
    # 1. Order Counts
    c.execute(f"""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN order_status = 'READY_TO_SHIP' THEN 1 ELSE 0 END) as to_ship,
            SUM(CASE WHEN order_status IN ('SHIPPING', 'TO_CONFIRM_RECEIVE') THEN 1 ELSE 0 END) as shipping,
            SUM(CASE WHEN order_status = 'COMPLETED' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN order_status IN ('CANCELLED', 'TO_RETURN') THEN 1 ELSE 0 END) as cancelled,
            SUM(CASE WHEN total_cost > 0 THEN 1 ELSE 0 END) as cost_entered,
            SUM(CASE WHEN total_cost <= 0 OR total_cost IS NULL THEN 1 ELSE 0 END) as cost_not_entered
        FROM orders
        WHERE {where_str}
    """, params)
    
    counts = c.fetchone()
    
    # 2. Financials & Timeline - 需要获取raw_data来计算准确的预估收入
    c.execute(f"""
        SELECT 
            total_amount,
            escrow_data,
            total_cost,
            order_status,
            create_time,
            currency,
            raw_data
        FROM orders
        WHERE {where_str}
        ORDER BY create_time ASC
    """, params)
    
    rows = c.fetchall()
    
    total_sales = 0.0
    total_product_cost = 0.0
    total_profit = 0.0
    
    daily_stats = {} # "YYYY-MM-DD" -> {sales, cost, profit}
    
    from datetime import datetime

    # Hardcoded Exchange Rates (Should optimally come from DB or API)
    EXCHANGE_RATES = {
        'BRL': 1.25, 'USD': 7.2, 'SGD': 5.3, 'MYR': 1.6,
        'PHP': 0.13, 'IDR': 0.00046, 'THB': 0.2, 'VND': 0.00029, 'TWD': 0.23,
        'CNY': 1.0
    }
    
    for r in rows:
        if r[3] in ('CANCELLED', 'TO_RETURN'):
            continue 
            
        amount = r[0] if r[0] else 0
        cost = r[2] if r[2] else 0 # Cost is already in CNY
        create_time = r[4]
        currency = r[5] if r[5] else 'CNY'
        raw_data_str = r[6]
        
        rate = EXCHANGE_RATES.get(currency, 1.0)
        
        # 计算预估订单收入 - 与OrderDetail.tsx保持一致
        # estimatedRevenue = itemTotal + estimatedShipping - totalFees
        estimated_revenue = 0.0
        
        try:
            # 解析raw_data获取item_list
            raw_data = json.loads(raw_data_str) if raw_data_str else {}
            item_list = raw_data.get('item_list', [])
            
            # 计算商品总额(折扣后)
            item_total = sum(
                item.get('model_discounted_price', 0) * item.get('model_quantity_purchased', 0)
                for item in item_list
            )
            
            # 从escrow_data获取费用和运费信息
            escrow_data = json.loads(r[1]) if r[1] else {}
            
            # 预估运费 = estimated_shipping_fee - actual_shipping_fee
            estimated_shipping_fee = float(escrow_data.get('estimated_shipping_fee', 0))
            actual_shipping_fee = float(escrow_data.get('actual_shipping_fee', 0))
            estimated_shipping = estimated_shipping_fee - actual_shipping_fee
            
            # 总费用 = 佣金 + 服务费 + 交易手续费
            commission = float(escrow_data.get('commission_fee', 0))
            service = float(escrow_data.get('service_fee', 0))
            transaction = float(escrow_data.get('seller_transaction_fee', 0))
            total_fees = commission + service + transaction
            
            # 预估订单收入 = 商品总额 + 预估运费 - 总费用
            estimated_revenue = item_total + estimated_shipping - total_fees
            
        except Exception as e:
            # 如果计算失败,使用fallback逻辑
            print(f"Error calculating estimated revenue for order: {e}")
            if r[1]:
                try:
                    ed = json.loads(r[1])
                    if 'order_income_amount' in ed:
                        estimated_revenue = float(ed['order_income_amount'])
                    elif 'buyer_total_amount' in ed:
                        fees = float(ed.get('commission_fee', 0)) + float(ed.get('service_fee', 0)) + float(ed.get('seller_transaction_fee', 0))
                        estimated_revenue = float(ed['buyer_total_amount']) - fees
                    else:
                        estimated_revenue = amount * 0.9
                except:
                    estimated_revenue = amount * 0.9
            else:
                estimated_revenue = amount * 0.88
        
        # Convert to CNY
        sales_cny = amount * rate
        revenue_cny = estimated_revenue * rate
        
        # 利润 = 预估订单收入(CNY) - 总成本
        profit = revenue_cny - cost
        
        total_sales += sales_cny
        total_product_cost += cost
        total_profit += profit
        
        # Aggregate Daily
        if create_time:
            dt = datetime.fromtimestamp(create_time)
            date_str = dt.strftime('%Y-%m-%d')
            if date_str not in daily_stats:
                daily_stats[date_str] = {"date": date_str, "sales": 0.0, "cost": 0.0, "profit": 0.0}
            
            daily_stats[date_str]["sales"] += sales_cny
            daily_stats[date_str]["cost"] += cost
            daily_stats[date_str]["profit"] += profit

    conn.close()
    
    total_count = counts[0] if counts[0] else 0
    
    # Convert daily_stats to list
    history_list = sorted(daily_stats.values(), key=lambda x: x['date'])
    
    return {
        "orders": {
            "total": total_count,
            "to_ship": counts[1] if counts[1] else 0,
            "shipping": counts[2] if counts[2] else 0,
            "completed": counts[3] if counts[3] else 0,
            "cancelled": counts[4] if counts[4] else 0,
            "cost_entered": counts[5] if counts[5] else 0,
            "cost_not_entered": counts[6] if counts[6] else 0
        },
        "financials": {
            "sales": total_sales,
            "cost": total_product_cost,
            "profit": total_profit,
            "margin": (total_profit / total_sales * 100) if total_sales > 0 else 0
        },
        "history": history_list
    }

if __name__ == "__main__":
    print("Server starting with LATEST FINANCIAL LOGIC (Merged Escrow + Tax)...")
    # Initialize database tables
    conn = get_db_connection()
    init_db_tables(conn)
    conn.close()
    print("Database tables initialized")
    import uvicorn
    # Run on 0.0.0.0:8000
    uvicorn.run(app, host="0.0.0.0", port=8000)

