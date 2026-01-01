#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
信号评估结果缓存系统
保存评估结果，避免重复计算
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 缓存文件路径
BASE_DIR = Path(__file__).parent.parent
CACHE_DIR = BASE_DIR / "trading_signals" / ".evaluation_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def get_cache_file_path(signal_time: datetime, timeframe: str = None) -> Path:
    """
    获取缓存文件路径
    
    Args:
        signal_time: 信号生成时间
        timeframe: 时间框架（可选，如果提供则只缓存该时间框架）
    
    Returns:
        缓存文件路径
    """
    date_str = signal_time.strftime('%Y%m%d')
    time_str = signal_time.strftime('%H%M%S')
    
    if timeframe:
        filename = f"evaluation_{date_str}_{time_str}_{timeframe}.json"
    else:
        filename = f"evaluation_{date_str}_{time_str}_all.json"
    
    return CACHE_DIR / filename

def save_evaluation_cache(signal_time: datetime, results: List[Dict], metadata: Dict = None):
    """
    保存评估结果到缓存
    
    Args:
        signal_time: 信号生成时间
        results: 评估结果列表
        metadata: 元数据（评估时间、当前价格等）
    """
    cache_file = get_cache_file_path(signal_time)
    
    cache_data = {
        'signal_time': signal_time.strftime('%Y-%m-%d %H:%M:%S'),
        'signal_timestamp': int(signal_time.timestamp()),
        'evaluation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'evaluation_timestamp': int(datetime.now().timestamp()),
        'metadata': metadata or {},
        'results': results
    }
    
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        print(f"✅ 评估结果已保存到缓存: {cache_file.name}", file=sys.stderr)
    except Exception as e:
        print(f"⚠️ 保存缓存失败: {e}", file=sys.stderr)

def load_evaluation_cache(signal_time: datetime, max_age_hours: int = 24) -> Optional[Dict]:
    """
    从缓存加载评估结果
    
    Args:
        signal_time: 信号生成时间
        max_age_hours: 缓存最大有效期（小时），超过此时间则视为过期
    
    Returns:
        缓存数据，如果不存在或已过期则返回None
    """
    cache_file = get_cache_file_path(signal_time)
    
    if not cache_file.exists():
        return None
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        # 检查缓存是否过期
        evaluation_timestamp = cache_data.get('evaluation_timestamp', 0)
        current_timestamp = int(datetime.now().timestamp())
        age_hours = (current_timestamp - evaluation_timestamp) / 3600
        
        if age_hours > max_age_hours:
            print(f"⚠️ 缓存已过期（{age_hours:.1f}小时前），将重新评估", file=sys.stderr)
            return None
        
        print(f"✅ 从缓存加载评估结果（{age_hours:.1f}小时前）", file=sys.stderr)
        return cache_data
    
    except Exception as e:
        print(f"⚠️ 加载缓存失败: {e}", file=sys.stderr)
        return None

def get_cached_evaluation(signal_time: datetime, force_refresh: bool = False) -> Optional[List[Dict]]:
    """
    获取缓存的评估结果
    
    Args:
        signal_time: 信号生成时间
        force_refresh: 是否强制刷新（忽略缓存）
    
    Returns:
        评估结果列表，如果不存在或需要刷新则返回None
    """
    if force_refresh:
        return None
    
    cache_data = load_evaluation_cache(signal_time)
    if cache_data:
        return cache_data.get('results', [])
    
    return None

def list_evaluation_cache(signal_date: str = None) -> List[Dict]:
    """
    列出所有缓存文件
    
    Args:
        signal_date: 信号日期（YYYYMMDD格式），如果提供则只列出该日期的缓存
    
    Returns:
        缓存文件信息列表
    """
    cache_files = []
    
    if signal_date:
        pattern = f"evaluation_{signal_date}_*.json"
    else:
        pattern = "evaluation_*.json"
    
    for cache_file in CACHE_DIR.glob(pattern):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            cache_files.append({
                'file': cache_file.name,
                'signal_time': cache_data.get('signal_time'),
                'evaluation_time': cache_data.get('evaluation_time'),
                'result_count': len(cache_data.get('results', []))
            })
        except:
            pass
    
    return sorted(cache_files, key=lambda x: x['evaluation_time'], reverse=True)

def clear_evaluation_cache(signal_date: str = None, older_than_days: int = None):
    """
    清理缓存文件
    
    Args:
        signal_date: 信号日期（YYYYMMDD格式），如果提供则只清理该日期的缓存
        older_than_days: 如果提供，只清理N天前的缓存
    """
    deleted_count = 0
    
    if signal_date:
        pattern = f"evaluation_{signal_date}_*.json"
    else:
        pattern = "evaluation_*.json"
    
    for cache_file in CACHE_DIR.glob(pattern):
        try:
            if older_than_days:
                file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
                age_days = (datetime.now() - file_time).days
                if age_days < older_than_days:
                    continue
            
            cache_file.unlink()
            deleted_count += 1
        except Exception as e:
            print(f"⚠️ 删除缓存文件失败 {cache_file.name}: {e}", file=sys.stderr)
    
    print(f"✅ 已清理 {deleted_count} 个缓存文件", file=sys.stderr)

if __name__ == "__main__":
    # 测试缓存功能
    print("信号评估缓存系统测试")
    print("=" * 80)
    
    # 列出所有缓存
    caches = list_evaluation_cache()
    print(f"\n找到 {len(caches)} 个缓存文件:")
    for cache in caches[:5]:  # 只显示前5个
        print(f"  - {cache['file']}: 信号时间={cache['signal_time']}, 评估时间={cache['evaluation_time']}, 结果数={cache['result_count']}")
    
    if len(caches) > 5:
        print(f"  ... 还有 {len(caches) - 5} 个缓存文件")


