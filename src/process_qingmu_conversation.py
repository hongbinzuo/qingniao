#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
处理青沐（De.）的完整对话文件
功能：
1. 解析Discord JSON导出文件
2. 提取De.的所有消息
3. 使用BTC价格缓存（优先本地缓存）
4. 去重处理（检查数据库是否已存在）
5. 分类和提取交易信息
6. 导入到数据库
7. 分析与现有系统的冲突和优化点
"""

import json
import re
import sys
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set, Optional, Tuple
from collections import defaultdict

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

# 对话文件路径
DIALOG_FILE = r"C:\Users\zuoho\Downloads\discord-msg\梦之队 - 梦梦 - 青沐 [1428778462981918951].html"

class QingmuConversationProcessor:
    """青沐对话处理器"""
    
    def __init__(self, trader_id='de'):
        self.trader_id = trader_id
        self.db = TraderDBManager(trader_id)
        self.processed_hashes: Set[str] = set()
        self.stats = {
            'total_messages': 0,
            'de_messages': 0,
            'duplicates': 0,
            'processed': 0,
            'errors': 0,
            'with_price': 0,
            'trading_signals': 0,
            'viewpoints': 0,
            'executions': 0
        }
        
        # 加载已存在的记录哈希（用于去重）
        self._load_existing_hashes()
    
    def _load_existing_hashes(self):
        """加载数据库中已存在的记录哈希"""
        try:
            conn = self.db._get_connection()
            # 查询所有已存在的对话和观点
            conversations = conn.execute('SELECT timestamp, trader_message FROM conversations WHERE trader_message IS NOT NULL').fetchall()
            viewpoints = conn.execute('SELECT timestamp, content FROM trader_viewpoints WHERE content IS NOT NULL').fetchall()
            
            for row in conversations:
                timestamp = row[0] if len(row) > 0 else ''
                content = row[1] if len(row) > 1 else ''
                if content:
                    hash_val = self._create_hash(content, timestamp)
                    self.processed_hashes.add(hash_val)
            
            for row in viewpoints:
                timestamp = row[0] if len(row) > 0 else ''
                content = row[1] if len(row) > 1 else ''
                if content:
                    hash_val = self._create_hash(content, timestamp)
                    self.processed_hashes.add(hash_val)
            
            print(f"  已加载 {len(self.processed_hashes)} 条已存在记录的哈希")
        except Exception as e:
            print(f"  加载已存在记录失败: {e}", file=sys.stderr)
    
    def _create_hash(self, content: str, timestamp: str) -> str:
        """创建内容哈希用于去重"""
        normalized_content = re.sub(r'\s+', ' ', content.strip())
        combined = f"{timestamp}|{normalized_content}"
        return hashlib.md5(combined.encode('utf-8')).hexdigest()
    
    def _is_duplicate(self, content: str, timestamp: str) -> bool:
        """检查是否重复"""
        hash_val = self._create_hash(content, timestamp)
        if hash_val in self.processed_hashes:
            return True
        self.processed_hashes.add(hash_val)
        return False
    
    def _normalize_timestamp(self, timestamp_str: str) -> str:
        """标准化时间戳"""
        try:
            # 处理ISO格式: 2025-10-18T00:15:42.698+08:00
            if 'T' in timestamp_str:
                dt_str = timestamp_str.replace('+08:00', '').split('.')[0]
                dt = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S')
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # 尝试其他格式
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y/%m/%d %H:%M:%S',
                '%Y-%m-%d %H:%M',
                '%Y/%m/%d %H:%M'
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(timestamp_str, fmt)
                    return dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    continue
            
            return timestamp_str
        except Exception as e:
            print(f"  时间戳标准化失败: {e}", file=sys.stderr)
            return timestamp_str
    
    def _classify_content(self, content: str, has_attachments: bool = False) -> Tuple[str, str]:
        """
        分类内容
        
        Returns:
            (category, confidence) - 类别和置信度
        """
        content_lower = content.lower()
        
        # 交易执行记录特征
        execution_keywords = [
            r'已经', r'目前', r'昨天', r'今天', r'刚才',
            r'止盈了', r'止损了', r'吃了', r'拿下', r'成交了',
            r'扫了', r'追单', r'执行了', r'平了',
            r'盈利', r'亏损', r'赚了', r'亏了',
            r'\d+点', r'已经.*点', r'目前.*点'
        ]
        
        # 交易信号特征
        signal_keywords = [
            r'可以', r'应该', r'建议', r'可以空', r'可以多',
            r'看起来', r'很好', r'机会', r'可以进',
            r'目标', r'止损', r'止盈', r'挂',
            r'如果.*可以', r'如果.*应该', r'建议.*挂'
        ]
        
        # 观点特征
        viewpoint_keywords = [
            r'理论', r'逻辑', r'道理', r'意义', r'概念',
            r'认为', r'觉得', r'应该', r'可能', r'大概',
            r'永远', r'都是', r'不是', r'没有',
            r'策略', r'方法', r'方式', r'理念',
            r'因为', r'所以', r'但是', r'如果',
            r'组织', r'庄家', r'巨鲸', r'市场'
        ]
        
        execution_score = sum(1 for kw in execution_keywords if re.search(kw, content))
        signal_score = sum(1 for kw in signal_keywords if re.search(kw, content))
        viewpoint_score = sum(1 for kw in viewpoint_keywords if re.search(kw, content))
        
        has_price_and_action = bool(re.search(r'\d{3,6}', content)) and (
            '止盈' in content or '止损' in content or '空' in content or '多' in content or
            '吃了' in content or '拿下' in content or '点' in content
        )
        
        if has_attachments:
            execution_score += 2
        
        if execution_score >= 2 or (has_price_and_action and execution_score >= 1):
            return ('trading_execution', 'high')
        elif signal_score >= 2 or (has_price_and_action and signal_score >= 1):
            return ('trading_signal', 'high')
        elif viewpoint_score >= 2:
            return ('viewpoint', 'high')
        elif has_price_and_action:
            return ('trading_signal', 'medium')
        else:
            return ('conversation', 'low')
    
    def _extract_tags(self, content: str) -> List[str]:
        """提取标签"""
        tags = []
        
        # 交易相关标签
        if '挂单' in content or '挂' in content:
            tags.append('挂单')
        if '止损' in content:
            tags.append('止损')
        if '止盈' in content:
            tags.append('止盈')
        if '保本' in content:
            tags.append('保本')
        if '多' in content or '做多' in content:
            tags.append('做多')
        if '空' in content or '做空' in content:
            tags.append('做空')
        if '加仓' in content:
            tags.append('加仓')
        if '减仓' in content:
            tags.append('减仓')
        
        # 策略相关标签
        if 'Vegas' in content or 'vegas' in content:
            tags.append('Vegas')
        if '突破' in content:
            tags.append('突破')
        if '回踩' in content:
            tags.append('回踩')
        if '支撑' in content:
            tags.append('支撑')
        if '阻力' in content:
            tags.append('阻力')
        
        return tags
    
    def _process_message(self, message: Dict) -> bool:
        """处理单条消息"""
        try:
            # 提取消息信息
            author = message.get('author', {})
            if isinstance(author, dict):
                nickname = author.get('nickname', '')
                name = author.get('name', '')
            else:
                nickname = ''
                name = str(author)
            
            # 只处理De.的消息
            if nickname != 'De.' and 'De.' not in name and 'de.' not in name.lower():
                return False
            
            content = message.get('content', '').strip()
            if not content or len(content) < 3:
                return False
            
            timestamp_str = message.get('timestamp', '')
            if not timestamp_str:
                return False
            
            self.stats['de_messages'] += 1
            
            # 标准化时间戳
            normalized_timestamp = self._normalize_timestamp(timestamp_str)
            
            # 检查重复
            if self._is_duplicate(content, normalized_timestamp):
                self.stats['duplicates'] += 1
                return False
            
            # 获取BTC价格（优先使用时序库缓存）
            btc_price = get_btc_price_cached(timestamp_str, use_api=False)
            if btc_price:
                self.stats['with_price'] += 1
            
            # 分类
            has_attachments = bool(message.get('attachments', []))
            category, confidence = self._classify_content(content, has_attachments)
            
            # 更新统计
            if category == 'trading_execution':
                self.stats['executions'] += 1
            elif category == 'trading_signal':
                self.stats['trading_signals'] += 1
            elif category == 'viewpoint':
                self.stats['viewpoints'] += 1
            
            # 提取标签
            tags = self._extract_tags(content)
            
            # 构建完整内容
            full_content = content
            if btc_price:
                full_content = f"[BTC价格: ${btc_price:,.2f}] {content}"
            
            # 获取用户消息（前一条消息，如果是@De.的话）
            user_message = None
            # 这里可以添加逻辑来获取上下文
            
            # 保存到数据库
            # 1. 保存对话记录
            conv_id = self.db.add_conversation(
                timestamp=normalized_timestamp,
                user_message=user_message,
                trader_message=content,
                source='discord_export',
                btc_price=btc_price,
                extracted_content=full_content if category != 'conversation' else None
            )
            
            # 2. 如果有交易信息，保存为观点
            if category != 'conversation':
                self.db.add_viewpoint(
                    content=full_content,
                    timestamp=normalized_timestamp,
                    source='discord_export',
                    category=category,
                    tags=tags if tags else None,
                    btc_price=btc_price,
                    related_conversation_id=conv_id
                )
            
            self.stats['processed'] += 1
            return True
            
        except Exception as e:
            self.stats['errors'] += 1
            print(f"  处理消息失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return False
    
    def process_file(self, file_path: Path):
        """处理对话文件"""
        print("=" * 80)
        print("处理青沐（De.）对话文件")
        print("=" * 80)
        print()
        
        if not file_path.exists():
            print(f"❌ 文件不存在: {file_path}")
            return
        
        print(f"📁 文件: {file_path.name}")
        print()
        
        # 读取JSON文件
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"❌ 读取文件失败: {e}")
            return
        
        # 提取消息
        messages = data.get('messages', [])
        self.stats['total_messages'] = len(messages)
        
        print(f"📊 总消息数: {len(messages)}")
        print()
        
        # 处理消息（批量提交，减少数据库锁定）
        print("开始处理消息...")
        processed_count = 0
        batch_size = 100
        batch = []
        
        for i, msg in enumerate(messages, 1):
            try:
                if self._process_message(msg):
                    processed_count += 1
                    batch.append(msg)
                    
                    # 每100条提交一次事务
                    if len(batch) >= batch_size:
                        try:
                            self.db._get_connection().commit()
                            batch = []
                        except:
                            pass
            except Exception as e:
                self.stats['errors'] += 1
                if i % 100 == 0:
                    print(f"  处理消息时出错: {e}", file=sys.stderr)
            
            if i % 100 == 0:
                print(f"  已处理 {i}/{len(messages)} 条消息... (De.消息: {self.stats['de_messages']}, 已导入: {processed_count})")
        
        # 提交剩余批次
        try:
            if batch:
                self.db._get_connection().commit()
        except:
            pass
        
        print()
        print("=" * 80)
        print("处理完成！统计信息:")
        print("=" * 80)
        print(f"  总消息数: {self.stats['total_messages']}")
        print(f"  De.消息数: {self.stats['de_messages']}")
        print(f"  重复消息: {self.stats['duplicates']}")
        print(f"  成功处理: {self.stats['processed']}")
        print(f"  带价格记录: {self.stats['with_price']}")
        print(f"  交易执行: {self.stats['executions']}")
        print(f"  交易信号: {self.stats['trading_signals']}")
        print(f"  观点: {self.stats['viewpoints']}")
        print(f"  错误数: {self.stats['errors']}")
        print()
        
        self.db.close()

def main():
    """主函数"""
    file_path = Path(DIALOG_FILE)
    
    processor = QingmuConversationProcessor(trader_id='de')
    processor.process_file(file_path)

if __name__ == '__main__':
    main()

