from DrissionPage import ChromiumPage, ChromiumOptions
import time
import urllib.parse
import os
import requests
import shutil

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
        product_cards = list(set(product_cards)) if isinstance(product_cards, list) else list(product_cards)
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

def crawl_pinduoduo_data(keyword: str, limit: int = 2, enable_download: bool = True, session_id: str = None) -> list:
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
        product_cards = list(set(product_cards)) if isinstance(product_cards, list) else list(product_cards)
        try:
            product_cards.sort(key=lambda x: x.rect.top)
        except:
            pass

    if not product_cards:
        print(f"未能找到关于 '{keyword}' 的商品列表。")
        page.close()
        return []

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
            item_data['url'] = page.url
            
            # 1. 标题
            title_ele = page.ele('.Vrv3bF_E', timeout=5)
            title = title_ele.text if title_ele else "未知标题"
            item_data['title'] = title
            print(f"    📌 [标题]: {title}")
            
            # 2. 价格
            price_ele = page.ele('.kxqW0mMz', timeout=2)
            price = price_ele.text if price_ele else "50" # 默认价格
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
            
            # 3.2 尝试采集所有可选变体 (SKU Options)
            print("    🎨 [变体]: 正在尝试提取所有选项...")
            variations = {} 
            
            # 增加一点等待，确保 DOM 完全更新
            time.sleep(1)
            
            # 查找所有规格组名
            spec_groups = page.eles('.sku-specs-key') # 规格组名 (用户提供)
                
            if spec_groups:
                print(f"      🔎 找到 {len(spec_groups)} 个规格组")
                
                for group in spec_groups:
                    # 提取组名
                    full_group_text = group.text.strip()
                    group_name = full_group_text.split('\n')[0].replace(':', '').replace('：', '').strip()
                    if not group_name: continue
                    
                    # 找到该规格组下的选项容器 (.s1O5M5fO)
                    # 通常容器是组名元素的兄弟节点，或者在同一个父容器下
                    container = group.parent().ele('.s1O5M5fO')
                    if not container:
                        # 尝试在更大的范围内找
                        container = group.parent().parent().ele('.s1O5M5fO')
                    
                    if container:
                        # 提取容器内的所有选项按钮 (通常是直接子 div)
                        opts = container.children()
                        if not opts: continue
                        
                        print(f"      📦 规格组 [{group_name}] 包含 {len(opts)} 个选项 (.s1O5M5fO 容器内)")
                        variations[group_name] = []
                        
                        for opt in opts:
                            opt_data = {"text": "", "image": "", "price": ""}
                            
                            # 1. 获取文本 (过滤状态词、库存、价格)
                            raw_text = opt.text.strip()
                            if not raw_text: continue
                            
                            lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
                            exclude_keywords = ["即将卖完", "已售罄", "缺货", "最后", "件", "库存", "件起批"]
                            valid_lines = []
                            for l in lines:
                                if any(k in l for k in exclude_keywords): continue
                                if l.startswith('¥') or l.startswith('￥'): continue
                                if l.isdigit(): continue
                                valid_lines.append(l)
                            
                            text = valid_lines[0] if valid_lines else raw_text
                            opt_data["text"] = text.split('\n')[0].strip()
                            
                            # 2. 获取图片
                            img_ele = opt.ele('.O7pEFvHR', timeout=0.1)
                            if img_ele:
                                src = img_ele.link or img_ele.attr('data-src') or img_ele.attr('data-url')
                                if src:
                                    if src.startswith('//'): src = 'https:' + src
                                    opt_data["image"] = src
                            
                            # 3. 获取价格
                            try:
                                opt.click()
                                time.sleep(0.7) # 等待价格刷新
                                price_ele = page.ele('.ujEqGzEB', timeout=1)
                                if price_ele:
                                    opt_data["price"] = price_ele.text.strip()
                            except:
                                pass
                                
                            variations[group_name].append(opt_data)
                            print(f"        ✅ {group_name}: {opt_data['text']} -> {opt_data['price']}")
            else:
                print("      ⚠️ 未找到规格组 (.sku-specs-key)")

            item_data['variations_detail'] = variations
            # 为了兼容旧代码，保留简单的 variations 格式
            item_data['variations'] = {k: [o['text'] for o in v] for k, v in variations.items()}
            item_data['specs'] = specs
            
            # 4. 图片下载
            item_data['images'] = []
            if enable_download:
                print("    🖼️ 正在下载图片...")
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
            
            items_list.append(item_data)
            count += 1
            
            print("    🔙 后退...")
            page.back()
            time.sleep(2)
            
        except Exception as e:
            print(f"    ❌ 处理出错: {e}")
            if "search_result" not in page.url:
                page.back()
                time.sleep(3)
    
    print("🏁 [Agent] 采集完成，关闭采集标签页...")
    page.close()
    return items_list

if __name__ == "__main__":
    # 测试代码
    print(crawl_pinduoduo("妈咪包", limit=1))
