from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from shared import get_db_connection
from pydantic import BaseModel
import math
import os
import requests
import json

# 配置 API 路由
router = APIRouter()

# -----------------------------------------------------------------------------
# 请求模型定义
# -----------------------------------------------------------------------------

class FavoriteRequest(BaseModel):
    """
    收藏/取消收藏请求体
    product_id: 商品 ID
    is_favorite: 目标状态 (True 为收藏, False 为取消收藏)
    """
    product_id: int
    is_favorite: bool

class TranslateRequest(BaseModel):
    """
    翻译请求体
    text: 需要翻译的原始文本
    """
    text: str

class TranslationItem(BaseModel):
    id: str
    text: str
    field: str # 'description' or 'keywords'

class BatchTranslateRequest(BaseModel):
    items: List[TranslationItem]

# -----------------------------------------------------------------------------
# API 接口实现
# -----------------------------------------------------------------------------

@router.post("/api/selection/favorite")
async def toggle_favorite(req: FavoriteRequest):
    """
    切换商品的收藏状态
    如果 is_favorite 为 True，则插入记录；否则删除记录。
    使用 INSERT IGNORE 避免重复插入报错。
    """
    conn = get_db_connection()
    c = conn.cursor()
    try:
        if req.is_favorite:
            # 插入收藏记录到 shopee_orders.selection_favorites 表
            c.execute("INSERT IGNORE INTO shopee_orders.selection_favorites (product_id) VALUES (%s)", (req.product_id,))
        else:
            # 从表中移除收藏记录
            c.execute("DELETE FROM shopee_orders.selection_favorites WHERE product_id = %s", (req.product_id,))
        
        conn.commit()
        return {"success": True}
    except Exception as e:
        print(f"Error toggling favorite: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        c.close()
        conn.close()

@router.get("/api/selection/products")
async def get_selection_products(
    page: int = 1,
    limit: int = 20,
    site: Optional[str] = None,
    category: Optional[str] = None,
    seller_type: Optional[str] = None,
    keyword: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    only_favorites: bool = False
):
    """
    获取选品商品列表
    支持多种筛选条件：站点、品类、卖家类型、关键词、价格范围、仅看收藏。
    返回结果包含分页信息、商品详情及其中文类目翻译。
    同时会查询 payload_translations 表返回已缓存的翻译。
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # 构建 SQL 查询语句
        from_part = "FROM shopee_data.product_selection p LEFT JOIN shopee_orders.selection_favorites f ON p.id = f.product_id"
        where_clauses = ["1=1"]
        params = []

        # 1. 站点筛选
        if site and site != "All":
            where_clauses.append("p.site = %s")
            params.append(site)
        
        # 2. 品类筛选 (支持模糊匹配)
        if category and category != "All":
            where_clauses.append("p.category LIKE %s")
            params.append(f"%{category}%")

        # 3. 卖家类型筛选
        if seller_type and seller_type != "All":
            where_clauses.append("p.seller_type = %s")
            params.append(seller_type)

        # 4. 关键词搜索 (匹配关键词、描述或推荐理由)
        if keyword:
            where_clauses.append("(p.keyword LIKE %s OR p.description LIKE %s OR p.recommendation LIKE %s)")
            search_pattern = f"%{keyword}%"
            params.extend([search_pattern, search_pattern, search_pattern])

        # 5. 价格范围筛选
        if min_price is not None:
             where_clauses.append("p.price_min >= %s")
             params.append(min_price)
        
        if max_price is not None:
             where_clauses.append("p.price_max <= %s")
             params.append(max_price)

        # 6. 仅看收藏
        if only_favorites:
             where_clauses.append("f.product_id IS NOT NULL")

        where_str = " AND ".join(where_clauses)

        # ----------------------------------------------------
        # 查询总数 (用于分页)
        # ----------------------------------------------------
        count_query = f"SELECT COUNT(*) as total {from_part} WHERE {where_str}"
        cursor.execute(count_query, params)
        total_res = cursor.fetchone()
        total_count = total_res['total'] if total_res else 0

        # ----------------------------------------------------
        # 查询详细数据
        # ----------------------------------------------------
        # p.*: 商品所有字段
        # (f.product_id IS NOT NULL) as is_favorite: 计算是否已收藏
        data_query = f"SELECT p.*, (f.product_id IS NOT NULL) as is_favorite {from_part} WHERE {where_str} ORDER BY p.id DESC LIMIT %s OFFSET %s"
        params.extend([limit, (page - 1) * limit])
        
        cursor.execute(data_query, params)
        products = cursor.fetchall()
        
        # ----------------------------------------------------
        # 查询已缓存的翻译
        # ----------------------------------------------------
        trans_cache = {} # pid -> field -> text
        if products:
            product_ids = [str(p['id']) for p in products]
            format_strings = ','.join(['%s'] * len(product_ids))
            trans_query = f"SELECT product_id, field_type, translated_text FROM shopee_orders.product_translations WHERE product_id IN ({format_strings})"
            cursor.execute(trans_query, product_ids)
            cached_rows = cursor.fetchall()
            
            for row in cached_rows:
                pid = str(row['product_id'])
                if pid not in trans_cache: trans_cache[pid] = {}
                trans_cache[pid][row['field_type']] = row['translated_text']

        # ----------------------------------------------------
        # 准备辅助数据：中文翻译映射表
        # ----------------------------------------------------
        cursor.execute("SELECT original_name, cn_name FROM shopee_orders.category_translations")
        trans_rows = cursor.fetchall()
        trans_map = {row['original_name']: row['cn_name'] for row in trans_rows}
        
        formatted_products = []
        
        # 站点货币符号映射表
        CURRENCY_MAP = {
            'TW': 'TWD', 'MY': 'MYR', 'PH': 'PHP', 'TH': 'THB', 
            'VN': 'VND', 'BR': 'BRL', 'SG': 'SGD', 'ID': 'IDR'
        }

        # ----------------------------------------------------
        # 格式化商品数据
        # ----------------------------------------------------
        for p in products:
            pid = str(p.get('id'))
            
            # 解析类目层级 (Category > SubCategory)
            cat_str = p.get('category', '') or ''
            parts = [c.strip() for c in cat_str.replace('>', '/').split('/')]
            main_cat = parts[0] if len(parts) > 0 else ''
            sub_cat = parts[1] if len(parts) > 1 else ''
            
            # 获取一级类目的中文翻译，如果没有则使用原名
            cat_cn = trans_map.get(main_cat, main_cat)
            
            # 获取缓存的翻译
            p_trans = trans_cache.get(pid, {})

            formatted_products.append({
                "id": pid,
                "image": p.get('image_url', ''), 
                "site": p.get('site', ''),
                "sellerType": p.get('seller_type', ''),
                "category": cat_cn, # 使用中文类目名称
                "originalCategory": main_cat, # 保留英文原名备用
                "subCategory": sub_cat,
                "keywords": p.get('keyword', ''), 
                "description": p.get('description', ''),
                "translatedDescription": p_trans.get('description'),
                "translatedKeywords": p_trans.get('keywords'),
                "minPrice": str(p.get('price_min', 0)), 
                "maxPrice": str(p.get('price_max', 0)), 
                "currency": CURRENCY_MAP.get(p.get('site'), 'TWD'),
                "reason": p.get('recommendation', '') or p.get('source', ''),
                "isFavorite": bool(p.get('is_favorite', 0)) # 转换 0/1 为 Boolean
            })

        return {
            "total": total_count,
            "page": page,
            "limit": limit,
            "totalPages": math.ceil(total_count / limit) if limit > 0 else 0,
            "products": formatted_products
        }

    except Exception as e:
        print(f"Error fetching selection products: {e}")
        # 发生错误时返回空列表，避免前端崩溃
        return {
            "total": 0,
            "page": page,
            "limit": limit,
            "totalPages": 0,
            "products": [],
            "error": str(e)
        }
    finally:
        cursor.close()
        conn.close()

@router.get("/api/selection/categories")
async def get_selection_categories():
    """
    获取商品类目列表
    返回结果包含原版英文名(value)和中文翻译名(label)。
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True) # 使用 dictionary模式方便通过列名访问
    try:
        # 获取所有翻译映射
        cursor.execute("SELECT * FROM shopee_orders.category_translations")
        trans_rows = cursor.fetchall()
        trans_map = {row['original_name']: row['cn_name'] for row in trans_rows}

        # 从商品表中查询所有不同的一级类目
        query = "SELECT DISTINCT SUBSTRING_INDEX(category, ' > ', 1) as main_cat FROM shopee_data.product_selection WHERE category IS NOT NULL AND category != '' ORDER BY main_cat"
        cursor.execute(query)
        rows = cursor.fetchall()
        
        categories = []
        for row in rows:
            original = row['main_cat']
            categories.append({
                "value": original, # 筛选时传给后端的还是英文原名
                "label": trans_map.get(original, original) # 前端展示时优先显示中文，没有则显示原名
            })
            
        return {"categories": categories}
    except Exception as e:
        print(f"Error fetching categories: {e}")
        return {"categories": []}
    finally:
        cursor.close()
        conn.close()

@router.get("/api/selection/seller-types")
async def get_selection_seller_types():
    """
    获取卖家类型列表 (如 'Local', 'CNCB')
    用于前端筛选下拉框。
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = "SELECT DISTINCT seller_type FROM shopee_data.product_selection WHERE seller_type IS NOT NULL AND seller_type != '' ORDER BY seller_type"
        cursor.execute(query)
        rows = cursor.fetchall()
        
        seller_types = [row[0] for row in rows]
        return {"sellerTypes": seller_types}
    except Exception as e:
        print(f"Error fetching seller types: {e}")
        return {"sellerTypes": []}
    finally:
        cursor.close()
        conn.close()

@router.post("/api/selection/translate")
async def translate_text(req: TranslateRequest):
    """
    单个文本翻译 (不推荐使用，建议使用 batch)
    """
    import os
    import requests
    
    if not req.text:
        return {"translatedText": ""}
    
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return {"translatedText": "Error: DEEPSEEK_API_KEY not set"}
    
    try:
        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "You are a professional translator. Translate the following e-commerce product description into concise Simplified Chinese. Only return the translation, no explanation."},
                    {"role": "user", "content": req.text}
                ],
                "temperature": 0.3
            },
            timeout=15 
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'choices' in data and len(data['choices']) > 0:
                translated = data['choices'][0]['message']['content'].strip()
                return {"translatedText": translated}
        
        print(f"Translation failed: {response.text}")
        return {"translatedText": "Translation failed"}
        
    except Exception as e:
        print(f"Translation exception: {e}")
        return {"translatedText": f"Error: {str(e)}"}

@router.post("/api/selection/translate/batch")
async def batch_translate(req: BatchTranslateRequest):
    """
    批量翻译接口 (带缓存)
    1. 查库: 如果所有 items 都在库中，直接返回。
    2. 翻译: 将未缓存的 items 合并发送给 AI。
    3. 存库: 将 AI 返回的结果存入 database。
    4. 返回: 合并数据返回。
    """
    if not req.items:
        return {"translations": []}
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Step 1: Check Cache
        items_to_translate = []
        cached_results = {} # index -> text
        
        # 收集所有需要检查的 product_id + field 组合
        # 为了简单，我们先不做复杂的批量查询优化（比如 create temporary table），直接用 IN 查询所有 ID
        # 然后在内存里匹配
        
        pids = list(set([item.id for item in req.items]))
        if pids:
            format_strings = ','.join(['%s'] * len(pids))
            cursor.execute(f"SELECT product_id, field_type, translated_text FROM shopee_orders.product_translations WHERE product_id IN ({format_strings})", pids)
            rows = cursor.fetchall()
            # trans_map[pid][field] = text
            trans_map = {}
            for row in rows:
                pid = str(row['product_id'])
                if pid not in trans_map: trans_map[pid] = {}
                trans_map[pid][row['field_type']] = row['translated_text']
                
            # 分类：命中缓存 vs 需要翻译
            for idx, item in enumerate(req.items):
                cached = trans_map.get(str(item.id), {}).get(item.field)
                if cached:
                    cached_results[idx] = cached
                else:
                    if item.text and item.text.strip():
                        items_to_translate.append((idx, item))
                    else:
                        cached_results[idx] = "" # 空文本直接返回空
        
        # Step 2: Translate if needed
        if items_to_translate:
            api_key = os.getenv("DEEPSEEK_API_KEY")
            if not api_key:
                # API Key missing, fill errors
                for idx, _ in items_to_translate:
                    cached_results[idx] = "Error: Key not set"
            else:
                texts_only = [item.text for _, item in items_to_translate]
                
                prompt_content = {
                    "instruction": "Translate the following e-commerce texts (product descriptions or keywords) to Simplified Chinese. Keep the order exactly.",
                    "items": texts_only
                }
                
                try:
                    response = requests.post(
                        "https://api.deepseek.com/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "deepseek-chat",
                            "messages": [
                                {"role": "system", "content": "You are a professional translator. User will provide a list of texts. You must return a JSON object with a key 'translations' containing the list of translated strings in the same order. Do not output anything else."},
                                {"role": "user", "content": json.dumps(prompt_content)}
                            ],
                            "response_format": { "type": "json_object" }, 
                            "temperature": 0.3
                        },
                        timeout=90
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        content = data['choices'][0]['message']['content']
                        result = json.loads(content)
                        translations = result.get('translations', [])
                        
                        # Step 3: Save to DB
                        save_values = []
                        for i, trans_text in enumerate(translations):
                            if i < len(items_to_translate):
                                original_idx, item = items_to_translate[i]
                                cached_results[original_idx] = trans_text
                                save_values.append((item.id, item.field, trans_text))
                        
                        if save_values:
                            cursor.executemany("""
                                INSERT INTO shopee_orders.product_translations (product_id, field_type, translated_text)
                                VALUES (%s, %s, %s)
                                ON DUPLICATE KEY UPDATE translated_text = VALUES(translated_text)
                            """, save_values)
                            conn.commit()
                            
                    else:
                        print(f"Translation API error: {response.text}")
                        for idx, _ in items_to_translate:
                            cached_results[idx] = "Error: API Failed"
                            
                except Exception as e:
                    print(f"Batch translation exception: {e}")
                    for idx, _ in items_to_translate:
                        cached_results[idx] = f"Error: {str(e)}"

        # Step 4: Merge results
        final_translations = []
        for i in range(len(req.items)):
            final_translations.append(cached_results.get(i, "Error: Unknown"))
            
        return {"translations": final_translations}

    except Exception as e:
        print(f"Overall batch error: {e}")
        return {"translations": [f"Error: {str(e)}"] * len(req.items)}
    finally:
        cursor.close()
        conn.close()
