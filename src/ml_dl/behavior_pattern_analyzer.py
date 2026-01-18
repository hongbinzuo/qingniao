#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易员行为模式分析器
识别De.的交易模式和偏好
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict, Counter
import re

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from db_manager_trader import TraderDBManager


class BehaviorPatternAnalyzer:
    """交易员行为模式分析器"""
    
    def __init__(self, trader_id='de'):
        self.trader_id = trader_id
        self.db = TraderDBManager(trader_id)
    
    def analyze_trading_time_pattern(self) -> Dict:
        """分析交易时间偏好"""
        viewpoints = self.db.get_viewpoints()
        
        time_patterns = {
            'hourly': defaultdict(int),
            'daily': defaultdict(int),
            'weekly': defaultdict(int)
        }
        
        for vp in viewpoints:
            timestamp = vp.get('timestamp')
            if not timestamp:
                continue
            
            try:
                dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            except:
                try:
                    dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M')
                except:
                    continue
            
            # 按小时统计
            hour = dt.hour
            time_patterns['hourly'][hour] += 1
            
            # 按星期统计
            weekday = dt.weekday()  # 0=Monday, 6=Sunday
            time_patterns['weekly'][weekday] += 1
        
        # 找出最活跃的时间
        most_active_hour = max(time_patterns['hourly'].items(), key=lambda x: x[1])[0] if time_patterns['hourly'] else None
        most_active_day = max(time_patterns['weekly'].items(), key=lambda x: x[1])[0] if time_patterns['weekly'] else None
        
        return {
            'hourly_distribution': dict(time_patterns['hourly']),
            'weekly_distribution': dict(time_patterns['weekly']),
            'most_active_hour': most_active_hour,
            'most_active_day': most_active_day,
            'total_records': len(viewpoints)
        }
    
    def analyze_price_range_preference(self) -> Dict:
        """分析价格区间偏好"""
        viewpoints = self.db.get_viewpoints()
        
        price_ranges = defaultdict(int)
        price_list = []
        
        for vp in viewpoints:
            btc_price = vp.get('btc_price')
            if btc_price:
                price_list.append(btc_price)
                # 按1000美元区间分组
                price_range = int(btc_price / 1000) * 1000
                price_ranges[price_range] += 1
        
        if not price_list:
            return {'message': '没有足够的价格数据'}
        
        avg_price = sum(price_list) / len(price_list)
        min_price = min(price_list)
        max_price = max(price_list)
        
        # 找出最活跃的价格区间
        most_active_range = max(price_ranges.items(), key=lambda x: x[1])[0] if price_ranges else None
        
        return {
            'price_ranges': dict(price_ranges),
            'average_price': avg_price,
            'min_price': min_price,
            'max_price': max_price,
            'most_active_range': most_active_range,
            'total_with_price': len(price_list)
        }
    
    def analyze_strategy_preference(self) -> Dict:
        """分析策略偏好"""
        viewpoints = self.db.get_viewpoints()
        
        strategies = Counter()
        directions = Counter()
        keywords = Counter()
        
        for vp in viewpoints:
            content = vp.get('content', '')
            if not content:
                continue
            
            # 提取策略关键词
            strategy_keywords = {
                'Vegas': ['vegas', 'Vegas', '维加斯'],
                'FVG': ['fvg', 'FVG', '回填'],
                'Pinbar': ['pinbar', 'Pinbar', 'pin bar'],
                '突破': ['突破', 'breakout'],
                '回踩': ['回踩', 'pullback'],
                '支撑': ['支撑', 'support'],
                '阻力': ['阻力', 'resistance']
            }
            
            for strategy, keywords_list in strategy_keywords.items():
                if any(kw in content for kw in keywords_list):
                    strategies[strategy] += 1
            
            # 提取方向
            if '多' in content or '做多' in content or 'long' in content.lower():
                directions['long'] += 1
            if '空' in content or '做空' in content or 'short' in content.lower():
                directions['short'] += 1
            
            # 提取其他关键词
            if '挂单' in content:
                keywords['挂单'] += 1
            if '止损' in content:
                keywords['止损'] += 1
            if '止盈' in content:
                keywords['止盈'] += 1
            if '保本' in content:
                keywords['保本'] += 1
        
        return {
            'strategies': dict(strategies),
            'directions': dict(directions),
            'keywords': dict(keywords),
            'total_analyzed': len(viewpoints)
        }
    
    def analyze_category_distribution(self) -> Dict:
        """分析类别分布"""
        viewpoints = self.db.get_viewpoints()
        
        categories = Counter()
        sources = Counter()
        
        for vp in viewpoints:
            category = vp.get('category', 'unknown')
            source = vp.get('source', 'unknown')
            categories[category] += 1
            sources[source] += 1
        
        return {
            'categories': dict(categories),
            'sources': dict(sources),
            'total': len(viewpoints)
        }
    
    def extract_trading_patterns(self) -> Dict:
        """提取交易模式"""
        viewpoints = self.db.get_viewpoints()
        
        patterns = {
            'entry_patterns': [],
            'exit_patterns': [],
            'risk_management': []
        }
        
        for vp in viewpoints:
            content = vp.get('content', '')
            category = vp.get('category', '')
            
            if category == 'trading_signal':
                # 提取入场模式
                if any(kw in content for kw in ['挂', '可以', '建议']):
                    patterns['entry_patterns'].append({
                        'content': content[:100],
                        'timestamp': vp.get('timestamp'),
                        'btc_price': vp.get('btc_price')
                    })
            
            if category == 'trading_execution':
                # 提取出场模式
                if any(kw in content for kw in ['止盈', '止损', '平了', '吃了']):
                    patterns['exit_patterns'].append({
                        'content': content[:100],
                        'timestamp': vp.get('timestamp'),
                        'btc_price': vp.get('btc_price')
                    })
            
            # 风险管理模式
            if '保本' in content or '止损' in content:
                patterns['risk_management'].append({
                    'content': content[:100],
                    'timestamp': vp.get('timestamp')
                })
        
        return patterns
    
    def generate_behavior_report(self) -> Dict:
        """生成完整的行为分析报告"""
        print("=" * 80)
        print("交易员行为模式分析报告")
        print("=" * 80)
        print()
        
        # 时间模式
        print("1. 交易时间偏好分析...")
        time_pattern = self.analyze_trading_time_pattern()
        print(f"  总记录数: {time_pattern['total_records']}")
        if time_pattern['most_active_hour'] is not None:
            print(f"  最活跃时段: {time_pattern['most_active_hour']}:00")
        if time_pattern['most_active_day'] is not None:
            weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
            print(f"  最活跃日期: {weekday_names[time_pattern['most_active_day']]}")
        print()
        
        # 价格区间偏好
        print("2. 价格区间偏好分析...")
        price_pattern = self.analyze_price_range_preference()
        if 'message' not in price_pattern:
            print(f"  平均价格: ${price_pattern['average_price']:,.2f}")
            print(f"  价格范围: ${price_pattern['min_price']:,.2f} - ${price_pattern['max_price']:,.2f}")
            if price_pattern['most_active_range']:
                print(f"  最活跃价格区间: ${price_pattern['most_active_range']:,.0f} - ${price_pattern['most_active_range'] + 1000:,.0f}")
        print()
        
        # 策略偏好
        print("3. 策略偏好分析...")
        strategy_pattern = self.analyze_strategy_preference()
        print("  策略使用频率:")
        for strategy, count in sorted(strategy_pattern['strategies'].items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"    {strategy}: {count} 次")
        print()
        print("  交易方向:")
        for direction, count in strategy_pattern['directions'].items():
            print(f"    {direction}: {count} 次")
        print()
        
        # 类别分布
        print("4. 类别分布...")
        category_dist = self.analyze_category_distribution()
        print("  类别分布:")
        for category, count in sorted(category_dist['categories'].items(), key=lambda x: x[1], reverse=True):
            print(f"    {category}: {count} 条")
        print()
        
        # 交易模式
        print("5. 交易模式提取...")
        patterns = self.extract_trading_patterns()
        print(f"  入场模式: {len(patterns['entry_patterns'])} 条")
        print(f"  出场模式: {len(patterns['exit_patterns'])} 条")
        print(f"  风险管理: {len(patterns['risk_management'])} 条")
        print()
        
        return {
            'time_pattern': time_pattern,
            'price_pattern': price_pattern,
            'strategy_pattern': strategy_pattern,
            'category_distribution': category_dist,
            'trading_patterns': patterns
        }


def main():
    """主函数"""
    analyzer = BehaviorPatternAnalyzer(trader_id='de')
    report = analyzer.generate_behavior_report()
    
    print("=" * 80)
    print("分析完成！")
    print("=" * 80)
    
    analyzer.db.close()

if __name__ == '__main__':
    main()










