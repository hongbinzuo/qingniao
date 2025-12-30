#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
价格验证器
验证对话中提到的价格是否合理，结合BTC实时价格数据
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False

class PriceValidator:
    """价格验证器"""
    
    def __init__(self):
        self.ts_file = Path(__file__).parent.parent / "data" / "btc_price_timeseries.duckdb"
        self.conn = None
        
        if self.ts_file.exists() and DUCKDB_AVAILABLE:
            try:
                self.conn = duckdb.connect(str(self.ts_file))
            except:
                self.conn = None
    
    def get_price_range(self, timestamp: str, hours: int = 2) -> Optional[Tuple[float, float]]:
        """
        获取指定时间点附近的价格范围
        
        Args:
            timestamp: 时间戳字符串
            hours: 查询时间范围（小时）
        
        Returns:
            (最低价, 最高价) 或 None
        """
        if not self.conn:
            return None
        
        try:
            # 解析时间戳
            try:
                dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            except:
                # 尝试其他格式
                try:
                    dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M')
                except:
                    # 如果只有时间，使用今天
                    if ':' in timestamp and len(timestamp) <= 8:
                        today = datetime.now().strftime('%Y-%m-%d')
                        timestamp_full = f"{today} {timestamp}"
                        dt = datetime.strptime(timestamp_full, '%Y-%m-%d %H:%M:%S')
                    else:
                        return None
            
            start_time = dt - timedelta(hours=hours)
            end_time = dt + timedelta(hours=hours)
            
            result = self.conn.execute('''
                SELECT MIN(close) as min_price, MAX(close) as max_price
                FROM btc_price_5m
                WHERE datetime >= ? AND datetime <= ?
            ''', [start_time.strftime('%Y-%m-%d %H:%M:%S'), 
                  end_time.strftime('%Y-%m-%d %H:%M:%S')]).fetchone()
            
            if result and result[0] and result[1]:
                return (result[0], result[1])
        except Exception as e:
            print(f"价格查询错误: {e}", file=sys.stderr)
        
        return None
    
    def validate_price(self, price: float, timestamp: str, tolerance: float = 0.05) -> Tuple[bool, Optional[str]]:
        """
        验证价格是否合理
        
        Args:
            price: 要验证的价格
            timestamp: 时间戳
            tolerance: 容忍度（5%）
        
        Returns:
            (是否合理, 错误信息)
        """
        price_range = self.get_price_range(timestamp)
        
        if not price_range:
            # 无法验证，返回警告但不阻止
            return (True, "⚠️ 无法获取价格数据，跳过验证")
        
        min_price, max_price = price_range
        
        # 检查价格是否在合理范围内
        if price < min_price * (1 - tolerance) or price > max_price * (1 + tolerance):
            error_msg = f"❌ 价格 ${price:,.0f} 不在合理范围内！"
            error_msg += f"\n   时间: {timestamp}"
            error_msg += f"\n   实际价格范围: ${min_price:,.0f} - ${max_price:,.0f}"
            error_msg += f"\n   建议检查是否为输入错误"
            return (False, error_msg)
        
        return (True, None)
    
    def validate_prices_in_text(self, text: str, timestamp: str) -> List[Tuple[float, bool, Optional[str]]]:
        """
        验证文本中提到的所有价格
        
        Returns:
            [(价格, 是否合理, 错误信息), ...]
        """
        import re
        
        # 提取价格（3-5位数字，可能是简化价格）
        prices = re.findall(r'(\d{3,5})', text)
        
        results = []
        for price_str in prices:
            price_val = int(price_str)
            
            # 判断是完整价格还是简化价格
            if 400 <= price_val <= 1000:
                # 可能是简化价格（需要乘以100）
                full_price = price_val * 100
                is_valid, error = self.validate_price(full_price, timestamp)
                results.append((full_price, is_valid, error))
            elif 40000 <= price_val <= 150000:
                # 完整价格
                is_valid, error = self.validate_price(price_val, timestamp)
                results.append((price_val, is_valid, error))
        
        return results
    
    def suggest_correction(self, invalid_price: float, timestamp: str) -> Optional[float]:
        """
        建议修正价格（查找最接近的合理价格）
        """
        price_range = self.get_price_range(timestamp)
        if not price_range:
            return None
        
        min_price, max_price = price_range
        
        # 如果价格接近范围边界，可能是输入错误
        # 检查是否是常见的输入错误（如818 vs 881）
        if 81000 <= invalid_price <= 82000:
            # 可能是881的误输入
            if 88000 <= max_price <= 89000:
                return 88100
        
        # 查找最接近的合理价格
        if invalid_price < min_price:
            # 价格太低，可能是少了一位数字
            # 例如：818 -> 8818 (不合理) -> 88100 (合理)
            if invalid_price < 1000:
                suggested = invalid_price * 100
                if min_price <= suggested <= max_price:
                    return suggested
        
        return None
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
            self.conn = None

