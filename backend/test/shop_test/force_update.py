
import requests
import time
import json
import sys
import os
import sqlite3
import hmac
import hashlib

# Config
SHOP_ID = 494829323
ORDER_SN = "2512114B1GNREJ"

# --- Token Logic ---
sys.path.append(os.path.join(os.getcwd(), 'backend', 'test', 'shop_test'))
from token_manager import get_valid_token, PARTNER_ID, PARTNER_KEY, HOST

import hmac
import hashlib

def generate_shop_sign(path, timestamp, access_token, shop_id):
    base_string = f"{PARTNER_ID}{path}{timestamp}{access_token}{shop_id}"
    return hmac.new(
        PARTNER_KEY.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def fetch_and_update():
    token = get_valid_token(SHOP_ID)
    if not token:
        print("Failed to get token")
        return

    path = "/api/v2/payment/get_escrow_detail"
    timestamp = int(time.time())
    sign = generate_shop_sign(path, timestamp, token, SHOP_ID)
    
    url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&access_token={token}&shop_id={SHOP_ID}&sign={sign}&order_sn={ORDER_SN}"
    
    print(f"Fetching raw escrow for {ORDER_SN}...")
    resp = requests.get(url)
    data = resp.json()
    
    if "error" in data and data["error"]:
        print(f"API Error: {data['message']}")
        return

    escrow_data = data.get("response", {}).get("order_income", {})
    if not escrow_data:
        print("No order_income found")
        return

    print("Got escrow data. ICMS:", escrow_data.get('icms_tax_amount'))
    
    # Save to DB
    db_paths = ['shopee_orders.db', 'backend/shopee_orders.db', 'orders.db']
    db_path = None
    for p in db_paths:
        if os.path.exists(p):
            db_path = p
            break
            
    if not db_path:
        # Fallback to creating one in root if not found (though assume it exists)
        db_path = 'shopee_orders.db'

    print(f"Updating DB at {db_path}...")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Check if order exists
    c.execute("SELECT order_sn FROM orders WHERE order_sn=?", (ORDER_SN,))
    if not c.fetchone():
        print("Order not in DB, cannot update blindly (need raw_data). Skipping insert, but if this was a real app we would insert.")
    else:
        # Update existing
        c.execute("UPDATE orders SET escrow_data=? WHERE order_sn=?", (json.dumps(escrow_data), ORDER_SN))
        conn.commit()
        print("✅ DB Updated successfully with new escrow data.")

    conn.close()

if __name__ == "__main__":
    fetch_and_update()
