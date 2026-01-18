# -*- coding: utf-8 -*-
from DrissionPage import Chromium, ChromiumOptions
import time

# 配置连接已打开的浏览器 (端口 9222)
co = ChromiumOptions().set_local_port(9222)
page = Chromium(co)
tab = page.latest_tab

print(f"当前页面: {tab.title}")

# 1. 打开1688首页 (用户提示搜索框已存在，跳过导航)
print("正在打开 1688 首页...")
tab.get('https://www.1688.com/')

# 2. 搜索 '妈妈包'
# 定位搜索框 (尝试常见ID和Class)
search_input = tab.ele('#alisearch-keywords')
if not search_input:
    search_input = tab.ele('.alisearch-keywords')

if search_input:
    # 如果表单已经有值 先把值删除再填
    search_input.clear()
    search_input.input('妈妈包')
    print("已输入关键词: 妈妈包")
    
    # 点击搜索按钮
    search_btn = tab.ele('.alisearch-submit')
    if search_btn:
        search_btn.click()
        print("已点击搜索按钮")
    else:
        search_input.input('\n')
        print("已发送回车键搜索")
    
    # 等待新页面加载
    # 搜索通常会跳转或打开新标签
    time.sleep(2)
    tab = page.latest_tab
    tab.wait.doc_loaded()
    print(f"搜索后页面: {tab.title}")
else:
    print("未找到搜索框，跳过搜索步骤")

# 获取所有商品图片容器
# 注意：这里假设页面已经加载了商品列表
product_wrappers = tab.eles('.ad-offer-img-wrapper')
print(f"找到 {len(product_wrappers)} 个商品")

# 遍历前3个商品
for i in range(min(3, len(product_wrappers))):
    print(f"\n=== 正在进入第 {i+1} 个商品详情 ===")
    
    # 重新获取元素防止stale
    # 虽然列表页没刷新，但为了稳健，我们重新获取列表并通过索引访问
    product_wrappers = tab.eles('.ad-offer-img-wrapper')
    if i >= len(product_wrappers):
        print("索引超出范围，停止")
        break
        
    wrapper = product_wrappers[i]
    
    # 点击进入详情
    # 通常电商网站点击商品会打开新标签页
    wrapper.click()
    
    # 等待新标签页出现
    # 逻辑：检查标签页数量是否增加
    if page.tabs_count > 1:
        new_tab = page.latest_tab
        print("检测到新标签页，正在加载...")
        # 等待页面加载完成
        new_tab.wait.doc_loaded()
        print(f"详情页标题: {new_tab.title}")
        
        # 在这里可以添加提取详情页数据的逻辑
        
        time.sleep(2) # 停留一下以便观察
        
        # 关闭详情页，切回列表页
        print("关闭详情页")
        new_tab.close()
    else:
        # 如果是在当前页跳转（不太常见，但处理一下）
        print("在当前页跳转，正在加载...")
        tab.wait.load_complete()
        print(f"详情页标题: {tab.title}")
        time.sleep(2)
        # 后退回列表页
        print("后退回列表页")
        tab.back()
        tab.wait.load_complete()

print("\n完成前3个商品的详情页访问")
