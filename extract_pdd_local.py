
import re
import json
import sys

def extract_data(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # Try to find window.leo or window.rawData
    # PDD often uses window.rawData or window.leo
    
    # 1. Try window.leo
    leo_match = re.search(r'window\.leo\s*=\s*(\{.*?\});', content, re.DOTALL)
    if leo_match:
        print("Found window.leo")
        try:
            leo_data = json.loads(leo_match.group(1))
            # print(json.dumps(leo_data, indent=2, ensure_ascii=False))
            # Explore leo_data for goods details
        except:
            print("Failed to parse window.leo JSON")

    # 2. Try window.rawData (common in PDD)
    raw_match = re.search(r'window\.rawData\s*=\s*(\{.*?\});', content, re.DOTALL)
    if raw_match:
        print("Found window.rawData")
        try:
            raw_data = json.loads(raw_match.group(1))
            # print(json.dumps(raw_data, indent=2, ensure_ascii=False))
            
            # Extract SKU data from rawData
            if 'store' in raw_data and 'initDataObj' in raw_data['store']:
                init_data = raw_data['store']['initDataObj']
                if 'goods' in init_data:
                    goods = init_data['goods']
                    print(f"Title: {goods.get('goodsName')}")
                    
                    if 'skus' in goods:
                        print("\nVariations (SKUs):")
                        for sku in goods['skus']:
                            specs = [spec['spec_value'] for spec in sku.get('specs', [])]
                            price = sku.get('groupPrice', sku.get('normalPrice'))
                            thumb_url = sku.get('thumbUrl')
                            print(f"  Specs: {specs}")
                            print(f"  Price: {price}")
                            print(f"  Image: {thumb_url}")
                            print("-" * 20)
                    else:
                        print("No 'skus' found in goods data.")
                else:
                     print("No 'goods' found in initDataObj.")
            else:
                print("Structure of rawData not as expected (store.initDataObj).")
                
        except json.JSONDecodeError as e:
            print(f"Failed to parse window.rawData JSON: {e}")
    else:
        print("window.rawData not found.")

    # 3. Fallback: Parse HTML with BeautifulSoup if JSON extraction fails or is incomplete
    # (Since I cannot install bs4 easily if not present, I will rely on regex for HTML parsing if needed, 
    # but the user environment likely has it or I can use simple string search)
    
    # Let's try to find the price and specs from the HTML text we saw earlier
    print("\n--- HTML Parsing (Fallback) ---")
    
    # Price
    price_match = re.search(r'class="ujEqGzEB">.*?(\d+\.?\d*).*?</div>', content, re.DOTALL)
    if price_match:
        # This regex is a bit loose, let's refine based on the snippet:
        # <div class="ujEqGzEB">¥<span style="font-size: 0.19rem;">29</span><span style="font-size: 0.16rem;">.8</span></div>
        # We can just extract the text content of that div
        pass # It's hard to parse complex HTML with regex reliably.

if __name__ == "__main__":
    extract_data("/Users/ning/Downloads/拼多多.html")
