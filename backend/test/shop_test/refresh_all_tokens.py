#!/usr/bin/env python3
"""
定期刷新所有店铺的 Token

功能：
1. 遍历所有配置的店铺
2. 检查每个店铺是否有独立 token
3. 如果没有，尝试用主账户的 refresh_token 为该店铺获取独立 token
4. 如果有，检查是否需要刷新（超过3小时）
5. 输出详细状态报告

使用方法：
  python refresh_all_tokens.py

建议设置 cron 定时任务，每2小时运行一次：
  0 */2 * * * cd /path/to/shop_test && python refresh_all_tokens.py >> token_refresh.log 2>&1
"""

import time
import hmac
import hashlib
import requests
import json
import os
from datetime import datetime

# 配置
PARTNER_ID = 2014583
PARTNER_KEY = 'shpk616b4d6468776273596f784a716941775743435174625566564f48615057'
HOST = 'https://openplatform.shopee.cn'

# Token 文件路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(BASE_DIR, "shopee_tokens.json")

# 主账户 ID
MAIN_ACCOUNT_ID = 781654

# 所有店铺列表
ALL_SHOPS = [
    {"id": 458007719, "name": "💕LOVE💕Storage", "region": "MY"},
    {"id": 474273630, "name": "七彩精致生活館", "region": "TW"},
    {"id": 485292426, "name": "儿童快乐成长梦工厂", "region": "TW"},
    {"id": 494829323, "name": "Saco multifuncional da mãe", "region": "BR"},
    {"id": 494831140, "name": "gaogen.mx", "region": "MX"},
    {"id": 521218078, "name": "音随律动专店", "region": "PH"},
    {"id": 572732988, "name": "gaogen.cl", "region": "CL"},
    {"id": 572736528, "name": "gaogen.co", "region": "CO"},
    {"id": 627503410, "name": "Haitao Market", "region": "VN"},
    {"id": 627504971, "name": "บิกีนี่", "region": "TH"},
    {"id": 627506657, "name": "gaogen.sg", "region": "SG"},
    {"id": 1162304902, "name": "gaogenmv.co", "region": "CO"},
    {"id": 1162319753, "name": "gaogende.cl", "region": "CL"},
    {"id": 1478672550, "name": "zhangning.br", "region": "BR"}
]

# Token 有效期阈值（3小时 = 10800秒）
TOKEN_REFRESH_THRESHOLD = 10800


def generate_sign(path, timestamp):
    """生成 API 签名"""
    tmp_base_string = f'{PARTNER_ID}{path}{timestamp}'
    base_string = tmp_base_string.encode()
    partner_key = PARTNER_KEY.encode()
    return hmac.new(partner_key, base_string, hashlib.sha256).hexdigest()


def load_all_tokens():
    """加载所有 token"""
    if not os.path.exists(TOKEN_FILE):
        return {}
    try:
        with open(TOKEN_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}


def save_all_tokens(data):
    """保存所有 token"""
    with open(TOKEN_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def refresh_shop_token(shop_id, refresh_token):
    """
    刷新店铺级别的 token

    Args:
        shop_id: 店铺 ID
        refresh_token: 当前的 refresh_token

    Returns:
        dict: 包含 access_token 和 refresh_token 的字典，失败返回 None
    """
    path = '/api/v2/auth/access_token/get'
    timestamp = int(time.time())
    sign = generate_sign(path, timestamp)

    url = f'{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&sign={sign}'

    body = {
        'shop_id': int(shop_id),
        'refresh_token': refresh_token,
        'partner_id': PARTNER_ID
    }

    try:
        resp = requests.post(url, json=body, headers={'Content-Type': 'application/json'}, timeout=30)
        result = resp.json()

        if result.get('error'):
            return None, result.get('message', 'Unknown error')

        return {
            'access_token': result['access_token'],
            'refresh_token': result['refresh_token']
        }, None
    except Exception as e:
        return None, str(e)


def main():
    print(f"\n{'='*80}")
    print(f"Token 刷新任务开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")

    # 加载现有 token
    all_tokens = load_all_tokens()
    current_time = int(time.time())

    # 获取主账户的 refresh_token（用于初始化新店铺）
    main_token_data = all_tokens.get(str(MAIN_ACCOUNT_ID), {})
    main_refresh_token = main_token_data.get('refresh_token')

    # 统计
    stats = {
        'total': len(ALL_SHOPS),
        'success': 0,
        'skipped': 0,
        'failed': 0,
        'new': 0
    }

    results = []

    for shop in ALL_SHOPS:
        shop_id = shop['id']
        shop_name = shop['name']
        region = shop['region']

        shop_token_data = all_tokens.get(str(shop_id), {})

        # 检查是否有店铺级别 token
        if shop_token_data:
            updated_at = shop_token_data.get('updated_at', 0)
            age = current_time - updated_at

            # 检查是否需要刷新（超过3小时）
            if age < TOKEN_REFRESH_THRESHOLD:
                # 不需要刷新
                remaining = TOKEN_REFRESH_THRESHOLD - age
                results.append({
                    'shop': shop_name,
                    'region': region,
                    'status': '✅ 有效',
                    'detail': f'剩余 {remaining//60} 分钟'
                })
                stats['skipped'] += 1
                continue

            # 需要刷新
            refresh_token = shop_token_data.get('refresh_token')
            if refresh_token:
                new_tokens, error = refresh_shop_token(shop_id, refresh_token)
                if new_tokens:
                    all_tokens[str(shop_id)] = {
                        'access_token': new_tokens['access_token'],
                        'refresh_token': new_tokens['refresh_token'],
                        'updated_at': current_time
                    }
                    results.append({
                        'shop': shop_name,
                        'region': region,
                        'status': '🔄 已刷新',
                        'detail': '成功'
                    })
                    stats['success'] += 1
                else:
                    results.append({
                        'shop': shop_name,
                        'region': region,
                        'status': '❌ 刷新失败',
                        'detail': error
                    })
                    stats['failed'] += 1
            else:
                results.append({
                    'shop': shop_name,
                    'region': region,
                    'status': '❌ 无 refresh_token',
                    'detail': '需要重新授权'
                })
                stats['failed'] += 1
        else:
            # 没有店铺级别 token，尝试用主账户 refresh_token 初始化
            if main_refresh_token:
                new_tokens, error = refresh_shop_token(shop_id, main_refresh_token)
                if new_tokens:
                    all_tokens[str(shop_id)] = {
                        'access_token': new_tokens['access_token'],
                        'refresh_token': new_tokens['refresh_token'],
                        'updated_at': current_time
                    }
                    results.append({
                        'shop': shop_name,
                        'region': region,
                        'status': '🆕 新建成功',
                        'detail': '使用主账户 token 初始化'
                    })
                    stats['new'] += 1
                else:
                    results.append({
                        'shop': shop_name,
                        'region': region,
                        'status': '❌ 初始化失败',
                        'detail': error
                    })
                    stats['failed'] += 1
            else:
                results.append({
                    'shop': shop_name,
                    'region': region,
                    'status': '❌ 无主账户 token',
                    'detail': '无法初始化'
                })
                stats['failed'] += 1

    # 保存更新后的 token
    save_all_tokens(all_tokens)

    # 打印结果表格
    print(f"{'店铺名称':<30} | {'地区':<6} | {'状态':<15} | {'详情'}")
    print("-" * 90)
    for r in results:
        print(f"{r['shop']:<30} | {r['region']:<6} | {r['status']:<15} | {r['detail']}")

    # 打印统计
    print(f"\n{'='*80}")
    print(f"统计汇总:")
    print(f"  总店铺数: {stats['total']}")
    print(f"  ✅ 有效（跳过）: {stats['skipped']}")
    print(f"  🔄 已刷新: {stats['success']}")
    print(f"  🆕 新建: {stats['new']}")
    print(f"  ❌ 失败: {stats['failed']}")
    print(f"{'='*80}\n")

    return stats['failed'] == 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
