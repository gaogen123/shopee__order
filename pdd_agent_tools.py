from DrissionPage import ChromiumPage
import time
import urllib.parse
import os
import requests
import shutil

def crawl_pinduoduo(keyword: str, limit: int = 2, enable_download: bool = False) -> str:
    """
    Crawls Pinduoduo search results for a given keyword.
    
    Args:
        keyword: Search keyword.
        limit: Number of items to crawl.
        enable_download: Whether to download images.
        
    Returns:
        A string summary of the crawled items.
    """
    
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
    
    page = ChromiumPage()
    print(f"🚀 [Agent] 正在打开拼多多搜索页: {keyword}")
    page.get(url)
    
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
            title = title_ele.text if title_ele else "未知标题"
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
    
    return "\n".join(results_summary)

if __name__ == "__main__":
    # 测试代码
    print(crawl_pinduoduo("妈咪包", limit=1))
