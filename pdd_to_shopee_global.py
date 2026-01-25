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

def upload_image(image_source):
    """上传图片到 Shopee Media Space (支持本地路径或 URL)"""
    print(f"  📤 上传图片: {image_source[:50]}...")
    token = get_valid_token(SHOP_ID)
    if not token: return None

    try:
        if image_source.startswith('http'):
            # 处理网络图片
            res = requests.get(image_source, timeout=10)
            if res.status_code != 200:
                print(f"    ❌ 下载图片失败: {res.status_code}")
                return None
            img_data = io.BytesIO(res.content)
            img = Image.open(img_data)
        else:
            # 处理本地图片
            img = Image.open(image_source)

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
        else:
            print(f"  ❌ 图片上传失败: {data.get('message')}")
    except Exception as e:
        print(f"  ❌ 图片上传异常: {e}")
    return None

def add_global_item(item_data, image_id):
    """
    第一步: 创建全球商品 (仅基础信息)
    """
    print(f"  🚀 [Step 1] 创建基础商品: {item_data['title'][:20]}...")

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

    # 构造基础 Payload (不含变体)
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

    headers = {"Content-Type": "application/json"}
    try:
        session = create_session_with_retries()
        resp = session.post(url, data=json.dumps(payload), headers=headers, timeout=30)
        data = resp.json()

        if data.get("error"):
            print(f"  ❌ [Step 1] 失败: {data.get('message')}")
            return None, None, None
        else:
            global_item_id = data.get("response", {}).get("global_item_id")
            print(f"  ✅ [Step 1] 成功! Global Item ID: {global_item_id}")
            return global_item_id, price, sku

    except Exception as e:
        print(f"  ❌ [Step 1] 异常: {e}")
        return None, None, None

def init_tier_variation(global_item_id, tier_variation, global_model):
    """
    第二步: 初始化变体结构 (同时提交 Model)
    """
    print(f"  🚀 [Step 2] 初始化变体结构 (含 Model)...")
    token = get_valid_token(ACTUAL_MERCHANT_ID)
    path = "/api/v2/global_product/init_tier_variation"
    timestamp = int(time.time())
    sign = generate_merchant_sign(path, timestamp, token, ACTUAL_MERCHANT_ID)
    url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&access_token={token}&merchant_id={ACTUAL_MERCHANT_ID}&sign={sign}"
    
    payload = {
        "global_item_id": global_item_id,
        "tier_variation": tier_variation,
        "global_model": global_model
    }
    
    try:
        session = create_session_with_retries()
        resp = session.post(url, data=json.dumps(payload), headers={"Content-Type": "application/json"}, timeout=30)
        data = resp.json()
        if data.get("error"):
            print(f"  ❌ [Step 2] 失败: {data.get('message')}")
            print(f"  完整响应: {json.dumps(data, ensure_ascii=False)}")
            return False
        else:
            print(f"  ✅ [Step 2] 变体结构初始化成功")
            return True
    except Exception as e:
        print(f"  ❌ [Step 2] 异常: {e}")
        return False

# def add_global_model(global_item_id, global_model):
#     """
#     第三步: 添加变体 SKU (Model)
#     """
#     print(f"  🚀 [Step 3] 添加变体 SKU...")
#     token = get_valid_token(ACTUAL_MERCHANT_ID)
#     path = "/api/v2/global_product/add_global_model"
#     timestamp = int(time.time())
#     sign = generate_merchant_sign(path, timestamp, token, ACTUAL_MERCHANT_ID)
#     url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&access_token={token}&merchant_id={ACTUAL_MERCHANT_ID}&sign={sign}"
#     
#     payload = {
#         "global_item_id": global_item_id,
#         "global_model_list": global_model
#     }
#     
#     try:
#         session = create_session_with_retries()
#         resp = session.post(url, data=json.dumps(payload), headers={"Content-Type": "application/json"}, timeout=30)
#         data = resp.json()
#         if data.get("error"):
#             print(f"  ❌ [Step 3] 失败: {data.get('message')}")
#             print(f"  完整响应: {json.dumps(data, ensure_ascii=False)}")
#             return False
#         else:
#             print(f"  ✅ [Step 3] 变体 SKU 添加成功")
#             return True
#     except Exception as e:
#         print(f"  ❌ [Step 3] 异常: {e}")
#         return False

def process_variations(item_data, image_id, price, sku):
    """处理变体数据，生成 tier_variation 和 global_model"""
    tier_variation = []
    global_model = []
    
    variations_detail = item_data.get('variations_detail', {})
    if not variations_detail:
        return None, None

    print(f"  💡 处理变体数据...")
    var_keys = list(variations_detail.keys())[:2] # 最多支持两层
    
    for idx, key in enumerate(var_keys):
        opts_list = variations_detail[key]
        opt_list = []
        seen_opts = set()
        
        for i, opt_obj in enumerate(opts_list):
            # Shopee 限制变体选项名称最多 30 个字符
            # 为了保险，我们截断到 15 个字符，并预留后缀空间
            raw_name = opt_obj['text'].strip()
            opt_name = raw_name[:15]
            
            if opt_name in seen_opts:
                opt_name = f"{opt_name[:12]}_{i}"
            seen_opts.add(opt_name)
            
            shopee_opt = {"option": opt_name}
            # 只有第一层变体可以绑定图片
            if idx == 0:
                v_img_url = opt_obj.get('image')
                if v_img_url:
                    print(f"    🖼️ 上传变体图片 [{opt_name}]: {v_img_url[:30]}...")
                    v_image_id = upload_image(v_img_url)
                    if v_image_id:
                        shopee_opt["image"] = {"image_id": v_image_id}
                    else:
                        print(f"    ⚠️ 变体图片上传失败，使用主图")
                        shopee_opt["image"] = {"image_id": image_id}
                else:
                    shopee_opt["image"] = {"image_id": image_id}
            
            opt_list.append(shopee_opt)
            
        tier_variation.append({
            "name": key[:20],
            "option_list": opt_list
        })
        
    # 构造 Global Model
    if len(tier_variation) == 1:
        opts_list = variations_detail[var_keys[0]]
        for i, opt_obj in enumerate(opts_list):
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
        for i in range(len(tier_variation[0]['option_list'])):
            for j in range(len(tier_variation[1]['option_list'])):
                global_model.append({
                    "tier_index": [i, j],
                    "normal_stock": 100,
                    "original_price": price,
                    "model_sku": f"{sku}-{i}-{j}"
                })
                
    return tier_variation, global_model

def main():
    keyword = "手机"
    items = crawl_pinduoduo_data(keyword, limit=1, enable_download=True)
    if not items: return
    
    for item in items:
        print(f"  🔗 原商品链接: {item.get('url', '未知')}")
        # 0. 上传主图
        image_id = upload_image(item['images'][0])
        if not image_id: continue
        
        # 1. 创建基础商品
        global_item_id, price, sku = add_global_item(item, image_id)
        if not global_item_id: continue
        
        # 检查是否有变体需要处理
        if item.get('variations_detail'):
            # 准备变体数据
            tier_variation, global_model = process_variations(item, image_id, price, sku)
            
            if tier_variation and global_model:
                # 等待几秒，确保商品创建完成
                print("  ⏳ 等待 5 秒，确保基础商品创建生效...")
                time.sleep(5)
                
                # 2. 初始化变体结构 (含 Model)
                if init_tier_variation(global_item_id, tier_variation, global_model):
                    print("  ✨ 变体创建完成")
                    # time.sleep(10)
                    # 3. 添加变体 SKU
                    # add_global_model(global_item_id, global_model)
        
        print(f"  ✨ 商品发布流程完成! Global Item ID: {global_item_id}")

if __name__ == "__main__":
    main()
