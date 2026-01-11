#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
15分钟信号扫描（使用扩展API，90天数据）
"""
import sys
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict

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
    from get_extended_gateio_klines import get_kline_gateio_extended
    EXTENDED_GATEIO_AVAILABLE = True
except ImportError:
    EXTENDED_GATEIO_AVAILABLE = False
    get_kline_gateio_extended = None

try:
    from abu.gemini_pattern_matcher_enhanced import EnhancedGeminiPatternMatcher
    MATCHER_AVAILABLE = True
except ImportError:
    MATCHER_AVAILABLE = False
    EnhancedGeminiPatternMatcher = None

from db_manager_trader import TraderDBManager

TOP_50_SYMBOLS = [
    'BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'AVAX', 'DOGE', 'LINK', 'DOT',
    'MATIC', 'TON', 'TRX', 'ATOM', 'SUI', 'APT', 'ARB', 'OP', 'NEAR', 'PEPE',
    'SEI', 'TIA', 'INJ', 'AAVE', 'UNI', 'RUNE', 'ETC', 'FIL', 'ICP', 'XLM',
    'LDO', 'STX', 'HBAR', 'VET', 'ALGO', 'SAND', 'MANA', 'AXS', 'THETA',
    'FLOW', 'EGLD', 'ZIL', 'ENJ', 'CHZ', 'BAT', 'ZEC', 'XMR', 'DASH', 'WAVES'
]

EXCL = set(['USDT', 'USDC', 'DAI', 'BUSD', 'FDUSD', 'TUSD', 'PYUSD', 'USDE', 'GUSD', 'EURT'])
EXCLUDED_PAGES = {222}  # 第222页是仓位管理教学

def get_klines(symbol: str, timeframe: str, limit: int, exchange: str = 'gate', days: int = None) -> List[Dict]:
    """获取K线数据（优先Gate.io，支持扩展）"""
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
            kl = _get_k_gate(symbol=symbol, timeframe=timeframe, limit=limit)
            if kl:
                return kl
            kl = _get_k_bin(symbol=symbol, timeframe=timeframe, limit=limit)
            return kl or []
        elif exchange == 'binance':
            kl = _get_k_bin(symbol=symbol, timeframe=timeframe, limit=limit)
            if kl:
                return kl
            kl = _get_k_gate(symbol=symbol, timeframe=timeframe, limit=limit)
            return kl or []
        else:
            kl = _get_k_gate(symbol=symbol, timeframe=timeframe, limit=limit)
            if kl:
                return kl
            kl = _get_k_bin(symbol=symbol, timeframe=timeframe, limit=limit)
            return kl or []
    except Exception:
        return []
    return []

def scan_15m_only(coins: int = 50, days: int = 90, top_n: int = 50, 
                  exchange: str = 'gate', min_similarity: float = 0.5,
                  max_matches_per_symbol: int = 5, write_db: bool = True) -> List[Dict]:
    """扫描15分钟时间框架"""
    print("=" * 80)
    print(f"扫描15分钟时间框架 (Top {coins}币种, {days}天跨度, Top {top_n}信号)")
    print("=" * 80)
    print()
    
    if not MATCHER_AVAILABLE or not EnhancedGeminiPatternMatcher:
        print("✗ 错误: 无法导入EnhancedGeminiPatternMatcher模块", file=sys.stderr)
        return []
    
    matcher = EnhancedGeminiPatternMatcher(use_dl=False)
    pattern_count = len(matcher.pattern_library) if hasattr(matcher, 'pattern_library') else 0
    print(f"✓ 模式库已加载: {pattern_count} 个模式")
    print()
    
    symbols = TOP_50_SYMBOLS[:coins]
    all_signals: List[Dict] = []
    processed_count = 0
    
    for symbol in symbols:
        if symbol.upper() in EXCL:
            continue
        
        processed_count += 1
        if processed_count % 10 == 0:
            print(f"[{processed_count}/{len(symbols)}] 扫描 {symbol}...", end=' ', flush=True)
        
        # 获取K线数据（使用扩展API，90天）
        klines = get_klines(symbol, '15m', limit=0, exchange=exchange, days=days)
        
        if not klines or len(klines) < 20:
            if processed_count % 10 == 0:
                print("跳过（K线数据不足）")
            continue
        
        # 构建klines_dict
        klines_dict = {'15m': klines}
        
        # 匹配模式
        try:
            matches = matcher.match_patterns(
                klines_dict,
                min_similarity=min_similarity,
                max_matches=max_matches_per_symbol
            )
        except Exception as e:
            if processed_count % 10 == 0:
                print(f"匹配失败: {e}")
            continue
        
        if not matches:
            if processed_count % 10 == 0:
                print("无匹配")
            continue
        
        # 生成信号
        current_price = klines[-1]['close']
        signals_count = 0
        
        for match in matches:
            try:
                # 检查是否来自排除的页面
                pattern_name = match.get('pattern_name', '')
                page_match = re.search(r'page\s+(\d+)', pattern_name, re.IGNORECASE)
                if page_match:
                    page_num = int(page_match.group(1))
                    if page_num in EXCLUDED_PAGES:
                        continue
                
                signal = matcher.generate_signal_from_match(match, current_price, klines)
                if signal:
                    # 验证信号合理性
                    entry = signal.get('entry_price', 0)
                    stop_loss = signal.get('stop_loss', 0)
                    tp1 = signal.get('take_profit_1', 0)
                    direction = signal.get('direction', '').lower()
                    
                    # 基本验证
                    if entry <= 0 or stop_loss <= 0 or tp1 <= 0:
                        continue
                    
                    # 检查价格是否相同
                    if abs(entry - stop_loss) < 0.0001 or abs(entry - tp1) < 0.0001 or abs(stop_loss - tp1) < 0.0001:
                        continue
                    
                    # 检查方向逻辑
                    if direction == 'long':
                        if stop_loss >= entry or tp1 <= entry:
                            continue
                    elif direction == 'short':
                        if stop_loss <= entry or tp1 >= entry:
                            continue
                    else:
                        continue
                    
                    signal['symbol'] = symbol
                    signal['timeframe'] = '15m'
                    
                    # 计算综合评分
                    similarity = match.get('similarity', 0.5)
                    probability = signal.get('probability', 0.5)
                    base_score = (similarity * 0.7 + probability * 0.3) * 100
                    signal['score'] = base_score
                    
                    all_signals.append(signal)
                    signals_count += 1
            except Exception as e:
                continue
        
        if processed_count % 10 == 0:
            print(f"信号: {signals_count}")
    
    print()
    print(f"总计: {len(all_signals)} 个信号")
    
    # 按评分排序
    all_signals.sort(key=lambda x: x.get('score', 0), reverse=True)
    top_signals = all_signals[:top_n]
    
    # 保存到数据库
    if write_db and top_signals:
        db = TraderDBManager('abu')
        signal_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for sig in top_signals:
            try:
                direction_cn = '做多' if sig.get('direction', '').lower() == 'long' else '做空'
                entry_model = sig.get('pattern_name', sig.get('reason', 'Unknown'))
                
                db.add_trading_signal(
                    signal_time=signal_time,
                    timeframe=sig.get('timeframe', '15m'),
                    symbol=sig.get('symbol'),
                    signal_type=direction_cn,
                    entry_price=sig.get('entry_price'),
                    stop_loss=sig.get('stop_loss'),
                    take_profit_1=sig.get('take_profit_1'),
                    take_profit_2=sig.get('take_profit_2'),
                    entry_model=entry_model,
                    strength='medium',
                    score=sig.get('score', 0),
                    notes=sig.get('reason', '')
                )
            except Exception:
                continue
        
        db.close()
    
    return top_signals

def save_signals_to_file(signals: List[Dict], output_dir: Path = None):
    """保存信号到Markdown文件"""
    if not signals:
        return
    
    if output_dir is None:
        output_dir = ROOT / 'trading_signals'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_file = output_dir / f'ABU_Gemini_15m_top{len(signals)}_{timestamp}.md'
    
    lines = []
    lines.append(f"# ABU Gemini 15分钟信号 (Top {len(signals)})")
    lines.append("")
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"数据跨度: 90天 (使用Gate.io扩展API)")
    lines.append("")
    lines.append("| 序号 | 币种 | 方向 | 入场 | 止损 | 止盈1 | 止盈2 | 评分 | 模式 |")
    lines.append("|------|------|------|------|------|-------|-------|------|------|")
    
    for i, sig in enumerate(signals, 1):
        direction = sig.get('direction', '').lower()
        direction_cn = '做多' if direction == 'long' else '做空'
        pattern_name = sig.get('pattern_name', sig.get('reason', 'Unknown'))
        
        lines.append(
            f"| {i} | {sig.get('symbol', 'N/A')} | {direction_cn} | "
            f"{sig.get('entry_price', 0):.4f} | {sig.get('stop_loss', 0):.4f} | "
            f"{sig.get('take_profit_1', 0):.4f} | {sig.get('take_profit_2', 0):.4f if sig.get('take_profit_2') else 'N/A'} | "
            f"{sig.get('score', 0):.2f} | {pattern_name} |"
        )
    
    out_file.write_text('\n'.join(lines), encoding='utf-8')
    print(f"\n✓ 已生成报告: {out_file}")
    return out_file

def validate_signals(signals: List[Dict]) -> Dict:
    """验证信号质量"""
    if not signals:
        return {'total': 0, 'valid': 0, 'invalid': 0, 'issues': []}
    
    valid_count = 0
    invalid_count = 0
    issues = []
    
    for sig in signals:
        entry = sig.get('entry_price', 0)
        stop_loss = sig.get('stop_loss', 0)
        tp1 = sig.get('take_profit_1', 0)
        direction = sig.get('direction', '').lower()
        
        sig_issues = []
        
        # 基本验证
        if entry <= 0 or stop_loss <= 0 or tp1 <= 0:
            sig_issues.append('价格无效（为零或负数）')
            invalid_count += 1
            issues.append({
                'symbol': sig.get('symbol', 'N/A'),
                'issues': sig_issues
            })
            continue
        
        # 检查价格是否相同
        if abs(entry - stop_loss) < 0.0001:
            sig_issues.append('入场价=止损价')
        if abs(entry - tp1) < 0.0001:
            sig_issues.append('入场价=止盈1价')
        
        # 检查方向逻辑
        if direction == 'long':
            if stop_loss >= entry:
                sig_issues.append('做多：止损>=入场')
            if tp1 <= entry:
                sig_issues.append('做多：止盈1<=入场')
        elif direction == 'short':
            if stop_loss <= entry:
                sig_issues.append('做空：止损<=入场')
            if tp1 >= entry:
                sig_issues.append('做空：止盈1>=入场')
        
        if sig_issues:
            invalid_count += 1
            issues.append({
                'symbol': sig.get('symbol', 'N/A'),
                'issues': sig_issues
            })
        else:
            valid_count += 1
    
    return {
        'total': len(signals),
        'valid': valid_count,
        'invalid': invalid_count,
        'issues': issues
    }

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='15分钟信号扫描（使用扩展API，90天数据）')
    parser.add_argument('--coins', type=int, default=50, help='扫描币种数量（默认50）')
    parser.add_argument('--days', type=int, default=90, help='数据跨度天数（默认90）')
    parser.add_argument('--top', type=int, default=50, help='Top N信号（默认50）')
    parser.add_argument('--exchange', type=str, default='gate', help='交易所（gate/binance，默认gate）')
    parser.add_argument('--write-db', type=int, default=1, help='是否写入数据库（0/1，默认1）')
    parser.add_argument('--min-similarity', type=float, default=0.5, help='最小相似度阈值（0.0-1.0，默认0.5）')
    parser.add_argument('--max-matches-per-symbol', type=int, default=5, help='每个币种最大匹配数（默认5）')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("15分钟信号扫描（扩展API，90天数据）")
    print("=" * 80)
    print(f"扫描币种: {args.coins}")
    print(f"数据跨度: {args.days}天")
    print(f"Top N信号: {args.top}")
    print(f"交易所: {args.exchange}")
    print(f"最小相似度: {args.min_similarity}")
    print()
    
    # 扫描信号
    signals = scan_15m_only(
        coins=args.coins,
        days=args.days,
        top_n=args.top,
        exchange=args.exchange,
        min_similarity=args.min_similarity,
        max_matches_per_symbol=args.max_matches_per_symbol,
        write_db=bool(args.write_db)
    )
    
    if not signals:
        print("未生成任何信号")
        return 0
    
    # 保存到文件
    save_signals_to_file(signals)
    
    # 验证信号
    print()
    print("=" * 80)
    print("信号验证")
    print("=" * 80)
    validation = validate_signals(signals)
    
    print(f"总信号数: {validation['total']}")
    print(f"有效信号: {validation['valid']} ({validation['valid']/validation['total']*100:.1f}%)")
    print(f"无效信号: {validation['invalid']} ({validation['invalid']/validation['total']*100:.1f}%)")
    
    if validation['issues']:
        print()
        print("有问题的信号:")
        for item in validation['issues'][:10]:  # 只显示前10个
            print(f"  {item['symbol']}: {', '.join(item['issues'])}")
        if len(validation['issues']) > 10:
            print(f"  ... 还有{len(validation['issues'])-10}个有问题的信号")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

