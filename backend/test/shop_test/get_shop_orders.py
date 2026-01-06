import time
import requests
import json
import hmac
import hashlib
from token_manager import get_valid_token, PARTNER_ID, PARTNER_KEY, HOST

SHOP_ID = 494829323

def generate_shop_sign(path, timestamp, access_token, shop_id):
    base_string = f"{PARTNER_ID}{path}{timestamp}{access_token}{shop_id}"
    return hmac.new(
        PARTNER_KEY.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def get_orders(shop_id):
    token = get_valid_token(shop_id)
    if not token:
        print("Failed to get token")
        return

    path = "/api/v2/order/get_order_list"
    timestamp = int(time.time())
    
    # Time range: Last 15 days (Shopee limit is usually 15 days per request)
    end_time = timestamp
    start_time = end_time - (15 * 24 * 60 * 60)
    
    sign = generate_shop_sign(path, timestamp, token, shop_id)
    
    url = f"{HOST}{path}"
    
    params = {
        "partner_id": PARTNER_ID,
        "timestamp": timestamp,
        "access_token": token,
        "shop_id": shop_id,
        "sign": sign,
        "time_range_field": "create_time",
        "time_from": start_time,
        "time_to": end_time,
        "page_size": 20
    }
    
    print(f"Fetching orders for Shop {shop_id}...")
    print(f"Time Range: {time.ctime(start_time)} to {time.ctime(end_time)}")
    
    try:
        resp = requests.get(url, params=params)
        data = resp.json()
        
        if "error" in data and data["error"]:
            print(f"Error fetching orders: {data['message']}")
            print(json.dumps(data, indent=2))
            return

        order_list = data.get("response", {}).get("order_list", [])
        total_count = len(order_list) # Note: 'more' field indicates if there are more
        more = data.get("response", {}).get("more", False)
        
        print(f"\nFound {total_count} orders (First page):")
        print("-" * 50)
        
        if not order_list:
            print("No orders found in this time range.")
        
        for order in order_list:
            order_sn = order.get("order_sn")
            order_status = order.get("order_status")
            print(f"Order SN: {order_sn} | Status: {order_status}")
            
        if more:
            print(f"\n... There are more orders. Pagination is required to see all.")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    get_orders(SHOP_ID)
