import sys
from pathlib import Path
import threading
import uuid
import time

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

if __name__ == "__main__":
    print("Server starting with LATEST FINANCIAL LOGIC (Merged Escrow + Tax)...")
    # Initialize database tables
    conn = get_db_connection()
    init_db_tables(conn)
    conn.close()
    print("Database tables initialized")
    import uvicorn
    # Run on 0.0.0.0:8000
    uvicorn.run(app, host="0.0.0.0", port=8000)