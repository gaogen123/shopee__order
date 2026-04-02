
import sys
import os
from pdd_agent_tools import crawl_pinduoduo_data

def test_crawl():
    print("开始测试拼多多采集 (集成 JSON 提取版)...")
    # 采集 1 个商品，启用下载
    # 注意：这需要本地 Chrome 开启 9222 端口调试模式
    # 如果浏览器未开启，会报错。
    try:
        for item in crawl_pinduoduo_data("手机壳", limit=1, enable_download=False):
            print("\n--- 采集结果 ---")
            print(f"标题: {item.get('title')}")
            print(f"价格: {item.get('price')}")
            print(f"变体数: {len(item.get('variations_detail', {}))}")
            
            print("\n--- 变体详情 (Variations) ---")
            for key, options in item.get('variations_detail', {}).items():
                print(f"  [{key}]: {len(options)} 个选项")
                for opt in options:
                    img_status = "有图" if opt.get('image') else "无图"
                    print(f"    - {opt['text']} ({img_status})")

            print("\n--- SKU 组合 (SKU Map) ---")
            if item.get('sku_map'):
                print(f"SKU Map 大小: {len(item.get('sku_map'))}")
                # 打印前 20 个组合作为示例，避免太多
                count = 0
                for key, val in item.get('sku_map', {}).items():
                    print(f"  [{key}] -> 价格: {val.get('price')}, 规格: {val.get('specs')}")
                    count += 1
                    if count >= 20:
                        print("  ... (更多组合省略)")
                        break
            else:
                print("  无 SKU Map")
            print("----------------\n")
    except Exception as e:
        print(f"测试出错 (可能是浏览器未连接): {e}")

if __name__ == "__main__":
    test_crawl()
