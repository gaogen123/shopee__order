import sys
from pathlib import Path
import threading
import uuid
import time
import logging
from contextlib import asynccontextmanager

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
BASE_DIR = Path(__file__).resolve().parent
TEST_DIR = BASE_DIR / "test" / "shop_test"
sys.path.append(str(TEST_DIR))
# Add project root to sys.path
sys.path.append(str(BASE_DIR.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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

# 配置requests重试策略
def create_session_with_retries():
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

api_session = create_session_with_retries()

DB_FILE = BASE_DIR.parent / "shopee_orders.db"
IMAGES_DIR = BASE_DIR.parent / "pdd_images"
os.makedirs(IMAGES_DIR, exist_ok=True)

# Import route modules
from routers.orders import router as orders_router
from routers.sync import router as sync_router
from routers.mappings import router as mappings_router
from routers.shops import router as shops_router
from routers.agent import router as agent_router

def refresh_all_shop_tokens():
    try:
        import importlib.util
        refresh_script = TEST_DIR / "refresh_all_tokens.py"
        spec = importlib.util.spec_from_file_location("refresh_all_tokens", refresh_script)
        refresh_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(refresh_module)
        logger.info("正在刷新所有店铺 Token...")
        refresh_module.main()
        logger.info("店铺 Token 刷新完成")
    except Exception as e:
        logger.error(f"刷新店铺 Token 时出错: {e}")

def scheduled_token_refresh():
    refresh_all_shop_tokens()
    REFRESH_INTERVAL = 2 * 60 * 60
    while True:
        time.sleep(REFRESH_INTERVAL)
        logger.info("[定时任务] 开始定时刷新店铺 Token...")
        refresh_all_shop_tokens()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Server starting with LATEST FINANCIAL LOGIC (Merged Escrow + Tax)...")
    conn = get_db_connection()
    init_db_tables(conn)
    conn.close()
    logger.info("Database tables initialized")

    token_refresh_thread = threading.Thread(target=scheduled_token_refresh, daemon=True)
    token_refresh_thread.start()
    logger.info("Token 定时刷新任务已启动")
    yield

app = FastAPI(lifespan=lifespan)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include route modules
app.include_router(orders_router)
app.include_router(sync_router)
app.include_router(mappings_router)
app.include_router(shops_router)
app.include_router(agent_router)

# Mount images directory
app.mount("/pdd_images", StaticFiles(directory=IMAGES_DIR), name="pdd_images")

if __name__ == "__main__":
    import uvicorn
    # 为了让代码修改后能自动重启，开启 reload=True
    # 注意：需要进入 backend 目录运行，或者正确配置模块路径
    uvicorn.run("server:app", host="0.0.0.0", port=9000, reload=True)