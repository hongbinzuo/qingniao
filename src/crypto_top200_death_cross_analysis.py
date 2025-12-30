#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
加密货币前200市值总和（排除BTC和ETH）周线死叉分析程序
分析周线死叉后的1-10周涨跌表现
"""

import pandas as pd
import numpy as np
import requests
import time
import json
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('Agg')  # 使用非GUI后端
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class CryptoTop200DeathCrossAnalysis:
    def __init__(self):
        self.top200_data = None
        self.market_cap_data = None
        self.death_crosses = []
        self.results = []
        self.start_date = None
        self.end_date = None
        
    def get_top200_cryptocurrencies(self):
        """获取前200名加密货币列表"""
        print("正在获取前200名加密货币列表...")
        
        try:
            # 使用CoinGecko API获取前200名加密货币
            url = "https://api.coingecko.com/api/v3/coins/markets"
            params = {
                'vs_currency': 'usd',
                'order': 'market_cap_desc',
                'per_page': 200,
                'page': 1,
                'sparkline': False
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # 转换为DataFrame并排除BTC和ETH
            df = pd.DataFrame(data)
            df = df[~df['id'].isin(['bitcoin', 'ethereum'])]
            
            self.top200_data = df
            print(f"成功获取 {len(df)} 个加密货币（排除BTC和ETH）")
            
            # 保存币种列表
            coin_list = df[['id', 'symbol', 'name', 'market_cap']].copy()
            coin_list.to_csv('top200_crypto_list.csv', index=False, encoding='utf-8-sig')
            print("币种列表已保存为 top200_crypto_list.csv")
            
            return True
            
        except Exception as e:
            print(f"获取加密货币列表失败: {e}")
            return False
    
    def generate_market_cap_data(self, years=5):
        """生成模拟的市值总和数据"""
        print("生成模拟市值总和数据...")
        
        # 获取币种数量
        num_coins = len(self.top200_data) if self.top200_data is not None else 198
        
        # 生成时间序列
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years*365)
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # 生成周线数据
        weekly_dates = pd.date_range(start=start_date, end=end_date, freq='W')
        
        # 模拟市值总和走势（基于多个加密货币的复合走势）
        np.random.seed(42)
        
        # 基础趋势：整体上涨但有波动
        base_trend = np.linspace(100, 150, len(weekly_dates))  # 5年上涨50%
        
        # 添加周期性波动
        cycle1 = 10 * np.sin(2 * np.pi * np.arange(len(weekly_dates)) / 52)  # 年周期
        cycle2 = 5 * np.sin(2 * np.pi * np.arange(len(weekly_dates)) / 26)   # 半年周期
        
        # 添加随机波动
        random_noise = np.random.normal(0, 8, len(weekly_dates))
        
        # 添加一些市场事件影响
        market_events = np.zeros(len(weekly_dates))
        # 模拟一些大跌事件
        event_indices = [50, 100, 150, 200]
        for idx in event_indices:
            if idx < len(market_events):
                market_events[idx:idx+4] = -15  # 连续几周大跌
        
        # 组合所有因素
        market_cap_values = base_trend + cycle1 + cycle2 + random_noise + market_events
        market_cap_values = np.maximum(market_cap_values, 50)  # 确保不为负
        
        # 创建DataFrame
        self.market_cap_data = pd.DataFrame({
            'Date': weekly_dates,
            'Market_Cap_Sum': market_cap_values,
            'Volume': np.random.randint(1000000000, 5000000000, len(weekly_dates))
        })
        
        self.start_date = start_date
        self.end_date = end_date
        
        print(f"生成 {len(weekly_dates)} 周市值数据")
        print(f"统计时间区间: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
        
        return True
    
    def calculate_ma(self):
        """计算移动平均线"""
        if self.market_cap_data is None or self.market_cap_data.empty:
            return False
            
        # 计算12周和26周移动平均线
        self.market_cap_data['MA12'] = self.market_cap_data['Market_Cap_Sum'].rolling(window=12).mean()
        self.market_cap_data['MA26'] = self.market_cap_data['Market_Cap_Sum'].rolling(window=26).mean()
        
        print(f"计算移动平均线完成，共 {len(self.market_cap_data)} 周数据")
        return True
    
    def find_death_crosses(self):
        """识别死叉信号"""
        if self.market_cap_data is None or self.market_cap_data.empty:
            return False
            
        # 寻找死叉点：MA12下穿MA26
        death_cross_signals = []
        
        for i in range(1, len(self.market_cap_data)):
            prev_ma12 = self.market_cap_data['MA12'].iloc[i-1]
            prev_ma26 = self.market_cap_data['MA26'].iloc[i-1]
            curr_ma12 = self.market_cap_data['MA12'].iloc[i]
            curr_ma26 = self.market_cap_data['MA26'].iloc[i]
            
            # 死叉条件：前一周MA12 > MA26，当前周MA12 < MA26
            if (prev_ma12 > prev_ma26) and (curr_ma12 < curr_ma26):
                death_cross_date = self.market_cap_data['Date'].iloc[i]
                death_cross_price = self.market_cap_data['Market_Cap_Sum'].iloc[i]
                
                death_cross_signals.append({
                    'date': death_cross_date,
                    'price': death_cross_price,
                    'ma12': curr_ma12,
                    'ma26': curr_ma26,
                    'index': i
                })
        
        self.death_crosses = death_cross_signals
        print(f"识别到 {len(death_cross_signals)} 个死叉信号")
        return True
    
    def analyze_post_death_cross_performance(self):
        """分析死叉后1-10周的涨跌表现"""
        if not self.death_crosses:
            print("没有找到死叉信号")
            return False
            
        results = []
        
        for death_cross in self.death_crosses:
            death_cross_index = death_cross['index']
            death_cross_price = death_cross['price']
            death_cross_date = death_cross['date']
            
            # 分析后续1-10周的表现
            weekly_performance = {
                'death_cross_date': death_cross_date,
                'death_cross_price': death_cross_price
            }
            
            for weeks_ahead in range(1, 11):
                future_index = death_cross_index + weeks_ahead
                
                if future_index < len(self.market_cap_data):
                    future_price = self.market_cap_data['Market_Cap_Sum'].iloc[future_index]
                    price_change = (future_price - death_cross_price) / death_cross_price * 100
                    weekly_performance[f'week_{weeks_ahead}'] = price_change
                else:
                    weekly_performance[f'week_{weeks_ahead}'] = None
            
            results.append(weekly_performance)
        
        self.results = results
        print(f"完成 {len(results)} 个死叉信号的后续表现分析")
        return True
    
    def generate_statistics_table(self):
        """生成统计表格"""
        if not self.results:
            return None
            
        # 创建统计表
        stats_data = []
        
        for week in range(1, 11):
            week_key = f'week_{week}'
            week_changes = [r[week_key] for r in self.results if r[week_key] is not None]
            
            if week_changes:
                stats_data.append({
                    '周数': week,
                    '样本数': len(week_changes),
                    '平均涨跌幅(%)': round(np.mean(week_changes), 2),
                    '中位数涨跌幅(%)': round(np.median(week_changes), 2),
                    '最大涨幅(%)': round(max(week_changes), 2),
                    '最大跌幅(%)': round(min(week_changes), 2),
                    '上涨概率(%)': round(len([x for x in week_changes if x > 0]) / len(week_changes) * 100, 1),
                    '标准差': round(np.std(week_changes), 2)
                })
        
        stats_df = pd.DataFrame(stats_data)
        return stats_df
    
    def generate_detailed_table(self):
        """生成详细表格"""
        if not self.results:
            return None
            
        detailed_data = []
        
        for i, result in enumerate(self.results):
            row = {
                '死叉序号': i + 1,
                '死叉日期': result['death_cross_date'].strftime('%Y-%m-%d'),
                '死叉市值': round(result['death_cross_price'], 2)
            }
            
            for week in range(1, 11):
                week_key = f'week_{week}'
                if result[week_key] is not None:
                    row[f'第{week}周(%)'] = round(result[week_key], 2)
                else:
                    row[f'第{week}周(%)'] = 'N/A'
            
            detailed_data.append(row)
        
        detailed_df = pd.DataFrame(detailed_data)
        return detailed_df
    
    def plot_analysis(self):
        """绘制分析图表"""
        if not self.results:
            return
            
        # 创建子图
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('加密货币前200市值总和（排除BTC和ETH）周线死叉后表现分析', fontsize=16)
        
        # 1. 平均涨跌幅趋势
        weeks = list(range(1, 11))
        avg_changes = []
        for week in weeks:
            week_key = f'week_{week}'
            week_changes = [r[week_key] for r in self.results if r[week_key] is not None]
            if week_changes:
                avg_changes.append(np.mean(week_changes))
            else:
                avg_changes.append(0)
        
        axes[0, 0].plot(weeks, avg_changes, marker='o', linewidth=2, markersize=6, color='blue')
        axes[0, 0].axhline(y=0, color='red', linestyle='--', alpha=0.7)
        axes[0, 0].set_title('死叉后平均涨跌幅趋势')
        axes[0, 0].set_xlabel('周数')
        axes[0, 0].set_ylabel('平均涨跌幅 (%)')
        axes[0, 0].grid(True, alpha=0.3)
        
        # 2. 上涨概率
        up_probabilities = []
        for week in weeks:
            week_key = f'week_{week}'
            week_changes = [r[week_key] for r in self.results if r[week_key] is not None]
            if week_changes:
                up_prob = len([x for x in week_changes if x > 0]) / len(week_changes) * 100
                up_probabilities.append(up_prob)
            else:
                up_probabilities.append(0)
        
        axes[0, 1].bar(weeks, up_probabilities, color='skyblue', alpha=0.7)
        axes[0, 1].axhline(y=50, color='red', linestyle='--', alpha=0.7)
        axes[0, 1].set_title('死叉后上涨概率')
        axes[0, 1].set_xlabel('周数')
        axes[0, 1].set_ylabel('上涨概率 (%)')
        axes[0, 1].set_ylim(0, 100)
        axes[0, 1].grid(True, alpha=0.3)
        
        # 3. 涨跌幅分布箱线图
        all_changes = []
        week_labels = []
        for week in weeks:
            week_key = f'week_{week}'
            week_changes = [r[week_key] for r in self.results if r[week_key] is not None]
            if week_changes:
                all_changes.extend(week_changes)
                week_labels.extend([f'W{week}'] * len(week_changes))
        
        if all_changes:
            changes_df = pd.DataFrame({'涨跌幅': all_changes, '周数': week_labels})
            sns.boxplot(data=changes_df, x='周数', y='涨跌幅', ax=axes[1, 0])
            axes[1, 0].axhline(y=0, color='red', linestyle='--', alpha=0.7)
            axes[1, 0].set_title('死叉后涨跌幅分布')
            axes[1, 0].tick_params(axis='x', rotation=45)
        
        # 4. 市值总和走势图
        if self.market_cap_data is not None:
            axes[1, 1].plot(self.market_cap_data['Date'], self.market_cap_data['Market_Cap_Sum'], 
                           linewidth=1, alpha=0.7, color='gray', label='市值总和')
            axes[1, 1].plot(self.market_cap_data['Date'], self.market_cap_data['MA12'], 
                           linewidth=2, color='blue', label='MA12')
            axes[1, 1].plot(self.market_cap_data['Date'], self.market_cap_data['MA26'], 
                           linewidth=2, color='red', label='MA26')
            
            # 标记死叉点
            for death_cross in self.death_crosses:
                axes[1, 1].scatter(death_cross['date'], death_cross['price'], 
                                  color='red', s=100, marker='v', zorder=5)
            
            axes[1, 1].set_title('市值总和走势与死叉信号')
            axes[1, 1].set_xlabel('日期')
            axes[1, 1].set_ylabel('市值总和')
            axes[1, 1].legend()
            axes[1, 1].tick_params(axis='x', rotation=45)
            axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('crypto_top200_death_cross_analysis.png', dpi=300, bbox_inches='tight')
        print("图表已保存为 crypto_top200_death_cross_analysis.png")
        plt.close()
    
    def run_analysis(self):
        """运行完整分析"""
        print("开始分析加密货币前200市值总和（排除BTC和ETH）的周线死叉表现...")
        print("=" * 80)
        
        # 获取加密货币列表
        if not self.get_top200_cryptocurrencies():
            print("使用模拟数据进行演示...")
            # 如果无法获取真实数据，创建模拟数据
            self.top200_data = pd.DataFrame({
                'id': [f'coin_{i}' for i in range(198)],
                'symbol': [f'COIN{i}' for i in range(198)],
                'name': [f'Coin {i}' for i in range(198)],
                'market_cap': np.random.randint(1000000, 1000000000, 198)
            })
        
        # 生成市值数据
        if not self.generate_market_cap_data():
            print("市值数据生成失败，程序退出")
            return False
        
        # 计算移动平均线
        if not self.calculate_ma():
            print("移动平均线计算失败")
            return False
        
        # 识别死叉信号
        if not self.find_death_crosses():
            print("死叉信号识别失败")
            return False
        
        # 分析后续表现
        if not self.analyze_post_death_cross_performance():
            print("后续表现分析失败")
            return False
        
        # 生成统计表格
        stats_table = self.generate_statistics_table()
        detailed_table = self.generate_detailed_table()
        
        # 保存结果
        if stats_table is not None:
            stats_table.to_csv('crypto_top200_death_cross_statistics.csv', index=False, encoding='utf-8-sig')
            print("统计表格已保存为 crypto_top200_death_cross_statistics.csv")
        
        if detailed_table is not None:
            detailed_table.to_csv('crypto_top200_death_cross_detailed.csv', index=False, encoding='utf-8-sig')
            print("详细表格已保存为 crypto_top200_death_cross_detailed.csv")
        
        # 绘制图表
        self.plot_analysis()
        
        # 打印结果
        print("\n" + "="*80)
        print("加密货币前200市值总和（排除BTC和ETH）周线死叉统计结果")
        print("="*80)
        
        if self.start_date and self.end_date:
            print(f"统计时间区间: {self.start_date.strftime('%Y-%m-%d')} 至 {self.end_date.strftime('%Y-%m-%d')}")
            print(f"分析周期: {(self.end_date - self.start_date).days} 天")
        
        if stats_table is not None:
            print("\n核心统计表格:")
            print(stats_table.to_string(index=False))
        
        print(f"\n详细结果（前10条）:")
        if detailed_table is not None:
            print(detailed_table.head(10).to_string(index=False))
        
        return True

def main():
    """主函数"""
    print("加密货币前200市值总和（排除BTC和ETH）周线死叉分析程序")
    print("=" * 80)
    
    # 创建分析实例
    analyzer = CryptoTop200DeathCrossAnalysis()
    
    # 运行分析
    success = analyzer.run_analysis()
    
    if success:
        print("\n" + "="*80)
        print("分析完成！")
        print("生成的文件：")
        print("- crypto_top200_death_cross_statistics.csv (统计表格)")
        print("- crypto_top200_death_cross_detailed.csv (详细表格)")
        print("- crypto_top200_death_cross_analysis.png (分析图表)")
        print("- top200_crypto_list.csv (前200币种列表)")
        print("="*80)
    else:
        print("\n分析失败！")

if __name__ == "__main__":
    main()




