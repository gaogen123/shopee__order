
import time
import requests
import json

print("Waiting 5s for server restart...")
time.sleep(5)

try:
    resp = requests.get('http://localhost:8000/api/order/2601069NC34KCU')
    if resp.status_code == 200:
        data = resp.json()
        fin = data.get('financials', {})
        print(f"DEBUG: Financials keys: {list(fin.keys())}")
        print(f"DEBUG: shopee_shipping_rebate value: {fin.get('shopee_shipping_rebate')}")
    else:
        print(f"Error: {resp.status_code}")
except Exception as e:
    print(f"Exception: {e}")
