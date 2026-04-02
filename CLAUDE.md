# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个 Shopee 订单财务管理系统，用于管理多店铺订单数据、成本核算和利润分析。

## 开发命令

### 前端 (React + TypeScript + Vite)
```bash
npm install          # 安装依赖
npm run dev          # 启动开发服务器 (默认端口 5173)
npm run build        # 构建生产版本
```

### 后端 (FastAPI + Python)
```bash
# 启动后端服务器 (端口 9000)
cd backend && python server.py

# 或使用 uvicorn
uvicorn backend.server:app --host 0.0.0.0 --port 9000 --reload
```

### 数据库
```bash
python init_db.py    # 初始化 MySQL 数据库表结构
python test_db.py    # 测试数据库连接
```

## 架构概述

```
前端 (localhost:5173)  →  后端 API (localhost:9000)  →  MySQL 数据库
                                    ↓
                          Shopee Open Platform API
```

### 前端结构 (`src/`)
- `App.tsx` - 主应用入口，管理全局状态和视图切换
- `components/Dashboard.tsx` - 财务仪表板，显示收入/成本/利润趋势
- `components/OrderDetail.tsx` - 订单详情页，支持成本编辑
- `components/OrderCard.tsx` - 订单卡片组件
- `components/ProductCostMappingManager.tsx` - 商品成本映射管理
- `components/SyncProgress.tsx` - 订单同步进度显示
- `components/ui/` - Radix-UI 基础组件库

### 后端结构 (`backend/`)
- `server.py` - FastAPI 应用入口
- `shared.py` - 共享函数（数据库连接、API 调用、订单保存）
- `routers/orders.py` - 订单 CRUD API
- `routers/sync.py` - 订单同步 API（支持时间范围、批量、单个同步）
- `routers/mappings.py` - 成本映射 API
- `routers/shops.py` - 店铺信息 API
- `test/shop_test/token_manager.py` - Shopee OAuth 令牌管理

### 核心数据流
1. **订单同步**: Shopee API → `fetch_order_from_api()` + `fetch_escrow_detail()` → `save_order_to_db()` → MySQL
2. **财务计算**: 预估收入优先使用 `escrow_data.order_income_amount`，利润 = 收入 × 汇率 - 成本

### 数据库表
- `orders` - 订单主表 (order_sn, shop_id, estimated_revenue, estimated_profit, total_cost 等)
- `order_items` - 订单商品表
- `cost_mappings` - 商品成本映射规则 (按站点+店铺+商品维度)
- `order_item_user_costs` - 用户输入的商品成本

## 关键业务逻辑

### 汇率配置 (`backend/shared.py`)
```python
EXCHANGE_RATES = {
    'BRL': 1.24, 'USD': 7.2, 'SGD': 5.3, 'MYR': 1.6,
    'PHP': 0.13, 'IDR': 0.00046, 'THB': 0.2, 'VND': 0.00029, 'TWD': 0.23
}
```

### 订单同步分段逻辑
Shopee API 限制单次请求最多 15 天数据，`sync.py` 中的 `fetch_order_list_from_api()` 会自动分段处理超过 15 天的时间范围。

### 店铺配置
所有店铺信息在 `backend/test/shop_test/token_manager.py` 的 `ALL_SHOPS` 列表中配置，支持 14 个多地区店铺 (BR, MX, CL, CO, VN, TH, SG, PH, MY, TW)。

## 代码规范

- 后端使用 Python 类型注解
- 前端使用 TypeScript 严格模式
- 所有代码注释使用中文
