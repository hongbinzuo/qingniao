#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
币种K线相似性分析程序
分析H、BANK、SOON、BLESS、COAI、MYX、BAS的历史K线数据
寻找相似性、领先跟随关系、破位特征
"""

import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import time
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

class CryptoKlineAnalyzer:
    def __init__(self):
        self.symbols = ['H', 'BANK', 'SOON', 'BLESS', 'COAI', 'MYX', 'BAS']
        self.data = {}
        self.analysis_results = {}
        
    def get_gateio_klines(self, symbol, interval='1d', limit=1000):
        """从Gate.io获取K线数据"""
        try:
            url = "https://api.gateio.ws/api/v4/spot/candlesticks"
            params = {
                'currency_pair': f'{symbol}_USDT',
                'interval': interval,
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data:
                    df = pd.DataFrame(data, columns=[
                        'timestamp', 'volume', 'close', 'high', 'low', 'open', 'amount'
                    ])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                    df['close'] = df['close'].astype(float)
                    df['high'] = df['high'].astype(float)
                    df['low'] = df['low'].astype(float)
                    df['open'] = df['open'].astype(float)
                    df['volume'] = df['volume'].astype(float)
                    return df
        except Exception as e:
            print(f"Gate.io获取{symbol}数据失败: {e}")
            
        return None
    
    def get_bitget_klines(self, symbol, interval='1d', limit=1000):
        """从Bitget获取K线数据"""
        try:
            url = "https://api.bitget.com/api/spot/v1/market/candles"
            params = {
                'symbol': f'{symbol}USDT',
                'granularity': '1d',
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('data'):
                    df = pd.DataFrame(data['data'], columns=[
                        'timestamp', 'open', 'high', 'low', 'close', 'volume', 'amount'
                    ])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df['close'] = df['close'].astype(float)
                    df['high'] = df['high'].astype(float)
                    df['low'] = df['low'].astype(float)
                    df['open'] = df['open'].astype(float)
                    df['volume'] = df['volume'].astype(float)
                    return df
        except Exception as e:
            print(f"Bitget获取{symbol}数据失败: {e}")
            
        return None
    
    def fetch_all_data(self):
        """获取所有币种的数据"""
        print("开始获取币种K线数据...")
        print(f"目标币种: {self.symbols}")
        
        for symbol in self.symbols:
            print(f"正在获取 {symbol} 数据...")
            
            # 优先使用Gate.io
            df = self.get_gateio_klines(symbol)
            if df is None:
                # 备用Bitget
                df = self.get_bitget_klines(symbol)
            
            if df is not None:
                self.data[symbol] = df
                print(f"✓ {symbol}: 获取到 {len(df)} 条数据")
            else:
                print(f"✗ {symbol}: 数据获取失败")
            
            time.sleep(0.5)  # 避免请求过快
        
        print(f"\n成功获取 {len(self.data)} 个币种的数据")
    
    def calculate_technical_indicators(self, df):
        """计算技术指标"""
        # 移动平均线
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma50'] = df['close'].rolling(50).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['close'].ewm(span=12).mean()
        exp2 = df['close'].ewm(span=26).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # 布林带
        df['bb_middle'] = df['close'].rolling(20).mean()
        bb_std = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # 成交量指标
        df['volume_ma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        return df
    
    def find_consolidation_breakouts(self, df, lookback=20):
        """识别盘整区间破位"""
        breakouts = []
        
        for i in range(lookback, len(df)):
            # 计算前lookback天的价格区间
            recent_data = df.iloc[i-lookback:i]
            high_max = recent_data['high'].max()
            low_min = recent_data['low'].min()
            range_size = high_max - low_min
            
            # 当前价格
            current_price = df.iloc[i]['close']
            current_volume = df.iloc[i]['volume']
            avg_volume = recent_data['volume'].mean()
            
            # 破位条件：价格突破区间且成交量放大
            if current_price > high_max and current_volume > avg_volume * 1.5:
                breakouts.append({
                    'date': df.iloc[i]['timestamp'],
                    'price': current_price,
                    'volume_ratio': current_volume / avg_volume,
                    'range_size': range_size,
                    'type': 'upward'
                })
            elif current_price < low_min and current_volume > avg_volume * 1.5:
                breakouts.append({
                    'date': df.iloc[i]['timestamp'],
                    'price': current_price,
                    'volume_ratio': current_volume / avg_volume,
                    'range_size': range_size,
                    'type': 'downward'
                })
        
        return breakouts
    
    def calculate_fibonacci_levels(self, df, start_idx, end_idx):
        """计算斐波那契扩展点位"""
        start_price = df.iloc[start_idx]['low']
        end_price = df.iloc[end_idx]['high']
        price_range = end_price - start_price
        
        fib_levels = {
            '0%': start_price,
            '23.6%': start_price + price_range * 0.236,
            '38.2%': start_price + price_range * 0.382,
            '50%': start_price + price_range * 0.5,
            '61.8%': start_price + price_range * 0.618,
            '100%': end_price,
            '161.8%': start_price + price_range * 1.618,
            '261.8%': start_price + price_range * 2.618
        }
        
        return fib_levels
    
    def analyze_correlation(self):
        """分析币种间的相关性"""
        print("\n分析币种相关性...")
        
        # 准备价格数据
        price_data = {}
        min_length = float('inf')
        
        for symbol, df in self.data.items():
            if len(df) > 0:
                price_data[symbol] = df['close'].values
                min_length = min(min_length, len(df))
        
        # 截取相同长度的数据
        for symbol in price_data:
            price_data[symbol] = price_data[symbol][-min_length:]
        
        # 计算相关性矩阵
        df_corr = pd.DataFrame(price_data)
        correlation_matrix = df_corr.corr()
        
        return correlation_matrix
    
    def analyze_lead_lag_relationship(self):
        """分析领先跟随关系"""
        print("\n分析领先跟随关系...")
        
        lead_lag_results = {}
        
        for i, symbol1 in enumerate(self.symbols):
            if symbol1 not in self.data:
                continue
                
            for j, symbol2 in enumerate(self.symbols):
                if i >= j or symbol2 not in self.data:
                    continue
                
                # 计算价格变化的相关性（不同时间偏移）
                df1 = self.data[symbol1]
                df2 = self.data[symbol2]
                
                min_len = min(len(df1), len(df2))
                price1 = df1['close'].values[-min_len:]
                price2 = df2['close'].values[-min_len:]
                
                # 计算不同时间偏移的相关性
                max_corr = 0
                best_lag = 0
                
                for lag in range(-10, 11):  # 测试前后10天的偏移
                    if lag < 0:
                        corr = np.corrcoef(price1[-lag:], price2[:lag])[0, 1]
                    elif lag > 0:
                        corr = np.corrcoef(price1[:-lag], price2[lag:])[0, 1]
                    else:
                        corr = np.corrcoef(price1, price2)[0, 1]
                    
                    if not np.isnan(corr) and abs(corr) > max_corr:
                        max_corr = abs(corr)
                        best_lag = lag
                
                lead_lag_results[f"{symbol1}-{symbol2}"] = {
                    'correlation': max_corr,
                    'lag': best_lag,
                    'leader': symbol1 if best_lag > 0 else symbol2
                }
        
        return lead_lag_results
    
    def generate_visualizations(self):
        """生成可视化图表"""
        print("\n生成可视化图表...")
        
        # 1. 价格走势对比图
        plt.figure(figsize=(15, 10))
        
        for i, (symbol, df) in enumerate(self.data.items()):
            if len(df) > 0:
                # 标准化价格（以第一天为基准）
                normalized_price = df['close'] / df['close'].iloc[0] * 100
                plt.plot(df['timestamp'], normalized_price, label=symbol, linewidth=2)
        
        plt.title('币种价格走势对比（标准化）', fontsize=16, fontweight='bold')
        plt.xlabel('时间')
        plt.ylabel('标准化价格 (基准=100)')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig('crypto_price_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # 2. 相关性热力图
        if len(self.data) > 1:
            correlation_matrix = self.analyze_correlation()
            
            plt.figure(figsize=(10, 8))
            sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0,
                       square=True, fmt='.2f')
            plt.title('币种价格相关性热力图', fontsize=16, fontweight='bold')
            plt.tight_layout()
            plt.savefig('crypto_correlation_heatmap.png', dpi=300, bbox_inches='tight')
            plt.close()
        
        # 3. 破位分析图
        self.plot_breakout_analysis()
    
    def plot_breakout_analysis(self):
        """绘制破位分析图"""
        fig, axes = plt.subplots(len(self.data), 1, figsize=(15, 4*len(self.data)))
        if len(self.data) == 1:
            axes = [axes]
        
        for i, (symbol, df) in enumerate(self.data.items()):
            if len(df) == 0:
                continue
                
            ax = axes[i]
            
            # 绘制价格和移动平均线
            ax.plot(df['timestamp'], df['close'], label='价格', linewidth=2)
            ax.plot(df['timestamp'], df['ma20'], label='MA20', alpha=0.7)
            ax.plot(df['timestamp'], df['bb_upper'], label='布林上轨', alpha=0.5, color='red')
            ax.plot(df['timestamp'], df['bb_lower'], label='布林下轨', alpha=0.5, color='green')
            
            # 标记破位点
            breakouts = self.find_consolidation_breakouts(df)
            for breakout in breakouts:
                color = 'red' if breakout['type'] == 'upward' else 'blue'
                ax.scatter(breakout['date'], breakout['price'], 
                          color=color, s=100, marker='^' if breakout['type'] == 'upward' else 'v',
                          label=f"{breakout['type']}破位")
            
            ax.set_title(f'{symbol} 破位分析', fontweight='bold')
            ax.set_ylabel('价格')
            ax.legend()
            ax.grid(True, alpha=0.3)
        
        plt.xlabel('时间')
        plt.tight_layout()
        plt.savefig('crypto_breakout_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def generate_report(self):
        """生成分析报告"""
        print("\n生成分析报告...")
        
        report = []
        report.append("# 币种K线相似性分析报告")
        report.append(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"分析币种: {', '.join(self.symbols)}")
        report.append("")
        
        # 数据概览
        report.append("## 数据概览")
        for symbol, df in self.data.items():
            if len(df) > 0:
                start_date = df['timestamp'].min().strftime('%Y-%m-%d')
                end_date = df['timestamp'].max().strftime('%Y-%m-%d')
                report.append(f"- **{symbol}**: {len(df)}条数据 ({start_date} 至 {end_date})")
        report.append("")
        
        # 相关性分析
        if len(self.data) > 1:
            correlation_matrix = self.analyze_correlation()
            report.append("## 相关性分析")
            report.append("| 币种对 | 相关系数 | 关系强度 |")
            report.append("|--------|----------|----------|")
            
            for i, symbol1 in enumerate(correlation_matrix.columns):
                for j, symbol2 in enumerate(correlation_matrix.columns):
                    if i < j:
                        corr = correlation_matrix.loc[symbol1, symbol2]
                        strength = "强" if abs(corr) > 0.7 else "中" if abs(corr) > 0.4 else "弱"
                        report.append(f"| {symbol1}-{symbol2} | {corr:.3f} | {strength} |")
            report.append("")
        
        # 领先跟随关系
        lead_lag_results = self.analyze_lead_lag_relationship()
        if lead_lag_results:
            report.append("## 领先跟随关系分析")
            report.append("| 币种对 | 最大相关性 | 时间偏移 | 领先币种 |")
            report.append("|--------|------------|----------|----------|")
            
            for pair, result in lead_lag_results.items():
                report.append(f"| {pair} | {result['correlation']:.3f} | {result['lag']}天 | {result['leader']} |")
            report.append("")
        
        # 破位分析
        report.append("## 破位特征分析")
        for symbol, df in self.data.items():
            if len(df) > 0:
                breakouts = self.find_consolidation_breakouts(df)
                report.append(f"### {symbol}")
                report.append(f"- 破位次数: {len(breakouts)}")
                
                if breakouts:
                    upward_breakouts = [b for b in breakouts if b['type'] == 'upward']
                    downward_breakouts = [b for b in breakouts if b['type'] == 'downward']
                    
                    report.append(f"- 向上破位: {len(upward_breakouts)}次")
                    report.append(f"- 向下破位: {len(downward_breakouts)}次")
                    
                    if upward_breakouts:
                        avg_volume_ratio = np.mean([b['volume_ratio'] for b in upward_breakouts])
                        report.append(f"- 向上破位平均成交量倍数: {avg_volume_ratio:.2f}")
                    
                    if downward_breakouts:
                        avg_volume_ratio = np.mean([b['volume_ratio'] for b in downward_breakouts])
                        report.append(f"- 向下破位平均成交量倍数: {avg_volume_ratio:.2f}")
                report.append("")
        
        # 保存报告
        with open('crypto_kline_analysis_report.md', 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        print("分析报告已保存: crypto_kline_analysis_report.md")
    
    def run_analysis(self):
        """运行完整分析"""
        print("🚀 开始币种K线相似性分析")
        print("="*50)
        print("程序开始运行...")
        
        # 获取数据
        self.fetch_all_data()
        
        if not self.data:
            print("❌ 没有获取到任何数据，分析终止")
            return
        
        # 计算技术指标
        print("\n计算技术指标...")
        for symbol, df in self.data.items():
            self.data[symbol] = self.calculate_technical_indicators(df)
        
        # 生成可视化
        self.generate_visualizations()
        
        # 生成报告
        self.generate_report()
        
        print("\n✅ 分析完成！")
        print("生成的文件:")
        print("- crypto_price_comparison.png (价格对比图)")
        print("- crypto_correlation_heatmap.png (相关性热力图)")
        print("- crypto_breakout_analysis.png (破位分析图)")
        print("- crypto_kline_analysis_report.md (分析报告)")

if __name__ == "__main__":
    analyzer = CryptoKlineAnalyzer()
    analyzer.run_analysis()
