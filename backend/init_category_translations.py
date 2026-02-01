
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared import get_db_connection

TRANSLATIONS = {
    "Audio": "音频设备",
    "Automobiles": "汽车用品",
    "Baby & Kids Fashion": "童装",
    "Beauty": "美妆保养",
    "Books & Magazines": "书籍杂志",
    "Cameras & Drones": "相机与无人机",
    "Computers & Accessories": "电脑与配件",
    "Fashion Accessories": "时尚配饰",
    "Food & Beverages": "食品饮料",
    "Food Delivery": "食品外卖",
    "Gaming & Consoles": "电玩游戏",
    "Health": "医疗保健",
    "Hobbies & Collections": "兴趣收藏",
    "Home & Living": "家居生活",
    "Home Appliances": "家用电器",
    "Men Bags": "男生包包",
    "Men Clothes": "男装",
    "Men Shoes": "男鞋",
    "Mobile & Gadgets": "手机平板与周边",
    "Mom & Baby": "母婴用品",
    "Motorcycles": "机车配件",
    "Muslim Fashion": "穆斯林时尚",
    "Pets": "宠物用品",
    "Sports & Outdoors": "户外运动",
    "Sports & Outdoors Footwear": "运动鞋",
    "Stationery": "文具",
    "Tickets, Vouchers & Services": "票卷服务",
    "Travel & Luggage": "旅游出行",
    "Watches": "手表",
    "Women Bags": "女生包包",
    "Women Clothes": "女装",
    "Women Shoes": "女鞋",
    "Others": "其他"
}

def init_translations():
    conn = get_db_connection()
    c = conn.cursor()
    print("Creating category_translations table...")
    c.execute("""
    CREATE TABLE IF NOT EXISTS category_translations (
        original_name VARCHAR(255) PRIMARY KEY,
        cn_name VARCHAR(255) NOT NULL
    )
    """)
    
    print("Inserting translations...")
    for eng, cn in TRANSLATIONS.items():
        c.execute("""
        INSERT INTO category_translations (original_name, cn_name)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE cn_name = VALUES(cn_name)
        """, (eng, cn))
        
    conn.commit()
    conn.close()
    print("Done.")

if __name__ == "__main__":
    init_translations()
