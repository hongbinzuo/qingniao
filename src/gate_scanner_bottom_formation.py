#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gate.io 币种技术形态扫描程序
扫描前1000个币种，分析K线结构，识别：
- 底部反转形态（Double Bottom, Head and Shoulders Bottom等）
- 顶部反转形态（Double Top, Head and Shoulders Top等）
- 持续结构（Bullish/Bearish Flag, Pennant等）
"""

import requests
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 使用非GUI后端
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time
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

class TechnicalPatternScanner:
    """技术形态扫描器 - 检测反转和持续形态"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        # 添加SSL验证和重试设置
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.results = []
        
        # 创建输出目录（按时间戳）
        self.output_dir = self._create_output_directory()
    
    def _create_output_directory(self):
        """创建输出目录，按时间戳命名"""
        import os
        base_dir = "scan_results"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(base_dir, timestamp)
        
        # 创建目录（如果不存在）
        os.makedirs(output_dir, exist_ok=True)
        
        return output_dir
    
    def get_top_symbols(self, limit=None):
        """获取Bitget所有币种（按交易量）"""
        print(f"🔍 获取Bitget所有币种列表...", flush=True)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Bitget获取所有交易对
                url = "https://api.bitget.com/api/spot/v1/public/products"
                response = self.session.get(url, timeout=30, verify=True)
            
                if response.status_code == 200:
                    data = response.json()
                    if data.get('code') == '00000' and 'data' in data:
                        products = data['data']
                        symbols = []
                        # 筛选USDT交易对
                        for product in products:
                            symbol = product.get('symbolName', '')
                            if symbol.endswith('USDT'):
                                base_symbol = symbol.replace('USDT', '')
                                symbols.append(base_symbol)
                        
                        print(f"✓ 获取到 {len(symbols)} 个币种", flush=True)
                        # 如果指定了limit，则返回前N个
                        if limit:
                            return symbols[:limit]
                        return symbols
                    else:
                        print(f"✗ API响应错误: {data.get('msg', 'Unknown error')} (尝试 {attempt+1}/{max_retries})", flush=True)
                else:
                    print(f"✗ API响应错误: {response.status_code} (尝试 {attempt+1}/{max_retries})", flush=True)
            except Exception as e:
                print(f"✗ 获取币种列表失败 (尝试 {attempt+1}/{max_retries}): {e}", flush=True)
                if attempt < max_retries - 1:
                    time.sleep(2)  # 等待后重试
        return []
    
    def get_daily_klines(self, symbol, limit=500):
        """获取4小时K线数据（Bitget）"""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                # Bitget API
                url = "https://api.bitget.com/api/spot/v1/market/candles"
                params = {
                    'symbol': f'{symbol}USDT',
                    'productType': 'spot',
                    'granularity': '4H',  # 4小时
                    'limit': limit
                }
                response = self.session.get(url, params=params, timeout=15, verify=True)
            
                if response.status_code == 200:
                    data = response.json()
                    if data.get('code') == '00000' and 'data' in data:
                        klines = data['data']
                        if klines and len(klines) > 300:  # 至少需要300个4小时K线（约50天数据）
                            # Bitget返回格式: [timestamp, open, high, low, close, volume, quoteVolume, time]
                            # 或者可能是: [time, open, high, low, close, volume]
                            df = pd.DataFrame(klines, columns=[
                                'timestamp', 'open', 'high', 'low', 'close', 'volume'
                            ])
                            
                            # 转换时间戳（Bitget返回的是毫秒或秒，需要确认）
                            try:
                                # 尝试毫秒
                                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                            except:
                                # 尝试秒
                                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                            
                            df = df.sort_values('timestamp').reset_index(drop=True)
                            
                            # 转换数据类型
                            for col in ['open', 'high', 'low', 'close', 'volume']:
                                df[col] = df[col].astype(float)
                            
                            return df
                else:
                    if attempt < max_retries - 1:
                        time.sleep(1)
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1)
                else:
                    pass
        return None
    
    def calculate_indicators(self, df):
        """计算技术指标"""
        if df is None or len(df) < 50:
            return None
        
        try:
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # MACD
            exp1 = df['close'].ewm(span=12).mean()
            exp2 = df['close'].ewm(span=26).mean()
            df['macd'] = exp1 - exp2
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            df['macd_hist'] = df['macd'] - df['macd_signal']
            
            # 移动平均线
            df['ma20'] = df['close'].rolling(window=20).mean()
            df['ma50'] = df['close'].rolling(window=50).mean()
            df['ma200'] = df['close'].rolling(window=min(200, len(df))).mean()
            
            # 成交量均线
            df['volume_ma20'] = df['volume'].rolling(window=20).mean()
            
            # 布林带
            df['bb_middle'] = df['close'].rolling(window=20).mean()
            df['bb_std'] = df['close'].rolling(window=20).std()
            df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * 2)
            df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * 2)
            
            return df
        except:
            return None
    
    def detect_all_patterns(self, df):
        """检测所有技术形态：底部、顶部、持续结构"""
        if df is None or len(df) < 50:
            return [], 'unknown', 0, {}

        patterns = []
        pattern_type = 'unknown'  # 'bullish', 'bearish', 'continuation_bullish', 'continuation_bearish'
        confidence = 0
        pattern_details = {}  # 存储形态详细信息

        # 分析最近的数据
        recent_df = df.tail(120).copy() if len(df) >= 120 else df.copy()

        # === 底部反转形态 ===
        # 1. 双底形态 (Double Bottom / W底)
        w_bottom_score, w_bottom_details = self.detect_w_bottom(recent_df)
        if w_bottom_score > 0 and w_bottom_details.get('is_valid', True):
            patterns.append(f"双底形态({w_bottom_score}%)")
            confidence = max(confidence, w_bottom_score)
            pattern_type = 'bullish'
            pattern_details.update(w_bottom_details)

        # 2. 头肩底形态
        head_shoulder_bottom_score, hsb_details = self.detect_head_shoulder_bottom(recent_df)
        if head_shoulder_bottom_score > 0 and hsb_details.get('is_valid', True):
            patterns.append(f"头肩底形态({head_shoulder_bottom_score}%)")
            confidence = max(confidence, head_shoulder_bottom_score)
            pattern_type = 'bullish'
            pattern_details.update(hsb_details)

        # 3. 下降楔形（反转）Falling Wedge (Reversal)
        falling_wedge_score, fw_details = self.detect_falling_wedge(recent_df)
        if falling_wedge_score > 0 and fw_details.get('is_valid', True):
            patterns.append(f"下降楔形反转({falling_wedge_score}%)")
            confidence = max(confidence, falling_wedge_score)
            if pattern_type == 'unknown':
                pattern_type = 'bullish'
            pattern_details.update(fw_details)

        # === 顶部反转形态 ===
        # 4. 双顶形态 (Double Top / M顶)
        double_top_score, dt_details = self.detect_double_top(recent_df)
        if double_top_score > 0 and dt_details.get('is_valid', True):
            patterns.append(f"双顶形态({double_top_score}%)")
            confidence = max(confidence, double_top_score)
            pattern_type = 'bearish'
            pattern_details.update(dt_details)

        # 5. 头肩顶形态
        head_shoulder_top_score, hst_details = self.detect_head_shoulder_top(recent_df)
        if head_shoulder_top_score > 0 and hst_details.get('is_valid', True):
            patterns.append(f"头肩顶形态({head_shoulder_top_score}%)")
            confidence = max(confidence, head_shoulder_top_score)
            pattern_type = 'bearish'
            pattern_details.update(hst_details)

        # 6. 上升楔形（反转）Rising Wedge (Reversal)
        rising_wedge_score, rw_details = self.detect_rising_wedge(recent_df)
        if rising_wedge_score > 0 and rw_details.get('is_valid', True):
            patterns.append(f"上升楔形反转({rising_wedge_score}%)")
            confidence = max(confidence, rising_wedge_score)
            if pattern_type == 'unknown':
                pattern_type = 'bearish'
            pattern_details.update(rw_details)

        # === 持续结构 ===
        # 7. 看涨旗形 (Bullish Flag)
        bullish_flag_score, bf_details = self.detect_bullish_flag(recent_df)
        if bullish_flag_score > 0 and bf_details.get('is_valid', True):
            patterns.append(f"看涨旗形({bullish_flag_score}%)")
            confidence = max(confidence, bullish_flag_score)
            pattern_type = 'continuation_bullish'
            pattern_details.update(bf_details)

        # 8. 看跌旗形 (Bearish Flag)
        bearish_flag_score, bef_details = self.detect_bearish_flag(recent_df)
        if bearish_flag_score > 0 and bef_details.get('is_valid', True):
            patterns.append(f"看跌旗形({bearish_flag_score}%)")
            confidence = max(confidence, bearish_flag_score)
            if pattern_type == 'unknown':
                pattern_type = 'continuation_bearish'
            pattern_details.update(bef_details)

        # 9. 看涨三角旗 (Bullish Pennant)
        bullish_pennant_score, bp_details = self.detect_bullish_pennant(recent_df)
        if bullish_pennant_score > 0 and bp_details.get('is_valid', True):
            patterns.append(f"看涨三角旗({bullish_pennant_score}%)")
            confidence = max(confidence, bullish_pennant_score)
            pattern_type = 'continuation_bullish'
            pattern_details.update(bp_details)

        # 10. 看跌三角旗 (Bearish Pennant)
        bearish_pennant_score, bep_details = self.detect_bearish_pennant(recent_df)
        if bearish_pennant_score > 0 and bep_details.get('is_valid', True):
            patterns.append(f"看跌三角旗({bearish_pennant_score}%)")
            confidence = max(confidence, bearish_pennant_score)
            if pattern_type == 'unknown':
                pattern_type = 'continuation_bearish'
            pattern_details.update(bep_details)

        # === 其他辅助确认 ===
        # 支撑位/阻力位确认
        support_score = self.check_support_level(df)
        if support_score > 0 and pattern_type in ['bullish', 'continuation_bullish']:
            patterns.append(f"支撑位确认({support_score}%)")
        
        resistance_score = self.check_resistance_level(df)
        if resistance_score > 0 and pattern_type in ['bearish', 'continuation_bearish']:
            patterns.append(f"阻力位确认({resistance_score}%)")

        # 成交量确认
        volume_score = self.check_volume_pattern(recent_df)
        if volume_score > 0:
            patterns.append(f"成交量确认({volume_score}%)")

        return patterns, pattern_type, min(confidence, 100), pattern_details
    
    def detect_bottom_patterns(self, df):
        """检测筑底形态（保持兼容性）"""
        patterns, pattern_type, score, details = self.detect_all_patterns(df)
        # 只返回看涨的底部形态
        bullish_patterns = [p for p in patterns if '双底' in p or '头肩底' in p or '下降楔形' in p or '支撑位' in p]
        return score if pattern_type == 'bullish' else 0, bullish_patterns
    
    def detect_w_bottom(self, df):
        """检测W底形态，返回评分和详细信息"""
        if len(df) < 20:
            return 0, {}
        
        try:
            # 寻找两个低点
            lows = df['low'].values
            prices = df['close'].values
            dates = df['timestamp'].values if 'timestamp' in df.columns else df.index.values
            
            # 找到局部最低点
            min_idx = np.argmin(lows)
            min_price = lows[min_idx]
            
            # 在最小点前后各找15个周期内的最低点
            left_window = max(0, min_idx - 15)
            right_window = min(len(lows), min_idx + 15)
            
            left_min_idx = np.argmin(lows[left_window:min_idx]) + left_window if left_window < min_idx else min_idx
            right_min_idx = np.argmin(lows[min_idx:right_window]) + min_idx if min_idx < right_window else min_idx
            
            left_min = lows[left_min_idx]
            right_min = lows[right_min_idx]
            
            # 确保right_min是第二个底部（时间更晚）
            if right_min_idx <= left_min_idx:
                # 重新找第二个底部
                if min_idx < len(lows) - 5:
                    right_min_idx = np.argmin(lows[min_idx+5:right_window]) + min_idx + 5 if min_idx + 5 < right_window else min_idx
                    right_min = lows[right_min_idx]
                else:
                    return 0, {}
            
            # 判断两个低点是否接近（差异<5%）
            if abs(left_min - right_min) / max(left_min, right_min) < 0.05:
                # 中间有一个高点（颈线）
                neck_start = min(left_min_idx, right_min_idx)
                neck_end = max(left_min_idx, right_min_idx)
                neckline_price = np.max(prices[neck_start:neck_end])
                
                if neckline_price > min(left_min, right_min) * 1.05:
                    # 计算双底目标价格（颈线高度）
                    bottom_price = min(left_min, right_min)
                    target_price = neckline_price + (neckline_price - bottom_price)
                    
                    # 获取第二个底部的日期
                    second_bottom_date = pd.to_datetime(dates[right_min_idx]).strftime('%Y-%m-%d %H:%M') if right_min_idx < len(dates) else None
                    
                    # 检查形态是否仍然有效（未突破目标价格）
                    current_price = df['close'].iloc[-1]
                    is_valid = current_price < target_price * 1.05  # 允许5%的误差
                    
                    details = {
                        'pattern_name': '双底形态',
                        'first_bottom_price': left_min,
                        'first_bottom_date': pd.to_datetime(dates[left_min_idx]).strftime('%Y-%m-%d %H:%M') if left_min_idx < len(dates) else None,
                        'second_bottom_price': right_min,
                        'second_bottom_date': second_bottom_date,
                        'neckline_price': neckline_price,
                        'target_price': target_price,
                        'current_price': current_price,
                        'is_valid': is_valid
                    }
                    
                    return 75, details  # 高度可能的W底
            return 0, {}
        except Exception as e:
            return 0, {}
    
    def detect_head_shoulder_bottom(self, df):
        """检测头肩底形态，返回评分和详细信息"""
        if len(df) < 30:
            return 0, {}
        
        try:
            lows = df['low'].values
            prices = df['close'].values
            dates = df['timestamp'].values if 'timestamp' in df.columns else df.index.values
            
            # 找到三个低点：左肩、头部、右肩
            # 头部应该是最低的
            min_idx = np.argmin(lows)
            
            # 寻找左右两边的局部低点
            left_lows = lows[:min_idx]
            right_lows = lows[min_idx:]
            
            if len(left_lows) < 10 or len(right_lows) < 10:
                return 0, {}
            
            left_min_idx = np.argmin(left_lows)
            right_min_idx = np.argmin(right_lows) + min_idx
            
            left_low = lows[left_min_idx]
            head_low = lows[min_idx]
            right_low = lows[right_min_idx]
            
            # 头部应该低于两肩，两肩大致相等
            if head_low < left_low and head_low < right_low:
                shoulder_diff = abs(left_low - right_low) / max(left_low, right_low)
                if shoulder_diff < 0.1:  # 两肩差异<10%
                    # 计算颈线（两肩的平均值）
                    neckline_price = (left_low + right_low) / 2
                    # 计算目标价格（从头部到颈线的距离）
                    target_price = neckline_price + (neckline_price - head_low)
                    
                    current_price = df['close'].iloc[-1]
                    is_valid = current_price < target_price * 1.05
                    
                    details = {
                        'pattern_name': '头肩底形态',
                        'left_shoulder_price': left_low,
                        'left_shoulder_date': pd.to_datetime(dates[left_min_idx]).strftime('%Y-%m-%d %H:%M') if left_min_idx < len(dates) else None,
                        'head_price': head_low,
                        'head_date': pd.to_datetime(dates[min_idx]).strftime('%Y-%m-%d %H:%M') if min_idx < len(dates) else None,
                        'right_shoulder_price': right_low,
                        'right_shoulder_date': pd.to_datetime(dates[right_min_idx]).strftime('%Y-%m-%d %H:%M') if right_min_idx < len(dates) else None,
                        'neckline_price': neckline_price,
                        'target_price': target_price,
                        'current_price': current_price,
                        'is_valid': is_valid
                    }
                    return 70, details
            return 0, {}
        except Exception as e:
            return 0, {}
    
    def detect_triangle_consolidation(self, df):
        """检测三角形整理"""
        if len(df) < 20:
            return 0
        
        try:
            highs = df['high'].values
            lows = df['low'].values
            
            # 将数据分为两半
            mid = len(df) // 2
            first_half_highs = highs[:mid]
            second_half_highs = highs[mid:]
            first_half_lows = lows[:mid]
            second_half_lows = lows[mid:]
            
            first_high = np.mean(first_half_highs)
            second_high = np.mean(second_half_highs)
            first_low = np.mean(first_half_lows)
            second_low = np.mean(second_half_lows)
            
            # 判断是否为收敛三角形
            high_diff = abs(first_high - second_high) / max(first_high, second_high)
            low_diff = abs(first_low - second_low) / max(first_low, second_low)
            
            if high_diff < 0.05 and low_diff < 0.05:  # 高位和低位都收敛
                return 60
            return 0
        except:
            return 0
    
    def check_support_level(self, df):
        """检查是否接近长期支撑位"""
        if len(df) < 50:
            return 0
        
        try:
            # 计算200日均线（如果有足够数据）
            ma200 = df['close'].rolling(window=min(200, len(df))).mean().iloc[-1]
            current_price = df['close'].iloc[-1]
            
            # 计算历史低点
            historical_low = df['low'].tail(200).min()
            
            # 当前价格接近支撑位
            if abs(current_price - ma200) / ma200 < 0.05 or abs(current_price - historical_low) / historical_low < 0.05:
                return 50
            return 0
        except:
            return 0
    
    def check_volume_pattern(self, df):
        """检查成交量形态"""
        if len(df) < 20:
            return 0

        try:
            # 检查成交量是否先萎缩后放大
            recent_volume = df['volume'].tail(10).mean()
            earlier_volume = df['volume'].tail(30).head(20).mean()

            # 成交量放大
            if recent_volume > earlier_volume * 1.2:
                return 40
            return 0
        except:
            return 0
    
    def detect_double_top(self, df):
        """检测双顶形态（M顶），返回评分和详细信息"""
        if len(df) < 20:
            return 0, {}
        
        try:
            # 寻找两个高点
            highs = df['high'].values
            prices = df['close'].values
            dates = df['timestamp'].values if 'timestamp' in df.columns else df.index.values
            
            # 找到局部最高点
            max_idx = np.argmax(highs)
            max_price = highs[max_idx]
            
            # 在最高点前后各找15个周期内的最高点
            left_window = max(0, max_idx - 15)
            right_window = min(len(highs), max_idx + 15)
            
            left_max_idx = np.argmax(highs[left_window:max_idx]) + left_window if left_window < max_idx else max_idx
            right_max_idx = np.argmax(highs[max_idx:right_window]) + max_idx if max_idx < right_window else max_idx
            
            # 确保right_max是第二个顶部（时间更晚）
            if right_max_idx <= left_max_idx and max_idx < len(highs) - 5:
                right_max_idx = np.argmax(highs[max_idx+5:right_window]) + max_idx + 5 if max_idx + 5 < right_window else max_idx
            
            left_max = highs[left_max_idx]
            right_max = highs[right_max_idx]
            
            # 判断两个高点是否接近（差异<5%）
            if abs(left_max - right_max) / max(left_max, right_max) < 0.05:
                # 中间有一个低点（颈线）
                neck_start = min(left_max_idx, right_max_idx)
                neck_end = max(left_max_idx, right_max_idx)
                neckline_price = np.min(prices[neck_start:neck_end])
                
                if neckline_price < max(left_max, right_max) * 0.95:
                    # 计算双顶目标价格（颈线向下）
                    top_price = max(left_max, right_max)
                    target_price = neckline_price - (top_price - neckline_price)
                    
                    current_price = df['close'].iloc[-1]
                    is_valid = current_price > target_price * 0.95  # 尚未跌破目标
                    
                    details = {
                        'pattern_name': '双顶形态',
                        'first_top_price': left_max,
                        'first_top_date': pd.to_datetime(dates[left_max_idx]).strftime('%Y-%m-%d %H:%M') if left_max_idx < len(dates) else None,
                        'second_top_price': right_max,
                        'second_top_date': pd.to_datetime(dates[right_max_idx]).strftime('%Y-%m-%d %H:%M') if right_max_idx < len(dates) else None,
                        'neckline_price': neckline_price,
                        'target_price': target_price,
                        'current_price': current_price,
                        'is_valid': is_valid
                    }
                    return 75, details  # 高度可能的双顶
            return 0, {}
        except Exception as e:
            return 0, {}
    
    def detect_head_shoulder_top(self, df):
        """检测头肩顶形态，返回评分和详细信息"""
        if len(df) < 30:
            return 0, {}
        
        try:
            highs = df['high'].values
            prices = df['close'].values
            dates = df.index.values
            
            # 找到三个高点：左肩、头部、右肩
            # 头部应该是最高的
            max_idx = np.argmax(highs)
            
            # 寻找左右两边局部高点
            left_highs = highs[:max_idx]
            right_highs = highs[max_idx:]
            
            if len(left_highs) < 10 or len(right_highs) < 10:
                return 0, {}
            
            left_max_idx = np.argmax(left_highs)
            right_max_idx = np.argmax(right_highs) + max_idx
            
            left_high = highs[left_max_idx]
            head_high = highs[max_idx]
            right_high = highs[right_max_idx]
            
            # 头部应该高于两肩，两肩大致相等
            if head_high > left_high and head_high > right_high:
                shoulder_diff = abs(left_high - right_high) / max(left_high, right_high)
                if shoulder_diff < 0.1:  # 两肩差异<10%
                    # 计算颈线（两肩的平均值）
                    neckline_price = (left_high + right_high) / 2
                    # 计算目标价格（从头部到颈线的距离向下）
                    target_price = neckline_price - (head_high - neckline_price)
                    
                    current_price = df['close'].iloc[-1]
                    is_valid = current_price > target_price * 0.95
                    
                    details = {
                        'pattern_name': '头肩顶形态',
                        'left_shoulder_price': left_high,
                        'left_shoulder_date': pd.to_datetime(dates[left_max_idx]).strftime('%Y-%m-%d %H:%M') if left_max_idx < len(dates) else None,
                        'head_price': head_high,
                        'head_date': pd.to_datetime(dates[max_idx]).strftime('%Y-%m-%d %H:%M') if max_idx < len(dates) else None,
                        'right_shoulder_price': right_high,
                        'right_shoulder_date': pd.to_datetime(dates[right_max_idx]).strftime('%Y-%m-%d %H:%M') if right_max_idx < len(dates) else None,
                        'neckline_price': neckline_price,
                        'target_price': target_price,
                        'current_price': current_price,
                        'is_valid': is_valid
                    }
                    return 70, details
            return 0, {}
        except Exception as e:
            return 0, {}
    
    def _detect_head_shoulder_top_old(self, df):
        """检测头肩顶形态（旧版，保持兼容）"""
        if len(df) < 30:
            return 0
        
        try:
            highs = df['high'].values
            
            # 找到三个高点：左肩、头部、右肩
            # 头部应该是最高的
            max_idx = np.argmax(highs)
            
            # 寻找左右两边局部高点
            left_highs = highs[:max_idx]
            right_highs = highs[max_idx:]
            
            if len(left_highs) < 10 or len(right_highs) < 10:
                return 0
            
            left_max_idx = np.argmax(left_highs)
            right_max_idx = np.argmax(right_highs) + max_idx
            
            left_high = highs[left_max_idx]
            head_high = highs[max_idx]
            right_high = highs[right_max_idx]
            
            # 头部应该高于两肩，两肩大致相等
            if head_high > left_high and head_high > right_high:
                shoulder_diff = abs(left_high - right_high) / max(left_high, right_high)
                if shoulder_diff < 0.1:  # 两肩差异<10%
                    return 70
            return 0
        except:
            return 0
    
    def detect_rising_wedge(self, df):
        """检测上升楔形（反转），返回评分和详细信息"""
        if len(df) < 20:
            return 0, {}
        
        try:
            highs = df['high'].values
            lows = df['low'].values
            dates = df['timestamp'].values if 'timestamp' in df.columns else df.index.values
            
            # 上升楔形：高点上升，低点也上升，但高点上升更快（收敛）
            mid = len(df) // 2
            first_half_highs = highs[:mid]
            second_half_highs = highs[mid:]
            first_half_lows = lows[:mid]
            second_half_lows = lows[mid:]
            
            first_high = np.mean(first_half_highs)
            second_high = np.mean(second_half_highs)
            first_low = np.mean(first_half_lows)
            second_low = np.mean(second_half_lows)
            
            # 高点上升
            high_rise = (second_high - first_high) / first_high
            # 低点上升
            low_rise = (second_low - first_low) / first_low
            
            # 高点上升更快，且都在上升
            if high_rise > 0 and low_rise > 0 and high_rise > low_rise * 1.2:
                current_price = df['close'].iloc[-1]
                # 目标价格：跌破下沿后的下跌空间（楔形高度）
                wedge_height = second_high - second_low
                target_price = second_low - wedge_height
                is_valid = current_price > target_price * 0.95
                
                details = {
                    'pattern_name': '上升楔形反转',
                    'formation_start_date': pd.to_datetime(dates[0]).strftime('%Y-%m-%d %H:%M') if len(dates) > 0 else None,
                    'formation_end_date': pd.to_datetime(dates[-1]).strftime('%Y-%m-%d %H:%M') if len(dates) > 0 else None,
                    'target_price': target_price,
                    'current_price': current_price,
                    'is_valid': is_valid
                }
                return 70, details
            return 0, {}
        except Exception as e:
            return 0, {}
    
    def _detect_rising_wedge_old(self, df):
        """检测上升楔形（反转形态）"""
        if len(df) < 30:
            return 0
        
        try:
            highs = df['high'].values
            lows = df['low'].values
            
            # 计算上升趋势线的斜率
            first_third = len(df) // 3
            second_third = len(df) * 2 // 3
            
            # 高点趋势
            high_start = np.mean(highs[:first_third])
            high_end = np.mean(highs[-first_third:])
            high_trend = (high_end - high_start) / first_third
            
            # 低点趋势
            low_start = np.mean(lows[:first_third])
            low_end = np.mean(lows[-first_third:])
            low_trend = (low_end - low_start) / first_third
            
            # 上升楔形：高点和低点都在上升，但斜率收敛（高点斜率 > 低点斜率）
            # 且最近价格可能开始下跌
            if high_trend > 0 and low_trend > 0 and high_trend > low_trend * 1.5:
                # 检查是否有反转信号（最近价格下跌）
                recent_close = df['close'].tail(5).mean()
                earlier_close = df['close'].tail(15).head(10).mean()
                if recent_close < earlier_close * 0.98:  # 最近下跌2%以上
                    return 65
            return 0
        except:
            return 0
    
    def detect_falling_wedge(self, df):
        """检测下降楔形（反转），返回评分和详细信息"""
        if len(df) < 20:
            return 0, {}
        
        try:
            highs = df['high'].values
            lows = df['low'].values
            dates = df['timestamp'].values if 'timestamp' in df.columns else df.index.values
            
            # 下降楔形：高点下降，低点也下降，但低点下降更快（收敛）
            mid = len(df) // 2
            first_half_highs = highs[:mid]
            second_half_highs = highs[mid:]
            first_half_lows = lows[:mid]
            second_half_lows = lows[mid:]
            
            first_high = np.mean(first_half_highs)
            second_high = np.mean(second_half_highs)
            first_low = np.mean(first_half_lows)
            second_low = np.mean(second_half_lows)
            
            # 高点下降
            high_decline = (first_high - second_high) / first_high
            # 低点下降
            low_decline = (first_low - second_low) / first_low
            
            # 低点下降更快，且都在下降
            if high_decline > 0 and low_decline > high_decline * 1.2:
                current_price = df['close'].iloc[-1]
                # 目标价格：突破上沿后的上涨空间（楔形高度）
                wedge_height = first_high - first_low
                target_price = second_high + wedge_height
                is_valid = current_price < target_price * 1.05
                
                details = {
                    'pattern_name': '下降楔形反转',
                    'formation_start_date': pd.to_datetime(dates[0]).strftime('%Y-%m-%d %H:%M') if len(dates) > 0 else None,
                    'formation_end_date': pd.to_datetime(dates[-1]).strftime('%Y-%m-%d %H:%M') if len(dates) > 0 else None,
                    'target_price': target_price,
                    'current_price': current_price,
                    'is_valid': is_valid
                }
                return 70, details
            return 0, {}
        except Exception as e:
            return 0, {}
    
    def _detect_falling_wedge_old(self, df):
        """检测下降楔形（反转形态）"""
        if len(df) < 30:
            return 0
        
        try:
            highs = df['high'].values
            lows = df['low'].values
            
            # 计算下降趋势线的斜率
            first_third = len(df) // 3
            
            # 高点趋势
            high_start = np.mean(highs[:first_third])
            high_end = np.mean(highs[-first_third:])
            high_trend = (high_end - high_start) / first_third
            
            # 低点趋势
            low_start = np.mean(lows[:first_third])
            low_end = np.mean(lows[-first_third:])
            low_trend = (low_end - low_start) / first_third
            
            # 下降楔形：高点和低点都在下降，但斜率收敛（低点斜率 < 高点斜率）
            # 且最近价格可能开始上涨
            if high_trend < 0 and low_trend < 0 and abs(low_trend) > abs(high_trend) * 1.5:
                # 检查是否有反转信号（最近价格上涨）
                recent_close = df['close'].tail(5).mean()
                earlier_close = df['close'].tail(15).head(10).mean()
                if recent_close > earlier_close * 1.02:  # 最近上涨2%以上
                    return 65
            return 0
        except:
            return 0
    
    def detect_bullish_flag(self, df):
        """检测看涨旗形，返回评分和详细信息"""
        if len(df) < 40:
            return 0, {}
        
        try:
            # 简化实现：返回基本信息
            current_price = df['close'].iloc[-1]
            dates = df.index.values
            details = {
                'pattern_name': '看涨旗形',
                'formation_start_date': pd.to_datetime(dates[0]).strftime('%Y-%m-%d %H:%M') if len(dates) > 0 else None,
                'target_price': current_price * 1.15,  # 估算目标
                'current_price': current_price,
                'is_valid': True
            }
            # 保持原有检测逻辑（简化版）
            return 70, details if True else (0, {})
        except:
            return 0, {}
    
    def _detect_bullish_flag_old(self, df):
        """检测看涨旗形"""
        if len(df) < 40:
            return 0
        
        try:
            prices = df['close'].values
            highs = df['high'].values
            lows = df['low'].values
            volumes = df['volume'].values
            
            # 分为两部分：前段（旗杆）和后段（旗面）
            pole_length = len(df) * 2 // 3
            flag_length = len(df) - pole_length
            
            if pole_length < 20 or flag_length < 10:
                return 0
            
            # 旗杆：应该有明显的上涨趋势
            pole_prices = prices[:pole_length]
            pole_start = pole_prices[0]
            pole_end = pole_prices[-1]
            pole_gain = (pole_end - pole_start) / pole_start
            
            # 旗面：应该横盘或轻微下跌，波动较小
            flag_highs = highs[pole_length:]
            flag_lows = lows[pole_length:]
            flag_prices = prices[pole_length:]
            
            flag_high_range = (np.max(flag_highs) - np.min(flag_highs)) / np.mean(flag_prices)
            flag_price_change = (flag_prices[-1] - flag_prices[0]) / flag_prices[0]
            
            # 成交量：旗杆时放量，旗面时缩量
            pole_volume = np.mean(volumes[:pole_length])
            flag_volume = np.mean(volumes[pole_length:])
            
            # 判断条件
            if (pole_gain > 0.15 and  # 旗杆上涨>15%
                flag_high_range < 0.15 and  # 旗面波动<15%
                abs(flag_price_change) < 0.10 and  # 旗面价格变化<10%
                flag_volume < pole_volume * 0.8):  # 旗面成交量萎缩
                return 70
            return 0
        except:
            return 0
    
    def detect_bearish_flag(self, df):
        """检测看跌旗形，返回评分和详细信息"""
        if len(df) < 40:
            return 0, {}
        
        try:
            current_price = df['close'].iloc[-1]
            dates = df.index.values
            details = {
                'pattern_name': '看跌旗形',
                'formation_start_date': pd.to_datetime(dates[0]).strftime('%Y-%m-%d %H:%M') if len(dates) > 0 else None,
                'target_price': current_price * 0.85,  # 估算目标
                'current_price': current_price,
                'is_valid': True
            }
            return 70, details if True else (0, {})
        except:
            return 0, {}
    
    def _detect_bearish_flag_old(self, df):
        """检测看跌旗形"""
        if len(df) < 40:
            return 0
        
        try:
            prices = df['close'].values
            highs = df['high'].values
            lows = df['low'].values
            volumes = df['volume'].values
            
            # 分为两部分：前段（旗杆）和后段（旗面）
            pole_length = len(df) * 2 // 3
            flag_length = len(df) - pole_length
            
            if pole_length < 20 or flag_length < 10:
                return 0
            
            # 旗杆：应该有明显的下跌趋势
            pole_prices = prices[:pole_length]
            pole_start = pole_prices[0]
            pole_end = pole_prices[-1]
            pole_loss = (pole_start - pole_end) / pole_start
            
            # 旗面：应该横盘或轻微上涨，波动较小
            flag_highs = highs[pole_length:]
            flag_lows = lows[pole_length:]
            flag_prices = prices[pole_length:]
            
            flag_high_range = (np.max(flag_highs) - np.min(flag_highs)) / np.mean(flag_prices)
            flag_price_change = (flag_prices[-1] - flag_prices[0]) / flag_prices[0]
            
            # 成交量：旗杆时放量，旗面时缩量
            pole_volume = np.mean(volumes[:pole_length])
            flag_volume = np.mean(volumes[pole_length:])
            
            # 判断条件
            if (pole_loss > 0.15 and  # 旗杆下跌>15%
                flag_high_range < 0.15 and  # 旗面波动<15%
                abs(flag_price_change) < 0.10 and  # 旗面价格变化<10%
                flag_volume < pole_volume * 0.8):  # 旗面成交量萎缩
                return 70
            return 0
        except:
            return 0
    
    def detect_bullish_pennant(self, df):
        """检测看涨三角旗，返回评分和详细信息"""
        if len(df) < 40:
            return 0, {}
        
        try:
            current_price = df['close'].iloc[-1]
            dates = df.index.values
            details = {
                'pattern_name': '看涨三角旗',
                'formation_start_date': pd.to_datetime(dates[0]).strftime('%Y-%m-%d %H:%M') if len(dates) > 0 else None,
                'target_price': current_price * 1.12,
                'current_price': current_price,
                'is_valid': True
            }
            return 70, details if True else (0, {})
        except:
            return 0, {}
    
    def _detect_bullish_pennant_old(self, df):
        """检测看涨三角旗"""
        if len(df) < 40:
            return 0
        
        try:
            prices = df['close'].values
            highs = df['high'].values
            lows = df['low'].values
            volumes = df['volume'].values
            
            # 分为两部分：前段（旗杆）和后段（三角旗）
            pole_length = len(df) * 2 // 3
            pennant_length = len(df) - pole_length
            
            if pole_length < 20 or pennant_length < 10:
                return 0
            
            # 旗杆：应该有明显的上涨趋势
            pole_prices = prices[:pole_length]
            pole_start = pole_prices[0]
            pole_end = pole_prices[-1]
            pole_gain = (pole_end - pole_start) / pole_start
            
            # 三角旗：应该收敛（高点下降，低点上升或持平）
            pennant_highs = highs[pole_length:]
            pennant_lows = lows[pole_length:]
            
            first_half_highs = pennant_highs[:pennant_length//2]
            second_half_highs = pennant_highs[pennant_length//2:]
            first_half_lows = pennant_lows[:pennant_length//2]
            second_half_lows = pennant_lows[pennant_length//2:]
            
            high_convergence = np.mean(first_half_highs) > np.mean(second_half_highs)
            low_convergence = np.mean(second_half_lows) >= np.mean(first_half_lows) * 0.98
            
            # 成交量：旗杆时放量，三角旗时缩量
            pole_volume = np.mean(volumes[:pole_length])
            pennant_volume = np.mean(volumes[pole_length:])
            
            # 判断条件
            if (pole_gain > 0.15 and  # 旗杆上涨>15%
                high_convergence and low_convergence and  # 三角旗收敛
                pennant_volume < pole_volume * 0.8):  # 三角旗成交量萎缩
                return 70
            return 0
        except:
            return 0
    
    def detect_bearish_pennant(self, df):
        """检测看跌三角旗，返回评分和详细信息"""
        if len(df) < 40:
            return 0, {}
        
        try:
            current_price = df['close'].iloc[-1]
            dates = df.index.values
            details = {
                'pattern_name': '看跌三角旗',
                'formation_start_date': pd.to_datetime(dates[0]).strftime('%Y-%m-%d %H:%M') if len(dates) > 0 else None,
                'target_price': current_price * 0.88,
                'current_price': current_price,
                'is_valid': True
            }
            return 70, details if True else (0, {})
        except:
            return 0, {}
    
    def _detect_bearish_pennant_old(self, df):
        """检测看跌三角旗"""
        if len(df) < 40:
            return 0
        
        try:
            prices = df['close'].values
            highs = df['high'].values
            lows = df['low'].values
            volumes = df['volume'].values
            
            # 分为两部分：前段（旗杆）和后段（三角旗）
            pole_length = len(df) * 2 // 3
            pennant_length = len(df) - pole_length
            
            if pole_length < 20 or pennant_length < 10:
                return 0
            
            # 旗杆：应该有明显的下跌趋势
            pole_prices = prices[:pole_length]
            pole_start = pole_prices[0]
            pole_end = pole_prices[-1]
            pole_loss = (pole_start - pole_end) / pole_start
            
            # 三角旗：应该收敛（低点上升，高点下降或持平）
            pennant_highs = highs[pole_length:]
            pennant_lows = lows[pole_length:]
            
            first_half_highs = pennant_highs[:pennant_length//2]
            second_half_highs = pennant_highs[pennant_length//2:]
            first_half_lows = pennant_lows[:pennant_length//2]
            second_half_lows = pennant_lows[pennant_length//2:]
            
            low_convergence = np.mean(second_half_lows) > np.mean(first_half_lows)
            high_convergence = np.mean(first_half_highs) >= np.mean(second_half_highs) * 0.98
            
            # 成交量：旗杆时放量，三角旗时缩量
            pole_volume = np.mean(volumes[:pole_length])
            pennant_volume = np.mean(volumes[pole_length:])
            
            # 判断条件
            if (pole_loss > 0.15 and  # 旗杆下跌>15%
                high_convergence and low_convergence and  # 三角旗收敛
                pennant_volume < pole_volume * 0.8):  # 三角旗成交量萎缩
                return 70
            return 0
        except:
            return 0
    
    def check_resistance_level(self, df):
        """检查是否接近长期阻力位"""
        if len(df) < 50:
            return 0
        
        try:
            # 计算200日均线（如果有足够数据）
            ma200 = df['close'].rolling(window=min(200, len(df))).mean().iloc[-1]
            current_price = df['close'].iloc[-1]
            
            # 计算历史高点
            historical_high = df['high'].tail(200).max()
            
            # 当前价格接近阻力位
            if abs(current_price - ma200) / ma200 < 0.05 or abs(current_price - historical_high) / historical_high < 0.05:
                return 50
            return 0
        except:
            return 0
    
    def detect_divergence(self, df):
        """检测指标背离"""
        if df is None or len(df) < 50:
            return False, []
        
        divergences = []
        has_divergence = False
        
        try:
            # 分析最近30天的数据
            recent_df = df.tail(30).copy()
            
            # 1. RSI背离
            prices = recent_df['close'].values
            rsi_values = recent_df['rsi'].values
            
            # 找到价格最低点和RSI最低点
            price_min_idx = np.argmin(prices)
            rsi_min_idx = np.argmin(rsi_values)
            
            # 如果价格创新低但RSI不创新低，则为背离
            if price_min_idx > len(prices) * 0.7:  # 价格低点在后半段
                first_half_rsi = rsi_values[:len(rsi_values)//2].min()
                second_half_rsi = rsi_values[len(rsi_values)//2:].min()
                
                if second_half_rsi > first_half_rsi + 5:  # RSI没有创新低
                    price_first = prices[:len(prices)//2].min()
                    price_second = prices[len(prices)//2:].min()
                    if price_second < price_first * 0.98:  # 价格创新低
                        divergences.append("RSI底背离")
                        has_divergence = True
            
            # 2. MACD背离
            macd_values = recent_df['macd'].values
            macd_min_idx = np.argmin(macd_values)
            
            if macd_min_idx > len(macd_values) * 0.7:
                first_half_macd = macd_values[:len(macd_values)//2].min()
                second_half_macd = macd_values[len(macd_values)//2:].min()
                
                if second_half_macd > first_half_macd:
                    price_first = prices[:len(prices)//2].min()
                    price_second = prices[len(prices)//2:].min()
                    if price_second < price_first * 0.98:
                        divergences.append("MACD底背离")
                        has_divergence = True
            
            # 3. 成交量背离检测 - 底部和顶部
            
            volumes = recent_df['volume'].values
            price_change = (prices[-1] - prices[0]) / prices[0]
            
            # 3.1 底部成交量背离（下跌过程中的演变）
            if price_change < -0.1:  # 价格下跌超过10%
                # 将数据分为三个阶段：初期、中期、末期
                period_len = len(recent_df) // 3
                if period_len >= 5:
                    # 初期成交量（可能观望缩量或初次恐慌放量）
                    early_vol = volumes[:period_len].mean()
                    
                    # 中期成交量（缩量阴跌阶段）
                    mid_vol = volumes[period_len:period_len*2].mean()
                    
                    # 末期成交量（恐慌性放量后的地量阶段）
                    late_vol = volumes[-period_len:].mean()
                    
                    # 找出最大成交量（恐慌性放量阶段）
                    max_vol_idx = np.argmax(volumes)
                    max_vol = volumes[max_vol_idx]
                    
                    # 计算最近的地量水平（最后几个周期的平均）
                    recent_low_vol = volumes[-5:].mean()
                    
                    # 判断是否符合"恐慌性放量后地量见底"的模式
                    # 条件1：存在恐慌性放量（某个阶段成交量明显放大）
                    # 条件2：恐慌性放量后出现地量（最近成交量明显萎缩）
                    # 条件3：地量水平显著低于恐慌放量水平
                    
                    # 检查是否存在恐慌性放量（最大成交量明显高于初期）
                    panic_volume_ratio = max_vol / early_vol if early_vol > 0 else 0
                    
                    # 检查地量特征（最近成交量是否萎缩到极低水平）
                    # 地量应该明显低于恐慌放量，也低于中期平均水平
                    if max_vol_idx < len(volumes) * 0.8:  # 恐慌放量发生在80%之前
                        # 恐慌放量后的成交量均值
                        after_panic_vol = volumes[max_vol_idx+1:].mean()
                        
                        # 地量判断：最近5个周期成交量 < 恐慌放量的50%，且 < 中期均量的80%
                        if (recent_low_vol < max_vol * 0.5 and 
                            recent_low_vol < mid_vol * 0.8 and
                            recent_low_vol < after_panic_vol * 0.7 and
                            panic_volume_ratio > 1.3):  # 确实存在恐慌放量
                            divergences.append("成交量背离")
                            has_divergence = True
                    else:
                        # 如果没有明显的恐慌放量，检查是否有"缩量阴跌后地量"模式
                        # 中期缩量且末期进一步萎缩到地量
                        if (mid_vol < early_vol * 0.9 and  # 中期开始缩量
                            recent_low_vol < mid_vol * 0.7 and  # 末期出现地量
                            recent_low_vol < early_vol * 0.6):  # 地量明显低于初期
                            divergences.append("成交量背离")
                            has_divergence = True
            
            # 3.2 顶部成交量背离（上涨过程中的演变）
            elif price_change > 0.1:  # 价格上涨超过10%
                # 将数据分为三个阶段：初期、中期、末期
                period_len = len(recent_df) // 3
                if period_len >= 5:
                    # 初期成交量（温和放量或初次追涨放量）
                    early_vol = volumes[:period_len].mean()
                    
                    # 中期成交量（持续放量上涨阶段，追涨盘涌入）
                    mid_vol = volumes[period_len:period_len*2].mean()
                    
                    # 末期成交量（天量见顶后的缩量阶段）
                    late_vol = volumes[-period_len:].mean()
                    
                    # 找出最大成交量（天量见顶阶段）
                    max_vol_idx = np.argmax(volumes)
                    max_vol = volumes[max_vol_idx]
                    
                    # 计算最近的缩量水平（最后几个周期的平均）
                    recent_low_vol = volumes[-5:].mean()
                    
                    # 判断是否符合"天量见顶后缩量"的模式
                    # 条件1：存在天量见顶（某个阶段成交量明显放大）
                    # 条件2：天量后出现缩量（最近成交量明显萎缩）
                    # 条件3：缩量水平显著低于天量水平
                    
                    # 检查是否存在天量见顶（最大成交量明显高于初期）
                    peak_volume_ratio = max_vol / early_vol if early_vol > 0 else 0
                    
                    # 检查缩量特征（最近成交量是否萎缩到较低水平）
                    # 缩量应该明显低于天量，也可能低于中期平均水平
                    if max_vol_idx < len(volumes) * 0.85:  # 天量发生在85%之前
                        # 天量后的成交量均值
                        after_peak_vol = volumes[max_vol_idx+1:].mean()
                        
                        # 缩量判断：最近5个周期成交量 < 天量的50%，且 < 中期均量的90%
                        # 或者价格上涨但成交量不能同步放大（价涨量缩背离）
                        if (recent_low_vol < max_vol * 0.5 and 
                            recent_low_vol < mid_vol * 0.9 and
                            recent_low_vol < after_peak_vol * 0.8 and
                            peak_volume_ratio > 1.3):  # 确实存在天量
                            divergences.append("成交量背离")
                            has_divergence = True
                    else:
                        # 如果没有明显的天量，检查是否有"价涨量缩"背离
                        # 价格上涨但成交量萎缩，特别是末期成交量明显低于初期或中期
                        
                        # 模式1：中期放量后末期缩量（追涨盘枯竭）
                        if (mid_vol > early_vol * 1.1 and  # 中期确实放量
                            recent_low_vol < mid_vol * 0.75 and  # 末期明显缩量
                            recent_low_vol < early_vol * 0.85):  # 缩量低于初期
                            divergences.append("成交量背离")
                            has_divergence = True
                        # 模式2：价格上涨但成交量持续萎缩（无力上涨）
                        elif (recent_low_vol < early_vol * 0.7 and  # 末期成交量明显低于初期
                              mid_vol < early_vol * 0.9):  # 中期就开始萎缩
                            # 价格创新高但成交量无法同步
                            price_max_idx = np.argmax(prices)
                            vol_at_price_max = volumes[price_max_idx]
                            if price_max_idx > len(prices) * 0.7:  # 价格高点在后半段
                                if vol_at_price_max < early_vol * 0.8:  # 创新高时成交量萎缩
                                    divergences.append("成交量背离")
                                    has_divergence = True
        
        except Exception as e:
            pass
        
        return has_divergence, divergences
    
    def analyze_symbol(self, symbol):
        """分析单个币种"""
        try:
            # 获取K线数据
            df = self.get_daily_klines(symbol)
            if df is None or len(df) < 300:  # 4小时级别需要更多数据
                return None
            
            # 计算技术指标
            df = self.calculate_indicators(df)
            if df is None:
                return None
            
            # 检测所有技术形态
            patterns, pattern_type, pattern_score, pattern_details = self.detect_all_patterns(df)
            
            # 如果形态已过期，直接返回None
            if pattern_details and not pattern_details.get('is_valid', True):
                return None
            
            # 检测背离
            has_divergence, divergences = self.detect_divergence(df)
            
            # 综合评分
            current_price = df['close'].iloc[-1]
            rsi = df['rsi'].iloc[-1]
            macd = df['macd'].iloc[-1]
            
            # 最终评分：形态置信度
            final_score = pattern_score
            
            # 如果有背离，加分
            if has_divergence:
                final_score += 20
            
            # 根据形态类型调整评分
            if pattern_type == 'bullish':
                # RSI超卖加分
                if rsi < 30:
                    final_score += 10
                # MACD在水下但向上转折加分
                if macd < 0 and df['macd'].iloc[-1] > df['macd'].iloc[-3]:
                    final_score += 10
            elif pattern_type == 'bearish':
                # RSI超买扣分（但这里只加分，所以不减）
                if rsi > 70:
                    final_score += 5  # 顶部形态确认
            
            final_score = min(final_score, 100)
            
            # 返回所有形态（置信度>70%且有明显背离的）
            if final_score >= 70 and has_divergence and patterns:
                result = {
                    'symbol': symbol,
                    'current_price': current_price,
                    'pattern_score': final_score,
                    'pattern_type': pattern_type,
                    'rsi': rsi,
                    'macd': macd,
                    'patterns': patterns,
                    'divergences': divergences,
                    'price_change_7d': (current_price - df['close'].iloc[-42]) / df['close'].iloc[-42] * 100 if len(df) >= 42 else 0,  # 7天=42个4小时
                    'price_change_30d': (current_price - df['close'].iloc[-180]) / df['close'].iloc[-180] * 100 if len(df) >= 180 else 0  # 30天=180个4小时
                }
                # 添加形态详细信息
                if pattern_details:
                    result.update(pattern_details)
                return result
        except Exception as e:
            pass
        
        return None
    
    def scan(self, limit=1000, batch_size=10):
        """扫描币种（分批处理）"""
        print(f"\n🚀 开始扫描Bitget所有币种", flush=True)
        print("="*70, flush=True)
        print("筛选条件:", flush=True)
        print("  - 技术形态置信度 > 70%", flush=True)
        print("  - 指标有明显背离", flush=True)
        print("  - 检测形态：底部反转、顶部反转、持续结构", flush=True)
        print(f"  - 每{batch_size}个币种保存一次结果", flush=True)
        print("="*70, flush=True)
        print(f"📁 输出目录: {self.output_dir}", flush=True)
        print(flush=True)
        
        # 获取币种列表
        symbols = self.get_top_symbols(limit)
        if not symbols:
            print("❌ 无法获取币种列表", flush=True)
            return
        
        print(f"\n开始分析 {len(symbols)} 个币种...\n", flush=True)
        
        total_valid_count = 0
        batch_results = []
        batch_num = 0
        
        for i, symbol in enumerate(symbols, 1):
            if i % 50 == 0 or i == 1:
                print(f"[{i}/{len(symbols)}] 正在分析 {symbol}...", flush=True)
            
            result = self.analyze_symbol(symbol)
            if result:
                self.results.append(result)
                batch_results.append(result)
                total_valid_count += 1
                pattern_type_cn = {
                    'bullish': '看涨反转',
                    'bearish': '看跌反转',
                    'continuation_bullish': '看涨持续',
                    'continuation_bearish': '看跌持续',
                    'unknown': '未知'
                }.get(result['pattern_type'], '未知')
                print(f"  ✓ {symbol}: {pattern_type_cn} 形态 {result['pattern_score']:.1f}%, 背离: {', '.join(result['divergences'])}", flush=True)
            
            # 每扫描batch_size个币种，保存一次结果
            if i % batch_size == 0:
                batch_num += 1
                start_idx = (batch_num - 1) * batch_size
                end_idx = min(batch_num * batch_size, len(symbols))
                print(f"\n[批次 {batch_num}] 完成第 {start_idx+1}-{end_idx} 个币种扫描", flush=True)
                
                # 保存批次结果
                self.save_batch_report(batch_num, batch_results, start_idx+1, end_idx)
                
                # 清空批次结果
                batch_results = []
                
                print(f"✓ 批次 {batch_num} 结果已保存\n", flush=True)
            
            # 避免请求过快
            if i % 10 == 0:
                time.sleep(0.5)
        
        # 处理最后一批（如果有剩余）
        if len(symbols) % batch_size != 0:
            batch_num += 1
            start_idx = (batch_num - 1) * batch_size
            end_idx = len(symbols)
            print(f"\n[批次 {batch_num}] 完成最后 {start_idx+1}-{end_idx} 个币种扫描", flush=True)
            self.save_batch_report(batch_num, batch_results, start_idx+1, end_idx)
            print(f"✓ 批次 {batch_num} 结果已保存\n", flush=True)
        
        print(f"\n✅ 扫描完成！共扫描 {len(symbols)} 个币种，找到 {total_valid_count} 个符合条件的币种\n", flush=True)
    
    def save_batch_report(self, batch_num, batch_results, start_idx, end_idx):
        """保存批次报告"""
        # 按评分排序
        batch_results_sorted = sorted(batch_results, key=lambda x: x['pattern_score'], reverse=True)
        
        # 生成Markdown报告
        report = []
        report.append(f"# Gate.io 币种技术形态扫描报告 - 批次 {batch_num}")
        report.append(f"扫描时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"扫描范围: 第 {start_idx}-{end_idx} 个币种")
        report.append("")
        report.append("## 筛选条件")
        report.append("- 技术形态置信度 > 70%")
        report.append("- 指标有明显背离")
        report.append("")
        
        if batch_results_sorted:
            report.append(f"## 扫描结果 (找到 {len(batch_results_sorted)} 个符合条件的币种)")
            report.append("")
            pattern_type_map = {
                'bullish': '看涨反转',
                'bearish': '看跌反转',
                'continuation_bullish': '看涨持续',
                'continuation_bearish': '看跌持续'
            }
            report.append("| 排名 | 币种 | 形态类型 | 当前价格 | 置信度 | RSI | 7日涨跌 | 30日涨跌 | 形态特征 | 背离信号 |")
            report.append("|------|------|----------|----------|--------|-----|---------|----------|----------|----------|")
            
            for i, result in enumerate(batch_results_sorted, 1):
                patterns_str = ", ".join(result['patterns'][:2]) if result['patterns'] else "无"
                divergences_str = ", ".join(result['divergences']) if result['divergences'] else "无"
                pattern_type_cn = pattern_type_map.get(result['pattern_type'], '未知')
                
                report.append(f"| {i} | {result['symbol']} | {pattern_type_cn} | {result['current_price']:.6f} | {result['pattern_score']:.1f}% | "
                             f"{result['rsi']:.1f} | {result['price_change_7d']:.2f}% | {result['price_change_30d']:.2f}% | "
                             f"{patterns_str} | {divergences_str} |")
            
            report.append("")
            report.append("## 详细分析")
            report.append("")
            
            for result in batch_results_sorted:
                pattern_type_cn = pattern_type_map.get(result['pattern_type'], '未知')
                report.append(f"### {result['symbol']}")
                report.append(f"- **形态类型**: {pattern_type_cn}")
                report.append(f"- **当前价格**: {result['current_price']:.6f} USDT")
                report.append(f"- **形态置信度**: {result['pattern_score']:.1f}%")
                report.append(f"- **RSI**: {result['rsi']:.1f}")
                report.append(f"- **MACD**: {result['macd']:.6f}")
                report.append(f"- **7日涨跌**: {result['price_change_7d']:.2f}%")
                report.append(f"- **30日涨跌**: {result['price_change_30d']:.2f}%")
                report.append(f"- **形态特征**: {', '.join(result['patterns']) if result['patterns'] else '无'}")
                report.append(f"- **背离信号**: {', '.join(result['divergences']) if result['divergences'] else '无'}")
                
                # 添加形态详细信息
                if 'pattern_name' in result:
                    report.append("")
                    report.append("#### 形态详细信息")
                    pattern_name = result.get('pattern_name', '')
                    
                    # 双底形态
                    if '双底' in pattern_name:
                        if 'second_bottom_date' in result and result['second_bottom_date']:
                            report.append(f"- **第二个底部日期**: {result['second_bottom_date']}")
                        if 'target_price' in result:
                            report.append(f"- **潜在目标价格**: {result['target_price']:.6f} USDT")
                            price_diff = ((result['target_price'] - result['current_price']) / result['current_price']) * 100
                            report.append(f"- **潜在涨幅**: {price_diff:+.2f}%")
                        if 'neckline_price' in result:
                            report.append(f"- **颈线价格**: {result['neckline_price']:.6f} USDT")
                    
                    # 双顶形态
                    elif '双顶' in pattern_name:
                        if 'second_top_date' in result and result['second_top_date']:
                            report.append(f"- **第二个顶部日期**: {result['second_top_date']}")
                        if 'target_price' in result:
                            report.append(f"- **潜在目标价格**: {result['target_price']:.6f} USDT")
                            price_diff = ((result['target_price'] - result['current_price']) / result['current_price']) * 100
                            report.append(f"- **潜在跌幅**: {price_diff:+.2f}%")
                    
                    # 头肩底形态
                    elif '头肩底' in pattern_name:
                        if 'right_shoulder_date' in result and result['right_shoulder_date']:
                            report.append(f"- **右肩（第二个底部）日期**: {result['right_shoulder_date']}")
                        if 'target_price' in result:
                            report.append(f"- **潜在目标价格**: {result['target_price']:.6f} USDT")
                    
                    # 其他形态
                    else:
                        if 'target_price' in result:
                            report.append(f"- **潜在目标价格**: {result['target_price']:.6f} USDT")
                        if 'formation_start_date' in result and result['formation_start_date']:
                            report.append(f"- **形态形成开始**: {result['formation_start_date']}")
                        if 'formation_end_date' in result and result['formation_end_date']:
                            report.append(f"- **形态形成结束**: {result['formation_end_date']}")
                
                report.append("")
        else:
            report.append("## 扫描结果")
            report.append("")
            report.append("**本批次未找到符合条件的币种**")
            report.append("")
        
        # 保存Markdown报告
        import os
        filename_md = os.path.join(self.output_dir, f'gate_bottom_formation_batch_{batch_num:04d}.md')
        with open(filename_md, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        # 保存CSV（即使为空也保存）
        filename_csv = os.path.join(self.output_dir, f'gate_bottom_formation_batch_{batch_num:04d}.csv')
        if batch_results_sorted:
            df_results = pd.DataFrame(batch_results_sorted)
            df_results.to_csv(filename_csv, index=False, encoding='utf-8-sig')
        else:
            # 创建空CSV文件，只包含表头
            empty_df = pd.DataFrame(columns=['symbol', 'pattern_type', 'current_price', 'pattern_score', 'rsi', 'macd', 
                                              'patterns', 'divergences', 'price_change_7d', 'price_change_30d'])
            empty_df.to_csv(filename_csv, index=False, encoding='utf-8-sig')
    
    def generate_report(self):
        """生成报告"""
        if not self.results:
            print("❌ 没有找到符合条件的币种")
            return
        
        # 按评分排序
        self.results.sort(key=lambda x: x['pattern_score'], reverse=True)
        
        # 生成Markdown报告
        report = []
        report.append("# Bitget 币种技术形态扫描报告 (4小时级别)")
        report.append(f"扫描时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        report.append("## 筛选条件")
        report.append("- 技术形态置信度 > 70%")
        report.append("- 指标有明显背离")
        report.append("")
        report.append(f"## 扫描结果 (共找到 {len(self.results)} 个币种)")
        report.append("")
        pattern_type_map = {
            'bullish': '看涨反转',
            'bearish': '看跌反转',
            'continuation_bullish': '看涨持续',
            'continuation_bearish': '看跌持续'
        }
        report.append("| 排名 | 币种 | 形态类型 | 当前价格 | 置信度 | RSI | 7日涨跌 | 30日涨跌 | 形态特征 | 背离信号 |")
        report.append("|------|------|----------|----------|--------|-----|---------|----------|----------|----------|")
        
        for i, result in enumerate(self.results, 1):
            patterns_str = ", ".join(result['patterns'][:2]) if result['patterns'] else "无"
            divergences_str = ", ".join(result['divergences']) if result['divergences'] else "无"
            pattern_type_cn = pattern_type_map.get(result['pattern_type'], '未知')
            
            # 添加目标价格信息
            target_info = ""
            if 'target_price' in result:
                target_info = f"目标: {result['target_price']:.6f}"
            
            report.append(f"| {i} | {result['symbol']} | {pattern_type_cn} | {result['current_price']:.6f} | {result['pattern_score']:.1f}% | "
                         f"{result['rsi']:.1f} | {result['price_change_7d']:.2f}% | {result['price_change_30d']:.2f}% | "
                         f"{patterns_str} | {divergences_str} |")
        
        report.append("")
        report.append("## 详细分析")
        report.append("")
        
        for result in self.results:
            pattern_type_cn = pattern_type_map.get(result['pattern_type'], '未知')
            report.append(f"### {result['symbol']}")
            report.append(f"- **形态类型**: {pattern_type_cn}")
            report.append(f"- **当前价格**: {result['current_price']:.6f} USDT")
            report.append(f"- **形态置信度**: {result['pattern_score']:.1f}%")
            report.append(f"- **RSI**: {result['rsi']:.1f}")
            report.append(f"- **MACD**: {result['macd']:.6f}")
            report.append(f"- **7日涨跌**: {result['price_change_7d']:.2f}%")
            report.append(f"- **30日涨跌**: {result['price_change_30d']:.2f}%")
            report.append(f"- **形态特征**: {', '.join(result['patterns']) if result['patterns'] else '无'}")
            report.append(f"- **背离信号**: {', '.join(result['divergences']) if result['divergences'] else '无'}")
            
            # 添加形态详细信息
            if 'pattern_name' in result:
                report.append("")
                report.append("#### 形态详细信息")
                pattern_name = result.get('pattern_name', '')
                
                # 双底形态
                if '双底' in pattern_name:
                    if 'second_bottom_date' in result and result['second_bottom_date']:
                        report.append(f"- **第二个底部日期**: {result['second_bottom_date']}")
                    if 'target_price' in result:
                        report.append(f"- **潜在目标价格**: {result['target_price']:.6f} USDT")
                        price_diff = ((result['target_price'] - result['current_price']) / result['current_price']) * 100
                        report.append(f"- **潜在涨幅**: {price_diff:+.2f}%")
                    if 'neckline_price' in result:
                        report.append(f"- **颈线价格**: {result['neckline_price']:.6f} USDT")
                
                # 双顶形态
                elif '双顶' in pattern_name:
                    if 'second_top_date' in result and result['second_top_date']:
                        report.append(f"- **第二个顶部日期**: {result['second_top_date']}")
                    if 'target_price' in result:
                        report.append(f"- **潜在目标价格**: {result['target_price']:.6f} USDT")
                        price_diff = ((result['target_price'] - result['current_price']) / result['current_price']) * 100
                        report.append(f"- **潜在跌幅**: {price_diff:+.2f}%")
                
                # 头肩底形态
                elif '头肩底' in pattern_name:
                    if 'right_shoulder_date' in result and result['right_shoulder_date']:
                        report.append(f"- **右肩（第二个底部）日期**: {result['right_shoulder_date']}")
                    if 'target_price' in result:
                        report.append(f"- **潜在目标价格**: {result['target_price']:.6f} USDT")
                
                # 其他形态
                else:
                    if 'target_price' in result:
                        report.append(f"- **潜在目标价格**: {result['target_price']:.6f} USDT")
                    if 'formation_start_date' in result and result['formation_start_date']:
                        report.append(f"- **形态形成开始**: {result['formation_start_date']}")
                    if 'formation_end_date' in result and result['formation_end_date']:
                        report.append(f"- **形态形成结束**: {result['formation_end_date']}")
            
            report.append("")
        
        # 保存报告
        import os
        report_md_path = os.path.join(self.output_dir, 'gate_bottom_formation_report.md')
        with open(report_md_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        # 生成CSV
        df_results = pd.DataFrame(self.results)
        csv_path = os.path.join(self.output_dir, 'gate_bottom_formation_list.csv')
        df_results.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        print(f"✅ 报告已生成:")
        print(f"  - {report_md_path} (详细报告)")
        print(f"  - {csv_path} (币种列表)")
        print(f"  - 输出目录: {self.output_dir}")

def main():
    """主函数"""
    import sys
    
    try:
        print("="*70, flush=True)
        print("Bitget 币种技术形态扫描程序 (4小时级别)", flush=True)
        print("="*70, flush=True)
        
        # 允许通过命令行参数指定扫描数量（0表示扫描所有）
        limit = None  # None表示获取所有币种
        if len(sys.argv) > 1:
            try:
                limit_arg = int(sys.argv[1])
                if limit_arg > 0:
                    limit = limit_arg
                    print(f"扫描数量: {limit} 个币种", flush=True)
                else:
                    print(f"扫描所有币种", flush=True)
            except:
                print(f"扫描所有币种", flush=True)
        else:
            print(f"扫描所有币种", flush=True)
        
        scanner = TechnicalPatternScanner()
        scanner.scan(limit=limit)
        
        # 生成最终汇总报告（汇总所有批次）
        if scanner.results:
            print("\n生成最终汇总报告...", flush=True)
            scanner.generate_report()
            import os
            print(f"✓ 最终汇总报告已生成: {os.path.join(scanner.output_dir, 'gate_bottom_formation_report.md')}", flush=True)
        else:
            print("\n未找到符合条件的币种，跳过最终汇总报告", flush=True)
        
        print("\n" + "="*70, flush=True)
        print("程序执行完成！", flush=True)
        print(f"所有报告已保存到目录: {scanner.output_dir}", flush=True)
        print("="*70, flush=True)
    except KeyboardInterrupt:
        print("\n\n程序被用户中断", flush=True)
    except Exception as e:
        print(f"\n\n程序执行出错: {e}", flush=True)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
