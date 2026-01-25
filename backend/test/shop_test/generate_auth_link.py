import time
import hmac
import hashlib

PARTNER_ID = 2014583
PARTNER_KEY = "shpk616b4d6468776273596f784a716941775743435174625566564f48615057"
HOST = "https://openplatform.shopee.cn"

def generate_auth_link():
    path = "/api/v2/shop/auth_partner"
    timestamp = int(time.time())
    
    # 签名基础字符串: partner_id + path + timestamp
    base_string = f"{PARTNER_ID}{path}{timestamp}"
    sign = hmac.new(
        PARTNER_KEY.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # 授权链接
    redirect_url = "https://www.google.com"
    auth_url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&sign={sign}&redirect={redirect_url}"
    
    print("\n" + "="*50)
    print("请在浏览器中打开以下链接进行授权：")
    print(auth_url)
    print("="*50 + "\n")

if __name__ == "__main__":
    generate_auth_link()
