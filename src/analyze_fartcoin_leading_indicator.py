#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析FARTCOIN是否是BTC市场的领先指标
验证逻辑：Fartcoin has been the leading indicator for the market whether it's been up or down
"""

import requests
import sys
import numpy as np
from datetime import datetime, timedelta
from scipy import stats
from scipy.stats import pearsonr
import json

def get_kline_gateio(symbol='FARTCOIN', timeframe='1h', limit=500):
    """从Gate.io获取K线数据"""
    try:
        tf_map = {
            '5m': '5m', '15m': '15m', '30m': '30m',
            '1h': '1h', '4h': '4h', '1d': '1d'
        }
        interval = tf_map.get(timeframe, '1h')
        
        # 尝试多种交易对格式
        pairs = [f'{symbol}_USDT', f'{symbol}USDT', 'FART_USDT', 'FARTUSDT']
        
        for pair in pairs:
            url = "https://api.gateio.ws/api/v4/spot/candlesticks"
            params = {
                'currency_pair': pair,
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
                    return klines, pair
    except Exception as e:
        print(f"Gate.io获取失败: {e}", file=sys.stderr)
    return None, None

def get_kline_bitget(symbol='FARTCOIN', timeframe='1h', limit=500):
    """从Bitget获取K线数据"""
    try:
        tf_map = {
            '5m': '5min', '15m': '15min', '30m': '30min',
            '1h': '1hour', '4h': '4hour', '1d': '1day'
        }
        interval = tf_map.get(timeframe, '1hour')
        
        symbols = [f'{symbol}USDT', f'{symbol}_USDT', 'FARTUSDT', 'FART_USDT']
        
        for sym in symbols:
            url = "https://api.bitget.com/api/spot/v1/market/candles"
            params = {
                'symbol': sym,
                'granularity': interval,
                'limit': limit
            }
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == '00000' and data.get('data'):
                    klines_data = data['data']
                    klines_data.reverse()
                    klines = []
                    for k in klines_data:
                        klines.append({
                            'timestamp': int(k[0]) // 1000,
                            'open': float(k[1]),
                            'high': float(k[3]),
                            'low': float(k[4]),
                            'close': float(k[2]),
                            'volume': float(k[5])
                        })
                    return klines, sym
    except Exception as e:
        print(f"Bitget获取失败: {e}", file=sys.stderr)
    return None, None

def get_btc_kline(timeframe='1h', limit=500):
    """获取BTC K线数据"""
    # 先尝试Gate.io
    klines, pair = get_kline_gateio('BTC', timeframe, limit)
    if klines:
        return klines, pair
    
    # 再尝试Bitget
    klines, pair = get_kline_bitget('BTC', timeframe, limit)
    if klines:
        return klines, pair
    
    return None, None

def calculate_returns(prices):
    """计算收益率"""
    if len(prices) < 2:
        return []
    returns = []
    for i in range(1, len(prices)):
        ret = (prices[i] - prices[i-1]) / prices[i-1] * 100
        returns.append(ret)
    return returns

def calculate_correlation(x, y):
    """计算相关系数"""
    if len(x) != len(y) or len(x) < 2:
        return None, None
    try:
        corr, p_value = pearsonr(x, y)
        return corr, p_value
    except:
        return None, None

def calculate_lead_lag_relationship(fart_returns, btc_returns, max_lag=24):
    """计算领先滞后关系（使用交叉相关函数）"""
    if len(fart_returns) < 50 or len(btc_returns) < 50:
        print(f"      数据不足: fart={len(fart_returns)}, btc={len(btc_returns)}", file=sys.stderr)
        return None
    
    # 动态调整max_lag，但不要太小
    if len(fart_returns) < max_lag * 2 or len(btc_returns) < max_lag * 2:
        max_lag = min(len(fart_returns) // 4, len(btc_returns) // 4, max_lag)
    
    if max_lag < 1:
        max_lag = 1
    
    best_corr = -2
    best_lag = 0
    best_p_value = 1.0
    valid_count = 0
    
    # 测试FART领先BTC的情况（正lag表示FART领先）
    for lag in range(-max_lag, max_lag + 1):
        try:
            if lag > 0:
                # FART领先lag个周期：使用FART的前N-lag个数据，对应BTC的lag到N个数据
                if len(fart_returns) > lag and len(btc_returns) > lag:
                    fart_shifted = fart_returns[:-lag]
                    btc_shifted = btc_returns[lag:]
                else:
                    continue
            elif lag < 0:
                # BTC领先|lag|个周期：使用BTC的前N-|lag|个数据，对应FART的|lag|到N个数据
                abs_lag = abs(lag)
                if len(fart_returns) > abs_lag and len(btc_returns) > abs_lag:
                    fart_shifted = fart_returns[abs_lag:]
                    btc_shifted = btc_returns[:-abs_lag]
                else:
                    continue
            else:
                # lag == 0: 同时期
                fart_shifted = fart_returns
                btc_shifted = btc_returns
            
            # 确保长度一致
            min_len = min(len(fart_shifted), len(btc_shifted))
            if min_len < 20:  # 至少需要20个数据点
                continue
            
            fart_shifted = fart_shifted[:min_len]
            btc_shifted = btc_shifted[:min_len]
            
            # 计算相关系数
            corr, p_value = calculate_correlation(fart_shifted, btc_shifted)
            if corr is not None and not np.isnan(corr) and not np.isinf(corr):
                valid_count += 1
                # 使用绝对值比较，但保存原始符号
                if abs(corr) > abs(best_corr) or best_corr == -2:
                    best_corr = corr
                    best_lag = lag
                    best_p_value = p_value if p_value is not None and not np.isnan(p_value) else 1.0
        except Exception as e:
            continue
    
    print(f"      有效计算次数: {valid_count}/{2*max_lag+1}", file=sys.stderr)
    
    # 如果best_corr仍然是-2，说明没有找到有效结果
    if best_corr == -2 or np.isnan(best_corr) or np.isinf(best_corr):
        print(f"      未找到有效结果: best_corr={best_corr}", file=sys.stderr)
        return None
    
    return {
        'best_lag': int(best_lag),
        'best_corr': float(best_corr),
        'p_value': float(best_p_value),
        'is_leading': best_lag > 0
    }

def calculate_strength(klines, period=20):
    """计算价格强度（基于RSI和趋势）"""
    if len(klines) < period + 1:
        return None
    
    closes = [k['close'] for k in klines]
    
    # 计算RSI
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas[-period:]]
    losses = [-d if d < 0 else 0 for d in deltas[-period:]]
    avg_gain = sum(gains) / period if len(gains) > 0 else 0
    avg_loss = sum(losses) / period if len(losses) > 0 else 0
    
    if avg_loss == 0:
        rsi = 100
    else:
        rs = avg_gain / avg_loss if avg_loss > 0 else 0
        rsi = 100 - (100 / (1 + rs))
    
    # 计算趋势强度（价格变化率）
    price_change = ((closes[-1] - closes[-period]) / closes[-period]) * 100
    
    # 综合强度（RSI权重0.6，价格变化权重0.4）
    strength = (rsi / 100) * 0.6 + (min(max(price_change / 50, -1), 1) + 1) / 2 * 0.4
    
    return {
        'rsi': rsi,
        'price_change_pct': price_change,
        'strength': strength * 100  # 转换为0-100
    }

def analyze_fartcoin_leading_indicator():
    """分析FARTCOIN是否是领先指标"""
    print("正在获取FARTCOIN和BTC数据...", file=sys.stderr)
    
    # 获取多个时间框架的数据
    timeframes = ['15m', '1h', '4h', '1d']
    results = {}
    
    for tf in timeframes:
        print(f"\n分析 {tf} 时间框架...", file=sys.stderr)
        
        # 获取FARTCOIN数据
        fart_klines, fart_pair = get_kline_gateio('FARTCOIN', tf, 500)
        if not fart_klines:
            fart_klines, fart_pair = get_kline_bitget('FARTCOIN', tf, 500)
        
        # 获取BTC数据
        btc_klines, btc_pair = get_btc_kline(tf, 500)
        
        if not fart_klines or not btc_klines:
            print(f"  {tf}: 数据获取失败", file=sys.stderr)
            continue
        
        print(f"  FARTCOIN: {len(fart_klines)}根K线 ({fart_pair})", file=sys.stderr)
        print(f"  BTC: {len(btc_klines)}根K线 ({btc_pair})", file=sys.stderr)
        
        # 对齐时间戳（取交集）
        fart_timestamps = {k['timestamp']: k for k in fart_klines}
        btc_timestamps = {k['timestamp']: k for k in btc_klines}
        common_timestamps = sorted(set(fart_timestamps.keys()) & set(btc_timestamps.keys()))
        
        if len(common_timestamps) < 50:
            print(f"  {tf}: 共同时间戳太少 ({len(common_timestamps)})", file=sys.stderr)
            continue
        
        # 对齐数据
        fart_aligned = [fart_timestamps[ts]['close'] for ts in common_timestamps]
        btc_aligned = [btc_timestamps[ts]['close'] for ts in common_timestamps]
        
        # 计算收益率
        fart_returns = calculate_returns(fart_aligned)
        btc_returns = calculate_returns(btc_aligned)
        
        # 计算相关性
        corr, p_value = calculate_correlation(fart_returns, btc_returns)
        
        # 计算领先滞后关系
        # 使用更合理的max_lag：对于500个数据点，可以测试最多50个周期的滞后
        max_lag_value = min(50, len(fart_returns)//10, len(btc_returns)//10)
        if max_lag_value < 5:
            max_lag_value = 5  # 至少测试5个周期
        
        print(f"    计算领先滞后关系: max_lag={max_lag_value}, 数据长度={len(fart_returns)}", file=sys.stderr)
        lead_lag = calculate_lead_lag_relationship(fart_returns, btc_returns, max_lag=max_lag_value)
        if lead_lag:
            print(f"    领先滞后: lag={lead_lag['best_lag']}, corr={lead_lag['best_corr']:.3f}, FART{'领先' if lead_lag['is_leading'] else '滞后'}", file=sys.stderr)
        else:
            print(f"    领先滞后: 计算失败，尝试调试...", file=sys.stderr)
            # 调试：直接测试lag=0的情况
            corr_test, p_test = calculate_correlation(fart_returns, btc_returns)
            print(f"    调试: lag=0时, corr={corr_test:.3f}, p={p_test:.4f}", file=sys.stderr)
        
        # 计算当前强度
        fart_strength = calculate_strength(fart_klines[-50:])
        btc_strength = calculate_strength(btc_klines[-50:])
        
        # 计算低时间框架强度（如果是1h或更小）
        lower_tf_strength = None
        if tf in ['15m', '1h']:
            lower_tf_strength = fart_strength
        
        results[tf] = {
            'fart_pair': fart_pair,
            'btc_pair': btc_pair,
            'data_points': len(common_timestamps),
            'fart_current_price': fart_aligned[-1],
            'btc_current_price': btc_aligned[-1],
            'correlation': corr,
            'p_value': p_value,
            'lead_lag': lead_lag,
            'fart_strength': fart_strength,
            'btc_strength': btc_strength,
            'lower_tf_strength': lower_tf_strength
        }
        
        print(f"  ✓ {tf}: 相关性={corr:.3f}, p值={p_value:.4f}", file=sys.stderr)
        if lead_lag:
            print(f"    领先滞后: {lead_lag['best_lag']}个周期, FART{'领先' if lead_lag['is_leading'] else '滞后'}", file=sys.stderr)
    
    # 生成报告
    report = []
    report.append("# FARTCOIN 领先指标分析报告")
    report.append("")
    report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    report.append("**分析目标**: 验证FARTCOIN是否是BTC市场的领先指标  ")
    report.append("")
    
    # 一、数据概览
    report.append("## 一、数据概览")
    report.append("")
    
    for tf in timeframes:
        if tf not in results:
            continue
        
        r = results[tf]
        report.append(f"### {tf} 时间框架")
        report.append("")
        report.append(f"**数据点**: {r['data_points']}  ")
        report.append(f"**FARTCOIN当前价格**: ${r['fart_current_price']:,.6f} ({r['fart_pair']})  ")
        report.append(f"**BTC当前价格**: ${r['btc_current_price']:,.2f} ({r['btc_pair']})  ")
        report.append("")
    
    # 二、相关性分析
    report.append("## 二、相关性分析")
    report.append("")
    report.append("**说明**: 相关系数接近1表示正相关，接近-1表示负相关，接近0表示无相关  ")
    report.append("p值<0.05表示相关性显著  ")
    report.append("")
    
    for tf in timeframes:
        if tf not in results:
            continue
        
        r = results[tf]
        corr = r['correlation']
        p_val = r['p_value']
        
        if corr is None:
            continue
        
        report.append(f"### {tf} 时间框架")
        report.append("")
        report.append(f"**相关系数**: {corr:.4f}")
        
        if abs(corr) > 0.7:
            corr_strength = "强"
        elif abs(corr) > 0.4:
            corr_strength = "中等"
        else:
            corr_strength = "弱"
        
        report.append(f"**相关性强度**: {corr_strength}")
        report.append(f"**p值**: {p_val:.4f}")
        
        if p_val < 0.05:
            report.append("**显著性**: ✅ 显著相关")
        else:
            report.append("**显著性**: ❌ 不显著")
        
        report.append("")
    
    # 三、领先滞后关系分析
    report.append("## 三、领先滞后关系分析（核心验证）")
    report.append("")
    report.append("**说明**: 正lag表示FARTCOIN领先BTC，负lag表示BTC领先FARTCOIN  ")
    report.append("lag值表示领先/滞后的周期数  ")
    report.append("")
    
    leading_count = 0
    total_count = 0
    
    for tf in timeframes:
        if tf not in results:
            continue
        
        if not results[tf]['lead_lag']:
            report.append(f"### {tf} 时间框架")
            report.append("")
            report.append("**结论**: ⚠️ 数据不足，无法计算领先滞后关系")
            report.append("")
            continue
        
        r = results[tf]
        ll = r['lead_lag']
        total_count += 1
        
        if ll['is_leading']:
            leading_count += 1
        
        report.append(f"### {tf} 时间框架")
        report.append("")
        report.append(f"**最佳滞后**: {ll['best_lag']}个周期")
        
        if ll['best_lag'] > 0:
            report.append(f"**结论**: ✅ FARTCOIN领先BTC {ll['best_lag']}个周期")
        elif ll['best_lag'] < 0:
            report.append(f"**结论**: ❌ BTC领先FARTCOIN {abs(ll['best_lag'])}个周期")
        else:
            report.append(f"**结论**: ⚠️ 无明显领先滞后关系")
        
        report.append(f"**相关系数**: {ll['best_corr']:.4f}")
        report.append(f"**p值**: {ll['p_value']:.4f}")
        report.append("")
    
    # 四、综合结论
    report.append("## 四、综合结论")
    report.append("")
    
    if total_count > 0:
        leading_ratio = leading_count / total_count
        report.append(f"**领先指标验证**:")
        report.append(f"- 分析的时间框架数: {total_count}")
        report.append(f"- FARTCOIN领先的时间框架数: {leading_count}")
        report.append(f"- 领先比例: {leading_ratio*100:.1f}%")
        report.append("")
        
        if leading_ratio >= 0.6:
            report.append("✅ **结论**: FARTCOIN确实是BTC市场的领先指标")
            report.append("")
            report.append("**证据**:")
            report.append("- 在多数时间框架上，FARTCOIN的价格变化领先于BTC")
            report.append("- 可以用于预测BTC的未来走势")
        elif leading_ratio >= 0.4:
            report.append("⚠️ **结论**: FARTCOIN部分时间框架上领先BTC")
            report.append("")
            report.append("**说明**:")
            report.append("- 在某些时间框架上FARTCOIN领先，但不是所有时间框架")
            report.append("- 需要结合具体时间框架判断")
        else:
            report.append("❌ **结论**: FARTCOIN不是BTC市场的领先指标")
            report.append("")
            report.append("**说明**:")
            report.append("- 在多数时间框架上，FARTCOIN并未明显领先BTC")
            report.append("- 或者BTC领先FARTCOIN")
    
    # 五、低时间框架强度分析（预测90k+）
    report.append("## 五、低时间框架强度分析（预测BTC到90k+）")
    report.append("")
    report.append("**假设**: FARTCOIN低时间框架的强度可能预示BTC上涨到90k+  ")
    report.append("")
    
    current_btc_price = None
    for tf in ['1h', '4h', '1d']:
        if tf in results:
            current_btc_price = results[tf]['btc_current_price']
            break
    
    if current_btc_price:
        target_price = 90000
        price_gap = target_price - current_btc_price
        price_gap_pct = (price_gap / current_btc_price) * 100
        
        report.append(f"**BTC当前价格**: ${current_btc_price:,.2f}  ")
        report.append(f"**目标价格**: $90,000  ")
        report.append(f"**价格差距**: ${price_gap:,.2f} ({price_gap_pct:+.2f}%)  ")
        report.append("")
    
    for tf in ['15m', '1h']:
        if tf not in results or not results[tf]['lower_tf_strength']:
            continue
        
        r = results[tf]
        strength = r['lower_tf_strength']
        
        report.append(f"### {tf} 时间框架强度")
        report.append("")
        report.append(f"**RSI**: {strength['rsi']:.1f}")
        report.append(f"**价格变化**: {strength['price_change_pct']:+.2f}%")
        report.append(f"**综合强度**: {strength['strength']:.1f}/100")
        report.append("")
        
        if strength['strength'] > 60:
            report.append("✅ **强度判断**: 强")
            report.append("**预测**: FARTCOIN低时间框架强度较高，可能预示BTC上涨")
        elif strength['strength'] > 40:
            report.append("⚠️ **强度判断**: 中等")
            report.append("**预测**: FARTCOIN低时间框架强度中等，需要更多确认")
        else:
            report.append("❌ **强度判断**: 弱")
            report.append("**预测**: FARTCOIN低时间框架强度较弱，可能不支持BTC上涨到90k+")
        report.append("")
    
    # 六、交易建议
    report.append("## 六、交易建议")
    report.append("")
    
    if total_count > 0 and leading_count / total_count >= 0.6:
        report.append("**基于分析结果**:")
        report.append("1. ✅ FARTCOIN可以作为BTC的领先指标使用")
        report.append("2. ✅ 关注FARTCOIN的价格变化，可能预示BTC的未来走势")
        report.append("3. ✅ 如果FARTCOIN低时间框架强度高，可以考虑BTC做多")
        report.append("")
        report.append("**风险提示**:")
        report.append("- 领先指标不是100%准确，需要结合其他分析")
        report.append("- 市场环境变化可能影响领先关系")
        report.append("- 建议设置止损，控制风险")
    else:
        report.append("**基于分析结果**:")
        report.append("1. ⚠️ FARTCOIN的领先指标作用有限")
        report.append("2. ⚠️ 需要更多数据验证")
        report.append("3. ⚠️ 不建议单独依赖FARTCOIN作为BTC的领先指标")
    
    report.append("")
    report.append("---")
    report.append("")
    report.append("**免责声明**: 本分析基于历史数据统计，仅供参考。交易有风险，入市需谨慎。")
    
    # 输出报告
    output = "\n".join(report)
    try:
        print(output)
    except UnicodeEncodeError:
        pass
    
    # 保存到文件
    filename = f"FARTCOIN_leading_indicator_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(output)
    print(f"\n分析报告已保存到: {filename}", file=sys.stderr)
    
    # 同时保存JSON数据
    json_filename = f"FARTCOIN_analysis_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_filename, 'w', encoding='utf-8') as f:
        # 转换numpy类型为Python原生类型
        json_data = {}
        for tf, r in results.items():
            json_data[tf] = {
                'fart_pair': r['fart_pair'],
                'btc_pair': r['btc_pair'],
                'data_points': r['data_points'],
                'fart_current_price': float(r['fart_current_price']),
                'btc_current_price': float(r['btc_current_price']),
                'correlation': float(r['correlation']) if r['correlation'] is not None else None,
                'p_value': float(r['p_value']) if r['p_value'] is not None else None,
                'lead_lag': {
                    'best_lag': int(r['lead_lag']['best_lag']) if r['lead_lag'] else None,
                    'best_corr': float(r['lead_lag']['best_corr']) if r['lead_lag'] else None,
                    'p_value': float(r['lead_lag']['p_value']) if r['lead_lag'] else None,
                    'is_leading': bool(r['lead_lag']['is_leading']) if r['lead_lag'] else None
                } if r['lead_lag'] else None,
                'fart_strength': {
                    'rsi': float(r['fart_strength']['rsi']) if r['fart_strength'] else None,
                    'price_change_pct': float(r['fart_strength']['price_change_pct']) if r['fart_strength'] else None,
                    'strength': float(r['fart_strength']['strength']) if r['fart_strength'] else None
                } if r['fart_strength'] else None,
                'btc_strength': {
                    'rsi': float(r['btc_strength']['rsi']) if r['btc_strength'] else None,
                    'price_change_pct': float(r['btc_strength']['price_change_pct']) if r['btc_strength'] else None,
                    'strength': float(r['btc_strength']['strength']) if r['btc_strength'] else None
                } if r['btc_strength'] else None
            }
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    print(f"数据已保存到: {json_filename}", file=sys.stderr)

if __name__ == '__main__':
    try:
        analyze_fartcoin_leading_indicator()
    except Exception as e:
        print(f"分析失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()

