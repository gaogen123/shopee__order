import time
import hmac
import hashlib
import requests
import json

# Configuration
PARTNER_ID = 2014583
PARTNER_KEY = "shpk616b4d6468776273596f784a716941775743435174625566564f48615057"
HOST = "https://openplatform.shopee.cn"

def generate_sign(path, timestamp, access_token=None, shop_id=None, merchant_id=None):
    """
    Generate the HMAC-SHA256 signature.
    Base string: partner_id + path + timestamp + [access_token] + [shop_id/merchant_id]
    """
    base_string = f"{PARTNER_ID}{path}{timestamp}"
    
    if access_token:
        base_string += access_token
    
    if shop_id:
        base_string += str(shop_id)
    elif merchant_id:
        base_string += str(merchant_id)
        
    sign = hmac.new(
        PARTNER_KEY.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return sign

def generate_auth_url(redirect_url="http://localhost/"):
    """
    Generate the URL for shop authorization.
    """
    path = "/api/v2/shop/auth_partner"
    timestamp = int(time.time())
    sign = generate_sign(path, timestamp)
    
    url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&sign={sign}&redirect={redirect_url}"
    return url

def get_access_token(code, shop_id):
    """
    Exchange authorization code for access_token.
    """
    path = "/api/v2/auth/token/get"
    timestamp = int(time.time())
    sign = generate_sign(path, timestamp) # Base string only uses partner_id + path + timestamp for this call
    
    url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&sign={sign}"
    
    payload = {
        "code": code,
        "shop_id": int(shop_id),
        "partner_id": PARTNER_ID
    }
    
    headers = {"Content-Type": "application/json"}
    
    print(f"Requesting Access Token from: {url}")
    try:
        resp = requests.post(url, json=payload, headers=headers)
        print(f"Status: {resp.status_code}")
        print(resp.json())
        return resp.json()
    except Exception as e:
        print(f"Error: {e}")

def call_shop_api(path, access_token, shop_id, params={}):
    """
    Generic function to call a Shop API (e.g. GetProductList).
    """
    timestamp = int(time.time())
    sign = generate_sign(path, timestamp, access_token, shop_id)
    
    url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&access_token={access_token}&shop_id={shop_id}&sign={sign}"
    
    headers = {"Content-Type": "application/json"}
    
    print(f"Calling Shop API: {url}")
    # Note: GET or POST depends on API.
    # Assuming GET for list, POST for updates. simpler to pass params in query for GET.
    # If POST, mix query params (auth) and body (data).
    
    resp = requests.get(url, params=params, headers=headers)
    print(resp.json())

def test_connectivity():
    """
    Test connection using Public API: GetAuthShopList
    /api/v2/public/get_shops_by_partner
    """
    path = "/api/v2/public/get_shops_by_partner"
    timestamp = int(time.time())
    sign = generate_sign(path, timestamp)
    
    url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&sign={sign}&page_size=10&page_no=1"
    
    print(f"Testing Connectivity to: {url}")
    resp = requests.get(url)
    print(f"Connectivity Result ({resp.status_code}):")
    print(json.dumps(resp.json(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    print("=== Shopee API Client Demo ===\n")
    
    # 1. Test Authorization/Connectivity
    print("Step 1: Testing Connectivity (Public API)...")
    test_connectivity()
    
    # 2. Generate Auth URL
    print("\nStep 2: Generate Authorization URL")
    print("Send this URL to the seller to authorize your app:")
    print(generate_auth_url())
    
    print("\n=== End Demo ===")
