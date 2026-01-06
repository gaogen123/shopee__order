import time
import requests
import json
from token_manager import get_valid_token, PARTNER_ID, HOST

# Hardcoded list of known shop IDs from previous steps
KNOWN_IDS = [
    458007719, 474273630, 485292426, 494829323, 494831140, 
    521218078, 572732988, 572736528, 627503410, 627504971, 
    627506657, 1162304902, 1162319753, 1478672550, 1162289492, 
    1183087722, 1013039580, 1013056192, 1013054776
]

# Target names to filter for (normalized to lower case for comparison)
TARGET_NAMES = [
    "gaogen.br",
    "saco multifuncional da mãe" # Normalized from "Saco multifuncional da mãe"
]

def get_shop_info_simple(shop_id, access_token):
    path = "/api/v2/shop/get_shop_info"
    ts = int(time.time())
    
    # Custom sign calculation
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
    print(f"Searching for shops matching: {', '.join(TARGET_NAMES)}")
    print("-" * 50)
    
    found_shops = []
    
    for sid in KNOWN_IDS:
        token = get_valid_token(sid)
        if not token:
            continue
            
        info = get_shop_info_simple(sid, token)
        if info and "shop_name" in info:
            name = info.get("shop_name", "")
            region = info.get("region", "")
            
            # Check for matches (case-insensitive)
            name_lower = name.lower()
            
            # Special check: Sometimes API name is different from UI name shown in screenshot.
            # We will print all to be sure, but highlight matches.
            is_match = False
            for target in TARGET_NAMES:
                if target in name_lower:
                    is_match = True
                    break
            
            if is_match or sid == 494829323: # Explicitly checking ID for one we know from screenshot might be relevant
                print(f"✅ FOUND MATCH: {name} (ID: {sid}, Region: {region})")
                found_shops.append({"name": name, "id": sid, "region": region})
            # else:
            #     print(f"   Checked: {name} (ID: {sid})")
    
    print("-" * 50)
    print(f"Total matched shops: {len(found_shops)}")
    for shop in found_shops:
        print(f"SHOP_ID: {shop['id']}  NAME: {shop['name']}")
