import sys
import os
import time

# 添加路径以导入模块
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from token_manager import refresh_access_token, save_tokens, load_tokens

MERCHANT_ID = 1291063

def force_refresh_merchant_token():
    token_data = load_tokens(MERCHANT_ID)
    if not token_data:
        print(f"No token data for {MERCHANT_ID}")
        return
    
    print(f"Attempting to force refresh token for Merchant {MERCHANT_ID}...")
    new_tokens = refresh_access_token(MERCHANT_ID, token_data["refresh_token"], is_main_account=True)
    
    if new_tokens:
        save_tokens(
            MERCHANT_ID, 
            new_tokens["access_token"], 
            new_tokens["refresh_token"]
        )
        print("✅ Success!")
    else:
        print("❌ Failed to refresh token. The refresh_token might be invalid or expired.")

if __name__ == "__main__":
    force_refresh_merchant_token()
