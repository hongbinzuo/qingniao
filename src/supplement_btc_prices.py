#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为现有对话记录补充BTC价格
从时序库读取价格并更新数据库
"""

import sys
from pathlib import Path
from datetime import datetime

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from db_manager_trader import TraderDBManager
from btc_price_cache import get_btc_price_cached

def supplement_prices(trader_id='de', batch_size=100):
    """为现有记录补充BTC价格"""
    print("=" * 80)
    print("为现有记录补充BTC价格")
    print("=" * 80)
    print()
    
    db = TraderDBManager(trader_id)
    conn = db._get_connection()
    
    # 获取所有没有价格的对话记录
    conversations = conn.execute('''
        SELECT id, timestamp, trader_message
        FROM conversations
        WHERE btc_price IS NULL AND trader_message IS NOT NULL
        ORDER BY timestamp
    ''').fetchall()
    
    print(f"找到 {len(conversations)} 条需要补充价格的对话记录")
    print()
    
    updated_count = 0
    failed_count = 0
    
    for i, (conv_id, timestamp, content) in enumerate(conversations, 1):
        try:
            # 从时序库获取价格
            btc_price = get_btc_price_cached(timestamp, use_api=False)
            
            if btc_price:
                # 更新数据库
                conn.execute('''
                    UPDATE conversations
                    SET btc_price = ?
                    WHERE id = ?
                ''', (btc_price, conv_id))
                updated_count += 1
            else:
                failed_count += 1
            
            # 每100条提交一次
            if i % batch_size == 0:
                conn.commit()
                print(f"  已处理 {i}/{len(conversations)} 条，成功: {updated_count}, 失败: {failed_count}")
        except Exception as e:
            failed_count += 1
            if i % 100 == 0:
                print(f"  处理失败: {e}", file=sys.stderr)
    
    # 提交剩余
    conn.commit()
    
    # 更新观点表
    print()
    print("更新观点表...")
    viewpoints = conn.execute('''
        SELECT id, timestamp, content
        FROM trader_viewpoints
        WHERE btc_price IS NULL
        ORDER BY timestamp
    ''').fetchall()
    
    print(f"找到 {len(viewpoints)} 条需要补充价格的观点记录")
    
    vp_updated = 0
    vp_failed = 0
    
    for i, (vp_id, timestamp, content) in enumerate(viewpoints, 1):
        try:
            btc_price = get_btc_price_cached(timestamp, use_api=False)
            
            if btc_price:
                conn.execute('''
                    UPDATE trader_viewpoints
                    SET btc_price = ?
                    WHERE id = ?
                ''', (btc_price, vp_id))
                vp_updated += 1
            else:
                vp_failed += 1
            
            if i % batch_size == 0:
                conn.commit()
                print(f"  已处理 {i}/{len(viewpoints)} 条，成功: {vp_updated}, 失败: {vp_failed}")
        except Exception as e:
            vp_failed += 1
    
    conn.commit()
    
    print()
    print("=" * 80)
    print("补充完成！")
    print("=" * 80)
    print(f"对话记录: 成功 {updated_count} 条, 失败 {failed_count} 条")
    print(f"观点记录: 成功 {vp_updated} 条, 失败 {vp_failed} 条")
    print()
    
    db.close()

if __name__ == '__main__':
    supplement_prices(trader_id='de')






