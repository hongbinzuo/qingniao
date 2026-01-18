#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证最近生成的信号质量
检查入场点、止损、止盈的合理性
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

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

from db_manager_trader import TraderDBManager

def validate_signal_quality(signal: Dict) -> Tuple[bool, List[str]]:
    """验证信号质量"""
    issues = []
    
    entry = signal.get('entry_price', 0)
    stop_loss = signal.get('stop_loss', 0)
    tp1 = signal.get('take_profit_1', 0)
    tp2 = signal.get('take_profit_2', 0)
    direction = signal.get('signal_type', '').lower()
    
    # 基本检查
    if entry <= 0 or stop_loss <= 0 or tp1 <= 0:
        issues.append("价格无效（<=0）")
        return False, issues
    
    # 检查方向逻辑
    if direction == 'long':
        if stop_loss >= entry:
            issues.append(f"LONG信号止损应该在入场下方（SL={stop_loss:.4f} >= Entry={entry:.4f}）")
        if tp1 <= entry:
            issues.append(f"LONG信号止盈应该在入场上方（TP1={tp1:.4f} <= Entry={entry:.4f}）")
    elif direction == 'short':
        if stop_loss <= entry:
            issues.append(f"SHORT信号止损应该在入场上方（SL={stop_loss:.4f} <= Entry={entry:.4f}）")
        if tp1 >= entry:
            issues.append(f"SHORT信号止盈应该在入场下方（TP1={tp1:.4f} >= Entry={entry:.4f}）")
    
    # 检查价格是否相同
    if abs(entry - stop_loss) < 0.0001:
        issues.append("入场和止损价格相同")
    if abs(entry - tp1) < 0.0001:
        issues.append("入场和止盈1价格相同")
    if abs(stop_loss - tp1) < 0.0001:
        issues.append("止损和止盈1价格相同")
    
    # 计算风险回报比
    if direction == 'long':
        risk = entry - stop_loss
        reward1 = tp1 - entry
        reward2 = tp2 - entry if tp2 > 0 else 0
    else:  # short
        risk = stop_loss - entry
        reward1 = entry - tp1
        reward2 = entry - tp2 if tp2 > 0 else 0
    
    if risk > 0:
        rr1 = reward1 / risk if reward1 > 0 else 0
        rr2 = reward2 / risk if reward2 > 0 else 0
        
        # 检查RR是否合理
        if rr1 < 1.0:
            issues.append(f"风险回报比过低（RR={rr1:.2f}:1）")
        if rr1 > 10.0:
            issues.append(f"风险回报比过高（RR={rr1:.2f}:1），可能不合理")
        
        # 检查止损距离
        stop_loss_pct = (risk / entry) * 100 if entry > 0 else 0
        if stop_loss_pct < 0.1:
            issues.append(f"止损距离过小（{stop_loss_pct:.2f}%），容易被扫")
        if stop_loss_pct > 5.0:
            issues.append(f"止损距离过大（{stop_loss_pct:.2f}%），风险较高")
    
    return len(issues) == 0, issues

def check_pattern_source(signal: Dict) -> Tuple[str, List[str]]:
    """检查模式来源"""
    issues = []
    
    entry_model = signal.get('entry_model', '')
    notes = signal.get('notes', '')
    
    # 已知的问题页面
    PROBLEM_PAGES = {
        222: "仓位管理教学页面（不应该生成信号）",
        273: "概念教学页面（H1/H2/H3讲解，可能不适合直接生成信号）"
    }
    
    pattern_source = "未知"
    
    # 从entry_model提取页面信息
    import re
    page_match = re.search(r'page\s+(\d+)', entry_model, re.IGNORECASE)
    if page_match:
        page_num = int(page_match.group(1))
        pattern_source = f"第{page_num}页"
        
        if page_num in PROBLEM_PAGES:
            issues.append(PROBLEM_PAGES[page_num])
    
    return pattern_source, issues

def main():
    db = TraderDBManager('abu')
    conn = db._get_connection()
    
    print("=" * 80)
    print("验证最近生成的信号质量")
    print("=" * 80)
    print()
    
    # 获取最近1小时内的信号
    one_hour_ago = (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
    
    query = """
        SELECT id, signal_time, timeframe, symbol, signal_type, 
               entry_price, stop_loss, take_profit_1, take_profit_2, 
               entry_model, score, notes
        FROM trading_signals
        WHERE signal_time >= ?
        ORDER BY signal_time DESC, score DESC
    """
    
    signals = conn.execute(query, [one_hour_ago]).fetchall()
    
    if not signals:
        print("⚠️  最近1小时内没有新信号")
        db.close()
        return
    
    print(f"找到 {len(signals)} 个最近1小时内的信号")
    print()
    
    # 按时间框架分组
    signals_by_tf = {}
    for sig in signals:
        tf = sig[2]  # timeframe
        if tf not in signals_by_tf:
            signals_by_tf[tf] = []
        signals_by_tf[tf].append(sig)
    
    # 验证每个信号
    total_issues = 0
    problem_signals = []
    
    for timeframe in ['5m', '15m', '1h', '4h']:
        if timeframe not in signals_by_tf:
            continue
        
        print("=" * 80)
        print(f"时间框架: {timeframe} ({len(signals_by_tf[timeframe])} 个信号)")
        print("=" * 80)
        print()
        
        for sig in signals_by_tf[timeframe]:
            signal_dict = {
                'id': sig[0],
                'signal_time': sig[1],
                'timeframe': sig[2],
                'symbol': sig[3],
                'signal_type': sig[4],
                'entry_price': sig[5],
                'stop_loss': sig[6],
                'take_profit_1': sig[7],
                'take_profit_2': sig[8],
                'entry_model': sig[9],
                'score': sig[10],
                'notes': sig[11]
            }
            
            # 验证信号质量
            is_valid, quality_issues = validate_signal_quality(signal_dict)
            
            # 检查模式来源
            pattern_source, source_issues = check_pattern_source(signal_dict)
            
            all_issues = quality_issues + source_issues
            
            if all_issues:
                total_issues += len(all_issues)
                problem_signals.append((signal_dict, all_issues))
                
                direction_cn = "做多" if signal_dict['signal_type'].lower() == 'long' else "做空"
                print(f"⚠️  {signal_dict['symbol']} {direction_cn} (ID: {signal_dict['id']})")
                print(f"   入场: {signal_dict['entry_price']:.4f} | 止损: {signal_dict['stop_loss']:.4f} | 止盈1: {signal_dict['take_profit_1']:.4f}")
                print(f"   模式: {pattern_source} | 评分: {signal_dict['score']:.2f}")
                print(f"   问题:")
                for issue in all_issues:
                    print(f"     - {issue}")
                print()
    
    # 总结
    print("=" * 80)
    print("验证总结")
    print("=" * 80)
    print(f"总信号数: {len(signals)}")
    print(f"有问题信号数: {len(problem_signals)}")
    print(f"总问题数: {total_issues}")
    print()
    
    if problem_signals:
        print("有问题信号列表:")
        for sig_dict, issues in problem_signals:
            direction_cn = "做多" if sig_dict['signal_type'].lower() == 'long' else "做空"
            print(f"  - {sig_dict['symbol']} {direction_cn} (ID: {sig_dict['id']}, 评分: {sig_dict['score']:.2f})")
            print(f"    问题: {', '.join(issues[:2])}")  # 只显示前2个问题
    else:
        print("✓ 所有信号验证通过")
    
    db.close()

if __name__ == '__main__':
    main()



