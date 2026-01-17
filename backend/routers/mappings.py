"""
成本映射路由模块

提供商品成本映射相关的API接口，包括：
- 保存成本映射规则
- 获取成本映射列表

用于管理不同店铺和站点的商品采购成本和国内物流成本

作者: AI Assistant
创建时间: 2025-01-09
"""

from fastapi import APIRouter
from pydantic import BaseModel
import sqlite3
import time

# 导入数据库连接
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from shared import get_db_connection

# 创建路由器实例
router = APIRouter()

class MappingBase(BaseModel):
    """成本映射基础模型"""
    site_id: str                    # 站点ID（如"SG"、"MY"等）
    shop_id: str                    # 店铺ID
    item_id: int                    # 商品ID
    sku_id: str | None = None       # SKU ID，可选
    product_name: str               # 商品名称
    purchase_cost: float            # 采购成本
    domestic_shipping_cost: float   # 国内物流成本

class MappingCreate(MappingBase):
    """创建成本映射的请求模型"""
    pass

class Mapping(MappingBase):
    """完整的成本映射模型（包含数据库字段）"""
    id: int                         # 数据库主键ID
    created_at: int                 # 创建时间戳

@router.post("/api/mappings/save")
def save_mapping(mapping: MappingCreate):
    """
    保存或更新成本映射规则

    如果相同的站点+店铺+商品+SKU组合已存在，则更新现有记录；
    否则创建新的映射记录

    Args:
        mapping (MappingCreate): 成本映射数据

    Returns:
        dict: 保存成功的响应 {"status": "success"}
    """
    # 建立数据库连接
    conn = get_db_connection()
    c = conn.cursor()

    # 执行Upsert操作（插入或更新）
    # 使用 site_id, shop_id, item_id, sku_id 作为唯一键
    c.execute(f"""
        INSERT INTO cost_mappings (
            site_id, shop_id, item_id, sku_id, product_name,
            purchase_cost, domestic_shipping_cost, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            purchase_cost=VALUES(purchase_cost),
            domestic_shipping_cost=VALUES(domestic_shipping_cost),
            product_name=VALUES(product_name),
            created_at=VALUES(created_at)
    """, (
        mapping.site_id,
        mapping.shop_id,
        mapping.item_id,
        mapping.sku_id or "",  # SKU ID为空时使用空字符串,
        mapping.product_name,
        mapping.purchase_cost,
        mapping.domestic_shipping_cost,
        int(time.time())  # 当前时间戳
    ))
    
    # 获取ID
    c.execute("SELECT id FROM cost_mappings WHERE site_id=%s AND shop_id=%s AND item_id=%s AND sku_id=%s", 
             (mapping.site_id, mapping.shop_id, mapping.item_id, mapping.sku_id or ""))
    row = c.fetchone()
    mapping_id = row[0] if row else None

    # 提交事务
    conn.commit()
    conn.close()

    return {"status": "success", "id": str(mapping_id)}

@router.get("/api/mappings")
def get_mappings():
    """
    获取所有成本映射规则列表

    按创建时间倒序排列，最新的映射排在前面

    Returns:
        list: 成本映射列表，每个映射包含完整的字段信息
    """
    # 建立数据库连接
    conn = get_db_connection()
    # conn.row_factory = sqlite3.Row  # MySQL Connector dictionary=True handles this
    c = conn.cursor(dictionary=True)

    # 查询所有映射记录，按创建时间倒序
    c.execute("SELECT * FROM cost_mappings ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()

    # 转换数据格式为前端友好的格式
    mappings = []
    for r in rows:
        mappings.append({
            "id": str(r["id"]),                       # 映射ID (转换为字符串)
            "siteId": r["site_id"],                   # 站点ID
            "shopId": r["shop_id"],                   # 店铺ID
            "productId": str(r["item_id"]),           # 商品ID（转换为字符串）
            "productName": r["product_name"],         # 商品名称
            "sku": r["sku_id"],                       # SKU ID
            "purchaseCost": r["purchase_cost"],       # 采购成本
            "domesticShippingCost": r["domestic_shipping_cost"],  # 国内物流成本
            "createdAt": r["created_at"]              # 创建时间
        })

    return mappings

@router.delete("/api/mappings/{mapping_id}")
def delete_mapping(mapping_id: int):
    """
    删除指定的成本映射规则
    """
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM cost_mappings WHERE id = %s", (mapping_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}
