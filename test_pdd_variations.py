import sys
import os
import time
import json
from DrissionPage import ChromiumPage, ChromiumOptions

# 添加路径以导入模块
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

def test_specific_url(url):
    co = ChromiumOptions()
    co.set_local_port(9222)
    browser = ChromiumPage(co)
    page = browser.new_tab(url)
    
    print(f"🚀 [测试] 正在分析详情页: {url}")
    time.sleep(3)
    
    # 3. 规格展开
    try:
        expand_btn = page.ele('.PfNbVesQ')
        if expand_btn:
            print("  👆 点击规格展开按钮 (.PfNbVesQ)...")
            expand_btn.click()
            time.sleep(2)
        else:
            buy_btn = page.ele('免拼购买')
            if buy_btn:
                print("  👆 点击免拼购买按钮...")
                buy_btn.click()
                time.sleep(2)
    except:
        pass

    # 4. 采集变体
    print("  🎨 [变体]: 正在尝试提取所有选项...")
    variations = {} 
    
    # 查找所有规格组名
    spec_groups = page.eles('.sku-specs-key')
    if not spec_groups:
        spec_groups = page.eles('.bIhLWVqm')
        
    if spec_groups:
        print(f"    🔎 找到 {len(spec_groups)} 个规格组")
        for group in spec_groups:
            group_name = group.text.strip().replace(':', '').replace('：', '')
            if not group_name: continue
            
            # 找到该规格组下的选项容器 (.s1O5M5fO)
            container = group.parent().ele('.s1O5M5fO')
            if not container:
                container = group.parent().parent().ele('.s1O5M5fO')
            
            if container:
                opts = container.children()
                print(f"    📦 规格组 [{group_name}] 包含 {len(opts)} 个选项 (.s1O5M5fO 容器内)")
                variations[group_name] = []
                for opt in opts:
                    opt_data = {"text": "", "image": "", "price": ""}
                    raw_text = opt.text.strip()
                    if not raw_text: continue
                    
                    lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
                    exclude_keywords = ["即将卖完", "已售罄", "缺货", "最后", "件", "库存", "件起批"]
                    valid_lines = [l for l in lines if not any(k in l for k in exclude_keywords) and not l.startswith('¥') and not l.startswith('￥') and not l.isdigit()]
                    
                    text = valid_lines[0] if valid_lines else raw_text
                    opt_data["text"] = text.split('\n')[0].strip()
                    
                    try:
                        opt.click()
                        time.sleep(0.5)
                        price_ele = page.ele('.ujEqGzEB', timeout=1)
                        if price_ele:
                            opt_data["price"] = price_ele.text.strip()
                    except:
                        pass
                    
                    variations[group_name].append(opt_data)
                    print(f"      ✅ {group_name}: {opt_data['text']} -> {opt_data['price']}")
    
    print("\n📊 采集结果汇总:")
    print(json.dumps(variations, ensure_ascii=False, indent=2))
    
    page.close()

if __name__ == "__main__":
    url = "https://mobile.pinduoduo.com/goods.html?goods_id=534143793648"
    test_specific_url(url)
