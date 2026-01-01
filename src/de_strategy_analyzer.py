#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
De.策略分析器
分析对话和交易记录，生成策略分析报告
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from collections import Counter, defaultdict

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

class DeStrategyAnalyzer:
    """De.策略分析器"""
    
    def __init__(self, trader_id='de'):
        self.trader_id = trader_id
        self.db = TraderDBManager(trader_id)
        self.extractor = DeStrategyExtractor()
    
    def analyze_recent_strategies(self, days: int = 7) -> Dict:
        """
        分析最近N天的策略
        
        Args:
            days: 分析天数
        
        Returns:
            策略分析结果
        """
        # 计算起始时间
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        start_timestamp = start_date.strftime('%Y-%m-%d %H:%M:%S')
        
        # 获取对话记录
        conn = self.db._get_connection()
        conversations = conn.execute('''
            SELECT * FROM conversations
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
        ''', [start_timestamp]).fetchall()
        
        # 获取观点记录
        viewpoints = conn.execute('''
            SELECT * FROM trader_viewpoints
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
        ''', [start_timestamp]).fetchall()
        
        # 获取交易记录
        trade_records = conn.execute('''
            SELECT * FROM trade_records
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
        ''', [start_timestamp]).fetchall()
        
        conn.close()
        
        # 分析策略
        analysis = {
            'period': {
                'start': start_timestamp,
                'end': end_date.strftime('%Y-%m-%d %H:%M:%S'),
                'days': days
            },
            'statistics': {
                'total_conversations': len(conversations),
                'total_viewpoints': len(viewpoints),
                'total_trades': len(trade_records)
            },
            'strategy_frequency': {},
            'action_frequency': {},
            'concept_frequency': {},
            'category_distribution': {},
            'price_ranges': {},
            'strategy_patterns': [],
            'recent_strategies': []
        }
        
        # 统计策略频率
        all_strategies = []
        all_actions = []
        all_concepts = []
        all_categories = []
        price_list = []
        
        # 从对话中提取策略
        for conv in conversations:
            trader_msg = conv[3] if len(conv) > 3 else ''  # trader_message字段
            if trader_msg:
                strategy_info = self.extractor.extract_strategy_info(trader_msg)
                all_strategies.extend(strategy_info.get('strategy', []))
                all_actions.extend(strategy_info.get('actions', []))
                all_concepts.extend(strategy_info.get('concepts', []))
                all_categories.append(strategy_info.get('category', 'conversation'))
                price_list.extend(strategy_info.get('prices', []))
        
        # 从观点中提取策略
        for vp in viewpoints:
            content = vp[1] if len(vp) > 1 else ''  # content字段
            if content:
                strategy_info = self.extractor.extract_strategy_info(content)
                all_strategies.extend(strategy_info.get('strategy', []))
                all_actions.extend(strategy_info.get('actions', []))
                all_concepts.extend(strategy_info.get('concepts', []))
        
        # 统计频率
        analysis['strategy_frequency'] = dict(Counter(all_strategies))
        analysis['action_frequency'] = dict(Counter(all_actions))
        analysis['concept_frequency'] = dict(Counter(all_concepts))
        analysis['category_distribution'] = dict(Counter(all_categories))
        
        # 分析价格区间
        if price_list:
            price_list = sorted(price_list)
            analysis['price_ranges'] = {
                'min': min(price_list),
                'max': max(price_list),
                'avg': sum(price_list) / len(price_list),
                'count': len(price_list)
            }
        
        # 分析最近的策略
        recent_strategies = []
        for conv in conversations[:20]:  # 最近20条
            trader_msg = conv[3] if len(conv) > 3 else ''
            timestamp = conv[1] if len(conv) > 1 else ''
            if trader_msg:
                strategy_info = self.extractor.extract_strategy_info(trader_msg)
                if strategy_info.get('category') != 'conversation':
                    recent_strategies.append({
                        'timestamp': timestamp,
                        'content': trader_msg[:50] + '...' if len(trader_msg) > 50 else trader_msg,
                        'category': strategy_info.get('category'),
                        'strategies': strategy_info.get('strategy', []),
                        'actions': strategy_info.get('actions', []),
                        'prices': strategy_info.get('prices', [])
                    })
        
        analysis['recent_strategies'] = recent_strategies
        
        # 分析交易记录
        if trade_records:
            analysis['trade_statistics'] = self._analyze_trades(trade_records)
        
        return analysis
    
    def _analyze_trades(self, trade_records: List) -> Dict:
        """分析交易记录"""
        stats = {
            'total_trades': len(trade_records),
            'long_count': 0,
            'short_count': 0,
            'total_profit_pct': 0.0,
            'total_profit_usdt': 0.0,
            'winning_trades': 0,
            'losing_trades': 0,
            'avg_profit_pct': 0.0,
            'avg_profit_usdt': 0.0
        }
        
        for trade in trade_records:
            direction = trade[4] if len(trade) > 4 else None  # direction字段
            profit_pct = trade[8] if len(trade) > 8 else 0.0  # profit_pct字段
            profit_usdt = trade[9] if len(trade) > 9 else 0.0  # profit_usdt字段
            
            if direction == 'long':
                stats['long_count'] += 1
            elif direction == 'short':
                stats['short_count'] += 1
            
            if profit_pct:
                stats['total_profit_pct'] += profit_pct
                if profit_pct > 0:
                    stats['winning_trades'] += 1
                else:
                    stats['losing_trades'] += 1
            
            if profit_usdt:
                stats['total_profit_usdt'] += profit_usdt
        
        if stats['total_trades'] > 0:
            stats['avg_profit_pct'] = stats['total_profit_pct'] / stats['total_trades']
            stats['avg_profit_usdt'] = stats['total_profit_usdt'] / stats['total_trades']
        
        return stats
    
    def generate_report(self, days: int = 7, output_file: Optional[str] = None) -> str:
        """
        生成策略分析报告
        
        Args:
            days: 分析天数
            output_file: 输出文件路径（可选）
        
        Returns:
            Markdown格式的报告
        """
        analysis = self.analyze_recent_strategies(days)
        
        report = []
        report.append("# De.交易策略分析报告")
        report.append("")
        report.append(f"**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**分析周期**: {analysis['period']['start']} 至 {analysis['period']['end']} ({analysis['period']['days']}天)")
        report.append("")
        
        # 统计数据
        report.append("## 一、数据统计")
        report.append("")
        stats = analysis['statistics']
        report.append(f"- 对话记录: {stats['total_conversations']} 条")
        report.append(f"- 观点记录: {stats['total_viewpoints']} 条")
        report.append(f"- 交易记录: {stats['total_trades']} 条")
        report.append("")
        
        # 策略频率
        report.append("## 二、策略使用频率")
        report.append("")
        if analysis['strategy_frequency']:
            report.append("### 2.1 策略类型")
            report.append("")
            sorted_strategies = sorted(analysis['strategy_frequency'].items(), key=lambda x: x[1], reverse=True)
            for strategy, count in sorted_strategies[:10]:  # 前10个
                report.append(f"- **{strategy}**: {count} 次")
            report.append("")
        else:
            report.append("暂无策略数据")
            report.append("")
        
        # 动作频率
        if analysis['action_frequency']:
            report.append("### 2.2 交易动作")
            report.append("")
            sorted_actions = sorted(analysis['action_frequency'].items(), key=lambda x: x[1], reverse=True)
            for action, count in sorted_actions:
                report.append(f"- **{action}**: {count} 次")
            report.append("")
        
        # 概念频率
        if analysis['concept_frequency']:
            report.append("### 2.3 策略概念")
            report.append("")
            sorted_concepts = sorted(analysis['concept_frequency'].items(), key=lambda x: x[1], reverse=True)
            for concept, count in sorted_concepts[:10]:
                report.append(f"- **{concept}**: {count} 次")
            report.append("")
        
        # 分类分布
        report.append("## 三、对话分类分布")
        report.append("")
        for category, count in analysis['category_distribution'].items():
            report.append(f"- **{category}**: {count} 条")
        report.append("")
        
        # 价格区间
        if analysis.get('price_ranges'):
            report.append("## 四、价格区间分析")
            report.append("")
            price_ranges = analysis['price_ranges']
            report.append(f"- 最低价格: ${price_ranges['min']:,.0f}")
            report.append(f"- 最高价格: ${price_ranges['max']:,.0f}")
            report.append(f"- 平均价格: ${price_ranges['avg']:,.0f}")
            report.append(f"- 价格提及次数: {price_ranges['count']} 次")
            report.append("")
        
        # 交易统计
        if analysis.get('trade_statistics'):
            report.append("## 五、交易统计")
            report.append("")
            trade_stats = analysis['trade_statistics']
            report.append(f"- 总交易次数: {trade_stats['total_trades']} 次")
            report.append(f"- 做多次数: {trade_stats['long_count']} 次")
            report.append(f"- 做空次数: {trade_stats['short_count']} 次")
            if trade_stats['total_trades'] > 0:
                report.append(f"- 平均收益率: {trade_stats['avg_profit_pct']:+.2f}%")
                report.append(f"- 平均盈利: {trade_stats['avg_profit_usdt']:+,.2f} USDT")
                report.append(f"- 盈利次数: {trade_stats['winning_trades']} 次")
                report.append(f"- 亏损次数: {trade_stats['losing_trades']} 次")
            report.append("")
        
        # 最近策略
        if analysis['recent_strategies']:
            report.append("## 六、最近策略示例")
            report.append("")
            for strategy in analysis['recent_strategies'][:10]:  # 最近10条
                report.append(f"### {strategy['timestamp']}")
                report.append("")
                report.append(f"**内容**: {strategy['content']}")
                report.append(f"**分类**: {strategy['category']}")
                if strategy.get('strategies'):
                    report.append(f"**策略**: {', '.join(strategy['strategies'])}")
                if strategy.get('actions'):
                    report.append(f"**动作**: {', '.join(strategy['actions'])}")
                if strategy.get('prices'):
                    report.append(f"**价格**: {', '.join([f'${p:,.0f}' for p in strategy['prices']])}")
                report.append("")
        
        report.append("---")
        report.append("")
        report.append(f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        
        report_text = '\n'.join(report)
        
        # 保存到文件
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"报告已保存到: {output_path}")
        
        return report_text

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='De.策略分析报告生成器')
    parser.add_argument('--days', type=int, default=7, help='分析天数（默认7天）')
    parser.add_argument('--output', type=str, help='输出文件路径（可选）')
    
    args = parser.parse_args()
    
    analyzer = DeStrategyAnalyzer()
    report = analyzer.generate_report(days=args.days, output_file=args.output)
    
    print(report)

if __name__ == '__main__':
    main()


