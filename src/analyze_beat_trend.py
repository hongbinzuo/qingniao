#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析BEAT/USDT 1小时级别价格走势特征
关注上升趋势和下降趋势的时间比例关系
"""

import requests
from datetime import datetime, timedelta
import json
import sys

def get_beat_kline_data(timeframe='1h', limit=1000):
    """获取BEAT/USDT K线数据"""
    try:
        url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {
            'currency_pair': 'BEAT_USDT',
            'interval': timeframe,
            'limit': limit
        }
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            # K线格式: [timestamp, volume, close, high, low, open]
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
            return list(reversed(klines))  # 按时间正序
    except Exception as e:
        print(f"获取K线数据失败: {e}")
    return None

def get_current_beat_price():
    """获取当前BEAT价格"""
    try:
        url = "https://api.gateio.ws/api/v4/spot/tickers"
        params = {'currency_pair': 'BEAT_USDT'}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                return float(data[0]['last'])
    except Exception as e:
        print(f"获取价格失败: {e}")
    return None

def identify_trend_segments(klines):
    """识别上升趋势和下降趋势段"""
    if not klines or len(klines) < 2:
        return []
    
    segments = []
    current_trend = None
    trend_start_idx = 0
    
    for i in range(1, len(klines)):
        prev_close = klines[i-1]['close']
        curr_close = klines[i]['close']
        
        # 判断趋势方向（使用0.1%作为阈值，避免噪音）
        price_change_pct = (curr_close - prev_close) / prev_close if prev_close > 0 else 0
        
        if price_change_pct > 0.001:  # 上升
            if current_trend != 'up':
                # 趋势转换：结束上一个趋势段
                if current_trend is not None:
                    segments.append({
                        'trend': current_trend,
                        'start_idx': trend_start_idx,
                        'end_idx': i - 1,
                        'start_price': klines[trend_start_idx]['close'],
                        'end_price': klines[i-1]['close'],
                        'duration': i - trend_start_idx,
                        'price_change': klines[i-1]['close'] - klines[trend_start_idx]['close'],
                        'price_change_pct': (klines[i-1]['close'] - klines[trend_start_idx]['close']) / klines[trend_start_idx]['close'] * 100
                    })
                # 开始新的上升趋势
                current_trend = 'up'
                trend_start_idx = i - 1
        elif price_change_pct < -0.001:  # 下降
            if current_trend != 'down':
                # 趋势转换：结束上一个趋势段
                if current_trend is not None:
                    segments.append({
                        'trend': current_trend,
                        'start_idx': trend_start_idx,
                        'end_idx': i - 1,
                        'start_price': klines[trend_start_idx]['close'],
                        'end_price': klines[i-1]['close'],
                        'duration': i - trend_start_idx,
                        'price_change': klines[i-1]['close'] - klines[trend_start_idx]['close'],
                        'price_change_pct': (klines[i-1]['close'] - klines[trend_start_idx]['close']) / klines[trend_start_idx]['close'] * 100
                    })
                # 开始新的下降趋势
                current_trend = 'down'
                trend_start_idx = i - 1
        # 如果价格变化很小（<0.1%），保持当前趋势
    
    # 添加最后一个趋势段
    if current_trend is not None:
        segments.append({
            'trend': current_trend,
            'start_idx': trend_start_idx,
            'end_idx': len(klines) - 1,
            'start_price': klines[trend_start_idx]['close'],
            'end_price': klines[-1]['close'],
            'duration': len(klines) - trend_start_idx,
            'price_change': klines[-1]['close'] - klines[trend_start_idx]['close'],
            'price_change_pct': (klines[-1]['close'] - klines[trend_start_idx]['close']) / klines[trend_start_idx]['close'] * 100
        })
    
    return segments

def analyze_trend_statistics(segments):
    """分析趋势统计信息"""
    if not segments:
        return None
    
    up_segments = [s for s in segments if s['trend'] == 'up']
    down_segments = [s for s in segments if s['trend'] == 'down']
    
    total_duration = sum(s['duration'] for s in segments)
    up_duration = sum(s['duration'] for s in up_segments)
    down_duration = sum(s['duration'] for s in down_segments)
    
    stats = {
        'total_segments': len(segments),
        'up_segments': len(up_segments),
        'down_segments': len(down_segments),
        'total_duration': total_duration,
        'up_duration': up_duration,
        'down_duration': down_duration,
        'up_duration_ratio': up_duration / total_duration * 100 if total_duration > 0 else 0,
        'down_duration_ratio': down_duration / total_duration * 100 if total_duration > 0 else 0,
        'avg_up_duration': up_duration / len(up_segments) if up_segments else 0,
        'avg_down_duration': down_duration / len(down_segments) if down_segments else 0,
        'avg_up_change_pct': sum(s['price_change_pct'] for s in up_segments) / len(up_segments) if up_segments else 0,
        'avg_down_change_pct': sum(s['price_change_pct'] for s in down_segments) / len(down_segments) if down_segments else 0,
        'max_up_change_pct': max((s['price_change_pct'] for s in up_segments), default=0),
        'max_down_change_pct': min((s['price_change_pct'] for s in down_segments), default=0),
    }
    
    return stats

def identify_current_trend(klines, segments):
    """识别当前趋势"""
    if not klines or not segments:
        return None
    
    # 获取最后一个趋势段
    last_segment = segments[-1] if segments else None
    if not last_segment:
        return None
    
    current_trend = last_segment['trend']
    current_price = klines[-1]['close']
    trend_start_price = last_segment['start_price']
    trend_duration = last_segment['duration']
    
    # 计算趋势进度
    if current_trend == 'up':
        price_change = current_price - trend_start_price
        total_change = last_segment['price_change']
        progress = (price_change / total_change * 100) if total_change > 0 else 0
    else:  # down
        price_change = current_price - trend_start_price
        total_change = last_segment['price_change']
        progress = (price_change / total_change * 100) if total_change < 0 else 0
    
    return {
        'trend': current_trend,
        'start_price': trend_start_price,
        'current_price': current_price,
        'duration': trend_duration,
        'progress': progress,
        'price_change_pct': last_segment['price_change_pct']
    }

def calculate_technical_indicators(klines):
    """计算技术指标"""
    if not klines or len(klines) < 20:
        return None
    
    closes = [k['close'] for k in klines]
    volumes = [k['volume'] for k in klines]
    
    # 简单移动平均
    sma_20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else None
    sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else None
    
    # 计算EMA
    def calculate_ema(prices, period):
        if len(prices) < period:
            return None
        multiplier = 2.0 / (period + 1)
        ema = [prices[0]]
        for i in range(1, len(prices)):
            ema.append((prices[i] - ema[-1]) * multiplier + ema[-1])
        return ema[-1]
    
    ema_20 = calculate_ema(closes, 20)
    ema_50 = calculate_ema(closes, 50)
    
    # 计算RSI
    def calculate_rsi(prices, period=14):
        if len(prices) < period + 1:
            return None
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas[-period:]]
        losses = [-d if d < 0 else 0 for d in deltas[-period:]]
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    rsi = calculate_rsi(closes)
    
    # 计算成交量平均值
    avg_volume = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else None
    current_volume = volumes[-1] if volumes else None
    
    return {
        'sma_20': sma_20,
        'sma_50': sma_50,
        'ema_20': ema_20,
        'ema_50': ema_50,
        'rsi': rsi,
        'avg_volume': avg_volume,
        'current_volume': current_volume,
        'volume_ratio': current_volume / avg_volume if avg_volume and avg_volume > 0 else None
    }

def generate_trading_recommendation(current_trend, trend_stats, indicators, current_price):
    """生成交易建议"""
    recommendation = {
        'direction': None,
        'confidence': 0,
        'reasons': [],
        'risk_level': 'medium'
    }
    
    score = 0
    
    # 1. 当前趋势方向
    if current_trend and current_trend['trend'] == 'up':
        recommendation['reasons'].append(f"当前处于上升趋势（已持续{current_trend['duration']}小时）")
        score += 2
    elif current_trend and current_trend['trend'] == 'down':
        recommendation['reasons'].append(f"当前处于下降趋势（已持续{current_trend['duration']}小时）")
        score -= 2
    
    # 2. 趋势进度
    if current_trend:
        progress = current_trend['progress']
        if current_trend['trend'] == 'up':
            if progress < 50:
                recommendation['reasons'].append(f"上升趋势进度{progress:.1f}%，可能还有上升空间")
                score += 1
            elif progress > 80:
                recommendation['reasons'].append(f"上升趋势进度{progress:.1f}%，可能接近尾声")
                score -= 1
        else:  # down
            if progress < 50:
                recommendation['reasons'].append(f"下降趋势进度{progress:.1f}%，可能还有下降空间")
                score -= 1
            elif progress > 80:
                recommendation['reasons'].append(f"下降趋势进度{progress:.1f}%，可能接近尾声")
                score += 1
    
    # 3. 历史趋势比例
    if trend_stats:
        if trend_stats['up_duration_ratio'] > 60:
            recommendation['reasons'].append(f"历史上上升趋势占比{trend_stats['up_duration_ratio']:.1f}%，偏多")
            score += 1
        elif trend_stats['down_duration_ratio'] > 60:
            recommendation['reasons'].append(f"历史上下降趋势占比{trend_stats['down_duration_ratio']:.1f}%，偏空")
            score -= 1
    
    # 4. 技术指标
    if indicators:
        # RSI
        if indicators['rsi']:
            if indicators['rsi'] > 70:
                recommendation['reasons'].append(f"RSI={indicators['rsi']:.1f}，超买，可能回调")
                score -= 1
            elif indicators['rsi'] < 30:
                recommendation['reasons'].append(f"RSI={indicators['rsi']:.1f}，超卖，可能反弹")
                score += 1
        
        # 均线
        if indicators['ema_20'] and indicators['ema_50']:
            if current_price > indicators['ema_20'] > indicators['ema_50']:
                recommendation['reasons'].append("价格在均线上方，均线多头排列")
                score += 1
            elif current_price < indicators['ema_20'] < indicators['ema_50']:
                recommendation['reasons'].append("价格在均线下方，均线空头排列")
                score -= 1
        
        # 成交量
        if indicators['volume_ratio']:
            if indicators['volume_ratio'] > 1.5:
                recommendation['reasons'].append(f"成交量放大{indicators['volume_ratio']:.1f}倍，趋势可能延续")
                if current_trend and current_trend['trend'] == 'up':
                    score += 1
                elif current_trend and current_trend['trend'] == 'down':
                    score -= 1
    
    # 确定方向
    if score > 2:
        recommendation['direction'] = '做多'
        recommendation['confidence'] = min(90, 50 + score * 5)
    elif score < -2:
        recommendation['direction'] = '做空'
        recommendation['confidence'] = min(90, 50 + abs(score) * 5)
    else:
        recommendation['direction'] = '观望'
        recommendation['confidence'] = 30
    
    # 风险等级
    if abs(score) >= 4:
        recommendation['risk_level'] = 'low'
    elif abs(score) >= 2:
        recommendation['risk_level'] = 'medium'
    else:
        recommendation['risk_level'] = 'high'
    
    return recommendation

def main():
    print("=" * 80)
    print("BEAT/USDT 1小时级别价格走势分析")
    print("=" * 80)
    print()
    
    # 获取数据
    print("正在获取BEAT/USDT数据...")
    current_price = get_current_beat_price()
    klines = get_beat_kline_data('1h', 1000)
    
    if not current_price or not klines:
        print("获取数据失败，请检查网络连接")
        return
    
    print(f"当前价格: ${current_price:.6f}")
    print(f"获取到 {len(klines)} 根K线数据")
    print()
    
    # 分析趋势
    print("正在分析价格走势特征...")
    segments = identify_trend_segments(klines)
    trend_stats = analyze_trend_statistics(segments)
    current_trend = identify_current_trend(klines, segments)
    indicators = calculate_technical_indicators(klines)
    
    # 生成报告
    report = []
    report.append("=" * 80)
    report.append("BEAT/USDT 1小时级别价格走势分析报告")
    report.append("=" * 80)
    report.append("")
    report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"当前价格: ${current_price:.6f}")
    report.append(f"分析数据: 最近 {len(klines)} 根1小时K线")
    report.append("")
    
    # 一、趋势统计
    report.append("## 一、历史趋势统计")
    report.append("")
    if trend_stats:
        report.append(f"**总趋势段数**: {trend_stats['total_segments']}")
        report.append(f"  - 上升趋势段: {trend_stats['up_segments']} 个")
        report.append(f"  - 下降趋势段: {trend_stats['down_segments']} 个")
        report.append("")
        report.append(f"**时间比例关系**:")
        report.append(f"  - 上升趋势时间占比: {trend_stats['up_duration_ratio']:.2f}%")
        report.append(f"  - 下降趋势时间占比: {trend_stats['down_duration_ratio']:.2f}%")
        report.append("")
        report.append(f"**平均持续时间**:")
        report.append(f"  - 上升趋势平均: {trend_stats['avg_up_duration']:.1f} 小时")
        report.append(f"  - 下降趋势平均: {trend_stats['avg_down_duration']:.1f} 小时")
        report.append("")
        report.append(f"**平均价格变化**:")
        report.append(f"  - 上升趋势平均涨幅: {trend_stats['avg_up_change_pct']:.2f}%")
        report.append(f"  - 下降趋势平均跌幅: {trend_stats['avg_down_change_pct']:.2f}%")
        report.append("")
        report.append(f"**最大变化**:")
        report.append(f"  - 最大涨幅: {trend_stats['max_up_change_pct']:.2f}%")
        report.append(f"  - 最大跌幅: {trend_stats['max_down_change_pct']:.2f}%")
        report.append("")
    
    # 二、当前趋势分析
    report.append("## 二、当前趋势分析")
    report.append("")
    if current_trend:
        trend_name = "上升趋势" if current_trend['trend'] == 'up' else "下降趋势"
        report.append(f"**当前趋势**: {trend_name}")
        report.append(f"  - 趋势开始价格: ${current_trend['start_price']:.6f}")
        report.append(f"  - 当前价格: ${current_trend['current_price']:.6f}")
        report.append(f"  - 已持续时长: {current_trend['duration']} 小时")
        report.append(f"  - 价格变化: {current_trend['price_change_pct']:.2f}%")
        report.append(f"  - **趋势进度: {current_trend['progress']:.1f}%**")
        report.append("")
        
        if current_trend['progress'] < 30:
            report.append("  → 趋势刚刚开始，可能还有较大空间")
        elif current_trend['progress'] < 70:
            report.append("  → 趋势进行中，仍有空间")
        else:
            report.append("  → 趋势可能接近尾声，需要谨慎")
        report.append("")
    else:
        report.append("**当前趋势**: 无法确定")
        report.append("")
    
    # 三、技术指标
    report.append("## 三、技术指标分析")
    report.append("")
    if indicators:
        if indicators['sma_20']:
            report.append(f"**移动平均线**:")
            report.append(f"  - SMA20: ${indicators['sma_20']:.6f}")
            if indicators['sma_50']:
                report.append(f"  - SMA50: ${indicators['sma_50']:.6f}")
            if indicators['ema_20']:
                report.append(f"  - EMA20: ${indicators['ema_20']:.6f}")
            if indicators['ema_50']:
                report.append(f"  - EMA50: ${indicators['ema_50']:.6f}")
            report.append("")
            
            # 均线判断
            if indicators['ema_20'] and indicators['ema_50']:
                if current_price > indicators['ema_20'] > indicators['ema_50']:
                    report.append("  → 价格在均线上方，均线多头排列（偏多）")
                elif current_price < indicators['ema_20'] < indicators['ema_50']:
                    report.append("  → 价格在均线下方，均线空头排列（偏空）")
                else:
                    report.append("  → 均线交叉，方向不明确")
            report.append("")
        
        if indicators['rsi']:
            report.append(f"**RSI（相对强弱指标）**: {indicators['rsi']:.2f}")
            if indicators['rsi'] > 70:
                report.append("  → 超买区域，可能回调（偏空）")
            elif indicators['rsi'] < 30:
                report.append("  → 超卖区域，可能反弹（偏多）")
            else:
                report.append("  → 正常区域")
            report.append("")
        
        if indicators['volume_ratio']:
            report.append(f"**成交量**:")
            report.append(f"  - 当前成交量/平均成交量: {indicators['volume_ratio']:.2f} 倍")
            if indicators['volume_ratio'] > 1.5:
                report.append("  → 成交量放大，趋势可能延续")
            elif indicators['volume_ratio'] < 0.5:
                report.append("  → 成交量萎缩，趋势可能减弱")
            else:
                report.append("  → 成交量正常")
            report.append("")
    
    # 四、交易建议
    report.append("## 四、交易建议")
    report.append("")
    recommendation = generate_trading_recommendation(current_trend, trend_stats, indicators, current_price)
    
    report.append(f"**建议方向**: {recommendation['direction']}")
    report.append(f"**信心度**: {recommendation['confidence']}%")
    report.append(f"**风险等级**: {recommendation['risk_level']}")
    report.append("")
    report.append("**理由**:")
    for reason in recommendation['reasons']:
        report.append(f"  - {reason}")
    report.append("")
    
    # 五、辅助交易参考信息
    report.append("## 五、辅助交易参考信息")
    report.append("")
    report.append("**关键支撑/阻力位**:")
    if klines:
        recent_highs = [k['high'] for k in klines[-50:]]
        recent_lows = [k['low'] for k in klines[-50:]]
        resistance = max(recent_highs)
        support = min(recent_lows)
        report.append(f"  - 阻力位（50小时高点）: ${resistance:.6f}")
        report.append(f"  - 支撑位（50小时低点）: ${support:.6f}")
        report.append(f"  - 当前价格距离阻力位: {((resistance - current_price) / current_price * 100):.2f}%")
        report.append(f"  - 当前价格距离支撑位: {((current_price - support) / current_price * 100):.2f}%")
    report.append("")
    
    report.append("**风险提示**:")
    report.append("  - 本分析仅供参考，不构成投资建议")
    report.append("  - 加密货币市场波动剧烈，请严格控制风险")
    report.append("  - 建议设置止损，风险不超过账户的5%")
    report.append("  - 结合其他技术分析和市场消息综合判断")
    report.append("")
    report.append("=" * 80)
    
    # 保存报告
    report_text = "\n".join(report)
    output_file = f"BEAT_USDT_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report_text)
    
    # 输出到控制台
    sys.stdout.buffer.write(report_text.encode('utf-8'))
    sys.stdout.buffer.write(f"\n\n报告已保存到: {output_file}\n".encode('utf-8'))

if __name__ == "__main__":
    main()




