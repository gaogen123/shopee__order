
import requests
import time
import json
import sys
import os
import hmac
import hashlib

# Adjust path to import modules
sys.path.append(os.path.join(os.getcwd(), 'backend', 'test', 'shop_test'))

from token_manager import get_valid_token, PARTNER_ID, PARTNER_KEY, HOST

# Config
SHOP_ID = 494829323
ORDER_SN = "2512114B1GNREJ"

def generate_shop_sign(path, timestamp, access_token, shop_id):
    base_string = f"{PARTNER_ID}{path}{timestamp}{access_token}{shop_id}"
    return hmac.new(
        PARTNER_KEY.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def fetch_batch_escrow():
    token = get_valid_token(SHOP_ID)
    if not token:
        print("Failed to get token")
        return

    path = "/api/v2/payment/get_escrow_detail_batch"
    timestamp = int(time.time())
    sign = generate_shop_sign(path, timestamp, token, SHOP_ID)
    
    # Batch API typically assumes order_sn_list
    url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&access_token={token}&shop_id={SHOP_ID}&sign={sign}&order_sn_list={ORDER_SN},"
    
    print(f"Fetching BATCH escrow for {ORDER_SN}...")
    resp = requests.get(url)
    try:
        data = resp.json()
        print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error parsing json: {e}")
        print(resp.text)

if __name__ == "__main__":
    fetch_batch_escrow()
