import time
import requests
import json
import sys
import os

# Add current directory to sys.path to import token_manager
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from token_manager import PARTNER_ID, PARTNER_KEY, HOST, generate_sign, save_tokens

def exchange_code_for_token(code, main_account_id):
    path = "/api/v2/auth/token/get"
    timestamp = int(time.time())
    sign = generate_sign(path, timestamp)
    
    url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&sign={sign}"
    
    payload = {
        "code": code,
        "partner_id": PARTNER_ID,
        "main_account_id": int(main_account_id)
    }
    
    print(f"Exchanging code for Main Account {main_account_id}...")
    
    try:
        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
        result = resp.json()
        
        if "error" in result and result["error"]:
            print(f"Error exchanging token: {result.get('message')}")
            print(f"Full response: {result}")
            return None
            
        print("Exchange successful!")
        return result
    except Exception as e:
        print(f"Network error exchanging token: {e}")
        return None

if __name__ == "__main__":
    CODE = "534d4e53646a67575469454259776d61"
    MAIN_ACCOUNT_ID = 781654
    
    tokens = exchange_code_for_token(CODE, MAIN_ACCOUNT_ID)
    
    if tokens:
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        
        if access_token and refresh_token:
            save_tokens(MAIN_ACCOUNT_ID, access_token, refresh_token)
            print(f"Tokens saved for Main Account {MAIN_ACCOUNT_ID}")
            print(f"Access Token: {access_token}")
            print(f"Refresh Token: {refresh_token}")
        else:
            print("Response did not contain tokens.")
