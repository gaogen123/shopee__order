import sys
from pathlib import Path
import threading
import uuid
import time
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Path(__file__).resolve().parent / 'server.log')
    ]
)
logger = logging.getLogger(__name__)

# Add the test/shop_test directory to sys.path to import token_manager
# Assuming server.py is in backend/ and token_manager is in backend/test/shop_test/
BASE_DIR = Path(__file__).resolve().parent
TEST_DIR = BASE_DIR / "test" / "shop_test"
sys.path.append(str(TEST_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import json
import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import hmac
import hashlib
from token_manager import PARTNER_ID, PARTNER_KEY, HOST, ALL_SHOPS

# Import shared functions
from shared import get_db_connection, init_db_tables

# 配置requests重试策略和SSL超时设置
def create_session_with_retries():
    """创建带有重试机制的requests session"""
    session = requests.Session()
    
    # 配置重试策略：总共重试3次，对于连接错误、读取错误、超时等进行重试
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,  # 重试间隔：1s, 2s, 4s
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

# 创建全局session
api_session = create_session_with_retries()

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = BASE_DIR.parent / "shopee_orders.db"


# Import route modules after all functions are defined
from routers.orders import router as orders_router
from routers.sync import router as sync_router
from routers.mappings import router as mappings_router
from routers.shops import router as shops_router

# Include route modules
app.include_router(orders_router)
app.include_router(sync_router)
app.include_router(mappings_router)
app.include_router(shops_router)

def refresh_all_shop_tokens():
    """
    刷新所有店铺的 Token
    """
    try:
        # 动态导入刷新脚本
        import importlib.util
        refresh_script = TEST_DIR / "refresh_all_tokens.py"
        spec = importlib.util.spec_from_file_location("refresh_all_tokens", refresh_script)
        refresh_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(refresh_module)

        # 运行刷新任务
        logger.info("正在刷新所有店铺 Token...")
        refresh_module.main()
        logger.info("店铺 Token 刷新完成")
    except Exception as e:
        logger.error(f"刷新店铺 Token 时出错: {e}")


def scheduled_token_refresh():
    """
    定时刷新 Token 的后台任务
    启动时立即执行一次，然后每2小时执行一次
    """
    # 启动时立即刷新一次
    refresh_all_shop_tokens()

    # 定时刷新间隔：2小时 = 7200秒
    REFRESH_INTERVAL = 2 * 60 * 60

    while True:
        time.sleep(REFRESH_INTERVAL)
        logger.info("[定时任务] 开始定时刷新店铺 Token...")
        refresh_all_shop_tokens()


if __name__ == "__main__":
    logger.info("Server starting with LATEST FINANCIAL LOGIC (Merged Escrow + Tax)...")
    # Initialize database tables
    conn = get_db_connection()
    init_db_tables(conn)
    conn.close()
    logger.info("Database tables initialized")

    # 启动定时刷新 Token 的后台线程
    token_refresh_thread = threading.Thread(target=scheduled_token_refresh, daemon=True)
    token_refresh_thread.start()
    logger.info("Token 定时刷新任务已启动（每2小时执行一次）")

    import uvicorn
    # Run on 0.0.0.0:9000
    uvicorn.run(app, host="0.0.0.0", port=9000)