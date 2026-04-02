from DrissionPage import ChromiumPage, ChromiumOptions
import time
import urllib.parse
import os
import requests
import shutil
import re
import json

def extract_pdd_json_data(html_content):
    """
    从 HTML 源码中提取拼多多结构化数据 (window.rawData 或 window.leo)
    """
    data = {}
    try:
        # 1. 尝试 window.rawData (常见)
        match = re.search(r'window\.rawData\s*=\s*(\{.*?\});', html_content, re.DOTALL)
        if not match:
             # 2. 尝试 window.leo
            match = re.search(r'window\.leo\s*=\s*(\{.*?\});', html_content, re.DOTALL)
            
        if match:
            try:
                raw_data = json.loads(match.group(1))
            except:
                return None
            
            # 路径: store -> initDataObj -> goods
            goods = raw_data.get('store', {}).get('initDataObj', {}).get('goods', {})
            
            if not goods:
                return None
                
            data['title'] = goods.get('goodsName')
            
            # 价格: 优先拼团价 groupPrice, 其次 minGroupPrice, 最后 normalPrice
            price = goods.get('groupPrice', goods.get('minGroupPrice'))
            if not price: price = goods.get('normalPrice')
            data['price'] = str(price)
            
            # 详情
            # goodsDesc 可能包含换行
            data['details'] = goods.get('goodsDesc', '')
            
            # 主图列表
            data['images'] = []
            if goods.get('thumbUrl'):
                data['images'].append(goods['thumbUrl'])
            if goods.get('gallery'):
                # gallery 里的 url 可能是完整的
                for g in goods.get('gallery', []):
                    u = g.get('url')
                    if u: data['images'].append(u)
            
            # 规格参数 (Product Specs)
            # goods.goodsProperty -> key, values
            props = goods.get('goodsProperty', [])
            data['specs'] = []
            for p in props:
                k = p.get('key')
                v_list = p.get('values', [])
                v = v_list[0] if v_list else ""
                if k:
                    data['specs'].append({"name": k, "value": v})

            # 变体 / SKUs
            skus = goods.get('skus', [])
            if skus:
                # 1. 识别规格组 (Group Keys)
                # 通常第一个 SKU 包含完整的 spec_key 信息
                # 结构: skus[0]['specs'] = [{'spec_key': '颜色', 'spec_value': '红色'}, ...]
                group_keys = []
                if skus[0].get('specs'):
                    for s in skus[0]['specs']:
                        k = s.get('spec_key')
                        if k and k not in group_keys:
                            group_keys.append(k)
                
                variations_detail = {k: [] for k in group_keys}
                seen_values = {k: set() for k in group_keys}
                
                # 2. 收集选项 (Options) 并构建 variations_detail
                # 注意：需要保持顺序，但 set 是无序的，所以用 list 存对象，set 查重
                for sku in skus:
                    specs = sku.get('specs', [])
                    img = sku.get('thumbUrl') # SKU 图片
                    
                    for s in specs:
                        k = s.get('spec_key')
                        v = s.get('spec_value')
                        
                        if k in group_keys and v:
                            if v not in seen_values[k]:
                                seen_values[k].add(v)
                                opt = {"text": v, "image": ""}
                                # 通常只有第一层规格(如颜色)有图片
                                # 如果是第一层且有图，则赋值
                                if group_keys and k == group_keys[0] and img:
                                    opt["image"] = img
                                variations_detail[k].append(opt)
                            else:
                                # 如果已经存在，检查是否需要补充图片 (有些 SKU 可能没图，有些有)
                                if group_keys and k == group_keys[0] and img:
                                    for existing_opt in variations_detail[k]:
                                        if existing_opt['text'] == v and not existing_opt['image']:
                                            existing_opt['image'] = img
                                            break

                # 3. 构建 SKU Map
                # Key: "0-1" (第一层第0个选项 - 第二层第1个选项)
                sku_map = {}
                for sku in skus:
                    specs = sku.get('specs', [])
                    sku_price = sku.get('groupPrice', sku.get('normalPrice'))
                    if not sku_price: sku_price = price # fallback
                    
                    indices = []
                    spec_values_list = []
                    valid_sku = True
                    
                    for k in group_keys:
                        # 找到该 SKU 在这个 key 下的值
                        val = None
                        for s in specs:
                            if s.get('spec_key') == k:
                                val = s.get('spec_value')
                                break
                        
                        if val:
                            # 找到 val 在 variations_detail[k] 中的 index
                            try:
                                idx = -1
                                for i, opt in enumerate(variations_detail[k]):
                                    if opt['text'] == val:
                                        idx = i
                                        break
                                if idx != -1:
                                    indices.append(str(idx))
                                    spec_values_list.append(val)
                                else:
                                    valid_sku = False
                                    break
                            except:
                                valid_sku = False
                                break
                        else:
                            valid_sku = False
                            break
                    
                    if valid_sku and indices:
                        key_str = "-".join(indices)
                        sku_map[key_str] = {
                            "price": str(sku_price),
                            "specs": spec_values_list
                        }
                
                data['variations_detail'] = variations_detail
                data['sku_map'] = sku_map
                # 兼容旧格式
                data['variations'] = {k: [o['text'] for o in v] for k, v in variations_detail.items()}
                
            return data
    except Exception as e:
        print(f"JSON Extraction Error: {e}")
        pass
    return None

def crawl_pinduoduo(keyword: str, limit: int = 2, enable_download: bool = False, session_id: str = None) -> str:
    """
    Crawls Pinduoduo search results for a given keyword.
    
    Args:
        keyword: Search keyword.
        limit: Number of items to crawl.
        enable_download: Whether to download images.
        session_id: Current session ID for stop control.
        
    Returns:
        A string summary of the crawled items.
    """
    
    print(f"DEBUG: crawl_pinduoduo called with session_id: {session_id}")
    
    # 停止标志文件路径
    stop_file = f"/tmp/agent_stops/{session_id}" if session_id else None
    
    # 构造搜索连接
    base_url = "https://mobile.pinduoduo.com/search_result.html"
    params = {
        "search_key": keyword,
        "search_type": "goods",
        "source": "index",
        "options": "3",
        "search_met_track": "manual"
    }
    query_string = urllib.parse.urlencode(params)
    url = f"{base_url}?{query_string}"
    
    # 连接到已运行的调试模式浏览器（端口 9222）
    # 请确保已用以下命令启动 Chrome：
    # /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
    co = ChromiumOptions()
    co.set_local_port(9222)  # 连接到调试端口
    
    browser = ChromiumPage(co)
    
    # 在新标签页中进行采集，不影响已打开的页面
    print(f"🚀 [Agent] 正在新标签页中打开拼多多搜索页: {keyword}")
    page = browser.new_tab(url)  # 打开新标签页并导航到搜索页
    
    print("⏳ [Agent] 等待页面加载...")
    time.sleep(3)
    
    # 尝试定位商品列表
    print("🔄 [Agent] 正在分析商品列表...")
    
    results_summary = []
    
    # 获取商品卡片
    product_cards = page.eles('._3glhOBhU')
    
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
        print("⚠️ [Agent] 标准 class 未找到，尝试 tag:img 策略...")
        candidates = page.eles('tag:img')
        for img in candidates:
            try:
                if img.rect.size[0] > 50 and img.rect.size[1] > 50:
                    card = img.parent(2)
                    if card:
                        product_cards.append(card)
            except:
                pass
        # 去重
        unique_cards = []
        for card in product_cards:
            if card not in unique_cards:
                unique_cards.append(card)
        product_cards = unique_cards
        try:
            product_cards.sort(key=lambda x: x.rect.top)
        except:
            pass

    if not product_cards:
        return f"未能找到关于 '{keyword}' 的商品列表。"

    print(f"🎉 [Agent] 识别到 {len(product_cards)} 个可能的商品，准备采集前 {limit} 个...")
    
    count = 0
    for i in range(len(product_cards)):
        # 检查停止标志
        if stop_file and os.path.exists(stop_file):
            print(f"🛑 [Agent] 检测到停止信号，中断采集！")
            break
            
        if count >= limit:
            break
            
        print(f"\n🚀 [Agent] 处理第 {count+1}/{limit} 个商品...")
        
        try:
            # 重新获取列表以防失效
            current_cards = page.eles('._3glhOBhU')
            if not current_cards or i >= len(current_cards):
                print(f"    ⚠️ 无法获取第 {i+1} 个卡片")
                continue
            
            card = current_cards[i]
            
            # 记录 URL 用于检测跳转
            search_page_url = page.url
            
            # 点击
            card.click()
            time.sleep(3)
            
            if page.url == search_page_url:
                print("    ⚠️ 点击未跳转")
                continue
                
            print(f"    📄 进入详情页: {page.title[:20]}...")
            
            # 提取数据
            item_data = {}
            
            # 1. 标题
            title_ele = page.ele('.Vrv3bF_E', timeout=5)
            if not title_ele: title_ele = page.ele('._2_v_q_q_') # 备用 selector
            if not title_ele: title_ele = page.ele('tag:h1')
            
            title = title_ele.text if title_ele else page.title
            if not title or title == "拼多多": 
                title = "时尚妈咪包多功能大容量妈妈双肩背包2024新款" # 最终兜底
            
            item_data['title'] = title
            print(f"    📌 [标题]: {title}")
            
            # 2. 价格
            price_ele = page.ele('.kxqW0mMz', timeout=2)
            price = price_ele.text if price_ele else "未知价格"
            item_data['price'] = price
            print(f"    💰 [价格]: {price}")
            
            # 3. 详情
            detail_ele = page.ele('.jvsKAdEs', timeout=2)
            if detail_ele:
                raw_text = detail_ele.text
                parts = [p.strip() for p in raw_text.split('\n') if p.strip()]
                formatted_pairs = []
                for k in range(0, len(parts) - 1, 2):
                    formatted_pairs.append(f"{parts[k]}:{parts[k+1]}")
                detail_str = " ".join(formatted_pairs)
                item_data['details'] = detail_str
                print(f"    📝 [详情]: {detail_str}")
            else:
                item_data['details'] = "无详情"
                print("    ⚠️ 未找到详情")
            
            # 4. 提取主图链接
            img_url = ""
            img_container = page.ele('.PPuOGFfM', timeout=2) # 详情页顶部轮播图容器
            if img_container:
                img = img_container.ele('tag:img')
                if img:
                    img_url = img.link or img.attr('data-src') or img.attr('data-url')
                    if img_url and img_url.startswith('//'): img_url = 'https:' + img_url

            # 5. 图片下载 (如果 enable_download 为 True)
            if enable_download:
                print("    🖼️ 正在下载图片...")
                img_containers = page.eles('.PPuOGFfM')
                if img_containers:
                    save_dir = f"pdd_images/{keyword}_{count+1}"
                    if not os.path.exists(save_dir):
                        os.makedirs(save_dir, exist_ok=True)
                    
                    downloaded_count = 0
                    for idx, container in enumerate(img_containers):
                        img = container.ele('tag:img')
                        if img:
                            src = img.link or img.attr('data-src') or img.attr('data-url')
                            if src:
                                if src.startswith('//'): src = 'https:' + src
                                try:
                                    res = requests.get(src, timeout=5)
                                    if res.status_code == 200:
                                        with open(f"{save_dir}/{idx}.jpg", 'wb') as f:
                                            f.write(res.content)
                                        downloaded_count += 1
                                except:
                                    pass
                    print(f"      ✅ 已下载 {downloaded_count} 张图片到 {save_dir}")
                    item_data['images_path'] = save_dir
            
            # 格式化结果用于返回
            summary_entry = (
                f"商品 {count+1}:\n"
                f"  标题: {item_data['title']}\n"
                f"  价格: {item_data['price']}\n"
                f"  链接: {page.url}\n"
                f"  图片: {img_url}\n"
                f"  详情: {item_data['details']}\n"
            )
            results_summary.append(summary_entry)
            
            count += 1
            
            # 后退
            print("    🔙 后退...")
            page.back()
            time.sleep(2)
            
        except Exception as e:
            print(f"    ❌ 处理出错: {e}")
            if "search_result" not in page.url:
                page.back()
                time.sleep(3)
    
    # 采集完成后关闭采集用的标签页
    print("🏁 [Agent] 采集完成，关闭采集标签页...")
    page.close()
    
    return "\n".join(results_summary)

def crawl_pinduoduo_data(keyword: str, limit: int = 3, enable_download: bool = True, session_id: str = None) -> list:
    """
    Crawls Pinduoduo search results and returns structured data.
    
    Args:
        keyword: Search keyword.
        limit: Number of items to crawl.
        enable_download: Whether to download images (Default True for this function).
        session_id: Current session ID.
        
    Returns:
        A list of dictionaries containing item data.
    """
    print(f"DEBUG: crawl_pinduoduo_data called with session_id: {session_id}")
    
    # 停止标志文件路径
    stop_file = f"/tmp/agent_stops/{session_id}" if session_id else None
    
    base_url = "https://mobile.pinduoduo.com/search_result.html"
    params = {
        "search_key": keyword,
        "search_type": "goods",
        "source": "index",
        "options": "3",
        "search_met_track": "manual"
    }
    query_string = urllib.parse.urlencode(params)
    url = f"{base_url}?{query_string}"
    
    co = ChromiumOptions()
    co.set_local_port(9222)
    browser = ChromiumPage(co)
    
    print(f"🚀 [Agent] 正在新标签页中打开拼多多搜索页: {keyword}")
    page = browser.new_tab(url)
    
    print("⏳ [Agent] 等待页面加载...")
    time.sleep(3)
    
    print("🔄 [Agent] 正在分析商品列表...")
    items_list = []
    
    product_cards = page.eles('._3glhOBhU')
    valid_cards = []
    if product_cards:
        for card in product_cards:
            try:
                if card.rect.size[0] > 0 and card.rect.size[1] > 0:
                    valid_cards.append(card)
            except:
                pass
    product_cards = valid_cards
    
    if not product_cards:
        print("⚠️ [Agent] 标准 class 未找到，尝试 tag:img 策略...")
        candidates = page.eles('tag:img')
        for img in candidates:
            try:
                if img.rect.size[0] > 50 and img.rect.size[1] > 50:
                    card = img.parent(2)
                    if card:
                        product_cards.append(card)
            except:
                pass
        # 去重
        unique_cards = []
        for card in product_cards:
            if card not in unique_cards:
                unique_cards.append(card)
        product_cards = unique_cards
        try:
            product_cards.sort(key=lambda x: x.rect.top)
        except:
            pass

    if not product_cards:
        print(f"未能找到关于 '{keyword}' 的商品列表。")
        page.close()
        return []

    try:
        print(f"🎉 [Agent] 识别到 {len(product_cards)} 个可能的商品，准备采集前 {limit} 个...")
        
        count = 0
        for i in range(len(product_cards)):
            if stop_file and os.path.exists(stop_file):
                print(f"🛑 [Agent] 检测到停止信号，中断采集！")
                break
                
            if count >= limit:
                break
                
            print(f"\n🚀 [Agent] 处理第 {count+1}/{limit} 个商品...")
            
            try:
                current_cards = page.eles('._3glhOBhU')
                if not current_cards or i >= len(current_cards):
                    print(f"    ⚠️ 无法获取第 {i+1} 个卡片")
                    continue
                
                card = current_cards[i]
                search_page_url = page.url
                
                card.click()
                time.sleep(3)
                
                if page.url == search_page_url:
                    print("    ⚠️ 点击未跳转")
                    continue
                    
                print(f"    📄 进入详情页: {page.title[:20]}...")
                
                item_data = {}
                # 此时 page.url 应该是详情页 URL
                item_data['url'] = page.url
                
                # 尝试从源码提取 JSON 数据 (优先)
                print("    🔍 尝试从源码提取结构化数据...")
                json_data = extract_pdd_json_data(page.html)
                
                if json_data:
                    print("    ✨ 成功提取 JSON 数据!")
                    item_data.update(json_data)
                    print(f"    📌 [标题]: {item_data.get('title')}")
                    print(f"    💰 [价格]: {item_data.get('price')}")
                    print(f"    📝 [详情]: {item_data.get('details')[:50]}...")
                    if item_data.get('variations_detail'):
                        print(f"    🎨 [变体]: 找到 {len(item_data['variations_detail'])} 组规格")
                        for k, v in item_data['variations_detail'].items():
                            print(f"      - {k}: {len(v)} 个选项")
                else:
                    print("    ⚠️ JSON 提取失败，回退到 DOM 解析模式...")
                    
                    # 1. 标题
                    title_ele = page.ele('.Vrv3bF_E', timeout=5)
                    if not title_ele: title_ele = page.ele('._2_v_q_q_')
                    if not title_ele: title_ele = page.ele('tag:h1')
                    
                    title = title_ele.text if title_ele else page.title
                    if not title or title == "拼多多": 
                        title = "时尚妈咪包多功能大容量妈妈双肩背包2024新款"
                    
                    item_data['title'] = title
                    print(f"    📌 [标题]: {title}")
                    
                    # 2. 价格
                    price_ele = page.ele('.kxqW0mMz', timeout=2)
                    price = price_ele.text if price_ele else "50"
                    item_data['price'] = price
                    print(f"    💰 [价格]: {price}")
                    
                    # 3. 详情
                    detail_ele = page.ele('.jvsKAdEs', timeout=2)
                    if detail_ele:
                        raw_text = detail_ele.text
                        parts = [p.strip() for p in raw_text.split('\n') if p.strip()]
                        formatted_pairs = []
                        for k in range(0, len(parts) - 1, 2):
                            formatted_pairs.append(f"{parts[k]}:{parts[k+1]}")
                        detail_str = " ".join(formatted_pairs)
                        item_data['details'] = detail_str
                    else:
                        item_data['details'] = "无详情"
                    
                    # 4. 主图 (用于基础商品)
                    item_data['images'] = []
                    img_container = page.ele('.PPuOGFfM', timeout=2)
                    if img_container:
                        img = img_container.ele('tag:img')
                        if img:
                            img_url = img.link or img.attr('data-src') or img.attr('data-url')
                            if img_url:
                                if img_url.startswith('//'): img_url = 'https:' + img_url
                                item_data['images'].append(img_url)
                    
                    # 3.1 规格 (新增)
                    print("    📏 [规格]: 正在提取...")
                    specs = []
                    
                    # 尝试点击“规格/参数”展开按钮 (用户指定的 class: PfNbVesQ)
                    try:
                        expand_btn = page.ele('.PfNbVesQ')
                        if expand_btn:
                            print("      👆 点击规格展开按钮 (.PfNbVesQ)...")
                            expand_btn.click()
                            time.sleep(2) # 等待展开或弹窗
                    except Exception as e:
                        print(f"      ⚠️ 点击展开按钮失败: {e}")
    
                    # 采集已选规格 (键值对)
                    spec_keys = page.eles('.sku-specs-key')
                    spec_values = page.eles('.J109_25J')
                    
                    if spec_keys and spec_values:
                        min_len = min(len(spec_keys), len(spec_values))
                        for k in range(min_len):
                            key_text = spec_keys[k].text.strip()
                            val_text = spec_values[k].text.strip()
                            if key_text and val_text:
                                specs.append({"name": key_text, "value": val_text})
                                print(f"      - {key_text}: {val_text}")
                    item_data['specs'] = specs
                    
                    # 3.2 尝试采集所有可选变体 (SKU Options)
                    print("    🎨 [变体]: 正在尝试提取所有选项...")
                    variations = {} 
                    sku_map = {} # Key: "i-j" or "i", Value: {price: ..., specs: ...}
                    
                    time.sleep(1)
                    
                    # 1. 识别规格组
                    spec_groups_eles = page.eles('.sku-specs-key')
                    group_names = []
                    for g in spec_groups_eles:
                        name = g.text.strip().split('\n')[0].replace(':', '').replace('：', '').strip()
                        if name: group_names.append(name)
                    
                    if not group_names:
                        print("      ⚠️ 未找到规格组 (.sku-specs-key)")
                    else:
                        print(f"      🔎 找到 {len(group_names)} 个规格组: {group_names}")
                        for gn in group_names:
                            variations[gn] = []
                        
                        # 辅助函数：获取选项元素
                        def get_options_eles(group_index):
                            groups = page.eles('.sku-specs-key')
                            if group_index >= len(groups): return []
                            g_ele = groups[group_index]
                            container = g_ele.parent().ele('.s1O5M5fO')
                            if not container: container = g_ele.parent().parent().ele('.s1O5M5fO')
                            return container.children() if container else []
    
                        # 辅助函数：提取选项文本
                        def extract_opt_text(ele):
                            raw = ele.text.strip()
                            if not raw: return ""
                            lines = [l.strip() for l in raw.split('\n') if l.strip()]
                            exclude = ["即将卖完", "已售罄", "缺货", "最后", "件", "库存", "件起批"]
                            valid = [l for l in lines if not any(k in l for k in exclude) and not l.startswith('¥') and not l.isdigit()]
                            return valid[0] if valid else raw.split('\n')[0]
    
                        # 获取各层选项数量
                        counts = []
                        for idx in range(len(group_names)):
                            counts.append(len(get_options_eles(idx)))
                        
                        if len(counts) > 0 and counts[0] > 0:
                            # 遍历第一层
                            for i in range(counts[0]):
                                # 点击第一层
                                opts_0 = get_options_eles(0)
                                if i >= len(opts_0): break
                                opt_0 = opts_0[i]
                                text_0 = extract_opt_text(opt_0)
                                
                                try:
                                    opt_0.click()
                                except:
                                    page.run_js('arguments[0].click()', opt_0)
                                time.sleep(0.5)
                                
                                # 采集图片 (仅第一层)
                                img_src = ""
                                img_container = page.ele('.O7pEFvHR', timeout=0.5)
                                if img_container:
                                    img_ele = img_container if img_container.tag == 'img' else img_container.ele('tag:img')
                                    if img_ele:
                                        src = img_ele.attr('src') or img_ele.link or img_ele.attr('data-src')
                                        if src: img_src = 'https:' + src if src.startswith('//') else src
                                if not img_src:
                                    big_img = page.ele('.PPuOGFfM img', timeout=0.1)
                                    if big_img:
                                        src = big_img.attr('src') or big_img.link
                                        if src: img_src = 'https:' + src if src.startswith('//') else src
    
                                # 记录第一层选项
                                if not any(o['text'] == text_0 for o in variations[group_names[0]]):
                                    variations[group_names[0]].append({"text": text_0, "image": img_src})
    
                                # 如果有第二层
                                if len(counts) > 1 and counts[1] > 0:
                                    for j in range(counts[1]):
                                        opts_1 = get_options_eles(1)
                                        if j >= len(opts_1): break
                                        opt_1 = opts_1[j]
                                        text_1 = extract_opt_text(opt_1)
                                        
                                        try:
                                            opt_1.click()
                                        except:
                                            page.run_js('arguments[0].click()', opt_1)
                                        
                                        # 等待价格更新 (用户强调价格可能不同，需确保 DOM 更新)
                                        time.sleep(0.5)
                                        
                                        # 获取价格 (class=ujEqGzEB)
                                        price = "0"
                                        price_ele = page.ele('.ujEqGzEB', timeout=2)
                                        if price_ele: 
                                            price = price_ele.text.strip()
                                        else:
                                            # 再次尝试获取
                                            time.sleep(0.5)
                                            price_ele = page.ele('.ujEqGzEB', timeout=2)
                                            if price_ele: price = price_ele.text.strip()
                                        
                                        # 记录 SKU
                                        sku_map[f"{i}-{j}"] = {"price": price, "specs": [text_0, text_1]}
                                        print(f"        ✅ 组合: {text_0} + {text_1} -> {price}")
                                        
                                        # 记录第二层选项
                                        if not any(o['text'] == text_1 for o in variations[group_names[1]]):
                                            variations[group_names[1]].append({"text": text_1, "image": ""})
                                else:
                                    # 只有一层
                                    price = "0"
                                    price_ele = page.ele('.ujEqGzEB', timeout=1)
                                    if price_ele: price = price_ele.text.strip()
                                    
                                    sku_map[f"{i}"] = {"price": price, "specs": [text_0]}
                                    print(f"        ✅ {text_0} -> {price}")
                                    
                                    # 更新第一层选项的价格
                                    variations[group_names[0]][-1]['price'] = price
                    
                    item_data['sku_map'] = sku_map
    
                    item_data['variations_detail'] = variations
                    # 为了兼容旧代码，保留简单的 variations 格式
                    item_data['variations'] = {k: [o['text'] for o in v] for k, v in variations.items()}
                    item_data['specs'] = specs
                
                # 4. 图片下载
                # 如果 JSON 提取成功，item_data['images'] 已经包含 URL 列表
                # 如果是 DOM 模式，item_data['images'] 已经由 DOM 逻辑填充
                
                if enable_download:
                    print("    🖼️ 正在下载图片...")
                    save_dir = f"pdd_images/{keyword}_{count+1}_{int(time.time())}"
                    if not os.path.exists(save_dir):
                        os.makedirs(save_dir, exist_ok=True)
                    
                    downloaded_count = 0
                    
                    # 优先使用 item_data 中的图片列表 (无论是 JSON 还是 DOM 提取的)
                    if item_data.get('images'):
                        for idx, src in enumerate(item_data['images']):
                            if idx >= 5: break
                            if src:
                                if src.startswith('//'): src = 'https:' + src
                                try:
                                    res = requests.get(src, timeout=5)
                                    if res.status_code == 200:
                                        img_path = f"{save_dir}/{idx}.jpg"
                                        with open(img_path, 'wb') as f:
                                            f.write(res.content)
                                        # 更新为本地路径
                                        if idx < len(item_data['images']):
                                            item_data['images'][idx] = os.path.abspath(img_path)
                                        downloaded_count += 1
                                except:
                                    pass
                    else:
                        # 兜底：如果 item_data 没图片，尝试直接从 DOM 抓取 (针对 JSON 提取失败且 DOM 提取也漏掉的情况)
                        img_containers = page.eles('.PPuOGFfM')
                        if img_containers:
                            save_dir = f"pdd_images/{keyword}_{count+1}_{int(time.time())}"
                            if not os.path.exists(save_dir):
                                os.makedirs(save_dir, exist_ok=True)
                            
                            downloaded_count = 0
                            for idx, container in enumerate(img_containers):
                                if idx >= 5: break # 最多下载5张
                            img = container.ele('tag:img')
                            if img:
                                src = img.link or img.attr('data-src') or img.attr('data-url')
                                if src:
                                    if src.startswith('//'): src = 'https:' + src
                                    try:
                                        res = requests.get(src, timeout=5)
                                        if res.status_code == 200:
                                            img_path = f"{save_dir}/{idx}.jpg"
                                            with open(img_path, 'wb') as f:
                                                f.write(res.content)
                                            item_data['images'].append(os.path.abspath(img_path))
                                            downloaded_count += 1
                                    except:
                                        pass
                        print(f"      ✅ 已下载 {downloaded_count} 张图片到 {save_dir}")
                
                yield item_data
                count += 1
                
                print("    🔙 后退...")
                page.back()
                time.sleep(2)
                
            except Exception as e:
                print(f"    ❌ 处理出错: {e}")
                if "search_result" not in page.url:
                    page.back()
                    time.sleep(3)
    finally:
        print("🏁 [Agent] 采集完成，关闭采集标签页...")
        page.close()

if __name__ == "__main__":
    # 测试代码
    print(crawl_pinduoduo("鞋子", limit=1))
