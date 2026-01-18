#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全自动信号生成与评估系统

每隔指定时间自动：
1. 生成交易信号
2. 评估信号质量
3. 运行回测
4. 生成报告
5. 显示状态和结果
"""

import sys
import time
import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import argparse
from dataclasses import asdict, is_dataclass

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
OUTPUTS = ROOT / 'outputs'
TRADING_PLANS = OUTPUTS / 'trading_plans'
BACKTEST_RESULTS = OUTPUTS / 'backtest_results'
FEEDBACK_DIR = OUTPUTS / 'feedback'
STATUS_DIR = OUTPUTS / 'auto_signal_status'
LOG_DIR = OUTPUTS / 'logs'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

# 确保目录存在
STATUS_DIR.mkdir(parents=True, exist_ok=True)
FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 设置日志文件
LOG_FILE = LOG_DIR / f'auto_signal_generator_{datetime.now().strftime("%Y%m%d")}.log'
ERROR_LOG_FILE = LOG_DIR / f'auto_signal_generator_error_{datetime.now().strftime("%Y%m%d")}.log'

try:
    from abu.enhanced_hybrid_matcher import EnhancedHybridMatcher
    from abu.common_pattern_extractor import CommonPatternExtractor
    from abu.brooks_parameter_extractor import BrooksParameterExtractor
    from abu.timeframe_risk_calculator import TimeframeRiskCalculator
    from abu.auto_evaluator import AutoEvaluator
    from abu.feedback_loop import FeedbackLoop
    from abu.auto_backtest_integration import AutoBacktestIntegration
    from abu.signal_result_feedback import SignalResultFeedback
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"[WARN] 部分模块导入失败: {e}", file=sys.stderr)
    IMPORTS_AVAILABLE = False


class AutoSignalGenerator:
    """全自动信号生成与评估系统"""
    
    def __init__(
        self,
        interval_hours: float = 4.0,
        top_n_coins: int = 10,
        timeframes: List[str] = None
    ):
        """
        初始化自动信号生成器
        
        Args:
            interval_hours: 生成间隔（小时）
            top_n_coins: 生成信号的币种数量（默认30个）
            timeframes: 时间框架列表，默认['5m', '15m']
        """
        self.interval_hours = interval_hours
        self.interval_seconds = int(interval_hours * 3600)
        self.top_n_coins = top_n_coins
        self.timeframes = timeframes or ['5m', '15m']
        
        # 初始化组件
        if IMPORTS_AVAILABLE:
            self.matcher = None
            self.common_extractor = None
            self.brooks_extractor = None
            self.risk_calculator = TimeframeRiskCalculator()
            self.auto_evaluator = AutoEvaluator()
            self.feedback_loop = FeedbackLoop()
            self.backtest_integration = AutoBacktestIntegration()
            self.signal_feedback = SignalResultFeedback(trader_id='abu', use_database=True)
        else:
            self.matcher = None
            self.common_extractor = None
            self.brooks_extractor = None
            self.risk_calculator = None
            self.auto_evaluator = None
            self.feedback_loop = None
            self.backtest_integration = None
            self.signal_feedback = None
        
        # 状态文件
        self.status_file = STATUS_DIR / 'current_status.json'
        self.history_file = STATUS_DIR / 'generation_history.json'
        
        # 日志文件（在类初始化时设置，确保_log方法可用）
        self.log_file = LOG_DIR / f'auto_signal_generator_{datetime.now().strftime("%Y%m%d")}.log'
        self.error_log_file = LOG_DIR / f'auto_signal_generator_error_{datetime.now().strftime("%Y%m%d")}.log'
        
        # 加载历史
        self.generation_history = self._load_history()
    
    def _load_history(self) -> List[Dict]:
        """加载生成历史"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if not content.strip():
                        print(f"   [WARN] 历史记录文件为空，返回空列表", file=sys.stderr)
                        return []
                    return json.loads(content)
            except json.JSONDecodeError as e:
                print(f"   [ERROR] JSON解析失败: {e}", file=sys.stderr)
                print(f"   [INFO] 尝试修复或备份损坏的历史记录文件...", file=sys.stderr)
                # 尝试备份损坏的文件
                try:
                    backup_file = self.history_file.with_suffix('.json.bak')
                    import shutil
                    shutil.copy2(self.history_file, backup_file)
                    print(f"   [INFO] 已备份损坏文件到: {backup_file.name}", file=sys.stderr)
                except Exception as backup_error:
                    print(f"   [WARN] 备份失败: {backup_error}", file=sys.stderr)
                return []
            except Exception as e:
                print(f"   [ERROR] 读取历史记录失败: {e}", file=sys.stderr)
                return []
        return []
    
    def _serialize_for_json(self, obj):
        """递归序列化对象为JSON可序列化的格式"""
        if is_dataclass(obj):
            return asdict(obj)
        elif isinstance(obj, dict):
            return {k: self._serialize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._serialize_for_json(item) for item in obj]
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        else:
            # 对于其他类型，尝试转换为字符串
            return str(obj)
    
    def _save_history(self):
        """保存生成历史"""
        try:
            # 序列化历史记录
            serialized_history = self._serialize_for_json(self.generation_history[-100:])
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(serialized_history, f, ensure_ascii=False, indent=2)  # 只保留最近100次
        except Exception as e:
            print(f"[WARN] 保存历史失败: {e}", file=sys.stderr)
    
    def _save_status(self, status: Dict):
        """保存当前状态"""
        try:
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(status, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARN] 保存状态失败: {e}", file=sys.stderr)
    
    def _init_components(self):
        """初始化组件"""
        if not IMPORTS_AVAILABLE:
            self._log_error("模块导入失败，无法初始化组件")
            return False
        
        if self.matcher is None:
            try:
                self._log("初始化模式匹配器...")
                self.matcher = EnhancedHybridMatcher(
                    strategy='comprehensive',
                    use_async=True,
                    use_vision=False,
                    top_k=10,
                    min_confidence=0.2,
                    min_similarity=0.25
                )
                
                self._log("初始化其他组件...")
                self.common_extractor = CommonPatternExtractor(self.matcher.pattern_library)
                self.brooks_extractor = BrooksParameterExtractor()
                self._log("组件初始化完成")
            except Exception as e:
                self._log_error(f"初始化组件失败: {e}", exc_info=sys.exc_info())
                return False
        
        return True
    
    def _get_top_coins(self) -> List[Dict]:
        """获取Top N币种（按市值排序）"""
        try:
            import requests
            # 优先使用CoinGecko API按市值排序
            url = "https://api.coingecko.com/api/v3/coins/markets"
            params = {
                'vs_currency': 'usd',
                'order': 'market_cap_desc',  # 按市值降序
                'per_page': self.top_n_coins,
                'page': 1,
                'sparkline': False
            }
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                top_coins = []
                stable_coins = {'USDC', 'USDT', 'BUSD', 'TUSD', 'DAI', 'PAXG', 'USDS', 'USDE'}
                for coin in data:
                    symbol = coin['symbol'].upper()
                    price = coin.get('current_price', 0)
                    market_cap = coin.get('market_cap', 0)
                    # 过滤稳定币、价格过低的币、以及包含特殊字符的币种（如WETH、WBTC等包装代币）
                    if (symbol not in stable_coins and 
                        price > 0.0001 and 
                        '_' not in symbol and 
                        '-' not in symbol and
                        len(symbol) <= 10):  # 过滤过长的币种名称
                        top_coins.append({
                            'symbol': symbol,
                            'price': price,
                            'market_cap': market_cap,
                            'volume_24h': coin.get('total_volume', 0)
                        })
                        if len(top_coins) >= self.top_n_coins:
                            break
                if top_coins:
                    print(f"   [INFO] 从CoinGecko获取到 {len(top_coins)} 个币种（按市值排序）", file=sys.stderr)
                    return top_coins
        except Exception as e:
            print(f"   [WARN] CoinGecko API失败: {e}，尝试Gate.io...", file=sys.stderr)
        
        # 回退到Gate.io API（按交易量排序）
        try:
            import requests
            url = "https://api.gateio.ws/api/v4/spot/tickers"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                tickers = response.json()
                # 按24h交易量排序
                tickers.sort(key=lambda x: float(x.get('quote_volume', 0)), reverse=True)
                # 过滤USDT交易对
                usdt_pairs = [t for t in tickers if t['currency_pair'].endswith('_USDT')]
                # 取前N个
                top_coins = []
                for ticker in usdt_pairs[:self.top_n_coins * 2]:  # 多取一些，过滤稳定币
                    symbol = ticker['currency_pair'].replace('_USDT', '')
                    price = float(ticker.get('last', 0))
                    # 过滤稳定币和价格过低的币
                    if symbol not in ['USDC', 'USDT', 'BUSD', 'TUSD', 'DAI', 'PAXG'] and price > 0.0001:
                        top_coins.append({
                            'symbol': symbol,
                            'price': price,
                            'market_cap': 0,  # Gate.io不提供市值
                            'volume_24h': float(ticker.get('quote_volume', 0))
                        })
                        if len(top_coins) >= self.top_n_coins:
                            break
                if top_coins:
                    print(f"   [INFO] 从Gate.io获取到 {len(top_coins)} 个币种（按交易量排序）", file=sys.stderr)
                    return top_coins
        except Exception as e:
            print(f"   [WARN] Gate.io API也失败: {e}", file=sys.stderr)
        
        # 默认币种列表（按市值排序）
        print(f"   [WARN] 使用默认币种列表", file=sys.stderr)
        return [
            {'symbol': 'BTC', 'price': 95000, 'market_cap': 0, 'volume_24h': 0},
            {'symbol': 'ETH', 'price': 3300, 'market_cap': 0, 'volume_24h': 0},
            {'symbol': 'BNB', 'price': 600, 'market_cap': 0, 'volume_24h': 0},
            {'symbol': 'SOL', 'price': 145, 'market_cap': 0, 'volume_24h': 0},
            {'symbol': 'XRP', 'price': 2.15, 'market_cap': 0, 'volume_24h': 0},
            {'symbol': 'USDC', 'price': 1.0, 'market_cap': 0, 'volume_24h': 0},  # 会被过滤
            {'symbol': 'DOGE', 'price': 0.15, 'market_cap': 0, 'volume_24h': 0},
            {'symbol': 'ADA', 'price': 0.5, 'market_cap': 0, 'volume_24h': 0},
            {'symbol': 'TRX', 'price': 0.1, 'market_cap': 0, 'volume_24h': 0},
            {'symbol': 'AVAX', 'price': 40, 'market_cap': 0, 'volume_24h': 0},
            {'symbol': 'SHIB', 'price': 0.00001, 'market_cap': 0, 'volume_24h': 0},
            {'symbol': 'DOT', 'price': 7, 'market_cap': 0, 'volume_24h': 0},
            {'symbol': 'LINK', 'price': 15, 'market_cap': 0, 'volume_24h': 0},
            {'symbol': 'MATIC', 'price': 1, 'market_cap': 0, 'volume_24h': 0},
            {'symbol': 'UNI', 'price': 10, 'market_cap': 0, 'volume_24h': 0},
            {'symbol': 'LTC', 'price': 100, 'market_cap': 0, 'volume_24h': 0},
            {'symbol': 'ATOM', 'price': 12, 'market_cap': 0, 'volume_24h': 0},
            {'symbol': 'ETC', 'price': 25, 'market_cap': 0, 'volume_24h': 0},
            {'symbol': 'XLM', 'price': 0.12, 'market_cap': 0, 'volume_24h': 0},
            {'symbol': 'BCH', 'price': 300, 'market_cap': 0, 'volume_24h': 0},
            {'symbol': 'ALGO', 'price': 0.2, 'market_cap': 0, 'volume_24h': 0},
            {'symbol': 'VET', 'price': 0.04, 'market_cap': 0, 'volume_24h': 0},
            {'symbol': 'FIL', 'price': 5, 'market_cap': 0, 'volume_24h': 0},
            {'symbol': 'ICP', 'price': 12, 'market_cap': 0, 'volume_24h': 0},
            {'symbol': 'APT', 'price': 10, 'market_cap': 0, 'volume_24h': 0},
            {'symbol': 'HBAR', 'price': 0.08, 'market_cap': 0, 'volume_24h': 0},
            {'symbol': 'NEAR', 'price': 3, 'market_cap': 0, 'volume_24h': 0},
            {'symbol': 'QNT', 'price': 100, 'market_cap': 0, 'volume_24h': 0},
            {'symbol': 'CRO', 'price': 0.1, 'market_cap': 0, 'volume_24h': 0},
            {'symbol': 'GRT', 'price': 0.2, 'market_cap': 0, 'volume_24h': 0},
        ][:self.top_n_coins]
    
    def _get_kline_gateio(self, symbol: str, timeframe: str = '5m', limit: int = 200) -> List[Dict]:
        """从Gate.io获取K线数据"""
        try:
            import requests
            tf_map = {'5m': '5m', '15m': '15m', '1h': '1h'}
            interval = tf_map.get(timeframe, '5m')
            
            url = "https://api.gateio.ws/api/v4/spot/candlesticks"
            params = {
                'currency_pair': f'{symbol}_USDT',
                'interval': interval,
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                klines = []
                for item in data:
                    klines.append({
                        'timestamp': int(item[0]),
                        'open': float(item[1]),
                        'high': float(item[2]),
                        'low': float(item[3]),
                        'close': float(item[4]),
                        'volume': float(item[5])
                    })
                return klines
        except Exception as e:
            print(f"      [WARN] 获取K线数据失败: {e}", file=sys.stderr)
        return []
    
    def _extract_features_from_klines(self, klines: List[Dict], timeframe: str) -> Dict:
        """从K线数据提取特征"""
        if not klines or len(klines) < 20:
            return {}
        
        # 计算基本特征
        closes = [k['close'] for k in klines]
        highs = [k['high'] for k in klines]
        lows = [k['low'] for k in klines]
        
        # 价格趋势
        recent_closes = closes[-10:]
        price_trend = 'bullish' if recent_closes[-1] > recent_closes[0] else 'bearish'
        
        # 波动性
        price_range = max(highs[-20:]) - min(lows[-20:])
        avg_price = sum(closes[-20:]) / len(closes[-20:])
        volatility = price_range / avg_price if avg_price > 0 else 0
        
        return {
            'price_trend': price_trend,
            'volatility': volatility,
            'current_price': closes[-1],
            'recent_high': max(highs[-10:]),
            'recent_low': min(lows[-10:]),
            'trend_direction': price_trend
        }
    
    async def _generate_coin_plan(self, symbol: str, timeframe: str) -> Optional[Dict]:
        """为单个币种生成交易计划（直接使用test_top10_pattern_only.py的完整逻辑）"""
        try:
            # 直接调用test_top10_pattern_only.py的生成函数
            scripts_dir = ROOT / 'scripts'
            if str(scripts_dir) not in sys.path:
                sys.path.insert(0, str(scripts_dir))
            
            # 导入test_top10_pattern_only模块
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "test_top10_pattern_only",
                scripts_dir / "test_top10_pattern_only.py"
            )
            test_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(test_module)
            
            # 调用完整的生成函数（包含所有验证和Brooks规则）
            plan = await test_module.generate_coin_plan_pattern_only(
                symbol, timeframe,
                self.matcher,
                self.common_extractor,
                self.brooks_extractor,
                self.risk_calculator
            )
            
            return plan
        except Exception as e:
            print(f"      [ERROR] {symbol} {timeframe} 生成失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return None
    
    async def generate_signals(self) -> Dict:
        """
        生成交易信号
        
        Returns:
            生成结果字典
        """
        start_time = datetime.now()
        print(f"\n[{start_time.strftime('%Y-%m-%d %H:%M:%S')}] 开始生成交易信号...", file=sys.stderr)
        
        # 初始化组件
        if not self._init_components():
            error_msg = '组件初始化失败'
            self._log_error(error_msg)
            return {'error': error_msg}
        
        # 获取币种列表
        print("  获取Top币种列表...", file=sys.stderr)
        coins = self._get_top_coins()
        print(f"  找到 {len(coins)} 个币种: {', '.join([c['symbol'] for c in coins])}", file=sys.stderr)
        
        # 生成所有币种的交易计划（按币种组织）
        all_plans = []
        for i, coin in enumerate(coins, 1):
            symbol = coin['symbol']
            print(f"  [{i}/{len(coins)}] {symbol}...", file=sys.stderr)
            
            plan_5m = None
            plan_15m = None
            
            for timeframe in self.timeframes:
                plan = await self._generate_coin_plan(symbol, timeframe)
                if plan:
                    if timeframe == '5m':
                        plan_5m = plan
                    elif timeframe == '15m':
                        plan_15m = plan
            
            if plan_5m or plan_15m:
                all_plans.append({
                    'coin': coin,
                    'plan_5m': plan_5m,
                    'plan_15m': plan_15m
                })
        
        # 生成报告文件
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = TRADING_PLANS / f'auto_generated_{timestamp}.md'
        
        # 生成Markdown报告（使用test_top10_pattern_only.py的格式）
        output = []
        output.append(f"# Top {len(coins)}币种纯模式匹配交易计划")
        output.append("")
        output.append(f"**生成时间**: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        output.append(f"**数据源**: Gemini Flash + Cursor AI + Brooks规则")
        output.append(f"**匹配方式**: 纯算法模式匹配（无视觉分析）")
        output.append(f"**成本**: $0.00 (无API调用)")
        output.append("")
        
        # 交易计划（使用test_top10_pattern_only.py的完整格式）
        for plan_data in all_plans:
            coin = plan_data.get('coin', {})
            plan_5m = plan_data.get('plan_5m')
            plan_15m = plan_data.get('plan_15m')
            
            # 从plan中获取symbol（优先使用plan中的symbol）
            symbol = coin.get('symbol')
            if plan_5m and plan_5m.get('symbol'):
                symbol = plan_5m.get('symbol')
            elif plan_15m and plan_15m.get('symbol'):
                symbol = plan_15m.get('symbol')
            
            # 获取价格（优先从plan中获取current_price）
            coin_price = coin.get('price', 0)
            if plan_5m and plan_5m.get('current_price'):
                coin_price = plan_5m.get('current_price')
            elif plan_15m and plan_15m.get('current_price'):
                coin_price = plan_15m.get('current_price')
            
            # 对于小价格币种，使用更多小数位显示
            is_small_coin = coin_price < 1.0
            price_format = ",.4f" if is_small_coin else ",.2f"
            
            # 确保symbol不为空
            if not symbol:
                symbol = 'Unknown'
            
            output.append(f"## {symbol} (${coin_price:{price_format}})")
            output.append("")
            
            if plan_5m:
                signal = plan_5m.get('signal', {})
                if signal:
                    entry_price = signal.get('entry_price', 0)
                    # 根据价格范围动态调整小数位
                    if entry_price < 0.01:
                        signal_price_format = ",.6f"
                    elif entry_price < 0.1:
                        signal_price_format = ",.5f"
                    elif entry_price < 1.0:
                        signal_price_format = ",.4f"
                    else:
                        signal_price_format = ",.2f"
                    
                    output.append("### 5分钟信号")
                    output.append("")
                    # 优化模式名称显示：如果pattern_name和pattern_type相同，只显示一个
                    pattern_name = signal.get('pattern_name', 'N/A')
                    pattern_type = signal.get('pattern_type', 'N/A')
                    if pattern_name == pattern_type or pattern_type == 'N/A' or pattern_type == '':
                        pattern_display = pattern_name
                    elif pattern_name == 'N/A' or pattern_name == '':
                        pattern_display = pattern_type
                    else:
                        pattern_display = f"{pattern_name} ({pattern_type})"
                    output.append(f"- **模式**: {pattern_display}")
                    output.append(f"- **方向**: {signal.get('direction', 'N/A').upper()}")
                    output.append(f"- **入场价**: ${entry_price:{signal_price_format}}")
                    output.append(f"- **止损**: ${signal.get('stop_loss', 0):{signal_price_format}}")
                    output.append(f"- **止盈1**: ${signal.get('take_profit_1', 0):{signal_price_format}}")
                    output.append(f"- **止盈2**: ${signal.get('take_profit_2', 0):{signal_price_format}}")
                    output.append(f"- **置信度**: {signal.get('confidence', 0):.2%}")
                    output.append(f"- **算法匹配**: {signal.get('algorithm_confidence', 0):.2%}")
                    
                    if signal.get('probability_score') is not None:
                        prob = signal['probability_score']
                        prob_level = "高" if prob >= 70 else "中" if prob >= 50 else "低"
                        output.append(f"- **Brooks概率**: {prob}% ({prob_level}概率)")
                    
                    if signal.get('stop_loss_distance_pct'):
                        output.append(f"- **止损距离**: {signal['stop_loss_distance_pct']*100:.2f}%")
                    if signal.get('position_size_pct'):
                        output.append(f"- **建议仓位**: {signal['position_size_pct']*100:.1f}% (风险: ${signal.get('risk_amount', 0):.2f})")
                    if signal.get('entry_probability') and signal.get('entry_probability') < 0.8:
                        output.append(f"- ⚠️ **入场概率**: {signal['entry_probability']*100:.0f}% (可能需等待)")
                    
                    if not signal.get('is_valid', True):
                        output.append(f"- ⚠️ **验证错误**: {', '.join(signal.get('validation_errors', []))}")
                    if signal.get('validation_warnings'):
                        output.append(f"- ⚠️ **Brooks警告**: {'; '.join(signal.get('validation_warnings', []))}")
                    
                    output.append("")
            
            if plan_15m:
                signal = plan_15m.get('signal', {})
                if signal:
                    entry_price = signal.get('entry_price', 0)
                    # 根据价格范围动态调整小数位
                    if entry_price < 0.01:
                        signal_price_format = ",.6f"
                    elif entry_price < 0.1:
                        signal_price_format = ",.5f"
                    elif entry_price < 1.0:
                        signal_price_format = ",.4f"
                    else:
                        signal_price_format = ",.2f"
                    
                    output.append("### 15分钟信号")
                    output.append("")
                    # 优化模式名称显示：如果pattern_name和pattern_type相同，只显示一个
                    pattern_name = signal.get('pattern_name', 'N/A')
                    pattern_type = signal.get('pattern_type', 'N/A')
                    if pattern_name == pattern_type or pattern_type == 'N/A' or pattern_type == '':
                        pattern_display = pattern_name
                    elif pattern_name == 'N/A' or pattern_name == '':
                        pattern_display = pattern_type
                    else:
                        pattern_display = f"{pattern_name} ({pattern_type})"
                    output.append(f"- **模式**: {pattern_display}")
                    output.append(f"- **方向**: {signal.get('direction', 'N/A').upper()}")
                    output.append(f"- **入场价**: ${entry_price:{signal_price_format}}")
                    output.append(f"- **止损**: ${signal.get('stop_loss', 0):{signal_price_format}}")
                    output.append(f"- **止盈1**: ${signal.get('take_profit_1', 0):{signal_price_format}}")
                    output.append(f"- **止盈2**: ${signal.get('take_profit_2', 0):{signal_price_format}}")
                    output.append(f"- **置信度**: {signal.get('confidence', 0):.2%}")
                    output.append(f"- **算法匹配**: {signal.get('algorithm_confidence', 0):.2%}")
                    
                    if signal.get('probability_score') is not None:
                        prob = signal['probability_score']
                        prob_level = "高" if prob >= 70 else "中" if prob >= 50 else "低"
                        output.append(f"- **Brooks概率**: {prob}% ({prob_level}概率)")
                    
                    if signal.get('stop_loss_distance_pct'):
                        output.append(f"- **止损距离**: {signal['stop_loss_distance_pct']*100:.2f}%")
                    if signal.get('position_size_pct'):
                        output.append(f"- **建议仓位**: {signal['position_size_pct']*100:.1f}% (风险: ${signal.get('risk_amount', 0):.2f})")
                    if signal.get('entry_probability') and signal.get('entry_probability') < 0.8:
                        output.append(f"- ⚠️ **入场概率**: {signal['entry_probability']*100:.0f}% (可能需等待)")
                    
                    if not signal.get('is_valid', True):
                        output.append(f"- ⚠️ **验证错误**: {', '.join(signal.get('validation_errors', []))}")
                    if signal.get('validation_warnings'):
                        output.append(f"- ⚠️ **Brooks警告**: {'; '.join(signal.get('validation_warnings', []))}")
                    
                    output.append("")
        
        # 保存报告
        report_file.write_text('\n'.join(output), encoding='utf-8')
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        result = {
            'success': True,
            'timestamp': start_time.isoformat(),
            'duration_seconds': duration,
            'coins_count': len(coins),
            'signals_count': sum(1 for p in all_plans if p.get('plan_5m') or p.get('plan_15m')),
            'report_file': str(report_file),
            'plans': all_plans
        }
        
        print(f"✅ 信号生成完成: {len(all_plans)} 个信号，耗时 {duration:.1f}秒", file=sys.stderr)
        print(f"   报告文件: {report_file.name}", file=sys.stderr)
        
        return result
    
    def evaluate_and_backtest(self, generation_result: Dict) -> Dict:
        """
        评估和回测生成的信号
        
        Args:
            generation_result: 生成结果
        
        Returns:
            评估和回测结果
        """
        if not generation_result.get('success'):
            return {'error': '信号生成失败'}
        
        print("\n开始评估和回测...", file=sys.stderr)
        start_time = datetime.now()
        
        report_file = Path(generation_result['report_file'])
        if not report_file.exists():
            return {'error': '报告文件不存在'}
        
        # 运行回测（包含自动评估）
        backtest_result, error = self.backtest_integration.run_backtest(report_file)
        
        if error:
            print(f"  [WARN] 回测失败: {error}", file=sys.stderr)
        
        # 评估统计
        evaluation_stats = {
            'total_signals': generation_result['signals_count'],
            'evaluated_signals': 0,
            'average_score': 0.0,
            'quality_distribution': {}
        }
        
        # 从回测结果中收集评估统计
        if backtest_result:
            # 方法1: 从evaluation_stats获取（如果auto_evaluator提供了统计）
            if backtest_result.get('evaluation_stats'):
                eval_stats = backtest_result['evaluation_stats']
                # 使用total_signals或total_evaluated（兼容两种字段名）
                total_eval = eval_stats.get('total_evaluated', eval_stats.get('total_signals', 0))
                if total_eval > 0:
                    evaluation_stats['evaluated_signals'] = total_eval
                    evaluation_stats['average_score'] = eval_stats.get('average_score', 0.0)
                    evaluation_stats['quality_distribution'] = eval_stats.get('quality_distribution', {})
                    print(f"  [INFO] 从评估统计获取: {total_eval} 个信号已评估，平均分数: {evaluation_stats['average_score']:.1f}", file=sys.stderr)
                else:
                    print(f"  [WARN] 评估统计存在但total_evaluated为0: {eval_stats}", file=sys.stderr)
            else:
                print(f"  [WARN] 回测结果中没有evaluation_stats字段", file=sys.stderr)
            
            # 方法2: 如果没有评估统计，从回测结果计算
            if evaluation_stats['evaluated_signals'] == 0:
                total_processed = backtest_result.get('total_signals', 0)
                successful = backtest_result.get('successful_signals', 0)
                failed = len(backtest_result.get('failed_signals', []))
                brooks_rejected = backtest_result.get('brooks_rejected', 0)
                
                # 评估的信号数 = 总信号数 - Brooks拒绝的信号数
                # 注意：这里只统计实际进行了评估的信号（不包括Brooks拒绝的）
                evaluated_count = total_processed - brooks_rejected
                if evaluated_count > 0:
                    evaluation_stats['evaluated_signals'] = evaluated_count
                    # 如果没有评估分数，使用回测成功率作为参考
                    if successful > 0:
                        evaluation_stats['average_score'] = (successful / evaluated_count) * 100
                    print(f"  [INFO] 从回测结果计算: {evaluated_count} 个信号被处理（总{total_processed}，Brooks拒绝{brooks_rejected}，成功{successful}）", file=sys.stderr)
                else:
                    print(f"  [WARN] 没有信号被评估: 总信号{total_processed}，Brooks拒绝{brooks_rejected}", file=sys.stderr)
                    if total_processed == 0:
                        print(f"  [WARN] 回测结果中没有信号数据，可能回测未正常运行", file=sys.stderr)
        else:
            print(f"  [WARN] 回测结果为空，无法收集评估统计", file=sys.stderr)
        
        # 收集反馈（如果有反馈循环系统）
        if backtest_result and self.feedback_loop:
            # 注意：feedback_loop已经在run_backtest中处理了，这里不需要重复添加
            pass
        
        # 注意：average_score已经从get_statistics()中获取，已经是平均值，不需要再除以evaluated_signals
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        result = {
            'success': True,
            'timestamp': start_time.isoformat(),
            'duration_seconds': duration,
            'backtest_result': backtest_result,
            'evaluation_stats': evaluation_stats,
            'error': error
        }
        
        print(f"✅ 评估和回测完成，耗时 {duration:.1f}秒", file=sys.stderr)
        
        return result
    
    def generate_summary_report(self, generation_result: Dict, evaluation_result: Dict, feedback_stats: Dict = None) -> Path:
        """生成总结报告"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = STATUS_DIR / f'summary_{timestamp}.md'
        
        lines = []
        lines.append("# 自动信号生成总结报告")
        lines.append("")
        lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # 生成结果
        lines.append("## 信号生成结果")
        lines.append("")
        if generation_result.get('success'):
            lines.append(f"- ✅ **状态**: 成功")
            lines.append(f"- **币种数量**: {generation_result.get('coins_count', 0)}")
            lines.append(f"- **信号数量**: {generation_result.get('signals_count', 0)}")
            lines.append(f"- **耗时**: {generation_result.get('duration_seconds', 0):.1f}秒")
            lines.append(f"- **报告文件**: `{Path(generation_result.get('report_file', '')).name}`")
        else:
            lines.append(f"- ❌ **状态**: 失败")
            lines.append(f"- **错误**: {generation_result.get('error', 'Unknown')}")
        lines.append("")
        
        # 评估结果
        lines.append("## 评估和回测结果")
        lines.append("")
        if evaluation_result.get('success'):
            eval_stats = evaluation_result.get('evaluation_stats', {})
            lines.append(f"- ✅ **状态**: 成功")
            lines.append(f"- **评估信号数**: {eval_stats.get('evaluated_signals', 0)}")
            lines.append(f"- **平均分数**: {eval_stats.get('average_score', 0):.1f}/100")
            lines.append(f"- **质量分布**:")
            for quality, count in eval_stats.get('quality_distribution', {}).items():
                lines.append(f"  - {quality}: {count}")
            lines.append(f"- **耗时**: {evaluation_result.get('duration_seconds', 0):.1f}秒")
        else:
            lines.append(f"- ❌ **状态**: 失败")
            lines.append(f"- **错误**: {evaluation_result.get('error', 'Unknown')}")
        lines.append("")
        
        # 系统改进建议
        if self.feedback_loop:
            improvements = self.feedback_loop.analyze_feedback()
            if improvements:
                lines.append("## 系统改进建议")
                lines.append("")
                for improvement in improvements[:5]:  # 只显示前5条
                    lines.append(f"### {improvement.category}")
                    lines.append("")
                    lines.append(f"- **问题**: {improvement.description}")
                    lines.append(f"- **当前值**: {improvement.current_value}")
                    lines.append(f"- **建议值**: {improvement.suggested_value}")
                    lines.append(f"- **优先级**: {improvement.priority}")
                    lines.append(f"- **置信度**: {improvement.confidence:.1f}%")
                    lines.append("")
        
        # 信号结果反馈
        if feedback_stats and self.signal_feedback:
            lines.append("## 信号结果反馈")
            lines.append("")
            lines.append(f"- **总信号数**: {feedback_stats.get('total', 0)}")
            lines.append(f"- **待激活**: {feedback_stats.get('pending', 0)}")
            lines.append(f"- **交易中**: {feedback_stats.get('active', 0)}")
            lines.append(f"- **快速止盈（0.5%）**: {feedback_stats.get('quick_tp', 0)}")
            lines.append(f"- **部分止盈**: {feedback_stats.get('partial_tp', 0)}")
            lines.append(f"- **全部止盈**: {feedback_stats.get('full_tp', 0)}")
            lines.append(f"- **已止损**: {feedback_stats.get('stopped', 0)}")
            lines.append(f"- **已过期**: {feedback_stats.get('expired', 0)}")
            lines.append("")
            
            # 生成详细反馈报告
            try:
                feedback_report = self.signal_feedback.get_feedback_report()
                feedback_report_file = STATUS_DIR / f'feedback_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
                feedback_report_file.write_text('\n'.join(feedback_report), encoding='utf-8')
                lines.append(f"- **详细反馈报告**: `{feedback_report_file.name}`")
                lines.append("")
            except Exception as e:
                print(f"  [WARN] 生成反馈报告失败: {e}", file=sys.stderr)
        
        report_file.write_text('\n'.join(lines), encoding='utf-8')
        
        return report_file
    
    async def run_cycle(self) -> Dict:
        """运行一个完整周期"""
        cycle_start = datetime.now()
        
        # 更新状态
        status = {
            'running': True,
            'last_cycle_start': cycle_start.isoformat(),
            'next_cycle_at': (cycle_start + timedelta(hours=self.interval_hours)).isoformat(),
            'total_cycles': len(self.generation_history) + 1
        }
        self._save_status(status)
        
        # 1. 检查历史信号状态（信号结果反馈）
        feedback_stats = {}
        if self.signal_feedback:
            try:
                print("\n检查历史信号状态...", file=sys.stderr)
                feedback_stats = self.signal_feedback.check_all_signals()
                print(f"  待激活: {feedback_stats.get('pending', 0)}, "
                      f"交易中: {feedback_stats.get('active', 0)}, "
                      f"快速止盈: {feedback_stats.get('quick_tp', 0)}, "
                      f"部分止盈: {feedback_stats.get('partial_tp', 0)}, "
                      f"全部止盈: {feedback_stats.get('full_tp', 0)}, "
                      f"已止损: {feedback_stats.get('stopped', 0)}, "
                      f"已过期: {feedback_stats.get('expired', 0)}", file=sys.stderr)
            except Exception as e:
                print(f"  [WARN] 检查信号状态失败: {e}", file=sys.stderr)
        
        # 2. 生成信号
        try:
            generation_result = await self.generate_signals()
        except Exception as e:
            self._log_error(f"生成信号失败: {e}", exc_info=sys.exc_info())
            raise
        
        # 3. 将新信号添加到反馈系统
        if generation_result.get('success') and self.signal_feedback:
            try:
                plans = generation_result.get('plans', [])
                for plan_data in plans:
                    plan_5m = plan_data.get('plan_5m')
                    plan_15m = plan_data.get('plan_15m')
                    
                    if plan_5m and plan_5m.get('signal'):
                        signal = plan_5m['signal']
                        self.signal_feedback.add_signal(signal, cycle_start)
                    
                    if plan_15m and plan_15m.get('signal'):
                        signal = plan_15m['signal']
                        self.signal_feedback.add_signal(signal, cycle_start)
            except Exception as e:
                print(f"  [WARN] 添加信号到反馈系统失败: {e}", file=sys.stderr)
        
        # 4. 评估和回测
        evaluation_result = {}
        if generation_result.get('success'):
            evaluation_result = self.evaluate_and_backtest(generation_result)
        
        # 5. 生成总结报告
        summary_report = self.generate_summary_report(generation_result, evaluation_result, feedback_stats)
        
        # 4. 保存历史
        cycle_result = {
            'cycle_start': cycle_start.isoformat(),
            'generation': generation_result,
            'evaluation': evaluation_result,
            'summary_report': str(summary_report)
        }
        self.generation_history.append(cycle_result)
        self._save_history()
        
        # 5. 显示结果
        print("\n" + "=" * 80, file=sys.stderr)
        print("📊 周期完成总结", file=sys.stderr)
        print("=" * 80, file=sys.stderr)
        if generation_result.get('success'):
            print(f"✅ 信号生成: {generation_result.get('signals_count', 0)} 个信号", file=sys.stderr)
        else:
            print(f"❌ 信号生成: 失败 - {generation_result.get('error', 'Unknown')}", file=sys.stderr)
        
        if evaluation_result.get('success'):
            eval_stats = evaluation_result.get('evaluation_stats', {})
            print(f"✅ 评估回测: {eval_stats.get('evaluated_signals', 0)} 个信号已评估", file=sys.stderr)
            print(f"   平均分数: {eval_stats.get('average_score', 0):.1f}/100", file=sys.stderr)
        else:
            print(f"❌ 评估回测: 失败 - {evaluation_result.get('error', 'Unknown')}", file=sys.stderr)
        
        print(f"📄 总结报告: {summary_report.name}", file=sys.stderr)
        
        # 显示信号反馈统计
        if feedback_stats:
            print(f"📊 信号反馈: 待激活{feedback_stats.get('pending', 0)}, "
                  f"交易中{feedback_stats.get('active', 0)}, "
                  f"快速止盈{feedback_stats.get('quick_tp', 0)}, "
                  f"部分止盈{feedback_stats.get('partial_tp', 0)}, "
                  f"全部止盈{feedback_stats.get('full_tp', 0)}, "
                  f"已止损{feedback_stats.get('stopped', 0)}", file=sys.stderr)
        
        print("=" * 80, file=sys.stderr)
        
        return cycle_result
    
    async def _signal_check_loop(self):
        """信号检查循环 - 每1分钟检查一次信号状态"""
        if not self.signal_feedback:
            return
        
        print("[INFO] 信号检查任务启动，每1分钟检查一次", file=sys.stderr)
        
        try:
            while True:
                try:
                    # 检查所有活跃信号
                    stats = self.signal_feedback.check_all_signals()
                    
                    # 如果有更新，显示简要信息
                    if stats.get('updated', 0) > 0:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 信号状态更新: "
                              f"待激活{stats.get('pending', 0)}, "
                              f"交易中{stats.get('active', 0)}, "
                              f"快速止盈{stats.get('quick_tp', 0)}, "
                              f"部分止盈{stats.get('partial_tp', 0)}, "
                              f"全部止盈{stats.get('full_tp', 0)}, "
                              f"已止损{stats.get('stopped', 0)}", file=sys.stderr)
                    
                except Exception as e:
                    print(f"[WARN] 信号检查失败: {e}", file=sys.stderr)
                
                # 等待1分钟
                await asyncio.sleep(60)  # 60秒 = 1分钟
                
        except asyncio.CancelledError:
            print("[INFO] 信号检查任务已停止", file=sys.stderr)
    
    def _log(self, message: str, level: str = 'INFO'):
        """记录日志到文件和控制台"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] [{level}] {message}"
        
        # 输出到控制台
        print(log_message, file=sys.stderr)
        
        # 写入日志文件
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_message + '\n')
        except Exception as e:
            print(f"[WARN] 写入日志失败: {e}", file=sys.stderr)
    
    def _log_error(self, message: str, exc_info=None):
        """记录错误日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] [ERROR] {message}"
        
        # 输出到控制台
        print(log_message, file=sys.stderr)
        if exc_info:
            import traceback
            traceback.print_exception(*exc_info, file=sys.stderr)
        
        # 写入错误日志文件
        try:
            with open(self.error_log_file, 'a', encoding='utf-8') as f:
                f.write(log_message + '\n')
                if exc_info:
                    import traceback
                    traceback.print_exception(*exc_info, file=f)
        except Exception as e:
            print(f"[WARN] 写入错误日志失败: {e}", file=sys.stderr)
    
    async def run_continuous(self):
        """持续运行"""
        self._log("=" * 80)
        self._log("🚀 全自动信号生成与评估系统启动")
        self._log("=" * 80)
        self._log(f"生成间隔: {self.interval_hours} 小时 ({self.interval_seconds} 秒)")
        self._log(f"币种数量: {self.top_n_coins}")
        self._log(f"时间框架: {', '.join(self.timeframes)}")
        self._log(f"状态目录: {STATUS_DIR}")
        self._log(f"日志文件: {LOG_FILE}")
        self._log(f"错误日志: {ERROR_LOG_FILE}")
        self._log(f"信号检查: 每1分钟检查一次")
        self._log("=" * 80)
        self._log("")
        
        # 启动信号检查任务（后台运行）
        check_task = None
        if self.signal_feedback:
            check_task = asyncio.create_task(self._signal_check_loop())
        
        try:
            while True:
                await self.run_cycle()
                
                next_cycle = datetime.now() + timedelta(seconds=self.interval_seconds)
                print(f"\n⏰ 下次生成时间: {next_cycle.strftime('%Y-%m-%d %H:%M:%S')}", file=sys.stderr)
                print(f"等待 {self.interval_seconds}秒 ({self.interval_hours} 小时)...\n", file=sys.stderr)
                
                await asyncio.sleep(self.interval_seconds)
        except KeyboardInterrupt:
            print("\n\n系统已停止", file=sys.stderr)
            if check_task:
                check_task.cancel()
                try:
                    await check_task
                except asyncio.CancelledError:
                    pass
            status = {
                'running': False,
                'stopped_at': datetime.now().isoformat()
            }
            self._save_status(status)


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='全自动信号生成与评估系统')
    parser.add_argument('--interval', type=float, default=1.0,
                       help='生成间隔（小时），默认1.0小时')
    parser.add_argument('--coins', type=int, default=30,
                       help='生成信号的币种数量，默认30')
    parser.add_argument('--timeframes', type=str, default='5m,15m',
                       help='时间框架，用逗号分隔，默认5m,15m')
    parser.add_argument('--once', action='store_true',
                       help='只运行一次，不持续运行')
    
    args = parser.parse_args()
    
    timeframes = [tf.strip() for tf in args.timeframes.split(',')]
    
    generator = AutoSignalGenerator(
        interval_hours=args.interval,
        top_n_coins=args.coins,
        timeframes=timeframes
    )
    
    if args.once:
        await generator.run_cycle()
    else:
        await generator.run_continuous()


if __name__ == '__main__':
    asyncio.run(main())
