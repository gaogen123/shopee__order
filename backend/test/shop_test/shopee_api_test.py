import time
import hmac
import hashlib
import requests
import json

# Configuration
PARTNER_ID = 2014583
PARTNER_KEY = "shpk616b4d6468776273596f784a716941775743435174625566564f48615057"
HOST = "https://openplatform.shopee.cn"  # Using CN production host

def generate_sign(path, timestamp, access_token=None, shop_id=None, merchant_id=None):
    # Base string construction: partner_id + api_path + timestamp + access_token + shop_id/merchant_id
    base_string = f"{PARTNER_ID}{path}{timestamp}"
    
    if access_token:
        base_string += access_token
    
    if shop_id:
        base_string += str(shop_id)
    elif merchant_id:
        base_string += str(merchant_id)
        
    print(f"Base String for Sign: {base_string}")
        
    # Calculate HMAC-SHA256 signature
    sign = hmac.new(
        PARTNER_KEY.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return sign

def call_public_api(path, params={}):
    timestamp = int(time.time())
    
    # Generate signature
    sign = generate_sign(path, timestamp)
    
    # Prepare URL parameters
    query_params = {
        "partner_id": PARTNER_ID,
        "timestamp": timestamp,
        "sign": sign
    }
    query_params.update(params)
    
    url = f"{HOST}{path}"
    
    print(f"Calling URL: {url}")
    print(f"Params: {query_params}")
    
    try:
        response = requests.get(url, params=query_params)
        print(f"Response Status Code: {response.status_code}")
        try:
            print("Response JSON:")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        except:
            print("Response Text:")
            print(response.text)
    except Exception as e:
        print(f"Error calling API: {e}")

if __name__ == "__main__":
    # Test with Public API: Get Shops By Partner
    # Endpoint: /api/v2/public/get_shops_by_partner
    # This endpoint allows us to verify the Partner ID and Key are valid
    
    api_path = "/api/v2/public/get_shops_by_partner"
    
    # Pagination parameters
    params = {
        "page_size": 10,
        "page_no": 1
    }
    
    call_public_api(api_path, params)
