# -*- coding: utf-8 -*-
"""
评估De.交易系统最新信号的质量和结果
"""

import sys
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
import duckdb

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))


def get_latest_signal_file() -> Optional[Path]:
    """获取最新的De.信号文件"""
    signals_dir = Path(__file__).parent.parent / "trading_signals"
    
    # 查找BTC和ETH的De.信号文件
    btc_files = list(signals_dir.glob("BTC_de_signals_*.md"))
    eth_files = list(signals_dir.glob("ETH_de_signals_*.md"))
    
    all_files = btc_files + eth_files
    if not all_files:
        return None
    
    # 按修改时间排序，返回最新的
    latest = max(all_files, key=lambda f: f.stat().st_mtime)
    return latest


def parse_signal_file(file_path: Path) -> Dict:
    """解析信号文件"""
    content = file_path.read_text(encoding='utf-8')
    
    # 提取生成时间
    time_match = re.search(r'\*\*生成时间\*\*:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', content)
    signal_time_str = time_match.group(1) if time_match else None
    signal_time = datetime.strptime(signal_time_str, '%Y-%m-%d %H:%M:%S') if signal_time_str else None
    
    # 提取当前价格
    price_match = re.search(r'\*\*当前价格\*\*:\s*\$?([\d,]+\.?\d*)', content)
    signal_price = float(price_match.group(1).replace(',', '')) if price_match else None
    
    # 判断是BTC还是ETH
    symbol = 'BTC' if 'BTC' in file_path.name else 'ETH'
    
    # 解析信号
    signals = []
    
    # 更灵活的匹配模式，匹配信号块
    # 格式：做多/做空，然后入场、止损、止盈
    signal_blocks = re.split(r'##\s+[一二三四五六七八九十\d]+、', content)
    
    for block in signal_blocks:
        # 查找做多或做空
        direction_match = re.search(r'(做多|做空)\s*\([^)]+\)', block)
        if not direction_match:
            continue
        
        direction = 'long' if direction_match.group(1) == '做多' else 'short'
        
        # 提取入场价
        entry_match = re.search(r'入场:\s*\$?([\d,]+\.?\d*)', block)
        if not entry_match:
            continue
        entry = float(entry_match.group(1).replace(',', ''))
        
        # 提取止损（可能有多行，取第一个数字）
        stop_loss_match = re.search(r'止损:\s*\$?([\d,]+\.?\d*)', block)
        if not stop_loss_match:
            continue
        stop_loss = float(stop_loss_match.group(1).replace(',', ''))
        
        # 提取止盈（格式：$xxx (50%) / $yyy (50%)）
        tp_match = re.search(r'止盈:\s*\$?([\d,]+\.?\d*)\s*\([^)]+\)\s*/\s*\$?([\d,]+\.?\d*)\s*\([^)]+\)', block)
        if not tp_match:
            continue
        tp1 = float(tp_match.group(1).replace(',', ''))
        tp2 = float(tp_match.group(2).replace(',', ''))
        
        signals.append({
            'direction': direction,
            'entry': entry,
            'stop_loss': stop_loss,
            'take_profit_1': tp1,
            'take_profit_2': tp2,
            'symbol': symbol
        })
    
    # 如果上面的方法没找到，尝试更宽松的匹配
    if not signals:
        # 直接在整个内容中搜索
        lines = content.split('\n')
        current_direction = None
        current_entry = None
        current_stop_loss = None
        current_tp1 = None
        current_tp2 = None
        
        for i, line in enumerate(lines):
            # 检测方向
            if '做多' in line or '做空' in line:
                if current_entry and current_stop_loss and current_tp1 and current_tp2:
                    # 保存之前的信号
                    signals.append({
                        'direction': current_direction,
                        'entry': current_entry,
                        'stop_loss': current_stop_loss,
                        'take_profit_1': current_tp1,
                        'take_profit_2': current_tp2,
                        'symbol': symbol
                    })
                # 开始新信号
                current_direction = 'long' if '做多' in line else 'short'
                current_entry = None
                current_stop_loss = None
                current_tp1 = None
                current_tp2 = None
            
            # 提取入场
            entry_m = re.search(r'入场:\s*\$?([\d,]+\.?\d*)', line)
            if entry_m:
                current_entry = float(entry_m.group(1).replace(',', ''))
            
            # 提取止损
            sl_m = re.search(r'止损:\s*\$?([\d,]+\.?\d*)', line)
            if sl_m:
                current_stop_loss = float(sl_m.group(1).replace(',', ''))
            
            # 提取止盈
            tp_m = re.search(r'止盈:\s*\$?([\d,]+\.?\d*)\s*\([^)]+\)\s*/\s*\$?([\d,]+\.?\d*)\s*\([^)]+\)', line)
            if tp_m:
                current_tp1 = float(tp_m.group(1).replace(',', ''))
                current_tp2 = float(tp_m.group(2).replace(',', ''))
        
        # 保存最后一个信号
        if current_entry and current_stop_loss and current_tp1 and current_tp2:
            signals.append({
                'direction': current_direction,
                'entry': current_entry,
                'stop_loss': current_stop_loss,
                'take_profit_1': current_tp1,
                'take_profit_2': current_tp2,
                'symbol': symbol
            })
    
    return {
        'file_path': file_path,
        'signal_time': signal_time,
        'signal_price': signal_price,
        'symbol': symbol,
        'signals': signals
    }


def get_current_price(symbol: str) -> Optional[float]:
    """获取当前价格"""
    try:
        if symbol == 'BTC':
            url = "https://api.gateio.ws/api/v4/spot/tickers"
            params = {'currency_pair': 'BTC_USDT'}
        elif symbol == 'ETH':
            url = "https://api.gateio.ws/api/v4/spot/tickers"
            params = {'currency_pair': 'ETH_USDT'}
        else:
            return None
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data:
                return float(data[0].get('last', 0))
    except Exception as e:
        print(f"获取当前价格失败: {e}", file=sys.stderr)
    return None


def get_price_history(symbol: str, start_time: datetime, end_time: datetime, timeframe: str = '1h') -> List[Dict]:
    """从数据库获取价格历史"""
    try:
        db_path = Path(__file__).parent.parent / "data" / "btc_price_timeseries.duckdb"
        if not db_path.exists():
            return []
        
        table_name = f"{symbol.lower()}_price_{timeframe}" if symbol == 'ETH' else f"btc_price_{timeframe}"
        
        conn = duckdb.connect(str(db_path))
        
        start_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
        end_str = end_time.strftime('%Y-%m-%d %H:%M:%S')
        
        query = f"""
            SELECT datetime, open, high, low, close, volume
            FROM {table_name}
            WHERE datetime >= ? AND datetime <= ?
            ORDER BY datetime ASC
        """
        
        results = conn.execute(query, [start_str, end_str]).fetchall()
        conn.close()
        
        return [
            {
                'datetime': row[0],
                'open': row[1],
                'high': row[2],
                'low': row[3],
                'close': row[4],
                'volume': row[5]
            }
            for row in results
        ]
    except Exception as e:
        print(f"获取价格历史失败: {e}", file=sys.stderr)
        return []


def evaluate_signal(signal: Dict, current_price: float, price_history: List[Dict], signal_time: datetime) -> Dict:
    """评估单个信号"""
    entry = signal['entry']
    stop_loss = signal['stop_loss']
    tp1 = signal['take_profit_1']
    tp2 = signal['take_profit_2']
    direction = signal['direction']
    
    # 计算最高/最低价格（从价格历史中）
    if price_history:
        max_price = max([p['high'] for p in price_history], default=current_price)
        min_price = min([p['low'] for p in price_history], default=current_price)
    else:
        max_price = current_price
        min_price = current_price
    
    # 计算价格变化
    price_change = current_price - entry
    price_change_pct = (price_change / entry) * 100
    
    # 判断信号状态 - 需要检查历史价格是否触及止损/止盈
    status = 'unknown'
    status_detail = ''
    
    # 检查历史价格是否触及止损/止盈
    hit_stop_loss = False
    hit_tp1 = False
    hit_tp2 = False
    reached_entry = False
    
    if direction == 'long':
        # 做多：检查最低价是否触及止损，最高价是否触及止盈
        if min_price <= stop_loss:
            hit_stop_loss = True
            status = 'stopped'
            status_detail = f'已触及止损 ${stop_loss:,.2f}（最低价 ${min_price:,.2f}）'
        elif max_price >= tp2:
            hit_tp2 = True
            status = 'full_tp'
            status_detail = f'已触及第二止盈 ${tp2:,.2f}（最高价 ${max_price:,.2f}）'
        elif max_price >= tp1:
            hit_tp1 = True
            status = 'partial_tp'
            status_detail = f'已触及第一止盈 ${tp1:,.2f}（最高价 ${max_price:,.2f}）'
        else:
            # 检查是否到达入场价（做多：价格需要跌到入场价或以下）
            if min_price <= entry:
                reached_entry = True
                status = 'active'
                status_detail = '持仓中'
            else:
                status = 'missed'
                status_detail = f'未到达入场价（最低价 ${min_price:,.2f}，入场价 ${entry:,.2f}）'
    else:  # short
        # 做空：检查最高价是否触及止损，最低价是否触及止盈
        if max_price >= stop_loss:
            hit_stop_loss = True
            status = 'stopped'
            status_detail = f'已触及止损 ${stop_loss:,.2f}（最高价 ${max_price:,.2f}）'
        elif min_price <= tp2:
            hit_tp2 = True
            status = 'full_tp'
            status_detail = f'已触及第二止盈 ${tp2:,.2f}（最低价 ${min_price:,.2f}）'
        elif min_price <= tp1:
            hit_tp1 = True
            status = 'partial_tp'
            status_detail = f'已触及第一止盈 ${tp1:,.2f}（最低价 ${min_price:,.2f}）'
        else:
            # 检查是否到达入场价（做空：价格需要涨到入场价或以上）
            if max_price >= entry:
                reached_entry = True
                status = 'active'
                status_detail = '持仓中'
            else:
                status = 'missed'
                status_detail = f'未到达入场价（最高价 ${max_price:,.2f}，入场价 ${entry:,.2f}）'
    
    
    # 计算盈亏比
    if direction == 'long':
        risk = entry - stop_loss
        reward1 = tp1 - entry
        reward2 = tp2 - entry
        max_profit = max_price - entry
        max_loss = min_price - entry
    else:
        risk = stop_loss - entry
        reward1 = entry - tp1
        reward2 = entry - tp2
        max_profit = entry - min_price
        max_loss = entry - max_price
    
    rr1 = reward1 / risk if risk > 0 else 0
    rr2 = reward2 / risk if risk > 0 else 0
    
    # 评估质量
    quality = 'good'
    quality_notes = []
    
    if status == 'stopped':
        quality = 'poor'
        quality_notes.append('信号被止损')
    elif status == 'missed':
        quality = 'poor'
        quality_notes.append('信号未到达入场价')
    elif status == 'full_tp':
        quality = 'excellent'
        quality_notes.append('信号达到第二止盈')
    elif status == 'partial_tp':
        quality = 'good'
        quality_notes.append('信号达到第一止盈')
    elif status == 'active':
        if direction == 'long':
            if current_price > entry:
                quality_notes.append(f'当前浮盈 {price_change_pct:.2f}%')
            else:
                quality_notes.append(f'当前浮亏 {abs(price_change_pct):.2f}%')
        else:
            if current_price < entry:
                quality_notes.append(f'当前浮盈 {abs(price_change_pct):.2f}%')
            else:
                quality_notes.append(f'当前浮亏 {price_change_pct:.2f}%')
    
    if rr1 < 1.5:
        quality_notes.append('盈亏比偏低')
    if abs(price_change_pct) > 5:
        quality_notes.append('价格波动较大')
    
    return {
        'signal': signal,
        'current_price': current_price,
        'status': status,
        'status_detail': status_detail,
        'price_change': price_change,
        'price_change_pct': price_change_pct,
        'max_price': max_price,
        'min_price': min_price,
        'risk_reward_1': rr1,
        'risk_reward_2': rr2,
        'quality': quality,
        'quality_notes': quality_notes
    }


def generate_report(data: Dict, evaluations: List[Dict]) -> str:
    """生成评估报告"""
    lines = []
    
    lines.append("# De.交易系统信号评估简报")
    lines.append("")
    lines.append(f"**信号生成时间**: {data['signal_time'].strftime('%Y-%m-%d %H:%M:%S') if data['signal_time'] else '未知'}")
    lines.append(f"**评估时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**交易对**: {data['symbol']}")
    lines.append("")
    
    # 时间统计
    if data['signal_time']:
        elapsed = datetime.now() - data['signal_time']
        lines.append(f"**信号已运行**: {elapsed.days}天 {elapsed.seconds // 3600}小时 {(elapsed.seconds % 3600) // 60}分钟")
        lines.append("")
    
    lines.append("---")
    lines.append("")
    
    # 每个信号的评估
    for i, eval_data in enumerate(evaluations, 1):
        signal = eval_data['signal']
        lines.append(f"## 信号 {i}: {signal['direction'].upper()} ({signal['symbol']})")
        lines.append("")
        lines.append(f"**入场价**: ${signal['entry']:,.2f}")
        lines.append(f"**止损**: ${signal['stop_loss']:,.2f}")
        lines.append(f"**第一止盈**: ${signal['take_profit_1']:,.2f}")
        lines.append(f"**第二止盈**: ${signal['take_profit_2']:,.2f}")
        lines.append("")
        lines.append(f"**当前价格**: ${eval_data['current_price']:,.2f}")
        lines.append(f"**状态**: {eval_data['status_detail']}")
        if eval_data['status'] != 'missed':
            lines.append(f"**价格变化**: {eval_data['price_change_pct']:+.2f}%")
        lines.append("")
        lines.append(f"**期间最高价**: ${eval_data['max_price']:,.2f}")
        lines.append(f"**期间最低价**: ${eval_data['min_price']:,.2f}")
        # 判断是否到达入场价（与状态判断逻辑一致）
        if signal['direction'] == 'long':
            reached_entry_price = eval_data['min_price'] <= signal['entry']
            lines.append(f"**是否到达入场价**: {'是' if reached_entry_price else '否'}（最低价 ${eval_data['min_price']:,.2f}，入场价 ${signal['entry']:,.2f}）")
        else:
            reached_entry_price = eval_data['max_price'] >= signal['entry']
            lines.append(f"**是否到达入场价**: {'是' if reached_entry_price else '否'}（最高价 ${eval_data['max_price']:,.2f}，入场价 ${signal['entry']:,.2f}）")
        lines.append("")
        lines.append(f"**盈亏比**: {eval_data['risk_reward_1']:.2f}:1 (第一止盈) / {eval_data['risk_reward_2']:.2f}:1 (第二止盈)")
        lines.append("")
        lines.append(f"**质量评估**: {eval_data['quality']}")
        if eval_data['quality_notes']:
            for note in eval_data['quality_notes']:
                lines.append(f"- {note}")
        lines.append("")
        lines.append("---")
        lines.append("")
    
    # 总体评估
    lines.append("## 总体评估")
    lines.append("")
    
    status_counts = {}
    quality_counts = {}
    for eval_data in evaluations:
        status = eval_data['status']
        quality = eval_data['quality']
        status_counts[status] = status_counts.get(status, 0) + 1
        quality_counts[quality] = quality_counts.get(quality, 0) + 1
    
    lines.append("**信号状态分布**:")
    for status, count in status_counts.items():
        status_name = {
            'stopped': '已止损',
            'partial_tp': '部分止盈',
            'full_tp': '完全止盈',
            'active': '持仓中',
            'missed': '未到达入场价',
            'unknown': '未知'
        }.get(status, status)
        lines.append(f"- {status_name}: {count}个")
    lines.append("")
    
    lines.append("**质量分布**:")
    for quality, count in quality_counts.items():
        quality_name = {
            'excellent': '优秀',
            'good': '良好',
            'poor': '较差'
        }.get(quality, quality)
        lines.append(f"- {quality_name}: {count}个")
    lines.append("")
    
    avg_rr = sum([e['risk_reward_1'] for e in evaluations]) / len(evaluations) if evaluations else 0
    lines.append(f"**平均盈亏比**: {avg_rr:.2f}:1")
    lines.append("")
    
    return "\n".join(lines)


def main():
    print("=" * 80)
    print("De.交易系统信号评估")
    print("=" * 80)
    print()
    
    # 获取最新信号文件
    signal_file = get_latest_signal_file()
    if not signal_file:
        print("❌ 未找到信号文件")
        return
    
    print(f"📄 找到信号文件: {signal_file.name}")
    
    # 解析信号
    data = parse_signal_file(signal_file)
    if not data['signals']:
        print("❌ 信号文件中未找到信号")
        return
    
    print(f"✓ 解析到 {len(data['signals'])} 个信号")
    print(f"✓ 信号生成时间: {data['signal_time']}")
    print()
    
    # 获取当前价格
    current_price = get_current_price(data['symbol'])
    if not current_price:
        print(f"❌ 无法获取{data['symbol']}当前价格")
        return
    
    print(f"✓ {data['symbol']}当前价格: ${current_price:,.2f}")
    print()
    
    # 获取价格历史
    if data['signal_time']:
        end_time = datetime.now()
        price_history = get_price_history(data['symbol'], data['signal_time'], end_time, '1h')
        print(f"✓ 获取到 {len(price_history)} 条价格历史数据")
    else:
        price_history = []
    print()
    
    # 评估每个信号
    evaluations = []
    for signal in data['signals']:
        eval_data = evaluate_signal(signal, current_price, price_history, data['signal_time'])
        evaluations.append(eval_data)
    
    # 生成报告
    report = generate_report(data, evaluations)
    
    # 保存报告
    report_file = Path(__file__).parent.parent / "trading_signals" / f"signal_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    report_file.write_text(report, encoding='utf-8')
    
    print("=" * 80)
    print("评估完成")
    print("=" * 80)
    print()
    print(report)
    print()
    print(f"报告已保存: {report_file}")
    print()


if __name__ == '__main__':
    main()

