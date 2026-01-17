import sys
import os
from pathlib import Path

# Add backend directory to sys.path
sys.path.append(os.path.join(os.getcwd(), 'backend'))
sys.path.append(os.path.join(os.getcwd(), 'backend', 'test', 'shop_test'))

from shared import fetch_order_from_api, save_order_to_db, get_db_connection, fetch_escrow_detail

ORDER_SN = "2601178V3Y9FE2"
BR_SHOP_IDS = [494829323, 1478672550]

def test_fetch_order():
    print(f"Searching for order {ORDER_SN} in BR shops...")
    
    found = False
    for shop_id in BR_SHOP_IDS:
        print(f"Checking Shop ID: {shop_id}...")
        order = fetch_order_from_api(shop_id, ORDER_SN)
        
        if order:
            print(f"✅ Found order in Shop {shop_id}!")
            print(f"Status: {order.get('order_status')}")
            print(f"Total Amount: {order.get('total_amount')}")
            
            # Try to fetch escrow details
            print("Fetching escrow details...")
            escrow = fetch_escrow_detail(shop_id, ORDER_SN)
            if escrow:
                print("✅ Escrow details fetched.")
            else:
                print("⚠️ Escrow details not found (might be unpaid or too new).")
            
            # Save to DB
            print("Saving to database...")
            conn = get_db_connection()
            save_order_to_db(conn, shop_id, order, escrow)
            conn.close()
            print("✅ Saved to database.")
            found = True
            break
        else:
            print(f"❌ Not found in Shop {shop_id}")
            
    if not found:
        print("❌ Order not found in any configured BR shop.")

if __name__ == "__main__":
    test_fetch_order()
