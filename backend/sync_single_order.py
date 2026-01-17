import sys
import os
import json
import time

# Add current directory to sys.path so we can import shared
sys.path.append(os.getcwd())
# Add test/shop_test to sys.path so shared can import token_manager
sys.path.append(os.path.join(os.getcwd(), "test", "shop_test"))

import shared

def main():
    order_sn = "2511062BHP007M"
    
    # 1. Get shop_id from DB
    print(f"Connecting to DB to find shop_id for order {order_sn}...")
    try:
        conn = shared.get_db_connection()
        c = conn.cursor(dictionary=True)
        c.execute("SELECT shop_id FROM orders WHERE order_sn = %s", (order_sn,))
        row = c.fetchone()
        
        if not row:
            print(f"Order {order_sn} not found in database. Cannot determine shop_id.")
            conn.close()
            return

        shop_id = row['shop_id']
        print(f"Found shop_id: {shop_id} for order {order_sn}")
        
        # 2. Call API to get Order Detail
        print(f"Fetching Order Detail from Shopee API...")
        order_detail = shared.fetch_order_from_api(shop_id, order_sn)
        if not order_detail:
            print("Failed to fetch order detail.")
            conn.close()
            return

        # 3. Call API to get Escrow Detail
        print(f"Fetching Escrow Detail from Shopee API...")
        escrow_detail = shared.fetch_escrow_detail(shop_id, order_sn)
        if not escrow_detail:
            print("Failed to fetch escrow detail.")
            # We might still want to save order detail even if escrow fails, but for this task escrow is key.
            # However, let's proceed with what we have, but warn.
            print("WARNING: Proceeding without escrow detail update.")
        
        # 4. Save to DB
        print(f"Saving to DB...")
        shared.save_order_to_db(conn, shop_id, order_detail, escrow_detail)
        
        # 5. Verify Update
        c.execute("SELECT estimated_revenue, escrow_data FROM orders WHERE order_sn = %s", (order_sn,))
        updated_row = c.fetchone()
        print(f"\n=== Updated DB Record ===")
        print(f"Estimated Revenue: {updated_row['estimated_revenue']}")
        # print(f"Escrow Data: {updated_row['escrow_data'][:100]}...")
        
        conn.close()
        print("\nSync Complete.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
