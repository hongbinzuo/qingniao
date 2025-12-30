#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TradingView OTHERS 周线死叉分析程序
分析周线死叉后的1-10周涨跌表现
"""

import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

class OthersDeathCrossAnalysis:
    def __init__(self, symbol="OTHERS", period="5y"):
        """
        初始化分析类
        symbol: 交易对符号
        period: 数据获取周期
        """
        self.symbol = symbol
        self.period = period
        self.data = None
        self.death_crosses = []
        self.results = []
        
    def fetch_data(self):
        """获取OHLCV数据"""
        print(f"正在获取 {self.symbol} 的数据...")
        try:
            # 尝试获取数据
            ticker = yf.Ticker(self.symbol)
            self.data = ticker.history(period=self.period)
            
            if self.data.empty:
                print(f"警告: 无法获取 {self.symbol} 的数据，尝试其他数据源...")
                return False
                
            print(f"成功获取 {len(self.data)} 条数据")
            return True
            
        except Exception as e:
            print(f"获取数据失败: {e}")
            return False
    
    def calculate_ma(self):
        """计算移动平均线"""
        if self.data is None or self.data.empty:
            return False
            
        # 计算周线数据（取每周最后一个交易日）
        weekly_data = self.data.resample('W').agg({
            'Open': 'first',
            'High': 'max', 
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()
        
        # 计算12周和26周移动平均线（对应日线的50日和200日均线）
        weekly_data['MA12'] = weekly_data['Close'].rolling(window=12).mean()
        weekly_data['MA26'] = weekly_data['Close'].rolling(window=26).mean()
        
        self.weekly_data = weekly_data
        print(f"计算移动平均线完成，共 {len(weekly_data)} 周数据")
        return True
    
    def find_death_crosses(self):
        """识别死叉信号"""
        if not hasattr(self, 'weekly_data'):
            return False
            
        weekly_data = self.weekly_data
        
        # 寻找死叉点：MA12下穿MA26
        death_cross_signals = []
        
        for i in range(1, len(weekly_data)):
            prev_ma12 = weekly_data['MA12'].iloc[i-1]
            prev_ma26 = weekly_data['MA26'].iloc[i-1]
            curr_ma12 = weekly_data['MA12'].iloc[i]
            curr_ma26 = weekly_data['MA26'].iloc[i]
            
            # 死叉条件：前一周MA12 > MA26，当前周MA12 < MA26
            if (prev_ma12 > prev_ma26) and (curr_ma12 < curr_ma26):
                death_cross_date = weekly_data.index[i]
                death_cross_price = weekly_data['Close'].iloc[i]
                
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
            
        weekly_data = self.weekly_data
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
                
                if future_index < len(weekly_data):
                    future_price = weekly_data['Close'].iloc[future_index]
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
                '死叉价格': round(result['death_cross_price'], 4)
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
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle(f'{self.symbol} 周线死叉后表现分析', fontsize=16)
        
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
        
        axes[0, 0].plot(weeks, avg_changes, marker='o', linewidth=2, markersize=6)
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
                week_labels.extend([f'第{week}周'] * len(week_changes))
        
        if all_changes:
            changes_df = pd.DataFrame({'涨跌幅': all_changes, '周数': week_labels})
            sns.boxplot(data=changes_df, x='周数', y='涨跌幅', ax=axes[1, 0])
            axes[1, 0].axhline(y=0, color='red', linestyle='--', alpha=0.7)
            axes[1, 0].set_title('死叉后涨跌幅分布')
            axes[1, 0].tick_params(axis='x', rotation=45)
        
        # 4. 累计收益曲线
        cumulative_returns = []
        for week in weeks:
            week_key = f'week_{week}'
            week_changes = [r[week_key] for r in self.results if r[week_key] is not None]
            if week_changes:
                avg_change = np.mean(week_changes)
                cumulative_returns.append(avg_change)
            else:
                cumulative_returns.append(0)
        
        axes[1, 1].plot(weeks, cumulative_returns, marker='s', linewidth=2, markersize=6, color='green')
        axes[1, 1].axhline(y=0, color='red', linestyle='--', alpha=0.7)
        axes[1, 1].set_title('死叉后累计平均收益')
        axes[1, 1].set_xlabel('周数')
        axes[1, 1].set_ylabel('累计收益 (%)')
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f'{self.symbol}_death_cross_analysis.png', dpi=300, bbox_inches='tight')
        plt.show()
    
    def run_analysis(self):
        """运行完整分析"""
        print(f"开始分析 {self.symbol} 的周线死叉表现...")
        
        # 获取数据
        if not self.fetch_data():
            print("数据获取失败，程序退出")
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
            stats_table.to_csv(f'{self.symbol}_death_cross_statistics.csv', index=False, encoding='utf-8-sig')
            print(f"统计表格已保存为 {self.symbol}_death_cross_statistics.csv")
        
        if detailed_table is not None:
            detailed_table.to_csv(f'{self.symbol}_death_cross_detailed.csv', index=False, encoding='utf-8-sig')
            print(f"详细表格已保存为 {self.symbol}_death_cross_detailed.csv")
        
        # 绘制图表
        self.plot_analysis()
        
        # 打印结果
        print("\n=== 统计结果 ===")
        if stats_table is not None:
            print(stats_table.to_string(index=False))
        
        print(f"\n=== 详细结果（前5条） ===")
        if detailed_table is not None:
            print(detailed_table.head().to_string(index=False))
        
        return True

def main():
    """主函数"""
    # 创建分析实例
    analyzer = OthersDeathCrossAnalysis(symbol="OTHERS", period="10y")
    
    # 运行分析
    success = analyzer.run_analysis()
    
    if success:
        print("\n分析完成！")
    else:
        print("\n分析失败！")

if __name__ == "__main__":
    main()




