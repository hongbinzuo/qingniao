#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
周线水下死叉分析程序
分析周线MACD在零轴下方死叉后的市场表现
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import sys
import warnings
warnings.filterwarnings('ignore')

# Windows UTF-8输出
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

def generate_weekly_data(symbol, weeks=200):
    """生成周线数据"""
    print(f"生成 {symbol} 周线数据...")
    
    # 生成日期序列（周线）
    dates = pd.date_range(start='2020-01-01', periods=weeks, freq='W')
    
    # 生成价格数据
    np.random.seed(hash(symbol) % 2**32)
    
    # 基础价格
    base_price = 1.0
    volatility = 0.08
    
    # 生成价格序列
    returns = np.random.normal(0.002, volatility, weeks)
    prices = [base_price]
    
    for i in range(1, weeks):
        price = prices[-1] * (1 + returns[i])
        prices.append(price)
    
    # 生成OHLC数据
    data = []
    for i, (date, price) in enumerate(zip(dates, prices)):
        # 生成当周的高低开收
        weekly_volatility = np.random.uniform(0.05, 0.15)
        high = price * (1 + weekly_volatility * np.random.uniform(0.3, 1.0))
        low = price * (1 - weekly_volatility * np.random.uniform(0.3, 1.0))
        open_price = price * (1 + weekly_volatility * np.random.uniform(-0.5, 0.5))
        close = price
        volume = np.random.uniform(10000, 100000)
        
        data.append({
            'timestamp': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    return df

def calculate_weekly_macd(df):
    """计算周线MACD"""
    # 周线MACD参数
    exp1 = df['close'].ewm(span=12).mean()
    exp2 = df['close'].ewm(span=26).mean()
    df['macd'] = exp1 - exp2
    df['macd_signal'] = df['macd'].ewm(span=9).mean()
    df['macd_histogram'] = df['macd'] - df['macd_signal']
    
    return df

def find_underwater_death_crosses(df):
    """识别水下死叉"""
    death_crosses = []
    
    for i in range(1, len(df)):
        # 检查是否为死叉
        if (df.iloc[i-1]['macd'] > df.iloc[i-1]['macd_signal'] and 
            df.iloc[i]['macd'] <= df.iloc[i]['macd_signal']):
            
            # 检查是否在水下（MACD < 0）
            if df.iloc[i]['macd'] < 0:
                death_crosses.append({
                    'date': df.iloc[i]['timestamp'],
                    'price': df.iloc[i]['close'],
                    'macd': df.iloc[i]['macd'],
                    'macd_signal': df.iloc[i]['macd_signal'],
                    'index': i
                })
    
    return death_crosses

def analyze_post_death_cross_performance(df, death_crosses, weeks_ahead=20):
    """分析死叉后的表现"""
    results = []
    
    for death_cross in death_crosses:
        start_idx = death_cross['index']
        start_price = death_cross['price']
        
        # 分析后续表现
        performance_data = []
        for weeks in range(1, weeks_ahead + 1):
            end_idx = start_idx + weeks
            if end_idx < len(df):
                end_price = df.iloc[end_idx]['close']
                performance = (end_price - start_price) / start_price * 100
                
                performance_data.append({
                    'weeks_after': weeks,
                    'performance': performance,
                    'price': end_price
                })
        
        if performance_data:
            results.append({
                'death_cross_date': death_cross['date'],
                'death_cross_price': start_price,
                'macd_value': death_cross['macd'],
                'performances': performance_data
            })
    
    return results

def calculate_statistics(results):
    """计算统计数据"""
    stats = {}
    
    for weeks in range(1, 21):
        performances = []
        for result in results:
            for perf in result['performances']:
                if perf['weeks_after'] == weeks:
                    performances.append(perf['performance'])
        
        if performances:
            stats[weeks] = {
                'count': len(performances),
                'mean': np.mean(performances),
                'median': np.median(performances),
                'std': np.std(performances),
                'min': np.min(performances),
                'max': np.max(performances),
                'positive_rate': len([p for p in performances if p > 0]) / len(performances) * 100
            }
    
    return stats

def generate_charts(df, death_crosses, results):
    """生成图表"""
    print("生成可视化图表...")
    
    # 1. 价格走势和死叉标记
    plt.figure(figsize=(15, 10))
    
    plt.subplot(2, 1, 1)
    plt.plot(df['timestamp'], df['close'], label='价格', linewidth=2)
    
    # 标记死叉点
    for death_cross in death_crosses:
        plt.scatter(death_cross['date'], death_cross['price'], 
                   color='red', s=100, marker='v', label='水下死叉' if death_cross == death_crosses[0] else "")
    
    plt.title('周线价格走势与水下死叉标记', fontsize=16, fontweight='bold')
    plt.ylabel('价格')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 2. MACD指标
    plt.subplot(2, 1, 2)
    plt.plot(df['timestamp'], df['macd'], label='MACD', linewidth=2)
    plt.plot(df['timestamp'], df['macd_signal'], label='Signal', linewidth=2)
    plt.axhline(y=0, color='black', linestyle='--', alpha=0.5)
    
    # 标记死叉点
    for death_cross in death_crosses:
        plt.scatter(death_cross['date'], death_cross['macd'], 
                   color='red', s=100, marker='v')
    
    plt.title('周线MACD指标', fontsize=16, fontweight='bold')
    plt.ylabel('MACD')
    plt.xlabel('时间')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('weekly_underwater_death_cross.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("✓ 周线水下死叉图已保存: weekly_underwater_death_cross.png")
    
    # 3. 死叉后表现统计
    stats = calculate_statistics(results)
    
    if stats:
        weeks = list(stats.keys())
        means = [stats[w]['mean'] for w in weeks]
        positive_rates = [stats[w]['positive_rate'] for w in weeks]
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))
        
        # 平均表现
        ax1.plot(weeks, means, 'b-o', linewidth=2, markersize=6)
        ax1.axhline(y=0, color='red', linestyle='--', alpha=0.5)
        ax1.set_title('周线水下死叉后平均表现', fontsize=16, fontweight='bold')
        ax1.set_ylabel('平均涨跌幅 (%)')
        ax1.grid(True, alpha=0.3)
        
        # 上涨概率
        ax2.plot(weeks, positive_rates, 'g-o', linewidth=2, markersize=6)
        ax2.axhline(y=50, color='red', linestyle='--', alpha=0.5)
        ax2.set_title('周线水下死叉后上涨概率', fontsize=16, fontweight='bold')
        ax2.set_ylabel('上涨概率 (%)')
        ax2.set_xlabel('周数')
        ax2.grid(True, alpha=0.5)
        
        plt.tight_layout()
        plt.savefig('weekly_death_cross_statistics.png', dpi=300, bbox_inches='tight')
        plt.close()
        print("✓ 死叉后统计图已保存: weekly_death_cross_statistics.png")

def generate_report(df, death_crosses, results):
    """生成分析报告"""
    print("生成分析报告...")
    
    stats = calculate_statistics(results)
    
    report = []
    report.append("# 周线水下死叉分析报告")
    report.append(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # 数据概览
    report.append("## 数据概览")
    report.append(f"- 分析周期: {df['timestamp'].min().strftime('%Y-%m-%d')} 至 {df['timestamp'].max().strftime('%Y-%m-%d')}")
    report.append(f"- 总周数: {len(df)}")
    report.append(f"- 水下死叉次数: {len(death_crosses)}")
    report.append("")
    
    # 死叉详情
    report.append("## 水下死叉详情")
    report.append("| 序号 | 死叉日期 | 死叉价格 | MACD值 | 后续表现 |")
    report.append("|------|----------|----------|--------|----------|")
    
    for i, death_cross in enumerate(death_crosses):
        # 计算后续表现
        follow_up_performance = "N/A"
        if i < len(results):
            result = results[i]
            if result['performances']:
                # 取第4周的表现
                week_4_perf = next((p['performance'] for p in result['performances'] if p['weeks_after'] == 4), None)
                if week_4_perf is not None:
                    follow_up_performance = f"{week_4_perf:.2f}%"
        
        report.append(f"| {i+1} | {death_cross['date'].strftime('%Y-%m-%d')} | {death_cross['price']:.4f} | {death_cross['macd']:.4f} | {follow_up_performance} |")
    
    report.append("")
    
    # 统计结果
    report.append("## 死叉后表现统计")
    report.append("| 周数 | 样本数 | 平均涨跌幅(%) | 中位数(%) | 最大涨幅(%) | 最大跌幅(%) | 上涨概率(%) | 标准差 |")
    report.append("|------|--------|---------------|-----------|-------------|-------------|-------------|--------|")
    
    for weeks in sorted(stats.keys()):
        stat = stats[weeks]
        report.append(f"| {weeks} | {stat['count']} | {stat['mean']:.2f} | {stat['median']:.2f} | {stat['max']:.2f} | {stat['min']:.2f} | {stat['positive_rate']:.1f} | {stat['std']:.2f} |")
    
    report.append("")
    
    # 关键发现
    report.append("## 关键发现")
    
    # 找到最佳表现周数
    best_week = max(stats.keys(), key=lambda w: stats[w]['mean'])
    worst_week = min(stats.keys(), key=lambda w: stats[w]['mean'])
    
    report.append(f"- **最佳表现周数**: 第{best_week}周，平均涨跌幅 {stats[best_week]['mean']:.2f}%")
    report.append(f"- **最差表现周数**: 第{worst_week}周，平均涨跌幅 {stats[worst_week]['mean']:.2f}%")
    
    # 上涨概率分析
    high_prob_weeks = [w for w, s in stats.items() if s['positive_rate'] > 60]
    if high_prob_weeks:
        report.append(f"- **高上涨概率周数**: {', '.join(map(str, high_prob_weeks))}周 (上涨概率>60%)")
    
    # 风险提示
    report.append("")
    report.append("## 风险提示")
    report.append("- 水下死叉通常表示市场处于弱势状态")
    report.append("- 死叉后短期内可能出现进一步下跌")
    report.append("- 建议结合其他技术指标和基本面分析")
    report.append("- 注意止损和仓位管理")
    
    # 保存报告
    with open('weekly_underwater_death_cross_report.md', 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    
    print("✓ 分析报告已保存: weekly_underwater_death_cross_report.md")

def main():
    """主函数"""
    print("🚀 开始周线水下死叉分析")
    print("="*50)
    
    # 生成模拟数据
    df = generate_weekly_data('BTC', weeks=200)
    df = calculate_weekly_macd(df)
    
    print(f"✓ 生成 {len(df)} 周数据")
    
    # 识别水下死叉
    death_crosses = find_underwater_death_crosses(df)
    print(f"✓ 识别到 {len(death_crosses)} 次水下死叉")
    
    if not death_crosses:
        print("❌ 未发现水下死叉，分析终止")
        return
    
    # 分析死叉后表现
    results = analyze_post_death_cross_performance(df, death_crosses)
    print(f"✓ 分析 {len(results)} 次死叉的后续表现")
    
    # 生成图表
    generate_charts(df, death_crosses, results)
    
    # 生成报告
    generate_report(df, death_crosses, results)
    
    print("\n✅ 分析完成！")
    print("生成的文件:")
    print("- weekly_underwater_death_cross.png (周线水下死叉图)")
    print("- weekly_death_cross_statistics.png (死叉后统计图)")
    print("- weekly_underwater_death_cross_report.md (分析报告)")

if __name__ == "__main__":
    main()



