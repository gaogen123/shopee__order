from DrissionPage import ChromiumPage
import time
import urllib.parse
import os
import requests
import shutil
import sys
import hmac
import hashlib
import json
import io
from PIL import Image
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 添加路径以导入模块
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
backend_dir = os.path.join(current_dir, "backend")
sys.path.append(backend_dir)
shop_test_dir = os.path.join(backend_dir, "test", "shop_test")
sys.path.append(shop_test_dir)

try:
    from token_manager import get_valid_token, PARTNER_ID, PARTNER_KEY, HOST, MAIN_ACCOUNT_ID
except ImportError:
    # Fallback or mock if token_manager is not found (e.g. in some test envs)
    print("Warning: token_manager not found")
    PARTNER_ID = 0
    PARTNER_KEY = ""
    HOST = ""
    MAIN_ACCOUNT_ID = 0
    def get_valid_token(shop_id): return ""

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
        return None, None, None

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
    
    # 附加原链接 - 用户要求移除
    # if item_data.get('url'):
    #     description += f"\n\n[Source URL]: {item_data['url']}"

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
    sku_map = item_data.get('sku_map', {})
    
    if len(tier_variation) == 1:
        opts_list = variations_detail[var_keys[0]]
        for i, opt_obj in enumerate(opts_list):
            v_price = price
            
            # 尝试从 sku_map 获取精确价格
            key = f"{i}"
            if key in sku_map:
                try:
                    p_str = sku_map[key]['price']
                    v_price = float(p_str.replace('￥', '').replace('$', '').replace('¥', '').replace(',', ''))
                except:
                    pass
            elif 'price' in opt_obj: # 兼容旧逻辑
                 try:
                    p_str = opt_obj['price']
                    v_price = float(p_str.replace('￥', '').replace('$', '').replace('¥', '').replace(',', ''))
                 except:
                    pass
                
            global_model.append({
                "tier_index": [i],
                "normal_stock": 100,
                "original_price": v_price,
                "model_sku": f"{sku}-{i}"
            })
    elif len(tier_variation) == 2:
        for i in range(len(tier_variation[0]['option_list'])):
            for j in range(len(tier_variation[1]['option_list'])):
                v_price = price
                
                # 尝试从 sku_map 获取精确价格
                key = f"{i}-{j}"
                if key in sku_map:
                    try:
                        p_str = sku_map[key]['price']
                        v_price = float(p_str.replace('￥', '').replace('$', '').replace('¥', '').replace(',', ''))
                    except:
                        pass
                
                global_model.append({
                    "tier_index": [i, j],
                    "normal_stock": 100,
                    "original_price": v_price,
                    "model_sku": f"{sku}-{i}-{j}"
                })
                
    return tier_variation, global_model

def publish_to_shopee_global(item_data):
    """
    发布商品到 Shopee Global
    
    Args:
        item_data: 包含商品信息的字典 (title, price, images, variations_detail, sku_map 等)
        
    Returns:
        global_item_id (str) or None
    """
    print(f"🚀 开始发布商品: {item_data.get('title', '未知')[:30]}...")
    
    # 0. 上传主图
    if not item_data.get('images'):
        print("  ❌ 缺少主图")
        return None
        
    image_id = upload_image(item_data['images'][0])
    if not image_id: 
        print("  ❌ 主图上传失败")
        return None
    
    # 1. 创建基础商品
    global_item_id, price, sku = add_global_item(item_data, image_id)
    if not global_item_id: return None
    
    # 检查是否有变体需要处理
    if item_data.get('variations_detail'):
        # 准备变体数据
        tier_variation, global_model = process_variations(item_data, image_id, price, sku)
        
        if tier_variation and global_model:
            # 等待几秒，确保商品创建完成
            print("  ⏳ 等待 5 秒，确保基础商品创建生效...")
            time.sleep(5)
            
            # 2. 初始化变体结构 (含 Model)
            if init_tier_variation(global_item_id, tier_variation, global_model):
                print("  ✨ 变体创建完成")
    
    print(f"  ✨ 商品发布流程完成! Global Item ID: {global_item_id}")
    return global_item_id

def crawl_shopee(keyword: str, limit: int = 2, enable_download: bool = False) -> str:
    """
    Crawls Shopee search results for a given keyword.
    
    Args:
        keyword: Search keyword.
        limit: Number of items to crawl.
        enable_download: Whether to download images.
        
    Returns:
        A string summary of the crawled items.
    """
    
    # 构造搜索连接 (默认为 Shopee 台湾站，可视需求修改为 sg, my 等)
    base_url = "https://shopee.tw/search"
    params = {
        "keyword": keyword
    }
    query_string = urllib.parse.urlencode(params)
    url = f"{base_url}?{query_string}"
    
    page = ChromiumPage()
    print(f"🚀 [Agent] 正在打开 Shopee 搜索页: {keyword}")
    page.get(url)
    
    print("⏳ [Agent] 等待页面加载...")
    time.sleep(3)
    
    # 尝试定位商品列表
    print("🔄 [Agent] 正在分析商品列表...")
    
    results_summary = []
    
    # 获取商品卡片 (Shopee 的 class 经常变动，建议使用 data-sqe 属性)
    # 常见 selector: div[data-sqe="item"]
    product_cards = page.eles('css:div[data-sqe="item"]')
    
    if not product_cards:
        # 尝试备用 selector
        product_cards = page.eles('.shopee-search-item-result__item')
    
    # 过滤无效卡片
    valid_cards = []
    if product_cards:
        for card in product_cards:
            try:
                if card.rect.size[0] > 0 and card.rect.size[1] > 0:
                    valid_cards.append(card)
            except:
                pass
    product_cards = valid_cards
    
    # 如果没找到，尝试模糊
    if not product_cards:
        print("⚠️ [Agent] 标准 selector 未找到，尝试 tag:a 包含 href='/product/' 策略...")
        candidates = page.eles('tag:a')
        for link in candidates:
            try:
                href = link.attr('href')
                if href and '-i.' in href: # Shopee 商品链接通常包含 -i.
                    if link.rect.size[0] > 50 and link.rect.size[1] > 50:
                        valid_cards.append(link)
            except:
                pass
        # 去重
        product_cards = list(set(valid_cards)) if isinstance(valid_cards, list) else list(valid_cards)
        try:
            product_cards.sort(key=lambda x: x.rect.top)
        except:
            pass

    if not product_cards:
        return f"未能找到关于 '{keyword}' 的商品列表。"

    print(f"🎉 [Agent] 识别到 {len(product_cards)} 个可能的商品，准备采集前 {limit} 个...")
    
    count = 0
    for i in range(len(product_cards)):
        if count >= limit:
            break
            
        print(f"\n🚀 [Agent] 处理第 {count+1}/{limit} 个商品...")
        
        try:
            # 重新获取列表以防失效
            current_cards = page.eles('css:div[data-sqe="item"]')
            if not current_cards:
                 current_cards = page.eles('.shopee-search-item-result__item')

            if not current_cards or i >= len(current_cards):
                print(f"    ⚠️ 无法获取第 {i+1} 个卡片")
                continue
            
            card = current_cards[i]
            
            # 记录 URL 用于检测跳转
            search_page_url = page.url
            
            # 点击
            card.click()
            time.sleep(3)
            
            # 检查是否打开了新标签页 (Shopee 经常在新标签页打开商品)
            if page.tabs_count > 1:
                page.close_other_tabs(page.tab_id) # 保持原页面，但这里我们需要切换到新标签页
                # 简单处理：Shopee 通常会在当前页或新标签页。
                # DrissionPage 的 click 如果触发新标签页，当前对象 page 指向的还是原标签页。
                # 我们需要获取最新标签页
                latest_tab = page.latest_tab
                latest_tab.activate() # 切换到新标签页
                page = latest_tab # 更新 page 对象引用 (注意：这只影响当前循环内的 page 引用)
            
            print(f"    📄 进入详情页: {page.title[:20]}...")
            
            # 提取数据
            item_data = {}
            
            # 1. 标题 (常见 class: ._44qnta 或 data-sqe="item-name")
            # 尝试通过文本长度判断
            title = "未知标题"
            title_eles = page.eles('tag:div')
            for ele in title_eles:
                # 标题通常字数较多且在上方
                if len(ele.text) > 10 and ele.rect.top < 500: 
                     # 这里很难有个通用标准，暂时使用 meta 标签取巧
                     pass
            
            # 更稳妥的方式：meta name="twitter:title"
            meta_title = page.ele('css:meta[name="twitter:title"]')
            if meta_title:
                title = meta_title.attr('content')
            else:
                 # 备用：尝试找 h1 或大字体 class
                 h1 = page.ele('tag:h1')
                 if h1: title = h1.text

            item_data['title'] = title
            print(f"    📌 [标题]: {title}")
            
            # 2. 价格
            # 尝试找 meta property="product:price:amount"
            price = "未知价格"
            meta_price = page.ele('css:meta[property="product:price:amount"]')
            if meta_price:
                 price = meta_price.attr('content')
                 currency = page.ele('css:meta[property="product:price:currency"]').attr('content') if page.ele('css:meta[property="product:price:currency"]') else ""
                 price = f"{currency} {price}"
            else:
                # 尝试找包含 $ 或 ￥ 或 NT$ 的元素
                price_ele = page.ele('text:$')
                if not price_ele: price_ele = page.ele('text:NT$')
                if price_ele: price = price_ele.parent().text

            item_data['price'] = price
            print(f"    💰 [价格]: {price}")
            
            # 3. 详情 (描述)
            detail_str = "无详情"
            # 详情通常在 page-product__info 或类似
            # 简单抓取 meta description
            meta_desc = page.ele('css:meta[name="twitter:description"]')
            if meta_desc:
                detail_str = meta_desc.attr('content')
            
            item_data['details'] = detail_str
            print(f"    📝 [详情]: {detail_str[:50]}...")
            
            # 4. 图片下载
            if enable_download:
                print("    🖼️ 正在提取图片...")
                # Shopee 图片通常在 style="background-image: url(...)" 或者 img src
                # 简单策略：抓取 meta image
                img_url = ""
                meta_img = page.ele('css:meta[name="twitter:image"]')
                if meta_img:
                    src = meta_img.attr('content')
                    if src:
                        save_dir = f"shopee_images/{keyword}_{count+1}"
                        if not os.path.exists(save_dir):
                            os.makedirs(save_dir, exist_ok=True)
                        
                        try:
                            res = requests.get(src, timeout=10)
                            if res.status_code == 200:
                                with open(f"{save_dir}/cover.jpg", 'wb') as f:
                                    f.write(res.content)
                                print(f"      ✅ 已下载封面图到 {save_dir}")
                        except:
                            pass
                        item_data['images_path'] = save_dir
            
            # 格式化结果用于返回
            summary_entry = (
                f"商品 {count+1}:\n"
                f"  标题: {item_data['title']}\n"
                f"  价格: {item_data['price']}\n"
                f"  链接: {page.url}\n"
                f"  详情: {item_data['details']}\n"
            )
            results_summary.append(summary_entry)
            
            count += 1
            
            # 后退 / 关闭标签页
            # 如果我们是在新标签页，关闭它回到搜索页
            if page != search_page_url: # 简单判断 url 变了或者 page 对象变了
                # 如果是多标签页情况
                if len(page.tabs) > 1:
                    page.close() # 关闭当前商品页
                    # 切换回第一个标签页 (通常是搜索页，但不一定，需要更严谨的 logic)
                    # 假设 0 是搜索页
                    page = page.get_tab(page.tabs[0])
                else:
                    print("    🔙 后退...")
                    page.back()
            
            time.sleep(2)
            
        except Exception as e:
            print(f"    ❌ 处理出错: {e}")
            # 尝试恢复状态
            try:
                if len(page.tabs) > 1:
                    page.close()
                    page = page.get_tab(page.tabs[0])
                else:
                    page.back()
            except:
                pass
            time.sleep(3)
    
    return "\n".join(results_summary)

if __name__ == "__main__":
    # 测试代码
    print(crawl_shopee("iphone 15", limit=1))
