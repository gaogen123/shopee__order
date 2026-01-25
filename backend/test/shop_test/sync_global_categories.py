import sys
import os
import time
import hmac
import hashlib
import requests
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 将当前目录添加到 sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 将 backend 目录添加到 sys.path 以导入 shared 模块
backend_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(backend_dir)

from token_manager import get_valid_token, PARTNER_ID, PARTNER_KEY, HOST, MAIN_ACCOUNT_ID

# 实际 Merchant ID (从之前的测试中获得)
ACTUAL_MERCHANT_ID = 1291063

def create_session_with_retries():
    """创建带有重试机制的 requests session"""
    session = requests.Session()
    retry_strategy = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def generate_sign(base_string):
    return hmac.new(
        PARTNER_KEY.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def generate_merchant_sign(path, timestamp, access_token, merchant_id):
    """生成商家级别的签名"""
    base_string = f"{PARTNER_ID}{path}{timestamp}{access_token}{merchant_id}"
    return generate_sign(base_string)

def sync_global_categories():
    """同步全球商品类目到数据库"""
    print("开始同步全球商品类目...")
    
    # 1. 获取 Token
    token = get_valid_token(MAIN_ACCOUNT_ID)
    if not token:
        print(f"❌ 无法获取主账户 (Main Account ID: {MAIN_ACCOUNT_ID}) 的有效 Token。")
        return

    # 2. 调用 API 获取类目
    path = "/api/v2/global_product/get_category"
    timestamp = int(time.time())
    sign = generate_merchant_sign(path, timestamp, token, ACTUAL_MERCHANT_ID)
    
    url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&access_token={token}&merchant_id={ACTUAL_MERCHANT_ID}&sign={sign}"
    
    params = {
        "language": "zh-hans" 
    }
    
    print(f"请求 API: {url}")
    
    try:
        session = create_session_with_retries()
        resp = session.get(url, params=params, timeout=30)
        data = resp.json()
        
        if data.get("error"):
            print(f"❌ API 错误: {data.get('message')}")
            return
            
        categories = data.get("response", {}).get("category_list", [])
        print(f"✅ 成功获取 {len(categories)} 个类目。")
        
        if not categories:
            print("没有类目数据，退出。")
            return

        # 3. 搜索包含 "Home" 的类目
        print("搜索 'Home' 相关类目:")
        count = 0
        for cat in categories:
            name = cat.get('original_category_name', '')
            if 'Home' in name and not cat.get('has_children'):
                print(f"ID: {cat.get('category_id')}, Name: {name} / {cat.get('display_category_name')}")
                count += 1
                if count >= 10:
                    break
            
    except Exception as e:
        print(f"❌ 发生异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    sync_global_categories()
