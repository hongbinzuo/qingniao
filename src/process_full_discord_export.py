#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
处理全量Discord对话导出
功能：
1. 解析Discord导出数据（JSON/CSV/TXT格式）
2. 自动去重
3. 结构化处理
4. 提取De.的观点和交易记录
5. 自动获取BTC价格
6. 正确分类
7. 批量导入数据库
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set
import requests
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

class DiscordConversationProcessor:
    """Discord对话处理器"""
    
    def __init__(self, trader_name='de'):
        self.trader_name = trader_name
        self.db = TraderDBManager(trader_name)
        self.processed_content_hash: Set[str] = set()  # 用于去重
        self.stats = {
            'total_messages': 0,
            'de_messages': 0,
            'duplicates': 0,
            'processed': 0,
            'errors': 0
        }
    
    def get_btc_price_at_time(self, timestamp_str):
        """获取指定时间的BTC价格"""
        try:
            # 支持多种时间格式
            time_formats = [
                '%Y/%m/%d %H:%M',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M',
                '%Y/%m/%d %H:%M:%S'
            ]
            
            dt = None
            for fmt in time_formats:
                try:
                    dt = datetime.strptime(timestamp_str, fmt)
                    break
                except:
                    continue
            
            if not dt:
                return None
            
            unix_ts = int(dt.timestamp())
            
            url = "https://api.gateio.ws/api/v4/spot/candlesticks"
            params = {
                'currency_pair': 'BTC_USDT',
                'interval': '1m',
                'from': unix_ts - 60,
                'to': unix_ts + 60,
                'limit': 3
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    closest_candle = min(data, key=lambda x: abs(int(x[0]) - unix_ts))
                    return float(closest_candle[2])
            
            # 如果1分钟数据失败，尝试5分钟
            params['interval'] = '5m'
            params['from'] = unix_ts - 300
            params['to'] = unix_ts + 300
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    closest_candle = min(data, key=lambda x: abs(int(x[0]) - unix_ts))
                    return float(closest_candle[2])
            
            return None
        except Exception as e:
            print(f"  获取价格失败: {e}")
            return None
    
    def classify_content(self, content: str, has_screenshot: bool = False) -> tuple:
        """分类内容"""
        content_lower = content.lower()
        
        # 交易执行记录特征
        execution_keywords = [
            '已经', '目前', '昨天', '今天', '刚才',
            '止盈了', '止损了', '吃了', '拿下', '成交了',
            '扫了', '追单', '挂单', '执行',
            '盈利', '亏损', '赚了', '亏了',
            '点', '已经.*点', '目前.*点'
        ]
        
        # 交易信号特征
        signal_keywords = [
            '可以', '应该', '建议', '可以空', '可以多',
            '看起来', '很好', '机会', '可以进',
            '目标', '止损', '止盈', '挂',
            '如果.*可以', '如果.*应该'
        ]
        
        # 观点特征
        viewpoint_keywords = [
            '理论', '逻辑', '道理', '意义', '概念',
            '认为', '觉得', '应该', '可能', '大概',
            '永远', '都是', '不是', '没有',
            '策略', '方法', '方式', '理念',
            '因为', '所以', '但是', '如果',
            '组织', '庄家', '巨鲸', '市场'
        ]
        
        execution_score = sum(1 for kw in execution_keywords if re.search(kw, content))
        signal_score = sum(1 for kw in signal_keywords if re.search(kw, content))
        viewpoint_score = sum(1 for kw in viewpoint_keywords if re.search(kw, content))
        
        has_price_and_action = bool(re.search(r'\d{3,4}', content)) and (
            '止盈' in content or '止损' in content or '空' in content or '多' in content or
            '吃了' in content or '拿下' in content or '点' in content
        )
        
        if has_screenshot:
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
    
    def parse_de_instructions(self, content: str) -> Dict:
        """解析De.的交易指令和观点"""
        analysis = {
            'prices': [],
            'actions': [],
            'strategy': [],
            'market_state': [],
            'concepts': [],
            'theories': [],
            'philosophy': [],
            'trading_signal': {},
            'trading_execution': {},
            'trading_philosophy': {}
        }
        
        # 提取价格
        prices = re.findall(r'(\d{3,6})', content)
        for p in prices:
            price_val = int(p)
            if 400 <= price_val <= 100000:  # 合理的价格范围
                analysis['prices'].append(price_val)
        
        # 这里可以添加更多的解析逻辑
        # 根据之前的经验，提取关键概念、策略等
        
        return analysis
    
    def normalize_timestamp(self, timestamp_str: str) -> str:
        """标准化时间戳"""
        time_formats = [
            '%Y/%m/%d %H:%M',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y/%m/%d %H:%M:%S',
            '%Y年%m月%d日 %H:%M',
            '%m/%d/%Y %H:%M:%S',
            '%m/%d/%Y %H:%M'
        ]
        
        for fmt in time_formats:
            try:
                dt = datetime.strptime(timestamp_str, fmt)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                continue
        
        return timestamp_str
    
    def create_content_hash(self, content: str, timestamp: str) -> str:
        """创建内容哈希用于去重"""
        # 去除多余空格和换行
        normalized = re.sub(r'\s+', ' ', content.strip())
        # 组合时间戳和内容
        combined = f"{timestamp}|{normalized}"
        return str(hash(combined))
    
    def is_duplicate(self, content: str, timestamp: str) -> bool:
        """检查是否重复"""
        content_hash = self.create_content_hash(content, timestamp)
        if content_hash in self.processed_content_hash:
            return True
        self.processed_content_hash.add(content_hash)
        return False
    
    def process_message(self, message: Dict) -> bool:
        """处理单条消息"""
        try:
            # 提取消息信息
            author = message.get('author', {}).get('name', '') if isinstance(message.get('author'), dict) else message.get('author', '')
            content = message.get('content', '').strip()
            timestamp_str = message.get('timestamp', '') or message.get('time', '')
            
            # 只处理De.的消息
            if 'De.' not in author and 'de.' not in author.lower():
                return False
            
            if not content:
                return False
            
            self.stats['de_messages'] += 1
            
            # 标准化时间戳
            normalized_timestamp = self.normalize_timestamp(timestamp_str)
            
            # 检查重复
            if self.is_duplicate(content, normalized_timestamp):
                self.stats['duplicates'] += 1
                return False
            
            # 获取BTC价格
            btc_price = self.get_btc_price_at_time(normalized_timestamp)
            
            # 分类
            has_screenshot = 'screenshot' in content.lower() or 'image' in content.lower() or message.get('attachments', [])
            category, confidence = self.classify_content(content, has_screenshot)
            
            # 解析指令
            analysis = self.parse_de_instructions(content)
            
            # 提取标签
            tags = []
            if analysis.get('actions'):
                tags.extend(analysis['actions'])
            if analysis.get('strategy'):
                tags.extend(analysis['strategy'])
            if analysis.get('concepts'):
                tags.extend(analysis['concepts'])
            
            # 构建完整内容
            full_content = content
            if btc_price:
                full_content = f"[BTC价格: ${btc_price:,.2f}] {full_content}"
            if analysis.get('prices'):
                full_content += f"\n[解析价格: {', '.join(map(str, analysis['prices']))}]"
            if analysis.get('concepts'):
                full_content += f"\n[概念: {', '.join(analysis['concepts'])}]"
            
            # 保存到数据库
            self.db.add_viewpoint(
                content=full_content,
                timestamp=normalized_timestamp,
                source='discord_export',
                category=category,
                tags=tags if tags else None,
                btc_price=btc_price
            )
            
            self.stats['processed'] += 1
            return True
            
        except Exception as e:
            self.stats['errors'] += 1
            print(f"  处理消息失败: {e}")
            return False
    
    def process_json_file(self, file_path: Path):
        """处理JSON格式的Discord导出"""
        print(f"处理JSON文件: {file_path.name}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 支持多种JSON格式
        messages = []
        if isinstance(data, list):
            messages = data
        elif isinstance(data, dict):
            # 可能是 {messages: [...]} 格式
            messages = data.get('messages', []) or data.get('data', [])
        
        self.stats['total_messages'] += len(messages)
        
        processed = 0
        for i, msg in enumerate(messages, 1):
            if self.process_message(msg):
                processed += 1
            if i % 100 == 0:
                print(f"  已处理 {i}/{len(messages)} 条消息...")
        
        print(f"  ✅ 处理完成: {processed} 条De.消息")
    
    def process_csv_file(self, file_path: Path):
        """处理CSV格式的Discord导出"""
        import csv
        print(f"处理CSV文件: {file_path.name}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            messages = list(reader)
        
        self.stats['total_messages'] += len(messages)
        
        processed = 0
        for i, row in enumerate(messages, 1):
            # 转换为标准格式
            message = {
                'author': row.get('Author', row.get('author', '')),
                'content': row.get('Content', row.get('content', '')),
                'timestamp': row.get('Timestamp', row.get('timestamp', row.get('Time', '')))
            }
            
            if self.process_message(message):
                processed += 1
            if i % 100 == 0:
                print(f"  已处理 {i}/{len(messages)} 条消息...")
        
        print(f"  ✅ 处理完成: {processed} 条De.消息")
    
    def process_txt_file(self, file_path: Path):
        """处理TXT格式的Discord导出"""
        print(f"处理TXT文件: {file_path.name}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 尝试解析TXT格式（可能是每行一条消息，或特定格式）
        messages = []
        current_message = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 尝试匹配常见格式
            # 格式1: [时间] 作者: 内容
            match = re.match(r'\[(.+?)\]\s*(.+?):\s*(.+)', line)
            if match:
                if current_message:
                    messages.append(current_message)
                current_message = {
                    'timestamp': match.group(1),
                    'author': match.group(2),
                    'content': match.group(3)
                }
            else:
                # 可能是多行内容
                if current_message:
                    current_message['content'] += '\n' + line
        
        if current_message:
            messages.append(current_message)
        
        self.stats['total_messages'] += len(messages)
        
        processed = 0
        for i, msg in enumerate(messages, 1):
            if self.process_message(msg):
                processed += 1
            if i % 100 == 0:
                print(f"  已处理 {i}/{len(messages)} 条消息...")
        
        print(f"  ✅ 处理完成: {processed} 条De.消息")
    
    def process_export_file(self, file_path: Path):
        """处理导出文件（自动识别格式）"""
        suffix = file_path.suffix.lower()
        
        if suffix == '.json':
            self.process_json_file(file_path)
        elif suffix == '.csv':
            self.process_csv_file(file_path)
        elif suffix == '.txt':
            self.process_txt_file(file_path)
        else:
            print(f"  ⚠️  不支持的文件格式: {suffix}")
    
    def process_directory(self, directory: Path):
        """处理目录中的所有导出文件"""
        print("=" * 80)
        print("处理Discord全量导出")
        print("=" * 80)
        print()
        
        # 查找所有可能的导出文件
        json_files = list(directory.glob("*.json"))
        csv_files = list(directory.glob("*.csv"))
        txt_files = list(directory.glob("*.txt"))
        
        all_files = json_files + csv_files + txt_files
        
        if not all_files:
            print(f"❌ 在 {directory} 中未找到导出文件")
            return
        
        print(f"📁 找到 {len(all_files)} 个导出文件")
        print()
        
        for file_path in sorted(all_files):
            self.process_export_file(file_path)
            print()
        
        # 显示统计
        print("=" * 80)
        print("处理完成！统计信息:")
        print("=" * 80)
        print(f"  总消息数: {self.stats['total_messages']}")
        print(f"  De.消息数: {self.stats['de_messages']}")
        print(f"  重复消息: {self.stats['duplicates']}")
        print(f"  成功处理: {self.stats['processed']}")
        print(f"  错误数: {self.stats['errors']}")
        print()
        
        self.db.close()

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='处理Discord全量导出')
    parser.add_argument('input', type=str, help='导出文件或目录路径')
    parser.add_argument('--trader', type=str, default='de', help='交易员名称（默认: de）')
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    
    if not input_path.exists():
        print(f"❌ 路径不存在: {input_path}")
        return
    
    processor = DiscordConversationProcessor(trader_name=args.trader)
    
    if input_path.is_file():
        processor.process_export_file(input_path)
    elif input_path.is_dir():
        processor.process_directory(input_path)
    else:
        print(f"❌ 无效的路径: {input_path}")

if __name__ == '__main__':
    main()

