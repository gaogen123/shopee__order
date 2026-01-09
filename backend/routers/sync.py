"""
数据同步路由模块

提供订单数据同步相关的所有API接口，包括：
- 获取待同步订单列表
- 批量同步订单数据
- 单个订单同步
- 同步任务状态查询

支持后台异步任务处理，避免长时间API调用阻塞

作者: AI Assistant
创建时间: 2025-01-09
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from typing import List
import threading
import uuid
import time

# 导入共享函数，避免循环依赖
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from shared import (
    get_db_connection, get_valid_token, fetch_order_from_api, fetch_escrow_detail,
    save_order_to_db, api_session, HOST, PARTNER_ID, generate_shop_sign
)
from token_manager import ALL_SHOPS

# 创建路由器实例
router = APIRouter()

class SyncRequest(BaseModel):
    """订单同步请求模型"""
    time_from: int  # 起始时间戳（Unix时间戳）
    time_to: int    # 结束时间戳（Unix时间戳）
    shop_id: int = 494829323  # 店铺ID，默认为494829323

class SingleSyncRequest(BaseModel):
    """单个订单同步请求模型"""
    order_sn: str   # 订单编号
    shop_id: int = 494829323  # 店铺ID

class BatchSyncItem(BaseModel):
    """批量同步项模型"""
    order_sn: str   # 订单编号
    shop_id: int    # 店铺ID

class BatchSyncRequest(BaseModel):
    """批量同步请求模型"""
    items: List[BatchSyncItem]  # 要同步的订单列表

# --- 后台同步任务管理 ---
# 存储同步任务状态：task_id -> {status, current, total, count, error}
SYNC_TASKS = {}

def fetch_order_list_from_api(shop_id, time_from, time_to):
    """
    从Shopee API获取指定时间范围内的订单编号列表

    Shopee API v2的get_order_list接口有以下限制：
    - 单次调用最多返回15天的数据
    - 需要分页获取（使用cursor）
    - 每页最多100条记录

    Args:
        shop_id (int): 店铺ID
        time_from (int): 起始时间戳（Unix时间戳）
        time_to (int): 结束时间戳（Unix时间戳）

    Returns:
        list: 订单编号列表

    Note:
        如果时间范围超过15天，会自动分段获取以满足API限制
    """
    # 获取有效的访问令牌
    token = get_valid_token(shop_id)
    if not token:
        print(f"错误：店铺 {shop_id} 没有有效的访问令牌")
        return []

    # API接口路径
    path = "/api/v2/order/get_order_list"
    timestamp = int(time.time())
    all_order_sns = []  # 存储所有获取到的订单编号

    # Shopee API v2限制：get_order_list最多返回15天的数据（1,296,000秒）
    MAX_RANGE = 15 * 24 * 3600

    # 将请求的时间范围分割为15天的块
    current_from = time_from
    while current_from < time_to:
        # 计算当前时间段的结束时间（不超过15天）
        current_to = min(current_from + MAX_RANGE, time_to)

        cursor = ""  # 分页游标
        while True:
            # 生成API签名
            sign = generate_shop_sign(path, timestamp, token, shop_id)
            url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&access_token={token}&shop_id={shop_id}&sign={sign}"

            # 构建请求参数
            params = {
                "time_range_field": "create_time",  # 按创建时间筛选
                "time_from": current_from,
                "time_to": current_to,
                "page_size": 100,  # 每页100条记录
                "cursor": cursor   # 分页游标
            }

            try:
                # 使用带重试机制的HTTP会话，设置30秒超时
                resp = api_session.get(url, params=params, timeout=30)
                data = resp.json()

                # 检查API响应是否包含错误
                if "error" in data and data["error"]:
                    msg = data.get("message", "Unknown error")
                    print(f"API错误 (订单列表段 {current_from}-{current_to}): {msg}")
                    # 如果是严重的错误（如令牌问题），停止获取并返回已有的数据
                    if "token" in msg.lower():
                        return all_order_sns  # 返回已获取的数据
                    break

                # 解析响应数据
                response_data = data.get("response", {})
                order_list = response_data.get("order_list", [])

                # 收集订单编号（去重）
                for o in order_list:
                    if o["order_sn"] not in all_order_sns:
                        all_order_sns.append(o["order_sn"])

                # 检查是否还有更多数据
                if not response_data.get("more", False):
                    break

                # 更新游标以获取下一页
                cursor = response_data.get("next_cursor", "")

            except Exception as e:
                print(f"获取订单列表段时出错: {e}")
                break

        # 移动到下一个15天的时段（无缝连接，避免遗漏订单）
        current_from = current_to

    return all_order_sns

def run_sync_task(task_id, shop_id, time_from, time_to):
    """
    执行订单同步任务（时间范围模式）

    后台任务函数，用于同步指定时间范围内的所有订单数据

    Args:
        task_id (str): 任务ID，用于跟踪任务状态
        shop_id (int): 店铺ID
        time_from (int): 起始时间戳
        time_to (int): 结束时间戳
    """
    try:
        # 第一步：获取待同步的订单编号列表
        order_sns = fetch_order_list_from_api(shop_id, time_from, time_to)
        total = len(order_sns)

        # 初始化任务状态
        SYNC_TASKS[task_id] = {
            "task_id": task_id,
            "status": "running",     # 任务状态：running, completed, failed
            "current": 0,            # 当前处理的订单索引
            "total": total,          # 总订单数
            "count": 0               # 成功同步的订单数
        }

        count = 0
        conn = get_db_connection()

        # 逐个同步订单数据
        for i, sn in enumerate(order_sns):
            # 获取订单详情
            order_data = fetch_order_from_api(shop_id, sn)
            if order_data:
                # 获取托管数据（财务信息）
                escrow_data = fetch_escrow_detail(shop_id, sn)
                # 保存到数据库
                save_order_to_db(conn, shop_id, order_data, escrow_data)
                count += 1

            # 更新任务进度
            SYNC_TASKS[task_id]["current"] = i + 1
            SYNC_TASKS[task_id]["count"] = count

        conn.close()
        # 标记任务完成
        SYNC_TASKS[task_id]["status"] = "completed"

    except Exception as e:
        print(f"同步任务错误: {e}")
        SYNC_TASKS[task_id]["status"] = "failed"
        SYNC_TASKS[task_id]["error"] = str(e)

def run_batch_sync_task(task_id, items):
    """
    执行批量订单同步任务

    后台任务函数，用于同步指定的订单列表

    Args:
        task_id (str): 任务ID
        items (list): 要同步的订单项列表，每个项包含order_sn和shop_id
    """
    total = len(items)

    # 初始化任务状态
    SYNC_TASKS[task_id] = {
        "task_id": task_id,
        "status": "running",
        "current": 0,
        "total": total,
        "count": 0
    }

    count = 0
    conn = get_db_connection()

    # 处理每个订单项
    for i, item in enumerate(items):
        try:
            shop_id = item.shop_id
            sn = item.order_sn

            # 获取订单数据并保存
            order_data = fetch_order_from_api(shop_id, sn)
            if order_data:
                escrow_data = fetch_escrow_detail(shop_id, sn)
                save_order_to_db(conn, shop_id, order_data, escrow_data)
                count += 1

        except Exception as e:
            print(f"批量同步错误 (订单 {item.order_sn}): {e}")

        # 更新进度
        SYNC_TASKS[task_id]["current"] = i + 1
        SYNC_TASKS[task_id]["count"] = count

    conn.close()
    # 标记任务完成
    SYNC_TASKS[task_id]["status"] = "completed"

@router.get("/api/sync/get_order_sns")
def get_order_sns_to_sync(time_from: int, time_to: int, shop_id: int = 494829323):
    """
    获取指定时间范围内待同步的订单编号列表

    这个接口用于预览需要同步的订单，不执行实际的数据同步操作

    Args:
        time_from (int): 起始时间戳
        time_to (int): 结束时间戳
        shop_id (int): 店铺ID，默认值为494829323

    Returns:
        dict: 包含订单编号列表的响应 {"order_sns": [...]}
    """
    order_sns = fetch_order_list_from_api(shop_id, time_from, time_to)
    return {"order_sns": order_sns}

@router.post("/api/sync_orders")
def sync_orders(req: SyncRequest):
    """
    启动时间范围内的订单同步任务

    创建后台异步任务来同步指定时间范围内的所有订单数据。
    这个过程可能需要很长时间，因此使用后台任务处理。

    Args:
        req (SyncRequest): 同步请求，包含时间范围和店铺ID

    Returns:
        dict: 包含任务ID的响应 {"status": "accepted", "task_id": "uuid"}
    """
    # 生成唯一的任务ID
    task_id = str(uuid.uuid4())

    # 初始化任务状态
    SYNC_TASKS[task_id] = {
        "task_id": task_id,
        "status": "starting",
        "current": 0,
        "total": 0,
        "count": 0
    }

    # 启动后台线程执行同步任务
    thread = threading.Thread(
        target=run_sync_task,
        args=(task_id, req.shop_id, req.time_from, req.time_to)
    )
    thread.start()

    return {"status": "accepted", "task_id": task_id}

@router.post("/api/sync_batch")
def sync_batch(req: BatchSyncRequest):
    """
    启动批量订单同步任务

    根据提供的订单列表批量同步指定的订单数据

    Args:
        req (BatchSyncRequest): 批量同步请求，包含订单列表

    Returns:
        dict: 包含任务ID的响应
    """
    task_id = str(uuid.uuid4())
    SYNC_TASKS[task_id] = {
        "task_id": task_id,
        "status": "starting",
        "current": 0,
        "total": 0,
        "count": 0
    }

    # 启动批量同步后台任务
    thread = threading.Thread(target=run_batch_sync_task, args=(task_id, req.items))
    thread.start()

    return {"status": "accepted", "task_id": task_id}

@router.get("/api/sync/status/{task_id}")
def get_sync_status(task_id: str):
    """
    获取同步任务的执行状态和进度

    Args:
        task_id (str): 任务ID

    Returns:
        dict: 任务状态信息，包含进度、状态、成功数量等

    Raises:
        HTTPException: 当任务ID不存在时返回404错误
    """
    if task_id not in SYNC_TASKS:
        raise HTTPException(status_code=404, detail="Task not found")
    return SYNC_TASKS[task_id]

@router.post("/api/sync/order")
def sync_single_order(req: SingleSyncRequest):
    """
    同步单个订单数据

    立即同步指定的单个订单，不使用后台任务

    Args:
        req (SingleSyncRequest): 单个订单同步请求

    Returns:
        dict: 同步结果 {"status": "success"} 或错误信息
    """
    # 获取订单数据
    order_data = fetch_order_from_api(req.shop_id, req.order_sn)
    if order_data:
        # 获取财务数据
        escrow_data = fetch_escrow_detail(req.shop_id, req.order_sn)
        # 保存到数据库
        conn = get_db_connection()
        save_order_to_db(conn, req.shop_id, order_data, escrow_data)
        conn.close()
        return {"status": "success"}

    return {"status": "error", "message": "Failed to fetch order data"}
