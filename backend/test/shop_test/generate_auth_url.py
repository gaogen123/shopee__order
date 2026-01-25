import time
import hmac
import hashlib
import urllib.parse

# Configuration
PARTNER_ID = 2014583
PARTNER_KEY = "shpk616b4d6468776273596f784a716941775743435174625566564f48615057"
HOST = "https://openplatform.shopee.cn"

def generate_sign(base_string):
    return hmac.new(
        PARTNER_KEY.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def get_auth_url():
    path = "/api/v2/shop/auth_partner"
    timestamp = int(time.time())
    redirect_url = "https://www.baidu.com"
    base_string = f"{PARTNER_ID}{path}{timestamp}"
    sign = generate_sign(base_string)
    
    url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&sign={sign}&redirect={redirect_url}"
    return url

if __name__ == "__main__":
    print("\n🔗 Shopee 授权链接 (点击链接进行授权):")
    print("-" * 60)
    print(get_auth_url())
    print("-" * 60)
    print("授权后，请获取 URL 中的 code 参数，并使用 exchange_main_token.py 或相关脚本换取 Token。")
