import time
import hmac
import hashlib
import requests
import json
from urllib.parse import urlparse, parse_qs

# 配置信息 (保持与之前一致)
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
    base_string = f"{PARTNER_ID}{path}{timestamp}"
    sign = generate_sign(base_string)
    # 使用 localhost 作为回调，方便您在浏览器地址栏复制
    redirect_url = "http://localhost/" 
    return f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&sign={sign}&redirect={redirect_url}"

def exchange_token(code, shop_id):
    path = "/api/v2/auth/token/get"
    timestamp = int(time.time())
    base_string = f"{PARTNER_ID}{path}{timestamp}"
    sign = generate_sign(base_string)
    
    url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&sign={sign}"
    payload = {
        "code": code,
        "shop_id": int(shop_id),
        "partner_id": PARTNER_ID
    }
    
    print(f"\n正在通过接口换取 Token...")
    try:
        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    print("=== Shopee Access Token 获取助手 ===\n")
    
    # 1. 生成链接
    auth_url = get_auth_url()
    print("步骤 1: 请复制以下链接到浏览器打开，并登录该店铺账号进行授权：")
    print("-" * 60)
    print(auth_url)
    print("-" * 60)
    
    # 2. 获取回调 URL
    print("\n步骤 2: 授权成功后，浏览器会跳转到一个类似 http://localhost/?code=... 的页面")
    print("请将该页面的【完整 URL】复制并粘贴到下方：")
    
    redirect_input = input("在此处粘贴 URL: ").strip()
    
    # 3. 解析并获取 Token
    if redirect_input:
        try:
            parsed = urlparse(redirect_input)
            qs = parse_qs(parsed.query)
            
            if 'code' in qs and 'shop_id' in qs:
                code = qs['code'][0]
                shop_id = qs['shop_id'][0]
                
                print(f"\n[解析成功]")
                print(f"Shop ID: {shop_id}")
                print(f"Code   : {code}")
                
                # 4. 换取 Token
                token_resp = exchange_token(code, shop_id)
                
                print("\n=== 获取结果 ===")
                print(json.dumps(token_resp, indent=2, ensure_ascii=False))
                
                if "access_token" in token_resp:
                    print("\n✅ 成功！请保存您的 access_token 和 refresh_token。")
                    print(f"access_token: {token_resp.get('access_token')}")
                else:
                    print("\n❌ 获取失败，请检查错误信息。注意 code 有效期极短。")
                    
            else:
                print("\n❌ URL 格式不正确，未能找到 code 或 shop_id 参数。")
        except Exception as e:
            print(f"\n❌ 解析出错: {e}")
    else:
        print("未输入 URL，程序退出。")
