from DrissionPage import ChromiumPage
import csv
import time
import json
import pymysql

# 配置
target_url = 'https://solutions.shopee.cn/sellers/category-sharing-portal/#/portal?m=trending&p_s=20'
output_csv_path = '/Users/ning/code/DrissionPage/shopee_api_data_all_sites.csv'
MAX_PAGES = 1000 # 设置为一个较大的值，配合翻页自动停止逻辑，采集所有数据
SITES = ['TW', 'MY', 'TH', 'PH', 'SG', 'VN', 'BR', 'MX']

# 数据库配置 (请根据实际情况修改)
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = '' # 默认空密码，如果有密码请修改这里
DB_NAME = 'shopee_data'

def get_db_connection(use_db=True):
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME if use_db else None,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def init_db():
    try:
        # 1. 创建数据库
        conn = get_db_connection(use_db=False)
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.close()

        # 2. 创建表
        conn = get_db_connection(use_db=True)
        with conn.cursor() as cursor:
            # 创建选品表 (product_selection)
            # 注意：如果表已存在，不会重新创建，需要后续 ALTER 添加字段
            sql = """
            CREATE TABLE IF NOT EXISTS product_selection (
                id INT AUTO_INCREMENT PRIMARY KEY,
                site VARCHAR(10) COMMENT '站点',
                product_id VARCHAR(50) COMMENT '商品ID',
                image_url TEXT COMMENT '图片链接',
                seller_type VARCHAR(50) COMMENT '卖家类型',
                category TEXT COMMENT '品类',
                keyword TEXT COMMENT '关键词',
                description TEXT COMMENT '描述',
                price_min DECIMAL(10, 2) COMMENT '最低价',
                price_max DECIMAL(10, 2) COMMENT '最高价',
                recommendation TEXT COMMENT '推荐理由',
                source VARCHAR(50) DEFAULT 'Shopee站点趋势' COMMENT '选品来源',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                UNIQUE KEY unique_product (site, product_id)
            )
            """
            cursor.execute(sql)
            
            # 尝试添加 product_id 字段 (针对表已存在但没该字段的情况)
            try:
                cursor.execute("ALTER TABLE product_selection ADD COLUMN product_id VARCHAR(50) COMMENT '商品ID' AFTER site")
            except Exception:
                pass # 字段可能已存在
                
            # 尝试添加唯一索引 (针对表已存在但没该索引的情况)
            try:
                cursor.execute("CREATE UNIQUE INDEX unique_product ON product_selection (site, product_id)")
                print("成功创建 unique_product 索引")
            except Exception:
                pass # 索引可能已存在

        conn.commit()
        conn.close()
        print("数据库初始化成功，表 'product_selection' 已准备就绪")
    except Exception as e:
        print(f"数据库初始化失败: {e}")

def save_to_mysql(data_list):
    if not data_list:
        return
    
    conn = None
    try:
        conn = get_db_connection(use_db=True)
        with conn.cursor() as cursor:
            # 使用 INSERT ... ON DUPLICATE KEY UPDATE 实现“存在则更新，不存在则插入”
            # 根据唯一索引 (site, product_id) 判断冲突
            sql = """
            INSERT INTO product_selection 
            (site, product_id, image_url, seller_type, category, keyword, description, price_min, price_max, recommendation, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            image_url=VALUES(image_url),
            seller_type=VALUES(seller_type),
            category=VALUES(category),
            keyword=VALUES(keyword),
            description=VALUES(description),
            price_min=VALUES(price_min),
            price_max=VALUES(price_max),
            recommendation=VALUES(recommendation),
            source=VALUES(source)
            """
            values = []
            for item in data_list:
                # 处理价格，确保是数字或 None
                p_min = item.get('最低价')
                p_max = item.get('最高价')
                try:
                    p_min = float(p_min) if p_min else 0
                    p_max = float(p_max) if p_max else 0
                except:
                    p_min = 0
                    p_max = 0

                values.append((
                    item.get('站点'),
                    item.get('商品ID'),
                    item.get('图片链接'),
                    item.get('卖家类型'),
                    item.get('品类'),
                    item.get('关键词'),
                    item.get('描述'),
                    p_min,
                    p_max,
                    item.get('推荐理由'),
                    'Shopee站点趋势' # 选品来源
                ))
            
            cursor.executemany(sql, values)
        conn.commit()
        print(f"成功保存/更新 {len(data_list)} 条数据到 MySQL 表 product_selection")
    except Exception as e:
        print(f"保存到 MySQL 失败: {e}")
    finally:
        if conn:
            conn.close()

def process_packet(res, site, target_list):
    try:
        json_data = res.response.body
        if not isinstance(json_data, dict):
             try:
                json_data = json.loads(json_data)
             except:
                pass
        
        if isinstance(json_data, dict) and 'data' in json_data:
            inner_data = json_data['data']
            items = []
            total = 0
            if isinstance(inner_data, dict):
                items = inner_data.get('sku_list', [])
                total = inner_data.get('total', 0) # 获取总条数
            
            if items:
                print(f"在响应中找到 {len(items)} 条商品数据 (站点总计: {total})")
                batch_data = []
                for item in items:
                    # 获取商品ID (行ID)
                    product_id = str(item.get('itemid') or item.get('id') or item.get('sku_id') or '')
                    
                    row = {
                        '站点': site,
                        '商品ID': product_id,
                        '图片链接': item.get('original_image', ''),
                        '卖家类型': item.get('seller_type', ''),
                        '品类': f"{item.get('category_l1','') or ''} > {item.get('category_l2','') or ''} > {item.get('category_l3','') or ''}".strip(' >'),
                        '关键词': item.get('keyword', ''),
                        '描述': item.get('description', ''),
                        '最低价': str(item.get('price_l', '')),
                        '最高价': str(item.get('price_h', '')),
                        '推荐理由': item.get('recommendations', '')
                    }
                    target_list.append(row)
                    batch_data.append(row)
                
                # 立即保存本页数据到 MySQL
                save_to_mysql(batch_data)
                return len(items), total # 返回 (当前条数, 站点总条数)
            else:
                print(f"未在响应中找到 sku_list (总数: {total})")
                return 0, total
        else:
            print(f"响应不包含 data 字段。")
    except Exception as e:
        print(f"解析响应失败: {e}")
    return 0, 0

def collect_from_api():
    # 初始化数据库
    init_db()
    
    page = ChromiumPage()
    
    # 1. 启动监听
    page.listen.start('api/sku/get_sku') 
    
    # 访问基础页面
    base_url = 'https://solutions.shopee.cn/sellers/category-sharing-portal/#/portal?m=trending&p_s=20'
    print(f"正在访问：{base_url}")
    page.get(base_url)
    print("正在等待页面加载...")
    page.wait.ele_displayed('.el-table__row')
    
    all_data_list = []
    
    for site in SITES:
        print(f"\n========== 开始采集站点: {site} ==========")
        
        # 记录该站点已采集的总量
        site_collected_total = 0
        
        # 构造 URL
        site_url = f'https://solutions.shopee.cn/sellers/category-sharing-portal/#/portal?m=trending&s={site.lower()}&p=1&p_s=20&c1=all&s_t=all'
        
        # 尝试访问并采集第1页（带重试机制）
        first_page_success = False
        is_last_page = False
        for attempt in range(3):
            page.listen.clear()
            
            if attempt == 0:
                print(f"正在访问：{site_url}")
                page.get(site_url)
            else:
                print(f"第 {attempt+1} 次尝试获取 {site} 第 1 页...")
                page.refresh()
                
            try:
                res = page.listen.wait(timeout=20)
            except Exception as e:
                print(f"等待第 1 页数据包时发生异常: {e}")
                res = None
            
            if res:
                count, total = process_packet(res, site, all_data_list)
                if count > 0:
                    first_page_success = True
                    site_collected_total += count
                    # 如果 count < 20，说明这已经是最后一页了
                    if count < 20: 
                        is_last_page = True
                    # 如果 API 提供了总数，且我们已经采够了，也标记结束
                    elif total > 0 and site_collected_total >= total:
                        is_last_page = True
                    break
            else:
                print("等待第 1 页数据包超时")
        
        if not first_page_success:
            print(f"站点 {site} 第 1 页采集失败，跳过该站点后续页码")
            continue
            
        if is_last_page:
            print(f"站点 {site} 采集完毕 (共 {site_collected_total} 条)，移至下一个站点")
            continue

        # 采集后续页码
        for page_num in range(2, MAX_PAGES + 1):
            print(f"--- 正在采集 {site} 第 {page_num} 页 ---")
            
            next_btn = page.ele('.btn-next')
            if next_btn and not next_btn.attr('disabled'):
                next_btn.click(by_js=True)
                time.sleep(1)
            else:
                print("下一页按钮已禁用或未找到")
                break
            
            try:
                res = page.listen.wait(timeout=20)
            except Exception as e:
                print(f"等待第 {page_num} 页数据包时发生异常: {e}")
                res = None
                
            if res:
                count, total = process_packet(res, site, all_data_list)
                site_collected_total += count
                # 判定结束：条数不满20条，或者已达到总数
                if count < 20:
                    print(f"已达到 {site} 最后一页 (当前页: {count}条, 总计: {site_collected_total})")
                    break
                elif total > 0 and site_collected_total >= total:
                    print(f"已达到 {site} 预定总数 (已采: {site_collected_total}, 总计: {total})")
                    break
            else:
                print(f"等待第 {page_num} 页数据包超时，判定为已无更多数据，采集结束。")
                break

    # 保存
    if all_data_list:
        headers = all_data_list[0].keys()
        with open(output_csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(all_data_list)
        print(f"\n全部采集完成！共保存 {len(all_data_list)} 条数据。")
        print(f"文件位置：{output_csv_path}")
    else:
        print("未采集到数据或解析失败。")

if __name__ == '__main__':
    collect_from_api()
