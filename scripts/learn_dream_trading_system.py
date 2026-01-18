#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从Dream的对话中深入学习交易系统
分析交易理念、技术方法、入场/出场规则、风险管理等
"""
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import defaultdict, Counter
import re
import json

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 添加src目录到路径
SRC = Path(__file__).resolve().parent.parent / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager

class DreamTradingSystemAnalyzer:
    """Dream交易系统分析器"""
    
    def __init__(self):
        self.db = TraderDBManager('dream')
        self.conversations = []
        self.insights = {
            'trading_philosophy': [],      # 交易理念
            'entry_rules': [],              # 入场规则
            'exit_rules': [],               # 出场规则
            'risk_management': [],          # 风险管理
            'technical_analysis': [],       # 技术分析
            'market_judgment': [],          # 市场判断
            'trading_psychology': [],       # 交易心态
            'patterns': defaultdict(list), # 交易模式
        }
        
        # 关键词模式
        self.patterns = {
            'entry': [
                r'开(多|空|仓)',
                r'做(多|空)',
                r'入场',
                r'进场',
                r'买(入|点)',
                r'卖(出|点)',
                r'long|short',
                r'开在',
                r'挂在',
            ],
            'exit': [
                r'止(盈|损)',
                r'平仓',
                r'清仓',
                r'出(场|局)',
                r'SL|TP',
                r'止损|止盈',
                r'目标',
            ],
            'risk': [
                r'止损',
                r'风控',
                r'风险',
                r'仓位',
                r'杠杆',
                r'防守',
                r'不破',
                r'破位',
            ],
            'technical': [
                r'K线',
                r'均线',
                r'EMA|MA|SMA',
                r'支撑|阻力',
                r'趋势',
                r'突破',
                r'回调',
                r'反弹',
                r'MACD|RSI',
                r'VWAP',
                r'FVG',
                r'缺口',
            ],
            'judgment': [
                r'看(多|空|涨|跌)',
                r'偏(多|空)',
                r'可能',
                r'应该',
                r'建议',
                r'机会',
                r'风险',
                r'谨慎',
            ],
        }
    
    def load_conversations(self):
        """加载所有对话"""
        print("📥 加载Dream的对话...")
        conn = self.db._get_connection()
        rows = conn.execute('''
            SELECT timestamp, trader_message, extracted_content
            FROM conversations 
            WHERE source = ? AND trader_message IS NOT NULL
            ORDER BY timestamp
        ''', ('dream',)).fetchall()
        
        for row in rows:
            self.conversations.append({
                'timestamp': row[0],
                'text': row[1],
                'extracted': row[2] if len(row) > 2 else None
            })
        
        print(f"   ✓ 加载了 {len(self.conversations)} 条对话\n")
    
    def extract_trading_insights(self):
        """提取交易洞察"""
        print("🔍 分析交易系统要素...\n")
        
        for conv in self.conversations:
            text = conv['text']
            if not text or len(text) < 5:
                continue
            
            # 1. 交易理念（较长且包含交易相关关键词）
            if len(text) > 50 and any(kw in text for kw in ['交易', '系统', '策略', '方法', '理念', '原则']):
                self.insights['trading_philosophy'].append({
                    'text': text,
                    'timestamp': conv['timestamp']
                })
            
            # 2. 入场规则
            if any(re.search(p, text, re.IGNORECASE) for p in self.patterns['entry']):
                if any(kw in text for kw in ['条件', '规则', '信号', '时机', '位置']):
                    self.insights['entry_rules'].append({
                        'text': text,
                        'timestamp': conv['timestamp']
                    })
            
            # 3. 出场规则
            if any(re.search(p, text, re.IGNORECASE) for p in self.patterns['exit']):
                self.insights['exit_rules'].append({
                    'text': text,
                    'timestamp': conv['timestamp']
                })
            
            # 4. 风险管理
            if any(re.search(p, text, re.IGNORECASE) for p in self.patterns['risk']):
                self.insights['risk_management'].append({
                    'text': text,
                    'timestamp': conv['timestamp']
                })
            
            # 5. 技术分析
            if any(re.search(p, text, re.IGNORECASE) for p in self.patterns['technical']):
                self.insights['technical_analysis'].append({
                    'text': text,
                    'timestamp': conv['timestamp']
                })
            
            # 6. 市场判断
            if any(re.search(p, text, re.IGNORECASE) for p in self.patterns['judgment']):
                self.insights['market_judgment'].append({
                    'text': text,
                    'timestamp': conv['timestamp']
                })
            
            # 7. 交易心态
            if any(kw in text for kw in ['心态', '情绪', '冷静', '耐心', '纪律', '执行', '坚持']):
                self.insights['trading_psychology'].append({
                    'text': text,
                    'timestamp': conv['timestamp']
                })
        
        # 统计
        print("📊 提取结果:")
        for key, items in self.insights.items():
            if key != 'patterns':
                print(f"   - {key}: {len(items)} 条")
        print()
    
    def analyze_patterns(self):
        """分析交易模式"""
        print("🔬 分析交易模式...\n")
        
        # 分析常见币种
        symbols = Counter()
        directions = Counter()
        time_patterns = defaultdict(int)
        
        for conv in self.conversations:
            text = conv['text'].upper()
            
            # 提取币种（简单模式）
            for match in re.finditer(r'\b([A-Z]{2,10})/USDT\b', text):
                symbols[match.group(1)] += 1
            
            # 提取方向
            if '多' in text or 'LONG' in text:
                directions['long'] += 1
            if '空' in text or 'SHORT' in text:
                directions['short'] += 1
            
            # 时间模式（如果有时间信息）
            if conv['timestamp']:
                try:
                    dt = datetime.strptime(conv['timestamp'], '%Y-%m-%d %H:%M:%S')
                    hour = dt.hour
                    if 0 <= hour < 6:
                        time_patterns['凌晨(0-6点)'] += 1
                    elif 6 <= hour < 12:
                        time_patterns['上午(6-12点)'] += 1
                    elif 12 <= hour < 18:
                        time_patterns['下午(12-18点)'] += 1
                    else:
                        time_patterns['晚上(18-24点)'] += 1
                except:
                    pass
        
        self.insights['patterns']['symbols'] = dict(symbols.most_common(20))
        self.insights['patterns']['directions'] = dict(directions)
        self.insights['patterns']['time_distribution'] = dict(time_patterns)
        
        print("   ✓ 模式分析完成\n")
    
    def generate_report(self) -> str:
        """生成学习报告"""
        print("📝 生成学习报告...\n")
        
        lines = [
            "# Dream 交易系统深度学习报告",
            "",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"分析对话数: {len(self.conversations)}",
            "",
            "---",
            "",
            "## 📚 目录",
            "",
            "1. [交易理念](#1-交易理念)",
            "2. [入场规则](#2-入场规则)",
            "3. [出场规则](#3-出场规则)",
            "4. [风险管理](#4-风险管理)",
            "5. [技术分析方法](#5-技术分析方法)",
            "6. [市场判断逻辑](#6-市场判断逻辑)",
            "7. [交易心态](#7-交易心态)",
            "8. [交易模式统计](#8-交易模式统计)",
            "",
            "---",
            "",
        ]
        
        # 1. 交易理念
        lines.extend([
            "## 1. 交易理念",
            "",
            "### 核心理念",
            ""
        ])
        for i, item in enumerate(self.insights['trading_philosophy'][:20], 1):
            lines.append(f"#### 理念 {i}")
            lines.append(f"**时间**: {item['timestamp']}")
            lines.append("")
            lines.append(f"> {item['text']}")
            lines.append("")
        
        # 2. 入场规则
        lines.extend([
            "## 2. 入场规则",
            "",
            "### 入场条件和信号",
            ""
        ])
        for i, item in enumerate(self.insights['entry_rules'][:30], 1):
            lines.append(f"**{item['timestamp']}**")
            lines.append(f"- {item['text']}")
            lines.append("")
        
        # 3. 出场规则
        lines.extend([
            "## 3. 出场规则",
            "",
            "### 止盈止损策略",
            ""
        ])
        for i, item in enumerate(self.insights['exit_rules'][:30], 1):
            lines.append(f"**{item['timestamp']}**")
            lines.append(f"- {item['text']}")
            lines.append("")
        
        # 4. 风险管理
        lines.extend([
            "## 4. 风险管理",
            "",
            "### 风险控制方法",
            ""
        ])
        for i, item in enumerate(self.insights['risk_management'][:30], 1):
            lines.append(f"**{item['timestamp']}**")
            lines.append(f"- {item['text']}")
            lines.append("")
        
        # 5. 技术分析
        lines.extend([
            "## 5. 技术分析方法",
            "",
            "### 使用的技术指标和工具",
            ""
        ])
        for i, item in enumerate(self.insights['technical_analysis'][:40], 1):
            lines.append(f"**{item['timestamp']}**")
            lines.append(f"- {item['text']}")
            lines.append("")
        
        # 6. 市场判断
        lines.extend([
            "## 6. 市场判断逻辑",
            "",
            "### 市场分析和判断",
            ""
        ])
        for i, item in enumerate(self.insights['market_judgment'][:40], 1):
            lines.append(f"**{item['timestamp']}**")
            lines.append(f"- {item['text']}")
            lines.append("")
        
        # 7. 交易心态
        lines.extend([
            "## 7. 交易心态",
            "",
            "### 心态和经验分享",
            ""
        ])
        for i, item in enumerate(self.insights['trading_psychology'][:20], 1):
            lines.append(f"**{item['timestamp']}**")
            lines.append(f"> {item['text']}")
            lines.append("")
        
        # 8. 交易模式统计
        lines.extend([
            "## 8. 交易模式统计",
            "",
            "### 常用币种",
            ""
        ])
        if 'symbols' in self.insights['patterns']:
            for symbol, count in list(self.insights['patterns']['symbols'].items())[:20]:
                lines.append(f"- **{symbol}**: {count} 次提及")
            lines.append("")
        
        lines.extend([
            "### 方向偏好",
            ""
        ])
        if 'directions' in self.insights['patterns']:
            for direction, count in self.insights['patterns']['directions'].items():
                lines.append(f"- **{direction}**: {count} 次")
            lines.append("")
        
        lines.extend([
            "### 交易时间分布",
            ""
        ])
        if 'time_distribution' in self.insights['patterns']:
            for period, count in self.insights['patterns']['time_distribution'].items():
                lines.append(f"- **{period}**: {count} 条消息")
            lines.append("")
        
        return '\n'.join(lines)
    
    def save_report(self, report: str):
        """保存报告"""
        out_dir = Path('outputs') / 'dream'
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = out_dir / f'dream_trading_system_analysis_{ts}.md'
        report_path.write_text(report, encoding='utf-8')
        print(f"✅ 报告已保存: {report_path}")
        return report_path

def main():
    analyzer = DreamTradingSystemAnalyzer()
    
    # 加载对话
    analyzer.load_conversations()
    
    # 提取洞察
    analyzer.extract_trading_insights()
    
    # 分析模式
    analyzer.analyze_patterns()
    
    # 生成报告
    report = analyzer.generate_report()
    
    # 保存报告
    report_path = analyzer.save_report(report)
    
    # 打开报告
    import subprocess
    try:
        subprocess.Popen(['notepad.exe', str(report_path)])
    except:
        print(f"\n📄 请手动打开报告: {report_path}")
    
    analyzer.db.close()
    print("\n✅ 分析完成！")

if __name__ == '__main__':
    main()



