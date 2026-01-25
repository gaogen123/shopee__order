import sys
import os
import json

# 添加路径以导入模块
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from pdd_agent_tools import crawl_pinduoduo_data

def test_variation_images():
    keyword = "鞋子"
    print(f"🚀 开始测试变体图片抓取: {keyword}")
    
    # 采集数据
    items = crawl_pinduoduo_data(keyword, limit=3, enable_download=False)
    
    if items:
       for item in items:
        print(f"\n✅ 商品: {item['title']}")
        print(f"🔗 链接: {item.get('url', '无链接')}")
        variations = item.get('variations_detail', {})
        
        all_images = []
        for group, opts in variations.items():
            print(f"  📦 规格组: {group}")
            for opt in opts:
                img_url = opt.get('image', '无')
                print(f"    🔹 {opt['text']}: {opt['price']} | 图片: {img_url}")
                if img_url != '无':
                    all_images.append(img_url)
        
        # 检查重复
        unique_images = set(all_images)
        print(f"\n📊 图片统计: 总数 {len(all_images)}, 唯一数 {len(unique_images)}")
        if len(all_images) != len(unique_images):
            print("⚠️ 警告: 存在重复的变体图片！")
            from collections import Counter
            duplicates = [item for item, count in Counter(all_images).items() if count > 1]
            for dup in duplicates:
                print(f"  重复图片: {dup}")
        else:
            print("✅ 所有变体图片均不相同。")

if __name__ == "__main__":
    test_variation_images()
