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
import time
import hmac
import hashlib
from token_manager import get_valid_token, PARTNER_ID, PARTNER_KEY, HOST, ALL_SHOPS

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
    # Check if escrow_data column exists, if not add it (simple migration)
    try:
        c.execute("SELECT escrow_data FROM orders LIMIT 1")
    except sqlite3.OperationalError:
        try:
            c.execute("ALTER TABLE orders ADD COLUMN escrow_data TEXT")
        except:
            pass # Table might not exist yet, create below

    # Check if estimated_shipping_fee column exists
    try:
        c.execute("SELECT estimated_shipping_fee FROM orders LIMIT 1")
    except sqlite3.OperationalError:
        try:
            c.execute("ALTER TABLE orders ADD COLUMN estimated_shipping_fee REAL")
        except:
            pass

 

    # Check if purchase_cost column exists
    try:
        c.execute("SELECT purchase_cost FROM orders LIMIT 1")
    except sqlite3.OperationalError:
        try:
            c.execute("ALTER TABLE orders ADD COLUMN purchase_cost REAL DEFAULT 0")
        except:
            pass

    # Check if domestic_shipping_cost column exists
    try:
        c.execute("SELECT domestic_shipping_cost FROM orders LIMIT 1")
    except sqlite3.OperationalError:
        try:
            c.execute("ALTER TABLE orders ADD COLUMN domestic_shipping_cost REAL DEFAULT 0")
        except:
            pass

    # Check if total_cost column exists
    try:
        c.execute("SELECT total_cost FROM orders LIMIT 1")
    except sqlite3.OperationalError:
        try:
            c.execute("ALTER TABLE orders ADD COLUMN total_cost REAL DEFAULT 0")
        except:
            pass

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
            model_name TEXT,
            model_quantity_purchased INTEGER,
            model_discounted_price REAL,
            image_info TEXT,
            purchase_cost REAL DEFAULT 0,
            domestic_shipping_cost REAL DEFAULT 0,
            FOREIGN KEY(order_sn) REFERENCES orders(order_sn)
        )
    ''')
    
    # Check if purchase_cost column exists in order_items table
    try:
        c.execute("SELECT purchase_cost FROM order_items LIMIT 1")
    except sqlite3.OperationalError:
        try:
            c.execute("ALTER TABLE order_items ADD COLUMN purchase_cost REAL DEFAULT 0")
        except:
            pass
    
    # Check if domestic_shipping_cost column exists in order_items table
    try:
        c.execute("SELECT domestic_shipping_cost FROM order_items LIMIT 1")
    except sqlite3.OperationalError:
        try:
            c.execute("ALTER TABLE order_items ADD COLUMN domestic_shipping_cost REAL DEFAULT 0")
        except:
            pass
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS order_item_costs (
            order_sn TEXT,
            item_id INTEGER,
            model_id INTEGER DEFAULT 0,
            sourcing_price REAL,
            PRIMARY KEY (order_sn, item_id, model_id)
        )
    ''')
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
    
    # Save Items
    c.execute('DELETE FROM order_items WHERE order_sn = ?', (order.get('order_sn'),))
    for item in order.get('item_list', []):
        c.execute('''
            INSERT INTO order_items (
                order_sn, item_id, item_name, model_name, 
                model_quantity_purchased, model_discounted_price, image_info
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            order.get('order_sn'),
            item.get('item_id'),
            item.get('item_name'),
            item.get('model_name'),
            item.get('model_quantity_purchased'),
            item.get('model_discounted_price'),
            json.dumps(item.get('image_info', {}))
        ))
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
        resp = requests.get(url, params=params)
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
        resp = requests.get(url)
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

    # Merge Item Costs
    cursor.execute("SELECT item_id, model_id, sourcing_price FROM order_item_costs WHERE order_sn = ?", (order_sn,))
    cost_rows = cursor.fetchall()
    cost_map = {}
    for cr in cost_rows:
        mid = cr['model_id'] if cr['model_id'] else 0
        key = f"{cr['item_id']}_{mid}"
        cost_map[key] = cr['sourcing_price']

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
        # Update order_item_costs table (legacy)
        c.execute("""
            INSERT INTO order_item_costs (order_sn, item_id, model_id, sourcing_price)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(order_sn, item_id, model_id) DO UPDATE SET sourcing_price=excluded.sourcing_price
        """, (order_sn, u.item_id, u.model_id, u.sourcing_price))
        
        # Update order_items table with purchase_cost and domestic_shipping_cost
        c.execute("""
            UPDATE order_items 
            SET purchase_cost = ?, domestic_shipping_cost = ?
            WHERE order_sn = ? AND item_id = ?
        """, (u.purchase_cost, u.domestic_shipping_cost, order_sn, u.item_id))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.get("/api/orders")
def get_orders(
    status: str = Query(None),
    keyword: str = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    conn = get_db_connection()
    c = conn.cursor()
    
    where_clauses = []
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
        
    where_str = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    # Count
    c.execute(f"SELECT count(*) FROM orders WHERE {where_str}", params)
    total = c.fetchone()[0]
    
    # Fetch orders
    query = f"SELECT raw_data, order_sn, order_status, total_amount, currency, create_time, buyer_username, shop_id, estimated_shipping_fee, total_cost FROM orders WHERE {where_str} ORDER BY create_time DESC LIMIT ? OFFSET ?"
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
        
        # Fetch order items with costs
        c.execute("""
            SELECT item_id, item_name, model_name, model_quantity_purchased, 
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
                'model_name': item_row['model_name'],
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
                resp = requests.get(url, params=params)
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
        
        current_from += MAX_RANGE + 1 # Advance to next segment

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

if __name__ == "__main__":
    print("🚀 Server starting with LATEST FINANCIAL LOGIC (Merged Escrow + Tax)...")
    # Initialize database tables
    conn = get_db_connection()
    init_db_tables(conn)
    conn.close()
    print("✅ Database tables initialized")
    import uvicorn
    # Run on 0.0.0.0:8000
    uvicorn.run(app, host="0.0.0.0", port=8000)

