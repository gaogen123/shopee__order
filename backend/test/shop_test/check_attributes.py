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

# 实际 Merchant ID
ACTUAL_MERCHANT_ID = 1291063

def create_session_with_retries():
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
    base_string = f"{PARTNER_ID}{path}{timestamp}{access_token}{merchant_id}"
    return generate_sign(base_string)

def check_attributes(category_id):
    """获取全球商品类目属性"""
    print(f"开始获取类目属性, Category ID: {category_id}")

    token = get_valid_token(MAIN_ACCOUNT_ID)
    if not token:
        print(f"❌ 无法获取 Token")
        return

    path = "/api/v2/global_product/get_attributes"
    timestamp = int(time.time())
    sign = generate_merchant_sign(path, timestamp, token, ACTUAL_MERCHANT_ID)
    
    url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&access_token={token}&merchant_id={ACTUAL_MERCHANT_ID}&sign={sign}&category_id={category_id}&language=zh-hans"

    print(f"请求 API: {url}")

    try:
        session = create_session_with_retries()
        resp = session.get(url, timeout=30)
        data = resp.json()

        if data.get("error"):
            print(f"❌ API 错误: {data.get('message')}")
            return
        
        attributes = data.get("response", {}).get("attribute_list", [])
        print(f"✅ 获取成功! 共 {len(attributes)} 个属性")
        
        for attr in attributes:
            is_mandatory = attr.get("is_mandatory")
            print(f"- [{attr.get('attribute_id')}] {attr.get('display_attribute_name')} (必填: {is_mandatory})")
            # if is_mandatory:
            #     print(f"  Type: {attr.get('input_type')}, Options: {len(attr.get('attribute_value_list', []))}")

    except Exception as e:
        print(f"❌ 发生异常: {e}")

if __name__ == "__main__":
    check_attributes(101127)
