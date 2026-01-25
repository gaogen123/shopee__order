import sys
import os
import time

# 添加路径以导入模块
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
backend_dir = os.path.join(current_dir, "backend")
sys.path.append(backend_dir)
shop_test_dir = os.path.join(backend_dir, "test", "shop_test")
sys.path.append(shop_test_dir)

from pdd_agent_tools import crawl_pinduoduo_data
from shopee_agent_tools import publish_to_shopee_global

def main():
    keyword = "衣服"
    limit = 3 # 默认采集3个，除非用户修改
    
    # 使用生成器流式处理：采集一个 -> 发布一个
    for item in crawl_pinduoduo_data(keyword, limit=limit, enable_download=True):
        print(f"  🔗 原商品链接: {item.get('url', '未知')}")
        
        # 调用 Shopee 发布工具
        publish_to_shopee_global(item)

if __name__ == "__main__":
    main()
