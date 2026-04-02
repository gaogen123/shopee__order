
import requests
import json
import time
from datetime import datetime, timedelta

# 计算过去30天的时间戳
end_date = datetime.now()
start_date = end_date - timedelta(days=30)
start_ts = int(start_date.timestamp())
end_ts = int(end_date.timestamp())

url = f"http://localhost:9000/api/dashboard/financials?start_time={start_ts}&end_time={end_ts}"

try:
    print(f"Requesting: {url}")
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        print("\n=== API Response Summary ===")
        print(f"Sales: {data.get('financials', {}).get('sales')}")
        print(f"Revenue (Local): {data.get('financials', {}).get('revenue')}")
        print(f"Revenue (RMB): {data.get('financials', {}).get('revenue_rmb')}")
        
        print("\n=== History Data (First 5 items) ===")
        history = data.get('history', [])
        for item in history[:5]:
            print(item)
            
        # Check specifically for revenue in history
        revenues = [h.get('revenue', 0) for h in history]
        print(f"\nNon-zero revenue entries in history: {len([r for r in revenues if r > 0])}/{len(revenues)}")
    else:
        print(f"Error: {response.status_code} - {response.text}")
except Exception as e:
    print(f"Exception: {e}")
