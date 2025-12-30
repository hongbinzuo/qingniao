#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从对话中提取交易记录
提取加仓、减仓、滚仓等操作
"""

import sys
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from db_manager_trader import TraderDBManager
from de_strategy_extractor import DeStrategyExtractor
try:
    from system_logger import get_system_logger
    SYSTEM_LOGGER_AVAILABLE = True
except ImportError:
    SYSTEM_LOGGER_AVAILABLE = False

class TradeExtractor:
    """交易记录提取器"""
    
    def __init__(self):
        self.extractor = DeStrategyExtractor()
    
    def extract_trades_from_conversation(self, conv_id: int, timestamp: str, 
                                        message: str, btc_price: float = None) -> List[Dict]:
        """
        从对话中提取交易记录
        
        Returns:
            交易记录列表
        """
        trades = []
        
        # 提取策略信息
        strategy_info = self.extractor.extract_strategy_info(message)
        prices = strategy_info.get('prices', [])
        actions = strategy_info.get('actions', [])
        
        if not prices and not actions:
            return trades
        
        # 解析滚仓操作
        # 格式：从876加到881，888减仓一半，883加回1/4
        price_actions = []
        
        # 1. 匹配"从876加到881"模式（向下加仓）
        pattern1 = re.search(r'从(\d{3,5})加[到至](\d{3,5})', message)
        if pattern1:
            price1 = int(pattern1.group(1))
            price2 = int(pattern1.group(2))
            if 400 <= price1 <= 1000:
                price1 = price1 * 100
            if 400 <= price2 <= 1000:
                price2 = price2 * 100
            if 40000 <= price1 <= 150000 and 40000 <= price2 <= 150000:
                # 初始入场
                price_actions.append({
                    'price': price1,
                    'action': 'add_position',
                    'description': f'初始入场{price1//100}'
                })
                # 向下加仓
                price_actions.append({
                    'price': price2,
                    'action': 'add_position',
                    'description': f'从{price1//100}加到{price2//100}'
                })
        
        # 2. 匹配"888减仓一半"模式
        pattern2 = re.finditer(r'(\d{3,5})减仓(?:一半|50%|1/2)', message)
        for match in pattern2:
            price = int(match.group(1))
            if 400 <= price <= 1000:
                price = price * 100
            if 40000 <= price <= 150000:
                price_actions.append({
                    'price': price,
                    'action': 'reduce_position',
                    'description': f'{price//100}减仓一半'
                })
        
        # 3. 匹配"883加回1/4"模式
        pattern3 = re.finditer(r'(\d{3,5})加回(?:1/4|25%|四分之一)', message)
        for match in pattern3:
            price = int(match.group(1))
            if 400 <= price <= 1000:
                price = price * 100
            if 40000 <= price <= 150000:
                price_actions.append({
                    'price': price,
                    'action': 'add_position',
                    'description': f'{price//100}加回1/4'
                })
        
        # 4. 匹配单独的加仓/减仓操作
        if not price_actions:
            # 提取所有3-5位数字
            all_numbers = re.findall(r'\b(\d{3,5})\b', message)
            for num_str in all_numbers:
                num = int(num_str)
                price = None
                if 400 <= num <= 1000:
                    price = num * 100
                elif 40000 <= num <= 150000:
                    price = num
                
                if not price:
                    continue
                
                # 判断上下文
                context_start = max(0, message.find(num_str) - 15)
                context_end = min(len(message), message.find(num_str) + len(num_str) + 15)
                context = message[context_start:context_end]
                
                if any(kw in context for kw in ['加', '加仓', 'add']):
                    price_actions.append({
                        'price': price,
                        'action': 'add_position',
                        'description': f'{price//100}加仓'
                    })
                elif any(kw in context for kw in ['减', '减仓', 'reduce']):
                    price_actions.append({
                        'price': price,
                        'action': 'reduce_position',
                        'description': f'{price//100}减仓'
                    })
        
        # 如果没有匹配到模式，使用提取的价格
        if not price_actions and prices:
            for price in prices:
                if any(kw in message for kw in ['加', '加仓', 'add']):
                    price_actions.append({
                        'price': price,
                        'action': 'add_position',
                        'description': f'在{price}加仓'
                    })
                elif any(kw in message for kw in ['减', '减仓', 'reduce']):
                    price_actions.append({
                        'price': price,
                        'action': 'reduce_position',
                        'description': f'在{price}减仓'
                    })
        
        # 创建交易记录
        for pa in price_actions:
            trade = {
                'timestamp': timestamp,
                'symbol': 'BTC/USDT',
                'direction': 'long',  # 默认做多，可以根据消息判断
                'entry_price': pa['price'] if pa['action'] == 'add_position' else None,
                'exit_price': pa['price'] if pa['action'] == 'reduce_position' else None,
                'action_type': pa['action'],
                'description': pa['description'],
                'related_conversation_id': conv_id,
                'btc_price': btc_price,
                'source': 'conversation_extraction'
            }
            
            # 判断方向
            if '空' in message or 'short' in message.lower():
                trade['direction'] = 'short'
            
            trades.append(trade)
        
        return trades
    
    def extract_all_trades_from_recent_conversations(self, days: int = 1) -> List[Dict]:
        """从最近的对话中提取所有交易记录"""
        db = TraderDBManager('de')
        conn = db._get_connection()
        
        start_date = datetime.now() - timedelta(days=days)
        start_timestamp = start_date.strftime('%Y-%m-%d %H:%M:%S')
        
        # 查询包含交易操作的对话
        conversations = conn.execute('''
            SELECT id, timestamp, trader_message, btc_price
            FROM conversations
            WHERE (trader_message LIKE '%加仓%' OR trader_message LIKE '%减仓%'
                   OR trader_message LIKE '%滚仓%' OR trader_message LIKE '%加%'
                   OR trader_message LIKE '%减%' OR trader_message LIKE '%876%'
                   OR trader_message LIKE '%881%' OR trader_message LIKE '%888%'
                   OR trader_message LIKE '%883%' OR trader_message LIKE '%885%'
                   OR trader_message LIKE '%895%' OR trader_message LIKE '%893%')
            AND timestamp >= ?
            ORDER BY timestamp ASC
        ''', [start_timestamp]).fetchall()
        
        all_trades = []
        for conv in conversations:
            conv_id = conv[0]
            timestamp = conv[1]
            message = conv[2] if len(conv) > 2 else ''
            btc_price = conv[3] if len(conv) > 3 else None
            
            if message:
                trades = self.extract_trades_from_conversation(
                    conv_id, timestamp, message, btc_price
                )
                all_trades.extend(trades)
        
        conn.close()
        return all_trades

def extract_and_save_trades(days: int = 1):
    """提取并保存交易记录"""
    extractor = TradeExtractor()
    db = TraderDBManager('de')
    
    print("=" * 80)
    print("从对话中提取交易记录")
    print("=" * 80)
    print()
    
    # 提取交易记录
    trades = extractor.extract_all_trades_from_recent_conversations(days)
    
    if not trades:
        print("⚠️ 没有找到可提取的交易记录")
        return
    
    print(f"找到 {len(trades)} 条交易操作")
    print()
    
    # 显示提取的交易记录
    print("提取的交易记录：")
    print()
    for i, trade in enumerate(trades, 1):
        print(f"{i}. {trade['timestamp']}")
        print(f"   操作: {trade['action_type']}")
        if trade.get('entry_price'):
            print(f"   入场价: ${trade['entry_price']:,.0f}")
        if trade.get('exit_price'):
            print(f"   出场价: ${trade['exit_price']:,.0f}")
        print(f"   描述: {trade['description']}")
        print(f"   关联对话ID: {trade['related_conversation_id']}")
        print()
    
    # 确认保存
    print("=" * 80)
    confirm = input("确认保存这些交易记录? (y/n): ").strip().lower()
    
    if confirm not in ['y', 'yes', '是']:
        print("已取消")
        return
    
    # 保存到数据库
    saved_count = 0
    for trade in trades:
        try:
            # 检查是否已存在（避免重复）
            conn = db._get_connection()
            existing = conn.execute('''
                SELECT id FROM trade_records
                WHERE timestamp = ? AND entry_price = ? AND exit_price = ?
            ''', [trade['timestamp'], trade.get('entry_price'), trade.get('exit_price')]).fetchone()
            
            if existing:
                print(f"⚠️ 交易记录已存在，跳过: {trade['description']}")
                continue
            
            # 构建text_content（包含原始对话信息）
            text_content = trade['description']
            if trade.get('related_conversation_id'):
                text_content += f"\n关联对话ID: {trade['related_conversation_id']}"
            
                trade_id = db.add_trade_record(
                    timestamp=trade['timestamp'],
                    symbol=trade['symbol'],
                    direction=trade['direction'],
                    entry_price=trade.get('entry_price'),
                    exit_price=trade.get('exit_price'),
                    strategy='滚仓策略',
                    text_content=text_content,
                    source='conversation_extraction'
                )
                
                # 记录交易记录提取操作
                if SYSTEM_LOGGER_AVAILABLE:
                    get_system_logger().log_trade_record(
                        action='extract',
                        trade_id=trade_id,
                        conversation_id=trade.get('related_conversation_id'),
                        details={
                            'description': trade['description'],
                            'action_type': trade.get('action_type'),
                            'entry_price': trade.get('entry_price'),
                            'exit_price': trade.get('exit_price')
                        }
                    )
                
                saved_count += 1
                print(f"✓ 已保存: {trade['description']} (ID: {trade_id})")
            
        except Exception as e:
            print(f"❌ 保存失败: {trade['description']} - {e}")
    
    db.close()
    
    print()
    print("=" * 80)
    print(f"完成！共保存 {saved_count} 条交易记录")
    print("=" * 80)

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='从对话中提取交易记录')
    parser.add_argument('--days', type=int, default=1, help='查询最近N天的对话（默认1天）')
    parser.add_argument('--auto', action='store_true', help='自动保存，不询问确认')
    
    args = parser.parse_args()
    
    if args.auto:
        # 自动模式
        extractor = TradeExtractor()
        trades = extractor.extract_all_trades_from_recent_conversations(args.days)
        
        db = TraderDBManager('de')
        saved_count = 0
        
        for trade in trades:
            try:
                conn = db._get_connection()
                existing = conn.execute('''
                    SELECT id FROM trade_records
                    WHERE timestamp = ? AND entry_price = ? AND exit_price = ?
                ''', [trade['timestamp'], trade.get('entry_price'), trade.get('exit_price')]).fetchone()
                
                if existing:
                    continue
                
                text_content = trade['description']
                if trade.get('related_conversation_id'):
                    text_content += f"\n关联对话ID: {trade['related_conversation_id']}"
                
                trade_id = db.add_trade_record(
                    timestamp=trade['timestamp'],
                    symbol=trade['symbol'],
                    direction=trade['direction'],
                    entry_price=trade.get('entry_price'),
                    exit_price=trade.get('exit_price'),
                    strategy='滚仓策略',
                    text_content=text_content,
                    source='conversation_extraction'
                )
                
                # 记录交易记录提取操作
                if SYSTEM_LOGGER_AVAILABLE:
                    get_system_logger().log_trade_record(
                        action='extract',
                        trade_id=trade_id,
                        conversation_id=trade.get('related_conversation_id'),
                        details={
                            'description': trade['description'],
                            'action_type': trade.get('action_type')
                        }
                    )
                
                saved_count += 1
            except Exception as e:
                print(f"错误: {e}")
        
        db.close()
        print(f"自动保存完成，共保存 {saved_count} 条交易记录")
    else:
        extract_and_save_trades(args.days)

