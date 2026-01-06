import time
import requests
import json
from token_manager import get_valid_token, PARTNER_ID, HOST, generate_sign

def get_all_shops_info():
    """
    1. Get list of all authorized shops (Public API).
    2. Then for each shop, use the token to get details (Shop API).
    """
    print("Fetching shop list...")
    
    # 1. Get raw shop_id list from Public API
    ts = int(time.time())
    path = "/api/v2/public/get_shops_by_partner"
    sign = generate_sign(path, ts)
    
    url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={ts}&sign={sign}&page_size=100&page_no=1"
    
    try:
        resp = requests.get(url)
        data = resp.json()
        
        # Note: The public API returns 'authed_shop_list' which contains basic info
        shops = data.get("authed_shop_list", [])
        print(f"Found {len(shops)} shops in Public API list.")
        
        # 2. Iterate and verify token/get details
        detailed_shops = []
        
        for shop in shops:
            sid = shop.get("shop_id")
            # This ensures we have a valid token (using Main Account fallback logic)
            token = get_valid_token(sid)
            
            if token:
                # Call Shop Info API to get name
                shop_info = get_shop_detail(sid, token)
                name = shop_info.get("shop_name", "Unknown") if shop_info else "Fetch Error"
                region = shop_info.get("region", "??") if shop_info else "??"
                
                detailed_shops.append({
                    "id": sid,
                    "name": name,
                    "region": region,
                    "token": token
                })
                print(f"✅ Shop {sid}: {name} ({region}) - Token Ready")
            else:
                print(f"❌ Shop {sid}: Failed to get token")
                
        return detailed_shops
        
    except Exception as e:
        print(f"Error fetching shops: {e}")
        return []

def get_shop_detail(shop_id, access_token):
    path = "/api/v2/shop/get_shop_info"
    ts = int(time.time())
    
    # Sign must include access_token and shop_id for Shop API
    base_string = f"{PARTNER_ID}{path}{ts}{access_token}{shop_id}"
    sign = generate_sign(path, ts) # Wait, my token_manager generate_sign is generic, let's look at custom sign here
    
    # Re-implement sign specific for Shop API call here to be safe or import if robust
    # Actually, let's just use the logic directly
    import hmac, hashlib
    from token_manager import PARTNER_KEY
    
    base_string = f"{PARTNER_ID}{path}{ts}{access_token}{shop_id}"
    sign = hmac.new(
        PARTNER_KEY.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={ts}&access_token={access_token}&shop_id={shop_id}&sign={sign}"
    
    try:
        resp = requests.get(url)
        return resp.json()
    except:
        return None

if __name__ == "__main__":
    # If the public list is empty (which happens if auth is Main Account level sometimes?), 
    # we might need to rely on the list we got from the Token Exchange earlier.
    # Let's try the public API first.
    
    results = get_all_shops_info()
    
    # If Public API is empty, let's fallback to the known list from the token exchange response
    if not results:
        print("\n[Info] Public API returned no shops (common for Main Account auth).")
        print("Using cached ID list from Main Account authorization...")
        
        # Hardcoded list from your previous step (Step 48 output)
        KNOWN_IDS = [
            458007719, 474273630, 485292426, 494829323, 494831140, 
            521218078, 572732988, 572736528, 627503410, 627504971, 
            627506657, 1162304902, 1162319753, 1478672550, 1162289492, 
            1183087722, 1013039580, 1013056192, 1013054776
        ]
        
        for sid in KNOWN_IDS:
            token = get_valid_token(sid)
            if token:
                shop_info = get_shop_detail(sid, token)
                # Parse
                if shop_info and "shop_name" in shop_info:
                    name = shop_info["shop_name"]
                    region = shop_info["region"]
                    print(f"✅ Shop {sid}: {name} ({region})")
                else:
                    err = shop_info.get("message", "Unknown Error") if shop_info else "Request Failed"
                    print(f"⚠️ Shop {sid}: Info Fetch Failed ({err})")
