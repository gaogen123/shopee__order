"""
店铺管理路由模块

提供店铺和站点相关信息的API接口

作者: AI Assistant
创建时间: 2025-01-09
"""

from fastapi import APIRouter

# 导入店铺配置
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from token_manager import ALL_SHOPS

# 创建路由器实例
router = APIRouter()

@router.get("/api/shops")
def get_shops_endpoint():
    """
    获取配置的店铺列表，按地区分组为站点

    从token_manager中获取所有配置的店铺信息，
    按地区（region）分组生成站点列表，
    为前端的下拉选择器提供数据

    Returns:
        dict: 包含店铺列表和站点列表的响应
            - shops: 店铺列表，每个店铺包含id、name、region等信息
            - sites: 站点列表，按地区分组
    """
    formatted_shops = []  # 格式化的店铺列表
    regions = set()       # 地区集合（用于去重）

    # 遍历所有配置的店铺
    for shop in ALL_SHOPS:
        # 获取店铺地区，默认为'Unknown'
        region = shop.get('region', 'Unknown')
        regions.add(region)

        # 格式化店铺信息为前端需要的格式
        formatted_shops.append({
            "value": str(shop['id']),    # 店铺ID（作为选择器的值）
            "label": shop['name'],       # 店铺名称（作为选择器的标签）
            "siteId": region,            # 站点ID（使用地区作为站点标识）
            "region": region             # 地区信息
        })

    # 对地区进行排序
    sorted_regions = sorted(list(regions))

    # 构建站点列表，以"全部站点"为默认选项
    formatted_sites = [{ "value": "all", "label": "全部站点" }]
    for r in sorted_regions:
        formatted_sites.append({
            "value": r,     # 站点值
            "label": r      # 站点标签
        })

    # 返回店铺和站点信息
    return {
        "shops": formatted_shops,     # 店铺列表
        "sites": formatted_sites      # 站点列表
    }
