from DrissionPage import ChromiumPage, ChromiumOptions
import time

def test_pdd_specs(url):
    co = ChromiumOptions()
    co.set_local_port(9222)
    page = ChromiumPage(co).new_tab(url)
    
    print(f"Navigated to: {url}")
    time.sleep(3)
    
    # 尝试展开规格
    expand_btn = page.ele('.PfNbVesQ')
    if expand_btn:
        print("Clicking expand button...")
        expand_btn.click()
        time.sleep(2)
    else:
        # 尝试点击“免拼购买”
        buy_btn = page.ele('免拼购买')
        if buy_btn:
            print("Clicking Buy button...")
            buy_btn.click()
            time.sleep(2)

    print("\n--- Specification Keys (.sku-specs-key) ---")
    keys = page.eles('.sku-specs-key')
    for i, k in enumerate(keys):
        print(f"{i}: {k.text}")

    print("\n--- Specification Values (.s1O5M5fO) ---")
    values = page.eles('.s1O5M5fO')
    for i, v in enumerate(values):
        print(f"{i}: {v.text}")

    print("\n--- Specification Names (.bIhLWVqm) ---")
    names = page.eles('.bIhLWVqm')
    for i, n in enumerate(names):
        print(f"{i}: {n.text}")

    # page.close()

if __name__ == "__main__":
    url = "https://mobile.pinduoduo.com/goods.html?goods_id=534143793648"
    test_pdd_specs(url)
