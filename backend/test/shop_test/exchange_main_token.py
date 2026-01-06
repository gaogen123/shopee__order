import time
import hmac
import hashlib
import requests
import json

# Configuration
PARTNER_ID = 2014583
PARTNER_KEY = "shpk616b4d6468776273596f784a716941775743435174625566564f48615057"
HOST = "https://openplatform.shopee.cn"

def generate_sign(path, timestamp):
    base_string = f"{PARTNER_ID}{path}{timestamp}"
    return hmac.new(
        PARTNER_KEY.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def exchange_token_for_main_account(code, main_account_id):
    path = "/api/v2/auth/token/get"
    timestamp = int(time.time())
    sign = generate_sign(path, timestamp)
    
    url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&sign={sign}"
    
    payload = {
        "code": code,
        "main_account_id": int(main_account_id),
        "partner_id": PARTNER_ID
    }
    
    print(f"Exchanging token for Main Account ID: {main_account_id}")
    try:
        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
        print(f"Status Code: {resp.status_code}")
        print("Response Body:")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    CODE = "68734a567a506b50475162495975624e"
    MAIN_ACCOUNT_ID = 781654
    exchange_token_for_main_account(CODE, MAIN_ACCOUNT_ID)
