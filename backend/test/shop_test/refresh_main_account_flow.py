import time
import hmac
import hashlib
import requests
import json
import os

# Configuration
PARTNER_ID = 2014583
PARTNER_KEY = "shpk616b4d6468776273596f784a716941775743435174625566564f48615057"
HOST = "https://openplatform.shopee.cn"

# File to store the latest tokens
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(BASE_DIR, "shopee_tokens.json")

def generate_sign(path, timestamp):
    base_string = f"{PARTNER_ID}{path}{timestamp}"
    return hmac.new(
        PARTNER_KEY.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def save_tokens(key_id, access_token, refresh_token):
    """Save tokens to local file. key_id can be shop_id or main_account_id"""
    data = {}
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'r') as f:
                data = json.load(f)
        except:
            pass
    
    data[str(key_id)] = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "updated_at": int(time.time())
    }
    
    with open(TOKEN_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"✅ Tokens saved for {key_id}")

def get_initial_tokens(code, main_account_id):
    """Step 1 & 2: Get initial tokens using code"""
    path = "/api/v2/auth/token/get"
    timestamp = int(time.time())
    sign = generate_sign(path, timestamp)
    
    url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&sign={sign}"
    
    payload = {
        "code": code,
        "main_account_id": int(main_account_id),
        "partner_id": PARTNER_ID
    }
    
    print(f"🚀 Step 1: Exchanging code for initial tokens (Main Account: {main_account_id})...")
    try:
        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
        result = resp.json()
        
        if "error" in result and result["error"]:
            print(f"❌ Error: {result['message']}")
            return None
            
        print("✅ Initial tokens received!")
        # print(json.dumps(result, indent=2))
        return result
    except Exception as e:
        print(f"❌ Network Error: {e}")
        return None

def refresh_token_for_entity(entity_id, refresh_token, is_merchant=False):
    """Step 3: Refresh token for specific shop_id or merchant_id"""
    path = "/api/v2/auth/access_token/get"
    timestamp = int(time.time())
    sign = generate_sign(path, timestamp)
    
    url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&sign={sign}"
    
    payload = {
        "refresh_token": refresh_token,
        "partner_id": PARTNER_ID
    }
    
    if is_merchant:
        payload["merchant_id"] = int(entity_id)
        entity_type = "Merchant"
    else:
        payload["shop_id"] = int(entity_id)
        entity_type = "Shop"
        
    print(f"🔄 Step 3: Refreshing token for {entity_type} ID: {entity_id}...")
    
    try:
        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
        result = resp.json()
        
        if "error" in result and result["error"]:
            print(f"  ❌ Error refreshing: {result['message']}")
            return None
            
        print(f"  ✅ Refresh successful for {entity_type} {entity_id}")
        return result
    except Exception as e:
        print(f"  ❌ Network Error: {e}")
        return None

def main_account_auth_flow(code, main_account_id):
    # 1. 获取初始 Token (包含主账号下所有店铺列表)
    initial_data = get_initial_tokens(code, main_account_id)
    if not initial_data:
        return
    
    # 2. 保存初始的主账号 Token (虽然这个 Token 实际上是用来刷新子 Token 的)
    # 注意：API 返回的结构里，access_token 和 refresh_token 是针对 Main Account 的
    initial_refresh_token = initial_data.get("refresh_token")
    
    # 3. 遍历 merchant_id_list 和 shop_id_list，分别刷新并保存 Token
    merchant_list = initial_data.get("merchant_id_list", [])
    shop_list = initial_data.get("shop_id_list", [])
    
    print(f"\n📋 Found {len(merchant_list)} merchants and {len(shop_list)} shops.")
    
    # 3.1 刷新 Merchant Token
    for mid in merchant_list:
        new_tokens = refresh_token_for_entity(mid, initial_refresh_token, is_merchant=True)
        if new_tokens:
            save_tokens(mid, new_tokens["access_token"], new_tokens["refresh_token"])
            
    # 3.2 刷新 Shop Token
    for sid in shop_list:
        new_tokens = refresh_token_for_entity(sid, initial_refresh_token, is_merchant=False)
        if new_tokens:
            save_tokens(sid, new_tokens["access_token"], new_tokens["refresh_token"])

if __name__ == "__main__":
    # 请填入最新的 Code
    CODE = "6e6969616151626958474a4c56615263" 
    MAIN_ACCOUNT_ID = 781654
    
    main_account_auth_flow(CODE, MAIN_ACCOUNT_ID)
