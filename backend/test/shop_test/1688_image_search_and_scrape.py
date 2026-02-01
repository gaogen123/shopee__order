# -*- coding: utf-8 -*-
from DrissionPage import Chromium, ChromiumOptions
import time
import os
import urllib.request
import json
import re

def content_search_and_scrape(image_source):
    """
    1688 以图搜款并采集数据 (DOM/Regex 混合解析版)
    相比纯 API 监听，这种方式更抗干扰，不易卡死。
    """
    print(f"\n[开始] 1688 以图搜款流程 (DOM/Regex)", flush=True)
    print(f"输入源: {image_source}", flush=True)
    
    # 1. 准备图片路径
    local_img_path = ""
    if image_source.startswith("http"):
        local_img_path = os.path.abspath("temp_search_image.jpg")
        try:
            print(f"正在下载图片...", flush=True)
            if os.path.exists(local_img_path):
                os.remove(local_img_path)
            
            opener = urllib.request.build_opener()
            opener.addheaders = [('User-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')]
            urllib.request.install_opener(opener)
            urllib.request.urlretrieve(image_source, local_img_path)
            print(f"图片已下载: {local_img_path}", flush=True)
        except Exception as e:
            print(f"[错误] 图片下载失败: {e}", flush=True)
            return
    else:
        if os.path.exists(image_source):
            local_img_path = os.path.abspath(image_source)
        else:
            print(f"[错误] 本地图片不存在: {image_source}", flush=True)
            return

    # 2. 启动/连接浏览器
    co = ChromiumOptions()
    co.set_argument('--no-sandbox')
    try:
        co.set_local_port(9222)
        browser = Chromium(co)
    except:
        print("未检测到调试端口，尝试启动新浏览器...", flush=True)
        browser = Chromium()
        
    tab = browser.latest_tab
    
    try:
        # 3. 打开图搜页面
        search_engine_url = "https://pages-fast.1688.com/wow/cbu/srch_rec/image_search/youyuan/index.html"
        print(f"打开搜图引擎: {search_engine_url}", flush=True)
        if search_engine_url not in tab.url:
            tab.get(search_engine_url)
            tab.wait.doc_loaded()
            time.sleep(2)
        else:
            tab.refresh() # 强制刷新
            tab.wait.doc_loaded()
            time.sleep(2)
        
        # 4. 上传图片
        # 策略更新：使用 set.upload_files + 点击触发，模拟真实用户行为
        # 1688 的上传按钮通常是一个包裹了 input 的很多层的 div
        
        # 1688 的上传按钮通常是一个包裹了 input 的很多层的 div
        click_target = tab.ele('.image-file-reader-wrapper')
        if not click_target:
            upl_input = tab.ele('#img-search-upload')
            if upl_input:
                click_target = upl_input.parent()
        
        if not click_target:
            click_target = tab.ele('tag:div@class=click-upload-box')
                       
        if click_target:
            print("找到上传按钮，准备点击上传...", flush=True)
            
            # 预设要上传的文件
            tab.set.upload_files(local_img_path)
            
            # 点击触发文件选择框（DrissionPage 会自动填入预设文件）
            click_target.click()
            
            # 等待上传完成的简单延时
            try:
                tab.wait.upload_paths_inputted()
                print("图片路径已填入...", flush=True)
            except:
                print("警告：未检测到自动填入，尝试强制回退到 input 赋值模式...", flush=True)
                inp = tab.ele('tag:input@type=file')
                if inp: inp.input(local_img_path)

            print("正在上传并等待结果渲染...", flush=True)
            
            # 6. [新增] 显式点击搜索按钮
            time.sleep(1)
            search_btn = tab.ele('.search-btn') or tab.ele('text=搜索') or tab.ele('button[class*="search"]')
            if search_btn:
                print("点击搜索按钮...", flush=True)
                search_btn.click()
            else:
                print("未找到显式的搜索按钮，假设会自动触发...", flush=True)
            
            # 5. 循环等待并解析 HTML
            start_time = time.time()
            extracted_items = []
            
            while time.time() - start_time < 30:
                elapsed = int(time.time() - start_time)
                if elapsed % 2 == 0:
                    print(f"   [等待中] {elapsed}s... Cur URL: {tab.url}", flush=True)
                
                # 检查验证码
                if tab.ele('.nc-container', timeout=0.1) or tab.ele('text=向右滑动', timeout=0.1) or tab.ele('text=验证', timeout=0.1):
                    print("\n[警告] 检测到验证码/滑块！请手动在浏览器中完成验证！", flush=True)
                    time.sleep(2)
                    continue

                # 检查是否 URL 发生了变化（如果是跳转式搜图）
                # 或者检查 DOM
                
                html_content = tab.html
                items = parse_html_content(html_content)
                
                if len(items) > 0:
                     print(f"\n[成功] 从页面中提取到 {len(items)} 条数据！")
                     extracted_items = items
                     break
                
                time.sleep(1)
                
            # 6. 数据归档
            if extracted_items:
                output_file = "/Users/ning/code/shopee__order-1/backend/test/shop_test/1688_image_search_result.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(extracted_items, f, ensure_ascii=False, indent=2)
                print(f"结果已保存: {output_file}", flush=True)
            else:
                print("\n[失败] 超时未获取到商品数据。", flush=True)
                # 保存一下当前 HTML 供调试
                debug_html = "/Users/ning/code/shopee__order-1/backend/test/shop_test/debug_last_page.html"
                with open(debug_html, 'w', encoding='utf-8') as f:
                    f.write(tab.html)
                print(f"已保存当前页面 HTML 到 {debug_html} 供分析。")

        else:
            print("[错误] 未找到上传控件。", flush=True)
            
    except Exception as e:
        print(f"[异常] {e}", flush=True)

def parse_html_content(html_content):
    """
    使用正则提取商品数据，逻辑源自 parse_local_1688.py
    """
    import re
    
    # 关键标记：searchOfferWrapper
    # 如果页面还没有渲染出这个类，说明还在加载
    if 'searchOfferWrapper' not in html_content:
        return []

    cards = html_content.split('class="searchOfferWrapper')
    products = []
    
    # 跳过 split 后的第一段（因为它在第一个 wrapper 之前）
    for card in cards[1:]: 
        try:
            # 1. Offer ID
            # 优先匹配 regex
            id_match = re.search(r'offerId&quot;:&quot;(\d+)&quot;', card)
            offer_id = id_match.group(1) if id_match else None
            
            if not offer_id:
                # Fallback: data-renderkey
                id_match = re.search(r'data-renderkey="[^"]+_(\d+)"', card)
                offer_id = id_match.group(1) if id_match else None
            
            # 如果依然拿不到 ID，可能是无关片段，跳过
            if not offer_id:
                continue

            # 2. Title
            # 尝试匹配 class="titleText..."><div>TITLE</div>
            title_match = re.search(r'class="titleText[^"]+"><div>([^<]+)</div>', card)
            title = title_match.group(1) if title_match else ""
            
            if not title:
                # Fallback: title="..." 
                # 排除 "点此" "旺旺"
                t_match = re.findall(r'title="([^"]+)"', card)
                valid_dt = [t for t in t_match if "点此" not in t and "旺旺" not in t and len(t)>5]
                if valid_dt:
                    title = valid_dt[0]
                
            # 3. Price
            # 尝试匹配 class="textMain..."> 10 </div>
            price_match = re.search(r'class="textMain[^"]+">\s*([\d\.]+)\s*</div>', card)
            price = price_match.group(1) if price_match else ""
            
            if not price:
                 # Fallback: price-integer
                 pm = re.search(r'price-integer[^>]*>(\d+)', card)
                 if pm:
                     price = pm.group(1)
                     dm = re.search(r'price-decimal[^>]*>(\.\d+)', card)
                     if dm: price += dm.group(1)
                    
            # 4. Image
            # 匹配 mainImg
            img_match = re.search(r'<img[^>]+class="mainImg[^"]+"[^>]+src="([^"]+)"', card)
            img_url = img_match.group(1) if img_match else ""
            
            if not img_url:
                # Fallback generic img
                im_m = re.search(r'<img[^>]+src="([^"]+)"', card)
                if im_m:
                    img_url = im_m.group(1)

            products.append({
                "id": offer_id,
                "title": title,
                "price": price,
                "img": img_url
            })
            
        except Exception:
            pass
            
    return products

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        image_source = sys.argv[1]
    else:
        image_source = "/Users/ning/code/shopee__order-1/backend/test/shop_test/test_search_image.jpg"
    
    content_search_and_scrape(image_source)
