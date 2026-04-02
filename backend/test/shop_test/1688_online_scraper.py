# -*- coding: utf-8 -*-
from DrissionPage import Chromium, ChromiumOptions
import time
import json
import os

def scrape_1688_online(url):
    print(f"\n[开始] 1688 在线采集流程")
    print(f"目标 URL: {url}")
    
    co = ChromiumOptions()
    co.set_local_port(9222)
    try:
        browser = Chromium(co)
    except:
        print("尝试启动新浏览器实例...")
        browser = Chromium()
        
    tab = browser.latest_tab
    
    # 导航到 URL
    if url not in tab.url:
        print("正在跳转到目标页面...")
        tab.get(url)
        tab.wait.doc_loaded()
        time.sleep(3)

    # 1. 模拟滚动加载更多商品
    print("正在模拟滚动以加载更多内容...")
    # 增加滚动次数以深度抓取
    for i in range(8):
        tab.scroll.down(2000)
        time.sleep(1)
        print(f"   已滚动 {i+1} 次...")

    # 2. 提取商品信息
    print("正在提取商品信息...")
    
    # 查找所有标题元素作为起点
    title_eles = tab.eles('tag:div@@class:titleText')
    print(f"检测到 {len(title_eles)} 个商品候选元素。")
    
    results = []
    seen_titles = set()
    skip_stats = {"duplicate": 0, "no_price": 0, "invalid": 0}
    
    for ele in title_eles:
        try:
            title = ele.text.strip()
            if not title or len(title) < 5:
                skip_stats["invalid"] += 1
                continue
            
            if title in seen_titles:
                skip_stats["duplicate"] += 1
                continue
                
            # 根据 trace 结果，向上寻找包含价格的父级容器
            container = ele
            found_price = False
            price = ""
            img_url = ""
            
            # 向上遍历父级寻找价格和图片
            for _ in range(6):
                container = container.parent()
                if not container: break
                
                # 寻找价格符号 ¥
                yen = container.ele('text:¥', timeout=0.1)
                if yen:
                    price_text = yen.parent().text
                    import re
                    price_match = re.search(r'¥\s*([\d\.]+)', price_text)
                    if price_match:
                        price = price_match.group(1)
                        found_price = True
                
                # 寻找商品图片
                if not img_url:
                    img = container.ele('tag:img', timeout=0.1)
                    if img:
                        img_url = img.attr('src')
                        
                if found_price and img_url:
                    break
            
            if title and price:
                results.append({
                    "title": title,
                    "price": price,
                    "image": img_url
                })
                seen_titles.add(title)
            else:
                skip_stats["no_price"] += 1
                
        except Exception:
            continue
            
    print(f"\n[数据统计与分析]：")
    print(f"- 原始提取总数: {len(title_eles)}")
    print(f"- 重复标题过滤: {skip_stats['duplicate']} (1688搜索结果中常有重复)")
    print(f"- 无效标题过滤: {skip_stats['invalid']}")
    print(f"- 未能解析价格: {skip_stats['no_price']} (可能是广告或占位符)")
    print(f"- 最终采集成功: {len(results)}")
    
    # 预览结果
    if results:
        print("-" * 60)
        for i, item in enumerate(results[:5]):
            print(f"[{i+1}] ¥{item['price']} | {item['title'][:30]}...")
        print("-" * 60)
        
        # 保存结果
        output_file = "/Users/ning/code/shopee__order-1/backend/test/shop_test/1688_online_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"完整数据已保存到: {output_file}")
    else:
        print("[错误] 未能成功解析商品，请检查页面是否被验证码拦截。")

if __name__ == "__main__":
    url = "https://pages-fast.1688.com/wow/cbu/srch_rec/image_search/youyuan/index.html?tab=imageSearch&imageId=1247408678672151714&imageIdList=1247408678672151714&spm=a26352.b28411319/2508.imagesearch.upload"
    scrape_1688_online(url)
