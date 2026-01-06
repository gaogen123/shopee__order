import sys
import os

# Adjust path to import modules
sys.path.append(os.path.join(os.getcwd(), 'backend', 'test', 'shop_test'))

from token_manager import get_valid_token, PARTNER_ID, PARTNER_KEY, HOST

import hmac
import hashlib
import requests
import time
import json

def generate_shop_sign(path, timestamp, access_token, shop_id):
    base_string = f"{PARTNER_ID}{path}{timestamp}{access_token}{shop_id}"
    return hmac.new(
        PARTNER_KEY.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

# Config
SHOP_ID = 494829323
ORDER_SN = "2512114B1GNREJ"

def fetch_raw_escrow():
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
    try:
        data = resp.json()
        text_dump = json.dumps(data, indent=2)
        
        # Search for known values
        print("\n--- Searching for known values ---")
        targets = ["44.73", "36.4", "2.1"] # Strings to match JSON representation
        
        for t in targets:
            if t in text_dump:
                print(f"FOUND {t} in response!")
                # Print lines around it
                lines = text_dump.split('\n')
                for i, line in enumerate(lines):
                    if t in line:
                         print(f"Line {i}: {line.strip()}")
            else:
                print(f"Value {t} NOT FOUND in response")

        # Save to file for manual inspection if needed
        with open("last_escrow_response.json", "w", encoding="utf-8") as f:
            f.write(text_dump)
            
    except Exception as e:
        print(f"Error parsing json: {e}")
        print(resp.text)

if __name__ == "__main__":
    fetch_raw_escrow()
