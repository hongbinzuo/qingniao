#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将现有JSON文件迁移到数据库
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from db_manager_duckdb import DuckDBManager

def migrate_conversation_json_files():
    """迁移对话JSON文件到数据库"""
    db = DuckDBManager()
    
    # 查找所有对话JSON文件
    data_dir = Path("data")
    json_files = list(data_dir.glob("de_conversations_*.json"))
    
    print(f"找到 {len(json_files)} 个对话JSON文件")
    print()
    
    migrated_count = 0
    
    for json_file in json_files:
        print(f"处理: {json_file.name}")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                records = json.load(f)
            
            for record in records:
                timestamp_str = record.get('timestamp', '')
                content = record.get('content', '')
                btc_price = record.get('btc_price')
                analysis = record.get('analysis', {})
                context = record.get('context', '')
                category = record.get('category', 'trading')
                
                # 构建完整内容
                full_content = content
                if btc_price:
                    full_content = f"[BTC价格: ${btc_price:,.2f}] {full_content}"
                if context:
                    full_content = f"[上下文: {context}] {full_content}"
                
                # 添加分析信息
                if analysis.get('prices'):
                    full_content += f"\n[解析价格: {', '.join(map(str, analysis['prices']))}]"
                if analysis.get('concepts'):
                    full_content += f"\n[概念: {', '.join(analysis['concepts'])}]"
                
                # 转换为标准时间格式
                try:
                    if '/' in timestamp_str:
                        dt = datetime.strptime(timestamp_str, '%Y/%m/%d %H:%M')
                    else:
                        dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    timestamp = timestamp_str
                
                # 提取标签
                tags = []
                if analysis.get('actions'):
                    tags.extend(analysis['actions'])
                if analysis.get('strategy'):
                    tags.extend(analysis['strategy'])
                if analysis.get('concepts'):
                    tags.extend(analysis['concepts'])
                
                # 添加到数据库
                db.add_de_viewpoint(
                    content=full_content,
                    timestamp=timestamp,
                    source='conversation',
                    category=category,
                    tags=tags if tags else None,
                    btc_price=btc_price
                )
                migrated_count += 1
            
            print(f"  [OK] 已迁移 {len(records)} 条记录")
            
        except Exception as e:
            print(f"  [ERROR] 迁移失败: {e}")
        
        print()
    
    db.close()
    
    print("=" * 80)
    print(f"迁移完成！共迁移 {migrated_count} 条记录")
    print("=" * 80)

def migrate_trade_record_json_files():
    """迁移交易记录JSON文件到数据库"""
    db = DuckDBManager()
    
    # 查找所有交易记录JSON文件
    data_dir = Path("data")
    json_files = list(data_dir.glob("de_trade_record_*.json"))
    
    print(f"找到 {len(json_files)} 个交易记录JSON文件")
    print()
    
    migrated_count = 0
    
    for json_file in json_files:
        print(f"处理: {json_file.name}")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                record = json.load(f)
            
            # 添加到数据库（需要创建trade_records表）
            # 这里先记录到de_viewpoints，后续可以单独处理
            
            timestamp_str = record.get('timestamp', '')
            symbol = record.get('symbol', 'BTC/USDT')
            direction = record.get('direction', '')
            leverage = record.get('leverage', 0)
            entry_price = record.get('entry_price', 0)
            current_price = record.get('current_price', 0)
            profit_pct = record.get('profit_pct', 0)
            profit_usdt = record.get('profit_usdt', 0)
            
            # 构建内容
            content = f"交易记录: {symbol} {direction.upper()} {leverage}x\n"
            content += f"时间: {timestamp_str}\n"
            content += f"开仓均价: ${entry_price:,.2f}\n"
            content += f"最新价格: ${current_price:,.2f}\n"
            content += f"收益率: +{profit_pct:.2f}%\n"
            content += f"盈利: +{profit_usdt:.2f} USDT"
            
            # 转换为标准时间格式
            try:
                if '/' in timestamp_str:
                    dt = datetime.strptime(timestamp_str, '%Y/%m/%d %H:%M:%S')
                else:
                    dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                timestamp = timestamp_str
            
            # 添加到数据库
            db.add_de_viewpoint(
                content=content,
                timestamp=timestamp,
                source='trade_record',
                category='trading',
                tags=['交易记录', direction, f'{leverage}x杠杆'],
                btc_price=current_price
            )
            migrated_count += 1
            
            print(f"  [OK] 已迁移")
            
        except Exception as e:
            print(f"  [ERROR] 迁移失败: {e}")
        
        print()
    
    db.close()
    
    print("=" * 80)
    print(f"迁移完成！共迁移 {migrated_count} 条记录")
    print("=" * 80)

def main():
    """主函数"""
    print("=" * 80)
    print("迁移JSON文件到数据库")
    print("=" * 80)
    print()
    
    # 迁移对话文件
    print("1. 迁移对话JSON文件...")
    print()
    migrate_conversation_json_files()
    
    print()
    
    # 迁移交易记录文件
    print("2. 迁移交易记录JSON文件...")
    print()
    migrate_trade_record_json_files()
    
    print()
    print("=" * 80)
    print("所有迁移完成！")
    print("=" * 80)

if __name__ == '__main__':
    main()

