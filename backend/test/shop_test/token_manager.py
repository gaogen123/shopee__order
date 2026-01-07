import time
import hmac
import hashlib
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import os

# 配置requests重试策略
def create_session_with_retries():
    """创建带有重试机制的requests session"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

# 创建全局session
api_session = create_session_with_retries()

# Configuration
PARTNER_ID = 2014583
PARTNER_KEY = "shpk616b4d6468776273596f784a716941775743435174625566564f48615057"
HOST = "https://openplatform.shopee.cn"

# File to store the latest tokens
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

# Main Account Configuration
# If using Main Account, set this ID. All shops will share this token.
MAIN_ACCOUNT_ID = 781654 


# Shop List Configuration
ALL_SHOPS = [
    {"id": 458007719, "name": "💕LOVE💕Storage", "region": "MY"},
    {"id": 474273630, "name": "七彩精致生活館", "region": "TW"},
    {"id": 485292426, "name": "儿童快乐成长梦工厂", "region": "TW"},
    {"id": 494829323, "name": "Saco multifuncional da mãe", "region": "BR"},
    {"id": 494831140, "name": "gaogen.mx", "region": "MX"},
    {"id": 521218078, "name": "音随律动专店", "region": "PH"},
    {"id": 572732988, "name": "gaogen.cl", "region": "CL"},
    {"id": 572736528, "name": "gaogen.co", "region": "CO"},
    {"id": 627503410, "name": "Haitao Market", "region": "VN"},
    {"id": 627504971, "name": "บิกีนี่", "region": "TH"},
    {"id": 627506657, "name": "gaogen.sg", "region": "SG"},
    {"id": 1162304902, "name": "gaogenmv.co", "region": "CO"},
    {"id": 1162319753, "name": "gaogende.cl", "region": "CL"},
    {"id": 1478672550, "name": "zhangning.br", "region": "BR"}
]

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
    # print(f"Tokens saved for ID {key_id}") # Reduce noise

def load_tokens(key_id):
    """Load tokens from local file"""
    if not os.path.exists(TOKEN_FILE):
        return None
        
    try:
        with open(TOKEN_FILE, 'r') as f:
            data = json.load(f)
            return data.get(str(key_id))
    except Exception as e:
        print(f"Error loading tokens: {e}")
        return None

def refresh_access_token(id_val, current_refresh_token, is_main_account=False):
    """
    Refresh the access token.
    If is_main_account is True, pass main_account_id, else shop_id.
    """
    path = "/api/v2/auth/access_token/get"
    timestamp = int(time.time())
    sign = generate_sign(path, timestamp)
    
    url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&sign={sign}"
    
    payload = {
        "refresh_token": current_refresh_token,
        "partner_id": PARTNER_ID
    }
    
    if is_main_account:
        payload["merchant_id"] = int(id_val)
        print(f"Refreshing token for Merchant/Main Account {id_val}...")
    else:
        payload["shop_id"] = int(id_val)
        print(f"Refreshing token for Shop {id_val}...")
        
    try:
        # 使用带重试机制的session，并设置30秒超时
        resp = api_session.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
        result = resp.json()
        
        if "error" in result and result["error"]:
            print(f"Error refreshing token: {result['message']}")
            return None
            
        print("Refresh successful!")
        return result
    except Exception as e:
        print(f"Network error refreshing token: {e}")
        return None

def get_valid_token(shop_id=None):
    """
    Get a valid token.
    Priority:
    1. Check specific Shop ID token.
    2. Check Main Account ID token (if configured).
    """
    # 1. Try specific shop token
    token_data = load_tokens(shop_id)
    target_id = shop_id
    is_main = False
    
    # 2. Fallback to Main Account
    if not token_data and MAIN_ACCOUNT_ID:
        token_data = load_tokens(MAIN_ACCOUNT_ID)
        target_id = MAIN_ACCOUNT_ID
        is_main = True
        # if token_data:
        #    print(f"Using Shared Main Account Token (ID: {MAIN_ACCOUNT_ID}) for Shop {shop_id}")
    
    if not token_data:
        print(f"No tokens found for Shop {shop_id} or Main Account {MAIN_ACCOUNT_ID}.")
        return None
        
    updated_at = token_data.get("updated_at", 0)
    current_time = int(time.time())
    
    # Check expiry (refresh if older than 3.5h)
    if current_time - updated_at > 12600: 
        print(f"Token for ID {target_id} is expiring. Refreshing...")
        new_tokens = refresh_access_token(target_id, token_data["refresh_token"], is_main_account=is_main)
        
        if new_tokens:
            save_tokens(
                target_id, 
                new_tokens["access_token"], 
                new_tokens["refresh_token"]
            )
            return new_tokens["access_token"]
        else:
            print("CRITICAL: Failed to refresh token.")
            return None
    else:
        # print(f"Token for ID {target_id} is valid.")
        return token_data["access_token"]

if __name__ == "__main__":
    # Setup Main Account Token
    INITIAL_REFRESH_TOKEN = "62444a6755556c5a6c7279516e53637a" 
    INITIAL_ACCESS_TOKEN = "515667454670616344616d4d4572716d"
    
    # Seed the Main Account Token
    current_tokens = load_tokens(MAIN_ACCOUNT_ID)
    if not current_tokens:
        print(f"Seeding Main Account tokens for ID {MAIN_ACCOUNT_ID}...")
        save_tokens(MAIN_ACCOUNT_ID, INITIAL_ACCESS_TOKEN, INITIAL_REFRESH_TOKEN)

    print(f"Verifying tokens for all {len(ALL_SHOPS)} shops...")
    print("-" * 120)
    print(f"{'Shop Name':<30} | {'Shop ID':<12} | {'Region':<6} | {'Status':<10} | {'Access Token'}")
    print("-" * 120)
    
    for shop in ALL_SHOPS:
        sid = shop['id']
        name = shop['name']
        region = shop['region']
        
        token = get_valid_token(sid)
        status = "✅ Ready" if token else "❌ Failed"
        token_str = token if token else "N/A"
        print(f"{name:<30} | {sid:<12} | {region:<6} | {status:<10} | {token_str}")

