
import sqlite3
import time
import requests
import hmac
import hashlib
import json
from token_manager import get_valid_token, ALL_SHOPS, PARTNER_ID, PARTNER_KEY, HOST

DB_FILE = "shopee_orders.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Orders Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
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
    conn.close()

def generate_shop_sign(path, timestamp, access_token, shop_id):
    base_string = f"{PARTNER_ID}{path}{timestamp}{access_token}{shop_id}"
    return hmac.new(
        PARTNER_KEY.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def save_order(conn, shop_id, order):
    c = conn.cursor()
    
    # Upsert Order
    c.execute('''
        INSERT OR REPLACE INTO orders (
            order_sn, shop_id, order_status, total_amount, currency, 
            create_time, pay_time, shipping_carrier, payment_method, buyer_username, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        int(time.time())
    ))
    
    # Insert Items (Delete existing for this order first to avoid duplicates/complex updates)
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
    print(f"Saved Order: {order.get('order_sn')}")

def fetch_order_detail(shop_id, access_token, order_sn_list):
    path = "/api/v2/order/get_order_detail"
    timestamp = int(time.time())
    sign = generate_shop_sign(path, timestamp, access_token, shop_id)
    
    url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&access_token={access_token}&shop_id={shop_id}&sign={sign}"
    
    fields = [
        "order_sn", "order_status", "total_amount", "currency", 
        "create_time", "pay_time", "shipping_carrier", "payment_method",
        "estimated_shipping_fee", "message_to_seller", "buyer_user_id", "buyer_username",
        "recipient_address", "item_list", "invoice_data", "checkout_shipping_carrier"
    ]
    
    # Chunking if too many, but list logic below handles chunking
    params = {
        "order_sn_list": ",".join(order_sn_list),
        "response_optional_fields": ",".join(fields)
    }
    
    try:
        resp = requests.get(url, params=params)
        data = resp.json()
        if "error" in data and data["error"]:
            print(f"Error fetching details: {data['message']}")
            return []
        return data.get("response", {}).get("order_list", [])
    except Exception as e:
        print(f"Detail fetch exception: {e}")
        return []

def process_shop(shop):
    shop_id = shop['id']
    shop_name = shop['name']
    
    print(f"\nProcessing Shop: {shop_name} ({shop_id})")
    token = get_valid_token(shop_id)
    
    if not token:
        print(f"Skipping {shop_name}: No valid token.")
        return

    # 1. Get Order List (Last 15 days)
    path = "/api/v2/order/get_order_list"
    timestamp = int(time.time())
    start_time = timestamp - (15 * 24 * 60 * 60)
    
    sign = generate_shop_sign(path, timestamp, token, shop_id)
    url = f"{HOST}{path}"
    
    params = {
        "partner_id": PARTNER_ID,
        "timestamp": timestamp,
        "access_token": token,
        "shop_id": shop_id,
        "sign": sign,
        "time_range_field": "create_time",
        "time_from": start_time,
        "time_to": timestamp,
        "page_size": 100 # Adjust if needed
    }
    
    all_order_sns = []
    cursor = ""
    
    while True:
        if cursor:
            params["cursor"] = cursor
            
        try:
            resp = requests.get(url, params=params)
            data = resp.json()
            
            if "error" in data and data["error"]:
                print(f"Error fetching list: {data['message']}")
                break
                
            orders = data.get("response", {}).get("order_list", [])
            for o in orders:
                all_order_sns.append(o['order_sn'])
                
            if data.get("response", {}).get("more"):
                cursor = data.get("response", {}).get("next_cursor")
            else:
                break
        except Exception as e:
            print(f"List fetch exception: {e}")
            break
            
    print(f"Found {len(all_order_sns)} orders.")
    
    if not all_order_sns:
        return

    # 2. Get Details in chunks of 50
    conn = sqlite3.connect(DB_FILE)
    
    chunk_size = 50
    for i in range(0, len(all_order_sns), chunk_size):
        chunk = all_order_sns[i:i + chunk_size]
        details = fetch_order_detail(shop_id, token, chunk)
        
        for order in details:
            save_order(conn, shop_id, order)
            
    conn.close()

if __name__ == "__main__":
    init_db()
    for shop in ALL_SHOPS:
        process_shop(shop)
