
import requests
import json

order_sn = "2512114B1GNREJ"
url = f"http://localhost:8000/api/order/{order_sn}"

print(f"Fetching {url}...")
try:
    resp = requests.get(url)
    data = resp.json()
    
    print("\n--- Root Fields ---")
    print(f"actual_shipping_fee: {data.get('actual_shipping_fee')}")
    print(f"estimated_shipping_fee: {data.get('estimated_shipping_fee')}")
    
    print("\n--- Financials (Derived) ---")
    fin = data.get('financials', {})
    print(json.dumps(fin, indent=2))
    
    print("\n--- Escrow Info (Raw Source) ---")
    escrow = data.get('escrow_info', {})
    print(f"escrow.actual_shipping_fee: {escrow.get('actual_shipping_fee')}")
    print(f"escrow.estimated_shipping_fee: {escrow.get('estimated_shipping_fee')}")
    print("\n--- Escrow Info Full ---")
    print(json.dumps(escrow, indent=2))

    print("\n--- Detailed Breakdown (Root) ---")
    print(f"escrow_tax: {data.get('escrow_tax')}")
    print(f"tax_amount: {data.get('tax_amount')}")
    print(f"coin_offset: {data.get('coin_offset_transaction_fee')}") # Check naming
    
    # Try to find coins, icms in raw json
    # Many fields might be in root
    keys_of_interest = [k for k in data.keys() if 'tax' in k or 'coin' in k or 'voucher' in k or 'amount' in k]
    print(f"Keys containing tax/coin/voucher/amount: {keys_of_interest}")
    
    print("\n--- Invoice Data ---")
    print(json.dumps(data.get('invoice_data'), indent=2))

except Exception as e:
    print(e)
