#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析系统冲突和优化点
比较新导入的对话与现有系统的功能和逻辑
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict
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

class SystemConflictAnalyzer:
    """系统冲突分析器"""
    
    def __init__(self, trader_id='de'):
        self.trader_id = trader_id
        self.db = TraderDBManager(trader_id)
        self.conflicts = []
        self.optimizations = []
    
    def analyze(self):
        """执行分析"""
        print("=" * 80)
        print("系统冲突和优化点分析")
        print("=" * 80)
        print()
        
        # 1. 分析数据一致性
        self._analyze_data_consistency()
        
        # 2. 分析分类逻辑
        self._analyze_classification_logic()
        
        # 3. 分析价格数据
        self._analyze_price_data()
        
        # 4. 分析重复数据
        self._analyze_duplicates()
        
        # 5. 生成报告
        self._generate_report()
        
        self.db.close()
    
    def _analyze_data_consistency(self):
        """分析数据一致性"""
        print("1. 分析数据一致性...")
        
        conn = self.db._get_connection()
        
        # 检查对话和观点的一致性
        conversations = conn.execute('''
            SELECT id, timestamp, trader_message, btc_price, extracted_content
            FROM conversations
            WHERE trader_message IS NOT NULL
            ORDER BY timestamp DESC
            LIMIT 100
        ''').fetchall()
        
        viewpoints = conn.execute('''
            SELECT id, timestamp, content, btc_price, related_conversation_id
            FROM trader_viewpoints
            ORDER BY timestamp DESC
            LIMIT 100
        ''').fetchall()
        
        # 检查时间戳格式一致性
        timestamp_issues = []
        for row in conversations:
            timestamp = row[1]
            if timestamp and not self._is_valid_timestamp(timestamp):
                timestamp_issues.append(f"对话ID {row[0]}: 时间戳格式异常 - {timestamp}")
        
        if timestamp_issues:
            self.conflicts.append({
                'type': '数据一致性',
                'issue': '时间戳格式不一致',
                'details': timestamp_issues[:10]  # 只显示前10个
            })
        
        print(f"  ✓ 检查了 {len(conversations)} 条对话记录")
        print(f"  ✓ 检查了 {len(viewpoints)} 条观点记录")
        if timestamp_issues:
            print(f"  ⚠️  发现 {len(timestamp_issues)} 个时间戳格式问题")
        print()
    
    def _analyze_classification_logic(self):
        """分析分类逻辑"""
        print("2. 分析分类逻辑...")
        
        conn = self.db._get_connection()
        
        # 统计各类别的分布
        category_stats = conn.execute('''
            SELECT category, COUNT(*) as count
            FROM trader_viewpoints
            WHERE category IS NOT NULL
            GROUP BY category
        ''').fetchall()
        
        print("  类别分布:")
        for row in category_stats:
            category, count = row[0], row[1]
            print(f"    {category}: {count} 条")
        
        # 检查是否有未分类的重要消息
        unclassified = conn.execute('''
            SELECT COUNT(*) 
            FROM trader_viewpoints
            WHERE category IS NULL OR category = 'conversation'
            AND (content LIKE '%挂%' OR content LIKE '%止损%' OR content LIKE '%止盈%'
                 OR content LIKE '%多%' OR content LIKE '%空%')
        ''').fetchone()
        
        if unclassified and unclassified[0] > 0:
            self.optimizations.append({
                'type': '分类优化',
                'suggestion': f'发现 {unclassified[0]} 条可能包含交易信息但未正确分类的消息',
                'action': '优化分类逻辑，识别更多交易相关关键词'
            })
        
        print()
    
    def _analyze_price_data(self):
        """分析价格数据"""
        print("3. 分析价格数据...")
        
        conn = self.db._get_connection()
        
        # 统计有价格和无价格的记录
        with_price = conn.execute('''
            SELECT COUNT(*) 
            FROM conversations
            WHERE btc_price IS NOT NULL
        ''').fetchone()[0]
        
        without_price = conn.execute('''
            SELECT COUNT(*) 
            FROM conversations
            WHERE btc_price IS NULL AND trader_message IS NOT NULL
        ''').fetchone()[0]
        
        print(f"  有价格记录: {with_price} 条")
        print(f"  无价格记录: {without_price} 条")
        
        if without_price > with_price:
            self.optimizations.append({
                'type': '价格数据优化',
                'suggestion': f'有 {without_price} 条记录缺少BTC价格数据',
                'action': '使用BTC价格缓存系统补充缺失的价格数据'
            })
        
        print()
    
    def _analyze_duplicates(self):
        """分析重复数据"""
        print("4. 分析重复数据...")
        
        conn = self.db._get_connection()
        
        # 检查可能的重复（相同时间戳和相似内容）
        duplicates = conn.execute('''
            SELECT timestamp, trader_message, COUNT(*) as count
            FROM conversations
            WHERE trader_message IS NOT NULL
            GROUP BY timestamp, trader_message
            HAVING COUNT(*) > 1
        ''').fetchall()
        
        if duplicates:
            self.conflicts.append({
                'type': '数据重复',
                'issue': f'发现 {len(duplicates)} 组重复的对话记录',
                'details': [f"时间戳: {row[0]}, 内容: {row[1][:50]}..." for row in duplicates[:5]]
            })
            print(f"  ⚠️  发现 {len(duplicates)} 组重复记录")
        else:
            print("  ✓ 未发现重复记录")
        
        print()
    
    def _is_valid_timestamp(self, timestamp: str) -> bool:
        """检查时间戳格式是否有效"""
        try:
            datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            return True
        except:
            try:
                datetime.strptime(timestamp, '%Y-%m-%d %H:%M')
                return True
            except:
                return False
    
    def _generate_report(self):
        """生成分析报告"""
        print("=" * 80)
        print("分析报告")
        print("=" * 80)
        print()
        
        if self.conflicts:
            print("⚠️  发现的冲突:")
            for i, conflict in enumerate(self.conflicts, 1):
                print(f"\n{i}. {conflict['type']}: {conflict['issue']}")
                if 'details' in conflict:
                    print("   详情:")
                    for detail in conflict['details']:
                        print(f"     - {detail}")
        else:
            print("✓ 未发现冲突")
        
        print()
        
        if self.optimizations:
            print("💡 优化建议:")
            for i, opt in enumerate(self.optimizations, 1):
                print(f"\n{i}. {opt['type']}")
                print(f"   建议: {opt['suggestion']}")
                print(f"   行动: {opt['action']}")
        else:
            print("✓ 暂无优化建议")
        
        print()
        print("=" * 80)
        
        # 保存报告到文件
        report_file = Path(__file__).parent.parent / f"系统分析报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# 系统冲突和优化点分析报告\n\n")
            f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            if self.conflicts:
                f.write("## ⚠️ 发现的冲突\n\n")
                for i, conflict in enumerate(self.conflicts, 1):
                    f.write(f"### {i}. {conflict['type']}: {conflict['issue']}\n\n")
                    if 'details' in conflict:
                        f.write("详情:\n")
                        for detail in conflict['details']:
                            f.write(f"- {detail}\n")
                    f.write("\n")
            
            if self.optimizations:
                f.write("## 💡 优化建议\n\n")
                for i, opt in enumerate(self.optimizations, 1):
                    f.write(f"### {i}. {opt['type']}\n\n")
                    f.write(f"**建议**: {opt['suggestion']}\n\n")
                    f.write(f"**行动**: {opt['action']}\n\n")
        
        print(f"📄 报告已保存到: {report_file}")

def main():
    """主函数"""
    analyzer = SystemConflictAnalyzer(trader_id='de')
    analyzer.analyze()

if __name__ == '__main__':
    main()







