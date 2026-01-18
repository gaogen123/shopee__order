# -*- coding: utf-8 -*-
from DrissionPage import Chromium, ChromiumOptions
import time

# 配置连接已打开的浏览器 (端口 9222)
co = ChromiumOptions().set_local_port(9222)
page = Chromium(co)
tab = page.latest_tab

print(f"当前页面: {tab.title}")

# 检查是否需要跳转到1688并搜索
if '妈妈包' not in tab.title:
    # 打开 1688
    tab.get('https://www.1688.com/')
    print("已跳转到1688,等待5秒...")
    time.sleep(5)
    
    # 定位搜索框 class=alisearch-input
    search_input = tab.ele('.ali-search-input')
    if search_input:
        # 如果表单已经有值 先把值删除再填
        search_input.clear()
        # 输入 妈妈包
        search_input.input('妈妈包')
    
        # 点击搜索按钮 class=input-button-text
        search_btn = tab.ele('.input-button-text')
        if search_btn:
            search_btn.click()
            print("已点击搜索按钮")
            time.sleep(5)  # 增加等待时间,确保搜索结果页面加载完成
            print(f"搜索后页面: {tab.title}")
else:
    print("已经在搜索结果页,跳过搜索步骤")



# 滚动以加载第一页所有商品
print("正在滚动第一页...")
for _ in range(10):
    tab.scroll.down(800)
    time.sleep(0.5)
tab.scroll.to_bottom()
time.sleep(1)

# 获取所有商品卡片元素（包含标题和链接）
# 用户指定 class 为 title-text
titles = tab.eles('.title-text')

print(f"找到 {len(titles)} 个商品标题:")

# 遍历每个商品，点击进入详情页
for i, title_ele in enumerate(titles):
    # 获取文本内容
    text = title_ele.text
    print(f"{i+1}. {text}")
    
    try:
        # 获取商品链接（通过父元素的 href 属性）
        # 通常标题的父元素 <a> 标签包含链接
        link_ele = title_ele.parent('tag:a')
        if link_ele:
            product_url = link_ele.attr('href')
            if product_url:
                print(f"  → 正在进入第 {i+1} 个商品详情页...")
                
                # 直接在当前标签页导航到详情页（不会打开新标签页）
                tab.get(product_url)
                time.sleep(5)  # 等待详情页加载
                
                print(f"  → 详情页标题: {tab.title}")
                
                # 在详情页可以进行其他操作，比如采集详情信息
                # ... 这里可以添加详情页的数据采集逻辑 ...
                
                # 等待5秒后再关闭详情页
                time.sleep(5)
                
                # 返回列表页
                tab.back()
                time.sleep(2)  # 等待列表页重新加载
                print(f"  → 已返回列表页")
                
                # 确保关闭所有多余的标签页，只保留当前标签页
                all_tabs = page.get_tabs()
                if len(all_tabs) > 1:
                    for extra_tab in all_tabs[1:]:
                        try:
                            extra_tab.close()
                        except:
                            pass
                    print(f"  → 已关闭 {len(all_tabs) - 1} 个多余标签页")
                
                # 重新滚动以确保页面元素可见
                if i < len(titles) - 1:  # 如果不是最后一个商品
                    tab.scroll.to_see(titles[i+1])
                    time.sleep(0.5)
            else:
                print(f"  ✗ 第 {i+1} 个商品没有找到链接")
        else:
            print(f"  ✗ 第 {i+1} 个商品没有找到父链接元素")
        
    except Exception as e:
        print(f"  ✗ 进入第 {i+1} 个商品详情页时出错: {e}")
        # 如果出错，尝试返回列表页
        try:
            tab.back()
            time.sleep(2)
        except:
            pass
        # 确保关闭所有多余的标签页
        try:
            all_tabs = page.get_tabs()
            if len(all_tabs) > 1:
                for extra_tab in all_tabs[1:]:
                    try:
                        extra_tab.close()
                    except:
                        pass
        except:
            pass

if len(titles) == 0:
    print("未找到任何 class 为 'title-text' 的元素。")

print("-" * 20)

# 定位到页码输入框
# class=input-page
input_page = tab.ele('.input-page')

if input_page:
    print("找到页码输入框")
    # 如果表单已经有值 先把值删除再填
    input_page.clear()
    # 输入 2
    input_page.input('2')
    print("已输入页码: 2")

    # 定位到跳转按钮并点击
    # class=paging-to-page-button
    jump_button = tab.ele('.paging-to-page-button')
    if jump_button:
        jump_button.click()
        print("已点击跳转按钮")

        # 等待页面加载
        time.sleep(3)
        
        print("正在滚动页面以加载更多数据...")
        # 慢慢滚动以触发懒加载
        for _ in range(10):
            tab.scroll.down(800)
            time.sleep(0.5)
        
        # 确保滚动到底部
        tab.scroll.to_bottom()
        time.sleep(1)

        print("-" * 20)
        print("跳转后重新采集:")

        # 再次获取所有标题元素
        titles_page2 = tab.eles('.title-text')
        print(f"找到 {len(titles_page2)} 个商品标题 (第2页):")

        # 遍历第二页每个商品，点击进入详情页
        for i, title_ele in enumerate(titles_page2):
            text = title_ele.text
            print(f"{i+1}. {text}")
            
            try:
                # 获取商品链接（通过父元素的 href 属性）
                link_ele = title_ele.parent('tag:a')
                if link_ele:
                    product_url = link_ele.attr('href')
                    if product_url:
                        print(f"  → 正在进入第 {i+1} 个商品详情页...")
                        
                        # 直接在当前标签页导航到详情页（不会打开新标签页）
                        tab.get(product_url)
                        time.sleep(5)  # 等待详情页加载
                        
                        print(f"  → 详情页标题: {tab.title}")
                        
                        # 在详情页可以进行其他操作，比如采集详情信息
                        # ... 这里可以添加详情页的数据采集逻辑 ...
                        
                        # 等待5秒后再关闭详情页
                        time.sleep(5)
                        
                        # 返回列表页
                        tab.back()
                        time.sleep(2)  # 等待列表页重新加载
                        print(f"  → 已返回列表页")
                        
                        # 确保关闭所有多余的标签页，只保留当前标签页
                        all_tabs = page.get_tabs()
                        if len(all_tabs) > 1:
                            for extra_tab in all_tabs[1:]:
                                try:
                                    extra_tab.close()
                                except:
                                    pass
                            print(f"  → 已关闭 {len(all_tabs) - 1} 个多余标签页")
                        
                        # 重新滚动以确保页面元素可见
                        if i < len(titles_page2) - 1:  # 如果不是最后一个商品
                            tab.scroll.to_see(titles_page2[i+1])
                            time.sleep(0.5)
                    else:
                        print(f"  ✗ 第 {i+1} 个商品没有找到链接")
                else:
                    print(f"  ✗ 第 {i+1} 个商品没有找到父链接元素")
                
            except Exception as e:
                print(f"  ✗ 进入第 {i+1} 个商品详情页时出错: {e}")
                # 如果出错，尝试返回列表页
                try:
                    tab.back()
                    time.sleep(2)
                except:
                    pass
                # 确保关闭所有多余的标签页
                try:
                    all_tabs = page.get_tabs()
                    if len(all_tabs) > 1:
                        for extra_tab in all_tabs[1:]:
                            try:
                                extra_tab.close()
                            except:
                                pass
                except:
                    pass

    else:
        print("未找到跳转按钮 (.paging-to-page-button)")
else:
    print("未找到页码输入框 (.input-page)")
