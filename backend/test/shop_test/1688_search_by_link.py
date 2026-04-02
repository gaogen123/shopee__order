from DrissionPage import Chromium, ChromiumOptions
import time
import os
import urllib.request
import json
import re

def search_1688_by_image_link_dedicated(img_url):
    """
    全自动搜款最终版：使用 1688 专用图搜页，并集成 API 并行采集。
    """
    print(f"\n[开始] 以图搜款与数据采集流程")
    print(f"目标链接: {img_url}")
    
    # 1. 准备本地文件
    local_img_path = os.path.abspath("temp_visual_search.jpg")
    try:
        if os.path.exists(local_img_path):
            os.remove(local_img_path)
        
        opener = urllib.request.build_opener()
        opener.addheaders = [('User-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')]
        urllib.request.install_opener(opener)
        urllib.request.urlretrieve(img_url, local_img_path)
        print(f"1. 图片已就绪: {local_img_path}")
    except Exception as e:
        print(f"   准备图片失败: {e}")
        return

    # 2. 启动浏览器
    co = ChromiumOptions()
    try:
        co.set_local_port(9222)
        browser = Chromium(co)
    except:
        browser = Chromium()
        
    tab = browser.latest_tab
    
    # 提前启动全局监听，防止错过第一个包
    tab.listen.start()
    
    try:
        search_engine_url = "https://pages-fast.1688.com/wow/cbu/srch_rec/image_search/youyuan/index.html"
        print(f"2. 打开图搜引擎...")
        tab.get(search_engine_url)
        tab.wait.doc_loaded()
        time.sleep(2)

        # 3. 注入图片
        upload_input = tab.ele('#img-search-upload') or \
                       tab.ele('.image-file-reader-wrapper') or \
                       tab.ele('tag:input@type=file')
        
        if upload_input:
            print("3. 正在上传图片检索...")
            upload_input.input(local_img_path)
            
            # 触发事件
            tab.run_js("""
                var el = arguments[0];
                ['change', 'input', 'blur'].forEach(ev => el.dispatchEvent(new Event(ev, { bubbles: true })));
            """, upload_input)
            
            # 监测跳转
            found_success = False
            result_tab = None
            start_time = time.time()
            
            while time.time() - start_time < 120:
                # 补偿方案 A: 尝试在全局或者 input 上敲回车
                tab.actions.key_down('ENTER').key_up('ENTER')
                
                # 补偿方案 B: 精准打击用户截图中的按钮
                # 用户截图显示: <div class="search-btn" data-tracker="pasteImagePreview">搜索图片</div>
                # 这是一个非常明确的目标
                
                confirm_btn = tab.ele('.search-btn', timeout=0.2) or \
                              tab.ele('@data-tracker=pasteImagePreview', timeout=0.2) or \
                              tab.ele('text=搜索图片', timeout=0.2)
                              
                if confirm_btn and confirm_btn.states.is_displayed:
                    print(f"\n[操作] 发现确认按钮 (class={confirm_btn.attr('class')})，正在点击...")
                    # 优先使用 JS 点击，因为有时候元素可能有覆盖遮挡
                    try:
                        tab.run_js("arguments[0].click();", confirm_btn)
                    except:
                        pass
                    time.sleep(1)
                
             
                
                time.sleep(0.5) # 缩短检测间隔，提高响应速度
                print(".", end="", flush=True)

                # 检查所有打开的标签页是否成功进入结果页
                # 必须看到从 s.1688.com 返回的结果，或者在 youyuan 页面看到商品列表
                for t in browser.get_tabs():
                    u = t.url
                    # 1. 如果跳转到了标准搜索结果页
                    if "s.1688.com/selloffer" in u:
                        print(f"\n[大功告成] 已跳转至标准搜索结果页！")
                        result_tab = t
                        found_success = True
                        break
                    
                    # 2. 如果停留在 youyuan 页面，必须确保看到了商品列表
                    if "youyuan" in u:
                        # 检查是否有商品元素
                        if t.ele('.sm-offer-item') or t.ele('.common-offer-card') or t.ele('.offer-list-item') or t.ele('.water-container'):
                            print(f"\n[大功告成] 当前页面 ({t.title}) 已加载商品列表！")
                            result_tab = t
                            found_success = True
                            break
                            
                if found_success: break

            if found_success:
                # 4. 开始采集逻辑
                print("\n\n4. 正在快速滚动以获取 API 数据...")
                
                # [关键修正] 不要重新 start，否则会清空之前捕获的包 (如果是同一个标签页)
                # 如果是新标签页，尝试开启监听后续请求
                if result_tab != tab:
                     result_tab.listen.start()
                
                # 优化为 6 次大步幅滚动，减少等待时间
                for i in range(6):
                    result_tab.scroll.down(4000) # 加大滚动距离
                    time.sleep(1) # 缩短等待
                    print(f"   进度: {i+1}/6...", end="\r")
                print("")
                
                # 停止监听并解析
                print("5. 正在提取并清洗商品数据...")
                all_items = []
                seen_ids = set()
                
                # ---------------------------------------------------------
                # [修正方案] 优先使用 DOM 抓取，确保“所见即所得”
                # 用户反馈 JS 数据不一致，说明页面可能动态渲染了通过 JS 变量拿不到的内容
                # ---------------------------------------------------------
                print("5. 正在执行 DOM 元素精准抓取 (所见即所得)...")
                
                dom_items = []
                # 适配 s.1688.com 和 youyuan 两种页面的常见卡片选择器
                card_selectors = [
                    '.sm-offer-item',           # s.1688.com 标准卡片
                    '.common-offer-card',       # 通用卡片
                    '.offer-list-item',         # 列表项
                    'div[data-offer-id]',       # 带有 offer-id 属性的 div
                    '.pin-offer-item'           # 瀑布流卡片
                ]
                
                found_cards = []
                for sel in card_selectors:
                    found_cards = result_tab.eles(sel)
                    if found_cards:
                        print(f"   命中选择器 [{sel}]，发现 {len(found_cards)} 个商品")
                        break
                
                for card in found_cards:
                    try:
                        # 1. 提取 ID
                        oid = card.attr('data-offer-id') or card.attr('id')
                        # 有些 ID 是 offer-12345 格式，需要清洗
                        if oid:
                            oid = re.sub(r'\D', '', oid)
                        
                        # 2. 提取标题 (尝试多个类名)
                        title_ele = card.ele('.title') or \
                                    card.ele('.title-entry') or \
                                    card.ele('.offer-title') or \
                                    card.ele('tag:a@@class:title') or \
                                    card.ele('.desc') 
                        title = title_ele.text.strip() if title_ele else "无标题"
                        
                        # 3. 提取价格
                        price_ele = card.ele('.price') or \
                                    card.ele('.price-num') or \
                                    card.ele('.identity-price') or \
                                    card.ele('.value')
                        price = price_ele.text.strip() if price_ele else "0"
                        
                        # 4. 提取图片
                        img_ele = card.ele('.img') or card.ele('tag:img')
                        img = img_ele.attr('src') if img_ele else ""
                        
                        # 5. 提取链接
                        link_ele = card.ele('tag:a')
                        link = link_ele.attr('href') if link_ele else ""
                        if not oid and link:
                            # 从链接提取 ID
                            match = re.search(r'offer/(\d+)\.html', link)
                            if match:
                                oid = match.group(1)
                        
                        if oid and title:
                            dom_items.append({
                                "id": oid,
                                "title": title,
                                "price": price,
                                "image": img,
                                "link": link
                            })
                    except:
                        continue
                
                # 如果 DOM 抓到了数据，优先使用 DOM 数据
                if dom_items:
                    print(f"   DOM 抓取成功: {len(dom_items)} 个")
                    all_items = dom_items
                else:
                    print("   DOM 抓取为空，尝试 fallback 到 JS/API 数据...")
                    try:
                        js_data = result_tab.run_js('return window.data || window.__INIT_DATA;')
                        if js_data:
                            # ... (复用之前的 JS 提取代码) ...
                            def harvest_js(data):
                                if isinstance(data, dict):
                                    if ('offerId' in data or 'id' in data) and \
                                       ('title' in data or 'subject' in data):
                                        oid = str(data.get('offerId') or data.get('id'))
                                        if oid.isdigit() and oid not in seen_ids:
                                            all_items.append({
                                                "id": oid,
                                                "title": data.get('title') or data.get('subject'),
                                                "price": data.get('priceInfo', {}).get('price') or data.get('price'),
                                                "image": data.get('offerPicUrl') or data.get('imgUrl'),
                                                "link": data.get('linkUrl') or f"https://detail.1688.com/offer/{oid}.html"
                                            })
                                            seen_ids.add(oid)
                                    for k, v in data.items():
                                        harvest_js(v)
                                elif isinstance(data, list):
                                    for item in data:
                                        harvest_js(item)
                            harvest_js(js_data)
                            
                            if all_items:
                                print(f"   JS 数据提取成功: {len(all_items)} 个")
                                print(f"   [调试] 第一条数据标题: {all_items[0]['title']}")
                    except Exception as e:
                        print(f"   JS 提取失败: {e}")

                # 保存
                output_file = "/Users/ning/code/shopee__order-1/backend/test/shop_test/1688_search_integrated_results.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(all_items, f, ensure_ascii=False, indent=2)
                
                print(f"\n[最终结论]")
                print(f"- 采集货源总数: {len(all_items)} 个")
                print(f"- 数据来源: {'DOM (所见即所得)' if dom_items else 'JS/API (后台数据)'}")
                print(f"- 结果保存路径: {output_file}")
                
            else:
                print("\n[失败] 无法定位结果页。")
        else:
            print("错误: 未能发现上传组件。")

    except Exception as e:
        print(f"\n[异常] {e}")
    finally:
        if 'tab' in locals() and tab:
            tab.listen.stop()
        print("\n流程结束。")

if __name__ == "__main__":
    # 指定图片链接
    source_image = "http://pfms.uss.shopee.cn/api/v4/03478754/sharing-portal-prod/image/293845/sku-34c8f9d7.jpeg"
    search_1688_by_image_link_dedicated(source_image)
