#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABU Gemini信号扫描器（扩展版）

新策略：
- 5分钟：Top 300币种，1天跨度
- 15分钟：Top 200币种，2天跨度
- 1h/4h：Top 50币种，7天跨度
- 每个级别输出一个文件
"""
from __future__ import annotations
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from generate_comprehensive_trading_plans import get_kline_gateio as _get_k_gate
from generate_comprehensive_trading_plans import get_kline_binance as _get_k_bin
try:
    import sys
    from pathlib import Path
    SRC_PATH = Path(__file__).parent.parent / 'src'
    if str(SRC_PATH) not in sys.path:
        sys.path.insert(0, str(SRC_PATH))
    from get_extended_gateio_klines import get_kline_gateio_extended
    EXTENDED_GATEIO_AVAILABLE = True
except ImportError:
    EXTENDED_GATEIO_AVAILABLE = False
    get_kline_gateio_extended = None
try:
    from get_extended_gateio_klines import get_kline_gateio_extended
    EXTENDED_GATEIO_AVAILABLE = True
except ImportError:
    EXTENDED_GATEIO_AVAILABLE = False
    get_kline_gateio_extended = None
try:
    from generate_btc_de_signals import get_btc_kline_bitget as _get_k_bitget_btc
    def _get_k_bitget(symbol='BTC', timeframe='15m', limit=200):
        return _get_k_bitget_btc(timeframe=timeframe, limit=limit) if symbol == 'BTC' else None
except Exception:
    _get_k_bitget = None

try:
    from abu.gemini_pattern_matcher_enhanced import EnhancedGeminiPatternMatcher
    MATCHER_AVAILABLE = True
except ImportError:
    MATCHER_AVAILABLE = False
    EnhancedGeminiPatternMatcher = None
    try:
        from abu.gemini_pattern_matcher import GeminiPatternMatcher
        # 兼容旧版本
        class EnhancedGeminiPatternMatcher:
            def __init__(self, use_dl=False):
                self.matcher = GeminiPatternMatcher()
                self.pattern_library = self.matcher.pattern_library
            
            def match_patterns(self, klines_dict, min_similarity=0.5, max_matches=10):
                # 兼容旧接口
                klines_15m = klines_dict.get('15m', [])
                klines_1h = klines_dict.get('1h', [])
                return self.matcher.match_patterns(klines_15m, klines_1h, min_similarity, max_matches)
            
            def generate_signal_from_match(self, match, current_price, klines_15m):
                return self.matcher.generate_signal_from_match(match, current_price, klines_15m)
    except ImportError:
        pass

from db_manager_trader import TraderDBManager

# TOP 50 加密货币（按市值，扩展版）
# 注意：目前只使用真实的50个币种，如需扩展到300个，请添加真实币种代码
TOP_50_SYMBOLS = [
    'BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'AVAX', 'DOGE', 'LINK', 'DOT',
    'MATIC', 'TON', 'TRX', 'ATOM', 'SUI', 'APT', 'ARB', 'OP', 'NEAR', 'PEPE',
    'SEI', 'TIA', 'INJ', 'AAVE', 'UNI', 'RUNE', 'ETC', 'FIL', 'ICP', 'XLM',
    'LDO', 'STX', 'HBAR', 'VET', 'ALGO', 'SAND', 'MANA', 'AXS', 'THETA',
    'FLOW', 'EGLD', 'ZIL', 'ENJ', 'CHZ', 'BAT', 'ZEC', 'XMR', 'DASH', 'WAVES'
]

# 排除稳定币
EXCL = set(['USDT', 'USDC', 'DAI', 'BUSD', 'FDUSD', 'TUSD', 'PYUSD', 'USDE', 'GUSD', 'EURT'])

# 排除的教学页面（仓位管理、理论教学等，不是实际的交易模式）
EXCLUDED_PAGES = {222}  # 第222页是仓位管理教学，不应作为交易模式
# 第273页：概念教学（H1/H2/H3讲解），太复杂细腻，不适合当前直接用于信号生成
# 保留作为后期高级识别的候选，但暂时降低优先级
CONCEPT_TEACHING_PAGES = {273}  # 概念教学页面，降低权重但不排除

# 时间框架配置
TIMEFRAME_CONFIGS = {
    '5m': {'limit_per_day': 288, 'description': '5分钟'},
    '15m': {'limit_per_day': 96, 'description': '15分钟'},
    '1h': {'limit_per_day': 24, 'description': '1小时'},
    '4h': {'limit_per_day': 6, 'description': '4小时'}
}


def get_klines(symbol: str, timeframe: str, limit: int, exchange: str = 'gate', days: int = None) -> List[Dict]:
    """
    获取K线数据（优先Gate.io，支持扩展）
    
    Args:
        symbol: 交易对
        timeframe: 时间框架
        limit: K线数量限制（如果days不为None，此参数会被忽略）
        exchange: 交易所（'gate'或'binance'，默认'gate'）
        days: 需要的天数（如果提供，会使用扩展API获取）
    
    Returns:
        K线数据列表
    """
    try:
        # 如果提供了days参数，使用扩展API（仅Gate.io支持）
        if days is not None and exchange in ['gate', 'auto'] and EXTENDED_GATEIO_AVAILABLE and get_kline_gateio_extended:
            try:
                kl = get_kline_gateio_extended(symbol=symbol, timeframe=timeframe, days=days)
                if kl:
                    return kl
            except Exception:
                pass
        
        # 标准API获取
        if exchange == 'gate' or exchange == 'auto':
            # 优先Gate.io
            kl = _get_k_gate(symbol=symbol, timeframe=timeframe, limit=limit)
            if kl:
                return kl
            # Gate.io失败，尝试Binance
            kl = _get_k_bin(symbol=symbol, timeframe=timeframe, limit=limit)
            return kl or []
        elif exchange == 'binance':
            kl = _get_k_bin(symbol=symbol, timeframe=timeframe, limit=limit)
            if kl:
                return kl
            kl = _get_k_gate(symbol=symbol, timeframe=timeframe, limit=limit)
            return kl or []
        else:
            # default: gate -> binance
            kl = _get_k_gate(symbol=symbol, timeframe=timeframe, limit=limit)
            if kl:
                return kl
            kl = _get_k_bin(symbol=symbol, timeframe=timeframe, limit=limit)
            return kl or []
    except Exception:
        return []
    
    return []