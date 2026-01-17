
import time
import requests
import json
import hmac
import hashlib
from token_manager import get_valid_token, PARTNER_ID, PARTNER_KEY, HOST

SHOP_ID = 494829323
ORDER_SN = "2511062BHP007M"

def generate_shop_sign(path, timestamp, access_token, shop_id):
    base_string = f"{PARTNER_ID}{path}{timestamp}{access_token}{shop_id}"
    return hmac.new(
        PARTNER_KEY.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def get_escrow_detail(shop_id, order_sn):
    token = get_valid_token(shop_id)
    if not token:
        print("Failed to get token")
        return

    path = "/api/v2/payment/get_escrow_detail"
    timestamp = int(time.time())
    
    sign = generate_shop_sign(path, timestamp, token, shop_id)
    
    url = f"{HOST}{path}"
    
    params = {
        "partner_id": PARTNER_ID,
        "timestamp": timestamp,
        "access_token": token,
        "shop_id": shop_id,
        "sign": sign,
        "order_sn": order_sn
    }
    
    print(f"Fetching Escrow Detail for Order {order_sn}...")
    
    try:
        resp = requests.get(url, params=params)
        data = resp.json()
        
        print("\n=== Escrow Detail Response ===")
        print(json.dumps(data, indent=2, ensure_ascii=False))
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    get_escrow_detail(SHOP_ID, ORDER_SN)
