import sys
import os
import time
import hmac
import hashlib
import requests
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from PIL import Image
import io

# 添加路径以导入模块
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
backend_dir = os.path.join(current_dir, "backend")
sys.path.append(backend_dir)
shop_test_dir = os.path.join(backend_dir, "test", "shop_test")
sys.path.append(shop_test_dir)

from pdd_agent_tools import crawl_pinduoduo_data
from token_manager import get_valid_token, PARTNER_ID, PARTNER_KEY, HOST, MAIN_ACCOUNT_ID

# 配置
SHOP_ID = 458007719
ACTUAL_MERCHANT_ID = 1291063
CATEGORY_ID = 100674 

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

def generate_shop_sign(path, timestamp, access_token, shop_id):
    base_string = f"{PARTNER_ID}{path}{timestamp}{access_token}{shop_id}"
    return generate_sign(base_string)

def generate_merchant_sign(path, timestamp, access_token, merchant_id):
    base_string = f"{PARTNER_ID}{path}{timestamp}{access_token}{merchant_id}"
    return generate_sign(base_string)

def upload_image(image_path):
    """上传图片到 Shopee Media Space"""
    print(f"  📤 上传图片: {image_path}")
    token = get_valid_token(SHOP_ID)
    if not token: return None

    try:
        img = Image.open(image_path)
        if img.mode != 'RGB': img = img.convert('RGB')
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG', quality=90)
        img_byte_arr.seek(0)
        
        path = "/api/v2/media_space/upload_image"
        timestamp = int(time.time())
        sign = generate_shop_sign(path, timestamp, token, SHOP_ID)
        url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&access_token={token}&shop_id={SHOP_ID}&sign={sign}"
        
        files = {'image': ('image.jpg', img_byte_arr, 'image/jpeg')}
        session = create_session_with_retries()
        resp = session.post(url, files=files, timeout=30)
        data = resp.json()
        
        image_id = data.get("response", {}).get("image_info", {}).get("image_id")
        if image_id:
            print(f"  ✅ 图片上传成功: {image_id}")
            return image_id
    except Exception as e:
        print(f"  ❌ 图片上传异常: {e}")
    return None

def add_global_item(item_data, image_id, include_variations=True):
    """
    创建全球商品 (Add Global Item)
    使用接口 /api/v2/global_product/add_global_item 在全球库中创建商品模版。
    """
    print(f"  🚀 发布全球商品: {item_data['title'][:20]}...")

    token = get_valid_token(ACTUAL_MERCHANT_ID)
    if not token:
        print(f"  ❌ 无法获取 Merchant Token")
        return None

    path = "/api/v2/global_product/add_global_item"
    timestamp = int(time.time())
    sign = generate_merchant_sign(path, timestamp, token, ACTUAL_MERCHANT_ID)
    url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&access_token={token}&merchant_id={ACTUAL_MERCHANT_ID}&sign={sign}"

    try:
        price_str = str(item_data.get('price', '50.00'))
        price = float(price_str.replace('￥', '').replace('$', '').replace('¥', '').replace(',', ''))
    except:
        price = 50.00

    sku = f"PDD-{int(time.time())}"
    description = item_data.get('details') or item_data.get('title')
    if item_data.get('specs'):
        description += "\n\n[规格参数]\n"
        for spec in item_data['specs']:
            description += f"{spec['name']}: {spec['value']}\n"

    # 1. 构造变体结构 (Tier Variation)
    tier_variation = []
    global_model = []
    
    # 使用采集到的详细变体信息
    variations_detail = item_data.get('variations_detail', {})
    
    if include_variations and variations_detail:
        print(f"  💡 构造变体结构...")
        var_keys = list(variations_detail.keys())[:2] # 最多支持两层
        
        for idx, key in enumerate(var_keys):
            opts_list = variations_detail[key]
            opt_list = []
            seen_opts = set()
            
            for i, opt_obj in enumerate(opts_list):
                opt_name = opt_obj['text'][:20]
                if opt_name in seen_opts:
                    opt_name = f"{opt_name[:17]}_{i}"
                seen_opts.add(opt_name)
                
                shopee_opt = {"option": opt_name}
                # 只有第一层变体可以绑定图片 (如果采集到了图片)
                if idx == 0 and opt_obj.get('image'):
                    # 这里可以考虑是否需要上传变体图片，目前先统一使用主图 ID
                    shopee_opt["image"] = {"image_id": image_id}
                
                opt_list.append(shopee_opt)
                
            tier_variation.append({
                "name": key[:20],
                "option_list": opt_list
            })
            
        # 2. 构造具体的 SKU 数据 (Global Model)
        if len(tier_variation) == 1:
            opts_list = variations_detail[var_keys[0]]
            for i, opt_obj in enumerate(opts_list):
                # 使用变体自带的价格，如果没有则用基础价格
                try:
                    v_price_str = opt_obj.get('price', '')
                    v_price = float(v_price_str.replace('￥', '').replace('$', '').replace('¥', '').replace(',', '')) if v_price_str else price
                except:
                    v_price = price
                    
                global_model.append({
                    "tier_index": [i],
                    "normal_stock": 100,
                    "original_price": v_price,
                    "model_sku": f"{sku}-{i}"
                })
        elif len(tier_variation) == 2:
            # 两层变体的情况，价格逻辑会更复杂，这里暂用基础价格
            for i in range(len(tier_variation[0]['option_list'])):
                for j in range(len(tier_variation[1]['option_list'])):
                    global_model.append({
                        "tier_index": [i, j],
                        "normal_stock": 100,
                        "original_price": price,
                        "model_sku": f"{sku}-{i}-{j}"
                    })

    # 3. 构造完整 Payload
    payload = {
        "category_id": CATEGORY_ID,
        "item_name": item_data['title'][:100],
        "global_item_name": item_data['title'][:100],
        "item_sku": sku,
        "global_item_sku": sku,
        "description": description,
        "original_price": price,
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
        "brand": {
            "brand_id": 0,
            "original_brand_name": "No Brand"
        },
        "pre_order": {
            "is_pre_order": True,
            "days_to_ship": 5
        },
        "seller_stock": [{"location_id": "CNZ", "stock": 100}]
    }

    if tier_variation and global_model:
        payload["tier_variation"] = tier_variation
        payload["global_model"] = global_model
        print(f"  🐛 [Debug] 发送多变体数据: {len(global_model)} 个 SKU")

    headers = {"Content-Type": "application/json"}
    try:
        session = create_session_with_retries()
        resp = session.post(url, data=json.dumps(payload), headers=headers, timeout=30)
        data = resp.json()

        if data.get("error"):
            print(f"  ❌ 发布失败: {data.get('message')}")
            print(f"  完整响应: {json.dumps(data, ensure_ascii=False)}")
            return None
        else:
            global_item_id = data.get("response", {}).get("global_item_id")
            print(f"  ✅ 发布成功! Global Item ID: {global_item_id}")
            return global_item_id

    except Exception as e:
        print(f"  ❌ 发布异常: {e}")
        return None

def main():
    keyword = "妈妈包"
    items = crawl_pinduoduo_data(keyword, limit=1, enable_download=True)
    if not items: return
    
    for item in items:
        image_id = upload_image(item['images'][0])
        if not image_id: continue
        
        # 方式 1: 一次性发布 (推荐)
        global_item_id = add_global_item(item, image_id, include_variations=True)
        
        if global_item_id:
            print(f"  ✨ 商品发布流程完成! Global Item ID: {global_item_id}")

if __name__ == "__main__":
    main()
