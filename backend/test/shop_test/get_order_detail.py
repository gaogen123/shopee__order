import time
import requests
import json
import hmac
import hashlib
from token_manager import get_valid_token, PARTNER_ID, PARTNER_KEY, HOST

SHOP_ID = 494829323
TARGET_ORDER_SN = "251208RD57K1WM"

def generate_shop_sign(path, timestamp, access_token, shop_id):
    base_string = f"{PARTNER_ID}{path}{timestamp}{access_token}{shop_id}"
    return hmac.new(
        PARTNER_KEY.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def get_order_detail(shop_id, order_sn):
    token = get_valid_token(shop_id)
    if not token:
        print("Failed to get token")
        return

    path = "/api/v2/order/get_order_detail"
    timestamp = int(time.time())
    
    sign = generate_shop_sign(path, timestamp, token, shop_id)
    
    url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&access_token={token}&shop_id={shop_id}&sign={sign}"
    
    # Specify fields to retrieve detailed info
    fields = [
        "order_sn", "order_status", "total_amount", "currency", 
        "create_time", "pay_time", "shipping_carrier", "payment_method",
        "estimated_shipping_fee", "message_to_seller", "buyer_user_id", "buyer_username",
        "recipient_address", "item_list", "invoice_data", "checkout_shipping_carrier"
    ]
    
    params = {
        "order_sn_list": order_sn, # Note: parameter is strictly comma-separated string for multi, or just one
        "response_optional_fields": ",".join(fields)
    }
    
    print(f"Fetching details for Order {order_sn}...")
    
    try:
        resp = requests.get(url, params=params)
        data = resp.json()
        
        if "error" in data and data["error"]:
            print(f"Error: {data['message']}")
            return

        order_list = data.get("response", {}).get("order_list", [])
        
        if order_list:
            order = order_list[0]
            print("\n=== Order Details ===")
            print(json.dumps(order, indent=2, ensure_ascii=False))
            
            # Simple Summary
            print("\n=== Summary ===")
            print(f"Order SN: {order.get('order_sn')}")
            print(f"Status: {order.get('order_status')}")
            print(f"Amount: {order.get('total_amount')} {order.get('currency')}")
            print(f"Buyer: {order.get('buyer_username')}")
            
            items = order.get("item_list", [])
            print(f"\nItems ({len(items)}):")
            for item in items:
                print(f"- {item.get('item_name')} (x{item.get('model_quantity_purchased')})")
                print(f"  Model: {item.get('model_name')}")
                print(f"  Price: {item.get('model_discounted_price')}")
        else:
            print("Order not found.")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    get_order_detail(SHOP_ID, TARGET_ORDER_SN)
