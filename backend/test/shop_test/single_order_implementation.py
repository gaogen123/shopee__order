
import sqlite3
import time
import requests
import json
import hmac
import hashlib
from token_manager import get_valid_token, PARTNER_ID, PARTNER_KEY, HOST

# Configuration
SHOP_ID = 494829323
TARGET_ORDER_SN = "2601069NC34KCU"  # Picked from recent list
DB_FILE = "shopee_orders.db"

def init_db():
    print(f"Initializing/Connecting to SQLite DB: {DB_FILE}...")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Reset Tables for Demo
    c.execute('DROP TABLE IF EXISTS orders')
    c.execute('DROP TABLE IF EXISTS order_items')

    # Orders Table
    c.execute('''
        CREATE TABLE orders (
            order_sn TEXT PRIMARY KEY,
            shop_id INTEGER,
            order_status TEXT,
            total_amount REAL,
            currency TEXT,
            create_time INTEGER,
            pay_time INTEGER,
            shipping_carrier TEXT,
            payment_method TEXT,
            buyer_username TEXT,
            recipient_address TEXT,
            raw_data TEXT,
            updated_at INTEGER
        )
    ''')
    
    # Order Items Table
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
            FOREIGN KEY(order_sn) REFERENCES orders(order_sn)
        )
    ''')
    
    conn.commit()
    return conn

def generate_shop_sign(path, timestamp, access_token, shop_id):
    base_string = f"{PARTNER_ID}{path}{timestamp}{access_token}{shop_id}"
    return hmac.new(
        PARTNER_KEY.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def fetch_order_from_api(shop_id, order_sn):
    print(f"Fetching Order {order_sn} from Shopee API...")
    token = get_valid_token(shop_id)
    if not token:
        print("Error: Could not get valid token.")
        return None

    path = "/api/v2/order/get_order_detail"
    timestamp = int(time.time())
    sign = generate_shop_sign(path, timestamp, token, shop_id)
    
    url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&access_token={token}&shop_id={shop_id}&sign={sign}"
    
    fields = [
        "order_sn", "order_status", "total_amount", "currency", 
        "create_time", "pay_time", "shipping_carrier", "payment_method",
        "buyer_username", "recipient_address", "item_list", "note"
    ]
    
    params = {
        "order_sn_list": order_sn,
        "response_optional_fields": ",".join(fields)
    }
    
    try:
        resp = requests.get(url, params=params)
        data = resp.json()
        
        if "error" in data and data["error"]:
            print(f"API Error: {data['message']}")
            return None
            
        order_list = data.get("response", {}).get("order_list", [])
        if not order_list:
            print("Order not found in API response.")
            return None
            
        return order_list[0]
    except Exception as e:
        print(f"Network Exception: {e}")
        return None

def save_order_to_db(conn, shop_id, order):
    print(f"Saving Order {order.get('order_sn')} to Database...")
    c = conn.cursor()
    
    # Save Main Order Info
    c.execute('''
        INSERT OR REPLACE INTO orders (
            order_sn, shop_id, order_status, total_amount, currency, 
            create_time, pay_time, shipping_carrier, payment_method, 
            buyer_username, recipient_address, raw_data, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        order.get('order_sn'),
        shop_id,
        order.get('order_status'),
        order.get('total_amount'),
        order.get('currency'),
        order.get('create_time'),
        order.get('pay_time'),
        order.get('shipping_carrier'),
        order.get('payment_method'),
        order.get('buyer_username'),
        json.dumps(order.get('recipient_address', {})),
        json.dumps(order),
        int(time.time())
    ))
    
    # Save Items
    # First clear existing items for this order to prevent duplication on re-run
    c.execute('DELETE FROM order_items WHERE order_sn = ?', (order.get('order_sn'),))
    
    items = order.get('item_list', [])
    print(f"Saving {len(items)} items...")
    
    for item in items:
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
    print("✅ Order saved successfully.")

def verify_db_data(conn, order_sn):
    print("\n--- Verifying Data from Database ---")
    c = conn.cursor()
    
    # Query Order
    c.execute("SELECT order_sn, status, total_amount, buyer FROM (SELECT order_sn, order_status as status, total_amount, buyer_username as buyer FROM orders WHERE order_sn = ?)", (order_sn,))
    row = c.fetchone()
    if row:
        print(f"Order Found in DB: {row}")
    else:
        print("❌ Order NOT found in DB.")
        
    # Query Items
    c.execute("SELECT item_name, model_name, model_quantity_purchased, model_discounted_price FROM order_items WHERE order_sn = ?", (order_sn,))
    items = c.fetchall()
    print(f"Items in DB ({len(items)}):")
    for item in items:
        print(f" - {item[0]} | {item[1]} | x{item[2]} | ${item[3]}")

if __name__ == "__main__":
    # 1. Init DB
    conn = init_db()
    
    # 2. Fetch from API
    order_data = fetch_order_from_api(SHOP_ID, TARGET_ORDER_SN)
    
    if order_data:
        # 3. Save to DB
        save_order_to_db(conn, SHOP_ID, order_data)
        
        # 4. Verify
        verify_db_data(conn, TARGET_ORDER_SN)
    
    conn.close()
