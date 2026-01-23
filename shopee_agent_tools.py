from DrissionPage import ChromiumPage
import time
import urllib.parse
import os
import requests
import shutil

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
