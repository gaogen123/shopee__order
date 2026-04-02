#!/usr/bin/env python3
"""
数据迁移脚本：将 order_items 表中的成本数据迁移到新的 order_item_user_costs 表

此脚本用于将现有的用户记录的订单项成本从 order_items 表迁移到专用的 order_item_user_costs 表，
以区分管理和用户记录的成本数据。

运行方式：
python migrate_costs.py
"""

import sqlite3
import time
from pathlib import Path

# 设置数据库路径
BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR.parent / "shopee_orders.db"

def migrate_cost_data():
    """迁移成本数据从 order_items 到 order_item_user_costs"""

    print("开始迁移成本数据...")

    # 连接数据库
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # 检查新表是否存在，如果不存在则创建
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_item_user_costs (
                order_sn TEXT,
                item_id INTEGER,
                model_id INTEGER DEFAULT 0,
                purchase_cost REAL DEFAULT 0,
                domestic_shipping_cost REAL DEFAULT 0,
                updated_at INTEGER DEFAULT 0,
                PRIMARY KEY (order_sn, item_id, model_id)
            )
        ''')

        # 检查 order_items 表中是否还有成本字段
        cursor.execute("PRAGMA table_info(order_items)")
        columns = cursor.fetchall()
        column_names = [col['name'] for col in columns]

        has_purchase_cost = 'purchase_cost' in column_names
        has_domestic_shipping_cost = 'domestic_shipping_cost' in column_names

        if not has_purchase_cost and not has_domestic_shipping_cost:
            print("order_items 表中没有成本字段，可能是已经迁移过了")
            return

        # 查询现有的成本数据
        if has_purchase_cost and has_domestic_shipping_cost:
            cursor.execute("""
                SELECT order_sn, item_id, model_id, purchase_cost, domestic_shipping_cost
                FROM order_items
                WHERE purchase_cost > 0 OR domestic_shipping_cost > 0
            """)
        elif has_purchase_cost:
            cursor.execute("""
                SELECT order_sn, item_id, model_id, purchase_cost, 0 as domestic_shipping_cost
                FROM order_items
                WHERE purchase_cost > 0
            """)
        else:  # only domestic_shipping_cost
            cursor.execute("""
                SELECT order_sn, item_id, model_id, 0 as purchase_cost, domestic_shipping_cost
                FROM order_items
                WHERE domestic_shipping_cost > 0
            """)

        cost_rows = cursor.fetchall()
        print(f"找到 {len(cost_rows)} 条成本记录需要迁移")

        # 迁移数据到新表
        migrated_count = 0
        for row in cost_rows:
            order_sn = row['order_sn']
            item_id = row['item_id']
            model_id = row['model_id'] if row['model_id'] else 0
            purchase_cost = row['purchase_cost'] or 0
            domestic_shipping_cost = row['domestic_shipping_cost'] or 0

            # 插入到新表
            cursor.execute("""
                INSERT INTO order_item_user_costs (
                    order_sn, item_id, model_id, purchase_cost, domestic_shipping_cost, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(order_sn, item_id, model_id) DO UPDATE SET
                    purchase_cost=excluded.purchase_cost,
                    domestic_shipping_cost=excluded.domestic_shipping_cost,
                    updated_at=excluded.updated_at
            """, (order_sn, item_id, model_id, purchase_cost, domestic_shipping_cost, int(time.time())))

            migrated_count += 1

        # 提交事务
        conn.commit()

        print(f"成功迁移 {migrated_count} 条成本记录")

        # 可选：移除旧表的成本字段（需要谨慎操作）
        # 注意：这里先不自动删除字段，需要手动确认后再删除
        print("\n注意：旧表中的成本字段暂时保留。如需删除，请手动执行以下SQL：")
        print("ALTER TABLE order_items DROP COLUMN purchase_cost;")
        print("ALTER TABLE order_items DROP COLUMN domestic_shipping_cost;")

    except Exception as e:
        print(f"迁移过程中发生错误: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_cost_data()
    print("迁移完成！")
