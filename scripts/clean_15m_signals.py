#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理15分钟信号：移除无效、重复和冲突的信号
"""
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from db_manager_trader import TraderDBManager

def is_valid_signal(signal: Dict) -> Tuple[bool, str]:
    """
    验证信号是否有效
    
    Returns:
        (is_valid, error_message)
    """
    entry = signal.get('entry') or signal.get('entry_price')
    stop_loss = signal.get('stop') or signal.get('stop_loss')
    tp1 = signal.get('tp1') or signal.get('take_profit_1')
    direction = signal.get('type') or signal.get('direction', '').lower()
    
    # 检查价格是否相同
    if entry == stop_loss or entry == tp1 or stop_loss == tp1:
        return False, "入场价、止损价或止盈价相同"
    
    # 检查方向逻辑
    if direction == 'long':
        if stop_loss >= entry:
            return False, "LONG信号：止损应该低于入场"
        if tp1 <= entry:
            return False, "LONG信号：止盈1应该高于入场"
    elif direction == 'short':
        if stop_loss <= entry:
            return False, "SHORT信号：止损应该高于入场"
        if tp1 >= entry:
            return False, "SHORT信号：止盈1应该低于入场"
    
    return True, ""


def clean_signals():
    """清理信号"""
    print("=" * 80)
    print("清理15分钟信号")
    print("=" * 80)
    print()
    
    db = TraderDBManager('abu')
    conn = db._get_connection()
    
    # 获取最新的信号时间（15分钟信号）
    latest_time = conn.execute("SELECT MAX(signal_time) FROM trading_signals WHERE timeframe='15m'").fetchone()[0]
    if not latest_time:
        print("❌ 数据库中没有15分钟信号")
        db.close()
        return
    
    print(f"📅 最新信号时间: {latest_time}")
    print()
    
    # 获取所有15分钟信号
    rows = conn.execute("""
        SELECT id, symbol, signal_type, entry_price, stop_loss, take_profit_1, take_profit_2,
               entry_model, strength, risk_reward_ratio, COALESCE(score,0), COALESCE(notes,''),
               timeframe
        FROM trading_signals
        WHERE signal_time=? AND timeframe='15m'
        ORDER BY COALESCE(score,0) DESC, id DESC
    """, [latest_time]).fetchall()
    
    signals = []
    for r in rows:
        signals.append({
            'id': r[0],
            'symbol': r[1],
            'type': r[2],
            'entry': r[3],
            'stop': r[4],
            'tp1': r[5],
            'tp2': r[6],
            'model': r[7],
            'strength': r[8],
            'rr': r[9],
            'score': r[10],
            'reason': r[11],
            'timeframe': r[12]
        })
    
    print(f"📊 原始信号数: {len(signals)}")
    print()
    
    # 1. 验证信号有效性
    valid_signals = []
    invalid_ids = []
    
    print("=" * 80)
    print("验证信号有效性")
    print("=" * 80)
    print()
    
    for sig in signals:
        is_valid, error = is_valid_signal(sig)
        if is_valid:
            valid_signals.append(sig)
        else:
            invalid_ids.append(sig['id'])
            print(f"❌ 无效信号 {sig['id']}: {sig['symbol']} {sig['type'].upper()} - {error}")
            print(f"   入场: {sig['entry']}, 止损: {sig['stop']}, 止盈1: {sig['tp1']}")
    
    print(f"\n有效信号: {len(valid_signals)} 个")
    print(f"无效信号: {len(invalid_ids)} 个")
    print()
    
    # 2. 去除重复信号（保留评分更高的）
    print("=" * 80)
    print("去除重复信号")
    print("=" * 80)
    print()
    
    seen = {}
    duplicate_ids = []
    unique_signals = []
    
    for sig in valid_signals:
        key = (sig['symbol'], sig['type'].lower(), sig['entry'], sig['stop'], sig['tp1'])
        if key in seen:
            # 比较评分，保留更高的
            existing = seen[key]
            if sig['score'] > existing['score']:
                duplicate_ids.append(existing['id'])
                seen[key] = sig
                unique_signals = [s for s in unique_signals if s['id'] != existing['id']]
                unique_signals.append(sig)
                print(f"⚠️  重复信号 {existing['id']} (评分{existing['score']:.2f}) < {sig['id']} (评分{sig['score']:.2f}): {sig['symbol']} {sig['type'].upper()}")
            else:
                duplicate_ids.append(sig['id'])
                print(f"⚠️  重复信号 {sig['id']} (评分{sig['score']:.2f}) < {seen[key]['id']} (评分{seen[key]['score']:.2f}): {sig['symbol']} {sig['type'].upper()}")
        else:
            seen[key] = sig
            unique_signals.append(sig)
    
    print(f"\n去重后信号: {len(unique_signals)} 个")
    print(f"重复信号: {len(duplicate_ids)} 个")
    print()
    
    # 3. 处理多空冲突（保留评分更高的）
    print("=" * 80)
    print("处理多空冲突")
    print("=" * 80)
    print()
    
    symbol_signals = {}
    for sig in unique_signals:
        symbol = sig['symbol']
        if symbol not in symbol_signals:
            symbol_signals[symbol] = []
        symbol_signals[symbol].append(sig)
    
    conflict_ids = []
    final_signals = []
    
    for symbol, sigs in symbol_signals.items():
        if len(sigs) > 1:
            longs = [s for s in sigs if s['type'].lower() == 'long']
            shorts = [s for s in sigs if s['type'].lower() == 'short']
            if longs and shorts:
                # 保留评分更高的
                best_long = max(longs, key=lambda x: x['score']) if longs else None
                best_short = max(shorts, key=lambda x: x['score']) if shorts else None
                
                if best_long and best_short:
                    if best_long['score'] > best_short['score']:
                        conflict_ids.append(best_short['id'])
                        final_signals.append(best_long)
                        print(f"⚠️  多空冲突 {symbol}: 保留LONG (评分{best_long['score']:.2f})，删除SHORT (评分{best_short['score']:.2f})")
                    else:
                        conflict_ids.append(best_long['id'])
                        final_signals.append(best_short)
                        print(f"⚠️  多空冲突 {symbol}: 保留SHORT (评分{best_short['score']:.2f})，删除LONG (评分{best_long['score']:.2f})")
                elif best_long:
                    final_signals.append(best_long)
                elif best_short:
                    final_signals.append(best_short)
            else:
                # 只有多或只有空，都保留
                final_signals.extend(sigs)
        else:
            final_signals.extend(sigs)
    
    print(f"\n最终信号: {len(final_signals)} 个")
    print(f"冲突信号: {len(conflict_ids)} 个")
    print()
    
    # 4. 删除无效、重复和冲突的信号
    all_ids_to_delete = list(set(invalid_ids + duplicate_ids + conflict_ids))
    
    if all_ids_to_delete:
        print("=" * 80)
        print("删除无效、重复和冲突的信号")
        print("=" * 80)
        print()
        print(f"将删除 {len(all_ids_to_delete)} 个信号:")
        for sig_id in all_ids_to_delete:
            sig = next((s for s in signals if s['id'] == sig_id), None)
            if sig:
                print(f"  - ID {sig_id}: {sig['symbol']} {sig['type'].upper()} (评分{sig['score']:.2f})")
        print()
        
        # 删除信号
        placeholders = ','.join(['?' for _ in all_ids_to_delete])
        conn.execute(f"DELETE FROM trading_signals WHERE id IN ({placeholders})", all_ids_to_delete)
        conn.commit()
        print(f"✓ 已删除 {len(all_ids_to_delete)} 个信号")
    else:
        print("✓ 没有需要删除的信号")
    
    print()
    print("=" * 80)
    print("清理完成总结")
    print("=" * 80)
    print(f"原始信号数: {len(signals)}")
    print(f"有效信号: {len(valid_signals)}")
    print(f"去重后信号: {len(unique_signals)}")
    print(f"最终信号: {len(final_signals)}")
    print(f"删除信号: {len(all_ids_to_delete)}")
    
    db.close()
    
    # 5. 重新生成报告文件
    if final_signals:
        print()
        print("=" * 80)
        print("重新生成报告文件")
        print("=" * 80)
        print()
        
        out_file = ROOT / 'trading_signals' / f"ABU_Gemini_15m_top200_clean_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 按评分排序
        final_signals.sort(key=lambda x: x['score'], reverse=True)
        
        # 方向映射
        direction_map = {'long': '做多', 'short': '做空', 'LONG': '做多', 'SHORT': '做空'}
        
        lines = [
            f"# ABU Gemini信号 15M Top200 (已清理)",
            f"",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**清理说明**: 已移除无效、重复和冲突信号",
            f"**原始信号数**: {len(signals)}",
            f"**清理后信号数**: {len(final_signals)}",
            f"**删除信号数**: {len(all_ids_to_delete)}",
            f"",
            "| # | 币种 | 方向 | 入场 | 止损 | 止盈1 | 止盈2 | 相似度 | 评分 | 模式 |",
            "|---|---|:---:|---:|---:|---:|---:|---:|:---:|---|"
        ]
        
        for i, sig in enumerate(final_signals, 1):
            direction = sig['type'].upper()
            direction_cn = direction_map.get(direction, direction)
            pattern_name = sig.get('model', 'Unknown').split('/')[-1] if sig.get('model') else 'Unknown'
            lines.append(
                f"| {i} | {sig['symbol']} | {direction_cn} | "
                f"{sig['entry']:.4f} | {sig['stop']:.4f} | "
                f"{sig['tp1']:.4f} | {sig.get('tp2', 0):.4f} | "
                f"N/A | {sig['score']:.2f} | {pattern_name} |"
            )
        
        out_file.write_text('\n'.join(lines), encoding='utf-8')
        print(f"✓ 已生成清理后的报告: {out_file}")


if __name__ == '__main__':
    clean_signals()

