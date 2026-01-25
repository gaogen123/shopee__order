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

# 实际 Shop ID (从 shopee_tokens.json 中选取一个)
SHOP_ID = 458007719
# 实际 Merchant ID
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

def generate_shop_sign(path, timestamp, access_token, shop_id):
    """生成店铺级别的签名"""
    base_string = f"{PARTNER_ID}{path}{timestamp}{access_token}{shop_id}"
    return generate_sign(base_string)

def generate_merchant_sign(path, timestamp, access_token, merchant_id):
    """生成商家级别的签名"""
    base_string = f"{PARTNER_ID}{path}{timestamp}{access_token}{merchant_id}"
    return generate_sign(base_string)

def upload_image(image_path):
    """上传图片到 Shopee Media Space (Shop Level)"""
    print(f"开始上传图片: {image_path}")
    
    # 1. 获取 Token
    token = get_valid_token(SHOP_ID)
    if not token:
        print(f"❌ 无法获取店铺 (Shop ID: {SHOP_ID}) 的有效 Token。")
        return None

    # 2. 准备 API 参数
    path = "/api/v2/media_space/upload_image"
    timestamp = int(time.time())
    sign = generate_shop_sign(path, timestamp, token, SHOP_ID)
    
    url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&access_token={token}&shop_id={SHOP_ID}&sign={sign}"
    
    # 3. 准备文件
    try:
        files = {
            'image': ('test_image.jpg', open(image_path, 'rb'), 'image/jpeg')
        }
    except FileNotFoundError:
        print(f"❌ 文件未找到: {image_path}")
        return None

    print(f"请求 API: {url}")
    
    try:
        session = create_session_with_retries()
        # 注意：上传文件时不需要手动设置 Content-Type，requests 会自动处理 multipart/form-data
        resp = session.post(url, files=files, timeout=30)
        data = resp.json()
        
        if data.get("error"):
            print(f"❌ API 错误: {data.get('message')}")
            print(f"完整响应: {data}")
            return None
            
        image_info = data.get("response", {}).get("image_info", {})
        image_id = image_info.get("image_id")
        
        if image_id:
            print(f"✅ 图片上传成功! Image ID: {image_id}")
            print(f"Image Info: {json.dumps(image_info, indent=2)}")
            return image_id
        else:
            print("❌ 未能获取 Image ID")
            print(f"完整响应: {data}")
            return None
            
    except Exception as e:
        print(f"❌ 发生异常: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        files['image'][1].close()

def add_global_item(category_id, image_id):
    """发布全球商品"""
    print(f"开始发布全球商品, Category ID: {category_id}, Image ID: {image_id}")

    # 1. 获取 Token (Merchant Level)
    token = get_valid_token(MAIN_ACCOUNT_ID)
    if not token:
        print(f"❌ 无法获取主账户 (Main Account ID: {MAIN_ACCOUNT_ID}) 的有效 Token。")
        return

    # 2. 准备 API 参数
    path = "/api/v2/global_product/add_global_item"
    timestamp = int(time.time())
    sign = generate_merchant_sign(path, timestamp, token, ACTUAL_MERCHANT_ID)
    
    url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&access_token={token}&merchant_id={ACTUAL_MERCHANT_ID}&sign={sign}"

    payload = {
        "category_id": 100674, # 用户指定的类目
        "item_name": f"Global Test Item {int(time.time())}",
        "global_item_name": f"Global Test Item {int(time.time())}",
        "item_sku": f"SKU-{int(time.time())}",
        "global_item_sku": f"SKU-{int(time.time())}",
        "description": "This is a test item description.\n\nFeature A\nFeature B",
        "original_price": 50.00,
        "normal_stock": 100,
        "weight": 0.5,
        "condition": "NEW",
        "image": {
            "image_id_list": [image_id]
        },
        "dimension": {
            "package_length": 10,
            "package_width": 10,
            "package_height": 10
        },
        "pre_order": {
            "is_pre_order": True,
            "days_to_ship": 5
        },
        "brand": {
            "brand_id": 0,
            "original_brand_name": "No Brand"
        },
        "seller_stock": [
            {
                "location_id": "CNZ",
                "stock": 100
            }
        ]
        # 故意不传 attribute_list 以触发报错，从而得知必填属性
    }

    print(f"请求 API: {url}")
    # print(f"Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")

    headers = {
        "Content-Type": "application/json"
    }

    try:
        session = create_session_with_retries()
        resp = session.post(url, data=json.dumps(payload), headers=headers, timeout=30)
        data = resp.json()

        if data.get("error"):
            print(f"❌ API 错误: {data.get('message')}")
            print(f"完整响应: {data}")
            return
        
        response = data.get("response", {})
        global_item_id = response.get("global_item_id")
        
        if global_item_id:
            print(f"✅ 全球商品发布成功! Global Item ID: {global_item_id}")
            # print(f"完整响应: {json.dumps(response, indent=2)}")
        else:
            print("❌ 未能获取 Global Item ID")
            print(f"完整响应: {data}")

    except Exception as e:
        print(f"❌ 发生异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # image_path = os.path.join(current_dir, "test_image.jpg")
    # image_id = upload_image(image_path)
    
    # 使用之前上传成功的 Image ID，避免重复上传
    image_id = "sg-11134201-8262z-mjv4dwu41gxyfc"
    
    if image_id:
        add_global_item(100674, image_id)
