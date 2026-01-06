
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

def fetch_batch_escrow_post():
    token = get_valid_token(SHOP_ID)
    if not token:
        print("Failed to get token")
        return

    path = "/api/v2/payment/get_escrow_detail_batch"
    timestamp = int(time.time())
    sign = generate_shop_sign(path, timestamp, token, SHOP_ID)
    
    # Common parameters in URL
    url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&access_token={token}&shop_id={SHOP_ID}&sign={sign}"
    
    # Request Body
    payload = {
        "order_sn_list": [ORDER_SN]
    }
    
    print(f"Fetching BATCH escrow (POST) for {ORDER_SN}...")
    headers = {"Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json=payload)
    
    try:
        data = resp.json()
        text_dump = json.dumps(data, indent=2)
        print(text_dump)
        
        target = "44.73"
        if target in text_dump:
            print(f"\nFOUND {target} IN BATCH RESPONSE!")
        else:
            print(f"\nValue {target} NOT FOUND IN BATCH RESPONSE")
            
    except Exception as e:
        print(f"Error parsing json: {e}")
        print(resp.text)

if __name__ == "__main__":
    fetch_batch_escrow_post()
