#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用De.交易系统生成ETH 5分钟和15分钟交易信号
数据来源：Bitget或Gate.io
集成实时订单簿止损功能
"""

import requests
import sys
from datetime import datetime
from pathlib import Path

# 导入实时订单簿止损功能
try:
    import os
    import sys
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    from get_realtime_stop_loss import (
        get_order_book_with_retry,
        get_current_price as get_ob_current_price,
        calculate_stop_loss_by_orderbook
    )
    ORDERBOOK_AVAILABLE = True
except ImportError as e:
    ORDERBOOK_AVAILABLE = False
    print(f"警告: 无法导入实时订单簿止损功能 ({e})，将使用技术指标止损", file=sys.stderr)

# 导入增强分析模块
try:
    from enhanced_de_analysis import (
        analyze_volume_profile,
        identify_consolidation_ranges,
        enhance_support_resistance_with_volume,
        identify_interval_breakout_opportunities
    )
    ENHANCED_ANALYSIS_AVAILABLE = True
except ImportError:
    ENHANCED_ANALYSIS_AVAILABLE = False

# 导入波动率分析模块
try:
    from volatility_analyzer import (
        calculate_atr_percent,
        assess_volatility_level,
        calculate_risk_reward_ratio,
        analyze_signal_with_volatility
    )
    VOLATILITY_ANALYZER_AVAILABLE = True
except ImportError:
    VOLATILITY_ANALYZER_AVAILABLE = False

def get_eth_kline_gateio(timeframe='5m', limit=200):
    """从Gate.io获取ETH K线数据"""
    try:
        tf_map = {'5m': '5m', '15m': '15m', '1h': '1h'}
        interval = tf_map.get(timeframe, '5m')
        
        url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {
            'currency_pair': 'ETH_USDT',
            'interval': interval,
            'limit': limit
        }
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data:
                data.reverse()
                klines = []
                for k in data:
                    klines.append({
                        'timestamp': int(k[0]),
                        'open': float(k[5]),
                        'high': float(k[3]),
                        'low': float(k[4]),
                        'close': float(k[2]),
                        'volume': float(k[1])
                    })
                return klines
    except Exception as e:
        print(f"Gate.io获取失败: {e}", file=sys.stderr)
    return None

def get_eth_kline_bitget(timeframe='5m', limit=200):
    """从Bitget获取ETH K线数据"""
    try:
        tf_map = {'5m': '5min', '15m': '15min', '1h': '1hour'}
        interval = tf_map.get(timeframe, '5min')
        
        url = "https://api.bitget.com/api/spot/v1/market/candles"
        params = {
            'symbol': 'ETHUSDT',
            'period': interval,
            'limit': min(limit, 200)
        }
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '00000' and data.get('data'):
                klines = []
                for k in data['data']:
                    klines.append({
                        'timestamp': int(k[0]),
                        'open': float(k[1]),
                        'close': float(k[2]),
                        'high': float(k[3]),
                        'low': float(k[4]),
                        'volume': float(k[5])
                    })
                return klines
    except Exception as e:
        print(f"Bitget获取失败: {e}", file=sys.stderr)
    return None

def get_eth_current_price():
    """获取ETH当前价格"""
    try:
        url = "https://api.gateio.ws/api/v4/spot/tickers"
        params = {'currency_pair': 'ETH_USDT'}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                return float(data[0]['last'])
    except:
        pass
    
    try:
        url = "https://api.bitget.com/api/spot/v1/market/ticker"
        params = {'symbol': 'ETHUSDT'}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '00000' and data.get('data'):
                return float(data['data']['last'])
    except:
        pass
    
    return None

# 导入BTC脚本中的分析函数（复用逻辑）
def import_btc_functions():
    """从BTC脚本导入分析函数"""
    import importlib.util
    btc_script_path = Path(__file__).parent / "generate_btc_de_signals.py"
    
    if not btc_script_path.exists():
        print("错误: 找不到BTC信号生成脚本", file=sys.stderr)
        return None
    
    spec = importlib.util.spec_from_file_location("generate_btc_de_signals", btc_script_path)
    btc_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(btc_module)
    
    return btc_module

def generate_eth_trading_plan():
    """生成ETH交易计划"""
    print("正在获取ETH市场数据...", file=sys.stderr)
    
    # 导入BTC脚本的分析函数
    btc_module = import_btc_functions()
    if not btc_module:
        print("错误: 无法导入分析函数", file=sys.stderr)
        return
    
    # 获取ETH数据
    current_price = get_eth_current_price()
    klines_5m = get_eth_kline_gateio('5m', 200)
    klines_15m = get_eth_kline_gateio('15m', 200)
    klines_1h = get_eth_kline_gateio('1h', 100)
    
    if not klines_5m:
        print("尝试从Bitget获取数据...", file=sys.stderr)
        klines_5m = get_eth_kline_bitget('5m', 200)
        klines_15m = get_eth_kline_bitget('15m', 200)
        klines_1h = get_eth_kline_bitget('1h', 100)
        if not current_price:
            current_price = get_eth_current_price()
    
    if not current_price or not klines_5m or not klines_15m:
        print("无法获取市场数据", file=sys.stderr)
        return
    
    # 使用最新K线价格
    if abs(klines_15m[-1]['close'] - current_price) / current_price > 0.1:
        current_price = klines_15m[-1]['close']
    
    # 使用BTC脚本的分析函数
    analyze_timeframe = btc_module.analyze_timeframe
    get_orderbook_stop_loss = btc_module.get_orderbook_stop_loss if hasattr(btc_module, 'get_orderbook_stop_loss') else None
    validate_signal = btc_module.validate_signal if hasattr(btc_module, 'validate_signal') else None
    
    # 分析各时间框架
    analysis_5m = analyze_timeframe(klines_5m, '5分钟', current_price)
    analysis_15m = analyze_timeframe(klines_15m, '15分钟', current_price)
    analysis_1h = analyze_timeframe(klines_1h, '1小时', current_price) if klines_1h else None
    
    # 盈亏比计算函数
    def calculate_rr_ratio(entry, stop_loss, take_profit, signal_type):
        """计算盈亏比"""
        if signal_type == 'long':
            risk = abs(entry - stop_loss)
            reward = abs(take_profit - entry)
        else:  # short
            risk = abs(stop_loss - entry)
            reward = abs(entry - take_profit)
        
        if risk == 0:
            return 0
        return reward / risk
    
    def filter_signals_by_rr(signals, min_rr=1.5):
        """过滤信号，只保留盈亏比≥min_rr的信号"""
        filtered = []
        for signal in signals:
            entry = signal.get('entry', 0)
            stop_loss = signal.get('stop_loss', 0)
            take_profit_1 = signal.get('take_profit_1', 0)
            take_profit_2 = signal.get('take_profit_2', 0)
            signal_type = signal.get('type', 'long')
            
            if entry == 0 or stop_loss == 0:
                continue
            
            # 计算平均盈亏比（基于两个止盈位）
            rr1 = calculate_rr_ratio(entry, stop_loss, take_profit_1, signal_type)
            rr2 = calculate_rr_ratio(entry, stop_loss, take_profit_2, signal_type)
            avg_rr = (rr1 + rr2) / 2
            
            # 只保留盈亏比≥min_rr的信号
            if avg_rr >= min_rr:
                signal['rr_ratio_1'] = rr1
                signal['rr_ratio_2'] = rr2
                signal['avg_rr_ratio'] = avg_rr
                signal['risk'] = abs(entry - stop_loss)
                signal['reward_1'] = abs(take_profit_1 - entry) if signal_type == 'long' else abs(entry - take_profit_1)
                signal['reward_2'] = abs(take_profit_2 - entry) if signal_type == 'long' else abs(entry - take_profit_2)
                filtered.append(signal)
        
        return filtered
    
    # 生成交易计划
    plan = []
    plan.append("# ETH 交易信号（青鸟交易系统 - De.策略）")
    plan.append("")
    plan.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    plan.append(f"**当前价格**: ${current_price:,.2f}  ")
    plan.append("**数据来源**: Gate.io / Bitget  ")
    plan.append("")
    
    # 5分钟信号
    plan.append("## 一、5分钟交易信号")
    plan.append("")
    
    if analysis_5m:
        signals_5m = analysis_5m.get('signals', [])
        # 过滤信号：只保留盈亏比≥1.5的信号
        filtered_signals_5m = filter_signals_by_rr(signals_5m, min_rr=1.5)
        
        if filtered_signals_5m:
            plan.append(f"✓ 从 {len(signals_5m)} 个信号中筛选出 {len(filtered_signals_5m)} 个盈亏比≥1.5:1的信号")
            plan.append("")
            
            for signal in filtered_signals_5m:
                direction = signal.get('type', 'unknown')
                entry = signal.get('entry', 0)
                stop_loss = signal.get('stop_loss', 0)
                take_profit_1 = signal.get('take_profit_1', 0)
                take_profit_2 = signal.get('take_profit_2', 0)
                strength = signal.get('strength', 'medium')
                entry_model = signal.get('entry_model', '')
                reason = signal.get('reason', '')
                avg_rr = signal.get('avg_rr_ratio', 0)
                rr1 = signal.get('rr_ratio_1', 0)
                rr2 = signal.get('rr_ratio_2', 0)
                risk = signal.get('risk', 0)
                reward_1 = signal.get('reward_1', 0)
                reward_2 = signal.get('reward_2', 0)
                
                # 盈亏比质量评级
                if avg_rr >= 3.0:
                    rr_quality = "优秀（≥3.0）"
                    rr_emoji = "✅✅"
                elif avg_rr >= 2.0:
                    rr_quality = "良好（2.0-3.0）"
                    rr_emoji = "✅"
                elif avg_rr >= 1.5:
                    rr_quality = "可接受（1.5-2.0）"
                    rr_emoji = "⚠️"
                else:
                    rr_quality = "较低"
                    rr_emoji = "⚠️"
                
                plan.append(f"**{direction}** ({strength})")
                plan.append(f"入场: ${entry:,.2f}")
                plan.append(f"止损: ${stop_loss:,.2f}")
                plan.append(f"止盈: ${take_profit_1:,.2f} (50%) / ${take_profit_2:,.2f} (50%)")
                plan.append(f"**预期盈亏比**: {avg_rr:.2f}:1 {rr_emoji} ({rr_quality})")
                plan.append(f"   - 风险: ${risk:,.2f} ({abs(entry - stop_loss) / entry * 100:.2f}%)")
                plan.append(f"   - 止盈1回报: ${reward_1:,.2f} ({rr1:.2f}:1)")
                plan.append(f"   - 止盈2回报: ${reward_2:,.2f} ({rr2:.2f}:1)")
                if entry_model:
                    plan.append(f"**入场模型**: {entry_model}")
                if reason:
                    plan.append(f"**入场原因**: {reason}")
                plan.append("")
        else:
            plan.append(f"⚠️ 从 {len(signals_5m)} 个信号中未找到盈亏比≥1.5:1的信号")
            plan.append("")
    else:
        plan.append("暂无分析数据")
        plan.append("")
    
    # 15分钟信号
    plan.append("## 二、15分钟交易信号")
    plan.append("")
    
    if analysis_15m:
        signals_15m = analysis_15m.get('signals', [])
        # 过滤信号：只保留盈亏比≥1.5的信号
        filtered_signals_15m = filter_signals_by_rr(signals_15m, min_rr=1.5)
        
        if filtered_signals_15m:
            plan.append(f"✓ 从 {len(signals_15m)} 个信号中筛选出 {len(filtered_signals_15m)} 个盈亏比≥1.5:1的信号")
            plan.append("")
            
            for signal in filtered_signals_15m:
                direction = signal.get('type', 'unknown')
                entry = signal.get('entry', 0)
                stop_loss = signal.get('stop_loss', 0)
                take_profit_1 = signal.get('take_profit_1', 0)
                take_profit_2 = signal.get('take_profit_2', 0)
                strength = signal.get('strength', 'medium')
                entry_model = signal.get('entry_model', '')
                reason = signal.get('reason', '')
                avg_rr = signal.get('avg_rr_ratio', 0)
                rr1 = signal.get('rr_ratio_1', 0)
                rr2 = signal.get('rr_ratio_2', 0)
                risk = signal.get('risk', 0)
                reward_1 = signal.get('reward_1', 0)
                reward_2 = signal.get('reward_2', 0)
                
                # 盈亏比质量评级
                if avg_rr >= 3.0:
                    rr_quality = "优秀（≥3.0）"
                    rr_emoji = "✅✅"
                elif avg_rr >= 2.0:
                    rr_quality = "良好（2.0-3.0）"
                    rr_emoji = "✅"
                elif avg_rr >= 1.5:
                    rr_quality = "可接受（1.5-2.0）"
                    rr_emoji = "⚠️"
                else:
                    rr_quality = "较低"
                    rr_emoji = "⚠️"
                
                plan.append(f"**{direction}** ({strength})")
                plan.append(f"入场: ${entry:,.2f}")
                plan.append(f"止损: ${stop_loss:,.2f}")
                plan.append(f"止盈: ${take_profit_1:,.2f} (50%) / ${take_profit_2:,.2f} (50%)")
                plan.append(f"**预期盈亏比**: {avg_rr:.2f}:1 {rr_emoji} ({rr_quality})")
                plan.append(f"   - 风险: ${risk:,.2f} ({abs(entry - stop_loss) / entry * 100:.2f}%)")
                plan.append(f"   - 止盈1回报: ${reward_1:,.2f} ({rr1:.2f}:1)")
                plan.append(f"   - 止盈2回报: ${reward_2:,.2f} ({rr2:.2f}:1)")
                if entry_model:
                    plan.append(f"**入场模型**: {entry_model}")
                if reason:
                    plan.append(f"**入场原因**: {reason}")
                plan.append("")
        else:
            plan.append(f"⚠️ 从 {len(signals_15m)} 个信号中未找到盈亏比≥1.5:1的信号")
            plan.append("")
    else:
        plan.append("暂无分析数据")
        plan.append("")
    
    # 1小时信号
    plan.append("## 三、1小时交易信号")
    plan.append("")
    
    if analysis_1h:
        signals_1h = analysis_1h.get('signals', [])
        # 过滤信号：只保留盈亏比≥1.5的信号
        filtered_signals_1h = filter_signals_by_rr(signals_1h, min_rr=1.5)
        
        if filtered_signals_1h:
            plan.append(f"✓ 从 {len(signals_1h)} 个信号中筛选出 {len(filtered_signals_1h)} 个盈亏比≥1.5:1的信号")
            plan.append("")
            
            for signal in filtered_signals_1h:
                direction = signal.get('type', 'unknown')
                entry = signal.get('entry', 0)
                stop_loss = signal.get('stop_loss', 0)
                take_profit_1 = signal.get('take_profit_1', 0)
                take_profit_2 = signal.get('take_profit_2', 0)
                strength = signal.get('strength', 'medium')
                entry_model = signal.get('entry_model', '')
                reason = signal.get('reason', '')
                avg_rr = signal.get('avg_rr_ratio', 0)
                rr1 = signal.get('rr_ratio_1', 0)
                rr2 = signal.get('rr_ratio_2', 0)
                risk = signal.get('risk', 0)
                reward_1 = signal.get('reward_1', 0)
                reward_2 = signal.get('reward_2', 0)
                
                # 盈亏比质量评级
                if avg_rr >= 3.0:
                    rr_quality = "优秀（≥3.0）"
                    rr_emoji = "✅✅"
                elif avg_rr >= 2.0:
                    rr_quality = "良好（2.0-3.0）"
                    rr_emoji = "✅"
                elif avg_rr >= 1.5:
                    rr_quality = "可接受（1.5-2.0）"
                    rr_emoji = "⚠️"
                else:
                    rr_quality = "较低"
                    rr_emoji = "⚠️"
                
                plan.append(f"**{direction}** ({strength})")
                plan.append(f"入场: ${entry:,.2f}")
                plan.append(f"止损: ${stop_loss:,.2f}")
                plan.append(f"止盈: ${take_profit_1:,.2f} (50%) / ${take_profit_2:,.2f} (50%)")
                plan.append(f"**预期盈亏比**: {avg_rr:.2f}:1 {rr_emoji} ({rr_quality})")
                plan.append(f"   - 风险: ${risk:,.2f} ({abs(entry - stop_loss) / entry * 100:.2f}%)")
                plan.append(f"   - 止盈1回报: ${reward_1:,.2f} ({rr1:.2f}:1)")
                plan.append(f"   - 止盈2回报: ${reward_2:,.2f} ({rr2:.2f}:1)")
                if entry_model:
                    plan.append(f"**入场模型**: {entry_model}")
                if reason:
                    plan.append(f"**入场原因**: {reason}")
                plan.append("")
        else:
            plan.append(f"⚠️ 从 {len(signals_1h)} 个信号中未找到盈亏比≥1.5:1的信号")
            plan.append("")
    else:
        plan.append("暂无分析数据")
        plan.append("")
    
    # 详细技术分析说明
    plan.append("---")
    plan.append("")
    plan.append("## 四、详细技术分析说明")
    plan.append("")
    plan.append("### 4.1 数据来源")
    plan.append("")
    plan.append("**Gate.io API** (主要数据源):")
    plan.append("- API端点: `https://api.gateio.ws/api/v4/spot/candlesticks`")
    plan.append("- 交易对: `ETH_USDT`")
    plan.append("- 时间框架: `5m` (5分钟), `15m` (15分钟), `1h` (1小时)")
    plan.append("- 数据量: 200根K线（5分钟/15分钟），100根K线（1小时）")
    plan.append("- 数据格式: `[timestamp, volume, close, high, low, open]`")
    plan.append("")
    plan.append("**Bitget API** (备用数据源):")
    plan.append("- API端点: `https://api.bitget.com/api/spot/v1/market/candles`")
    plan.append("- 交易对: `ETHUSDT`")
    plan.append("- 时间框架: `5min`, `15min`, `1hour`")
    plan.append("- 数据格式: `[timestamp, open, close, high, low, volume]`")
    plan.append("")
    plan.append("**数据获取逻辑**:")
    plan.append("1. 优先使用Gate.io API获取数据")
    plan.append("2. 如果Gate.io失败，自动切换到Bitget API")
    plan.append("3. 如果两个都失败，提示无法获取数据")
    plan.append("")
    plan.append("### 4.2 技术指标计算方法")
    plan.append("")
    plan.append("**Vegas通道 (EMA144/169)**:")
    plan.append("- EMA144: 144周期指数移动平均线")
    plan.append("- EMA169: 169周期指数移动平均线")
    plan.append("- 计算公式: `EMA = (价格 - 前一日EMA) × 2/(周期+1) + 前一日EMA`")
    plan.append("- 作用: 动态支撑/阻力，价格在通道内=震荡，在通道外=趋势")
    plan.append("")
    plan.append("**VWAP (成交量加权平均价)**:")
    plan.append("- 计算公式: `VWAP = Σ(典型价格 × 成交量) / Σ成交量`")
    plan.append("- 典型价格: `(最高价 + 最低价 + 收盘价) / 3`")
    plan.append("- 作用: 代表市场平均成本，价格在VWAP上方=VWAP作为支撑，下方=阻力")
    plan.append("")
    plan.append("**RSI (相对强弱指标)**:")
    plan.append("- 周期: 14")
    plan.append("- 计算公式: `RSI = 100 - (100 / (1 + RS))`，其中`RS = 平均涨幅 / 平均跌幅`")
    plan.append("- 作用: RSI > 70 = 超买，RSI < 30 = 超卖")
    plan.append("")
    plan.append("**FVG (Fair Value Gap)**:")
    plan.append("- 识别方法: 价格快速移动，中间K线没有重叠")
    plan.append("- 上涨FVG: 前一根K线高点 < 当前K线低点")
    plan.append("- 下跌FVG: 前一根K线低点 > 当前K线高点")
    plan.append("- 作用: 价格缺口，通常会被回填")
    plan.append("")
    plan.append("**支撑阻力位**:")
    plan.append("- 方法: 最近50根K线的最高点和最低点")
    plan.append("- 支撑位: 价格下方的关键低点")
    plan.append("- 阻力位: 价格上方的关键高点")
    plan.append("")
    
    # 5分钟详细分析
    if analysis_5m:
        plan.append("### 5分钟级别")
        plan.append("")
        plan.append(f"**Vegas通道**:")
        if analysis_5m.get('ema_144') and analysis_5m.get('ema_169'):
            plan.append(f"  - EMA144: ${analysis_5m['ema_144']:,.2f}")
            plan.append(f"  - EMA169: ${analysis_5m['ema_169']:,.2f}")
            if current_price > analysis_5m['ema_169']:
                plan.append("  → 价格在通道上方，偏多")
            elif current_price < analysis_5m['ema_144']:
                plan.append("  → 价格在通道下方，偏空")
            else:
                plan.append("  → 价格在通道内，震荡")
        plan.append("")
        
        if analysis_5m.get('vwap'):
            plan.append(f"**VWAP**: ${analysis_5m['vwap']:,.2f}")
            if current_price > analysis_5m['vwap']:
                plan.append("  → 价格在VWAP上方，VWAP作为支撑")
            else:
                plan.append("  → 价格在VWAP下方，VWAP作为阻力")
            plan.append("")
        
        if analysis_5m.get('rsi'):
            plan.append(f"**RSI**: {analysis_5m['rsi']:.1f}")
            if analysis_5m['rsi'] > 70:
                plan.append("  → 超买区域，可能回调")
            elif analysis_5m['rsi'] < 30:
                plan.append("  → 超卖区域，可能反弹")
            else:
                plan.append("  → 正常区域")
            plan.append("")
        
        if analysis_5m.get('fvgs'):
            plan.append(f"**FVG**: 发现{len(analysis_5m['fvgs'])}个FVG")
            for fvg in analysis_5m['fvgs'][-3:]:
                fvg_type = "上涨" if fvg.get('type') == 'bullish' else "下跌"
                plan.append(f"  - {fvg_type}FVG: ${fvg.get('low', 0):,.0f} - ${fvg.get('high', 0):,.0f}")
            plan.append("")
        
        if analysis_5m.get('support_resistance', {}).get('support'):
            plan.append("**支撑位**:")
            for s in analysis_5m['support_resistance']['support'][:3]:
                plan.append(f"  - ${s:,.0f}")
            plan.append("")
        
        if analysis_5m.get('support_resistance', {}).get('resistance'):
            plan.append("**阻力位**:")
            for r in analysis_5m['support_resistance']['resistance'][:3]:
                plan.append(f"  - ${r:,.0f}")
            plan.append("")
        
        # 量能分析信息
        if ENHANCED_ANALYSIS_AVAILABLE and analysis_5m.get('volume_profile'):
            vp = analysis_5m['volume_profile']
            plan.append("**量能分析** (Volume Profile):")
            if vp.get('poc'):
                plan.append(f"  - POC (成交量最大点): ${vp['poc']:,.0f}")
            if vp.get('high_volume_zones'):
                plan.append(f"  - 高量区域数量: {len(vp['high_volume_zones'])} 个（真正的支撑阻力位）")
            if vp.get('va_high') and vp.get('va_low'):
                plan.append(f"  - Value Area: ${vp['va_low']:,.0f} - ${vp['va_high']:,.0f}")
            plan.append("")
        
        # 区间识别信息
        if ENHANCED_ANALYSIS_AVAILABLE and analysis_5m.get('consolidation_ranges'):
            ranges = analysis_5m['consolidation_ranges']
            plan.append("**区间识别** (Consolidation Ranges):")
            plan.append(f"  - 当前区间数量: {len(ranges)} 个")
            for i, r in enumerate(ranges[:2], 1):
                plan.append(f"  - 区间{i}: ${r.get('range_low', 0):,.0f} - ${r.get('range_high', 0):,.0f} (强度: {r.get('strength', 'unknown')}, 触及{r.get('touches', 0)}次)")
            plan.append("")
    
    # 15分钟详细分析
    if analysis_15m:
        plan.append("### 15分钟级别")
        plan.append("")
        plan.append(f"**Vegas通道**:")
        if analysis_15m.get('ema_144') and analysis_15m.get('ema_169'):
            plan.append(f"  - EMA144: ${analysis_15m['ema_144']:,.2f}")
            plan.append(f"  - EMA169: ${analysis_15m['ema_169']:,.2f}")
            if current_price > analysis_15m['ema_169']:
                plan.append("  → 价格在通道上方，偏多")
            elif current_price < analysis_15m['ema_144']:
                plan.append("  → 价格在通道下方，偏空")
            else:
                plan.append("  → 价格在通道内，震荡")
        plan.append("")
        
        if analysis_15m.get('vwap'):
            plan.append(f"**VWAP**: ${analysis_15m['vwap']:,.2f}")
            if current_price > analysis_15m['vwap']:
                plan.append("  → 价格在VWAP上方，VWAP作为支撑")
            else:
                plan.append("  → 价格在VWAP下方，VWAP作为阻力")
            plan.append("")
        
        if analysis_15m.get('rsi'):
            plan.append(f"**RSI**: {analysis_15m['rsi']:.1f}")
            if analysis_15m['rsi'] > 70:
                plan.append("  → 超买区域，可能回调")
            elif analysis_15m['rsi'] < 30:
                plan.append("  → 超卖区域，可能反弹")
            else:
                plan.append("  → 正常区域")
            plan.append("")
        
        if analysis_15m.get('support_resistance', {}).get('support'):
            plan.append("**支撑位**:")
            for s in analysis_15m['support_resistance']['support'][:3]:
                plan.append(f"  - ${s:,.0f}")
            plan.append("")
        
        if analysis_15m.get('support_resistance', {}).get('resistance'):
            plan.append("**阻力位**:")
            for r in analysis_15m['support_resistance']['resistance'][:3]:
                plan.append(f"  - ${r:,.0f}")
            plan.append("")
        
        # 量能分析信息
        if ENHANCED_ANALYSIS_AVAILABLE and analysis_15m.get('volume_profile'):
            vp = analysis_15m['volume_profile']
            plan.append("**量能分析** (Volume Profile):")
            if vp.get('poc'):
                plan.append(f"  - POC (成交量最大点): ${vp['poc']:,.0f}")
            if vp.get('high_volume_zones'):
                plan.append(f"  - 高量区域数量: {len(vp['high_volume_zones'])} 个（真正的支撑阻力位）")
            if vp.get('va_high') and vp.get('va_low'):
                plan.append(f"  - Value Area: ${vp['va_low']:,.0f} - ${vp['va_high']:,.0f}")
            plan.append("")
        
        # 区间识别信息
        if ENHANCED_ANALYSIS_AVAILABLE and analysis_15m.get('consolidation_ranges'):
            ranges = analysis_15m['consolidation_ranges']
            plan.append("**区间识别** (Consolidation Ranges):")
            plan.append(f"  - 当前区间数量: {len(ranges)} 个")
            for i, r in enumerate(ranges[:2], 1):
                plan.append(f"  - 区间{i}: ${r.get('range_low', 0):,.0f} - ${r.get('range_high', 0):,.0f} (强度: {r.get('strength', 'unknown')}, 触及{r.get('touches', 0)}次)")
            plan.append("")
    
    # 1小时详细分析
    if analysis_1h:
        plan.append("### 1小时级别")
        plan.append("")
        plan.append(f"**Vegas通道**:")
        if analysis_1h.get('ema_144') and analysis_1h.get('ema_169'):
            plan.append(f"  - EMA144: ${analysis_1h['ema_144']:,.2f}")
            plan.append(f"  - EMA169: ${analysis_1h['ema_169']:,.2f}")
            if current_price > analysis_1h['ema_169']:
                plan.append("  → 价格在通道上方，偏多")
            elif current_price < analysis_1h['ema_144']:
                plan.append("  → 价格在通道下方，偏空")
            else:
                plan.append("  → 价格在通道内，震荡")
        plan.append("")
        
        if analysis_1h.get('vwap'):
            plan.append(f"**VWAP**: ${analysis_1h['vwap']:,.2f}")
            if current_price > analysis_1h['vwap']:
                plan.append("  → 价格在VWAP上方，VWAP作为支撑")
            else:
                plan.append("  → 价格在VWAP下方，VWAP作为阻力")
            plan.append("")
        
        if analysis_1h.get('rsi'):
            plan.append(f"**RSI**: {analysis_1h['rsi']:.1f}")
            if analysis_1h['rsi'] > 70:
                plan.append("  → 超买区域，可能回调")
            elif analysis_1h['rsi'] < 30:
                plan.append("  → 超卖区域，可能反弹")
            else:
                plan.append("  → 正常区域")
            plan.append("")
        
        if analysis_1h.get('support_resistance', {}).get('support'):
            plan.append("**支撑位**:")
            for s in analysis_1h['support_resistance']['support'][:3]:
                plan.append(f"  - ${s:,.0f}")
            plan.append("")
        
        if analysis_1h.get('support_resistance', {}).get('resistance'):
            plan.append("**阻力位**:")
            for r in analysis_1h['support_resistance']['resistance'][:3]:
                plan.append(f"  - ${r:,.0f}")
            plan.append("")
    
    plan.append("---")
    plan.append("")
    plan.append("**免责声明**: 本交易信号基于De.交易系统自动生成，仅供参考。交易有风险，入市需谨慎。")
    
    # 保存文件
    output_dir = Path(__file__).parent.parent
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = output_dir / f"ETH_de_signals_{timestamp}.md"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(plan))
    
    print(f"ETH交易信号已保存到: {filename}")
    
    # 输出到控制台
    print('\n'.join(plan))

if __name__ == '__main__':
    generate_eth_trading_plan()

