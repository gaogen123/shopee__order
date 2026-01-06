import time
import hmac
import hashlib
import requests
import json

# Configuration
PARTNER_ID = 2014583
PARTNER_KEY = "shpk616b4d6468776273596f784a716941775743435174625566564f48615057"
HOST = "https://openplatform.shopee.cn"

# Obtained from previous step
ACCESS_TOKEN = "515667454670616344616d4d4572716d"
SHOP_ID = 458007719  # Using the first shop from the list

def generate_sign(path, timestamp, access_token, shop_id):
    """
    Generate signature for Shop API.
    Base string: partner_id + path + timestamp + access_token + shop_id
    """
    base_string = f"{PARTNER_ID}{path}{timestamp}{access_token}{shop_id}"
    
    return hmac.new(
        PARTNER_KEY.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def get_shop_info():
    path = "/api/v2/shop/get_shop_info"
    timestamp = int(time.time())
    sign = generate_sign(path, timestamp, ACCESS_TOKEN, SHOP_ID)
    
    url = f"{HOST}{path}"
    
    params = {
        "partner_id": PARTNER_ID,
        "timestamp": timestamp,
        "access_token": ACCESS_TOKEN,
        "shop_id": SHOP_ID,
        "sign": sign
    }
    
    print(f"Calling Get Shop Info for Shop ID: {SHOP_ID}...")
    try:
        resp = requests.get(url, params=params)
        print(f"Status Code: {resp.status_code}")
        print("Response Body:")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_shop_info()
