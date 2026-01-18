#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面验证信号质量
检查所有最近生成的信号，识别问题
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
import re

# 已知的问题页面
PROBLEM_PAGES = {
    222: "仓位管理教学页面（不应该生成信号）",
    273: "概念教学页面（H1/H2/H3讲解，可能不适合直接生成信号）"
}

def validate_signal(signal: Dict) -> Tuple[bool, List[str]]:
    """验证单个信号"""
    issues = []
    
    entry = signal.get('entry_price', 0)
    sl = signal.get('stop_loss', 0)
    tp1 = signal.get('take_profit_1', 0)
    direction = signal.get('signal_type', '').lower()
    
    # 基本检查
    if entry <= 0 or sl <= 0 or tp1 <= 0:
        issues.append("价格无效")
        return False, issues
    
    # 方向逻辑
    if direction == 'long':
        if sl >= entry:
            issues.append(f"LONG: SL({sl:.4f}) >= Entry({entry:.4f})")
        if tp1 <= entry:
            issues.append(f"LONG: TP1({tp1:.4f}) <= Entry({entry:.4f})")
    elif direction == 'short':
        if sl <= entry:
            issues.append(f"SHORT: SL({sl:.4f}) <= Entry({entry:.4f})")
        if tp1 >= entry:
            issues.append(f"SHORT: TP1({tp1:.4f}) >= Entry({entry:.4f})")
    
    # 价格相同
    if abs(entry - sl) < 0.0001:
        issues.append("Entry = SL")
    if abs(entry - tp1) < 0.0001:
        issues.append("Entry = TP1")
    
    # 风险回报比
    if direction == 'long':
        risk = entry - sl
        reward = tp1 - entry
    else:
        risk = sl - entry
        reward = entry - tp1
    
    if risk > 0:
        rr = reward / risk
        if rr < 0.5:
            issues.append(f"RR过低({rr:.2f}:1)")
        if rr > 10:
            issues.append(f"RR过高({rr:.2f}:1)")
        
        sl_pct = (risk / entry) * 100 if entry > 0 else 0
        if sl_pct < 0.1:
            issues.append(f"止损过紧({sl_pct:.2f}%)")
        if sl_pct > 5:
            issues.append(f"止损过宽({sl_pct:.2f}%)")
    
    return len(issues) == 0, issues

def check_pattern_source(entry_model: str) -> Tuple[str, List[str]]:
    """检查模式来源"""
    issues = []
    source = "未知"
    
    page_match = re.search(r'page\s+(\d+)', entry_model, re.IGNORECASE)
    if page_match:
        page_num = int(page_match.group(1))
        source = f"第{page_num}页"
        
        if page_num in PROBLEM_PAGES:
            issues.append(PROBLEM_PAGES[page_num])
    
    return source, issues

def main():
    db = TraderDBManager('abu')
    conn = db._get_connection()
    
    print("=" * 80)
    print("全面验证信号质量")
    print("=" * 80)
    print()
    
    # 获取最近3天的信号
    three_days_ago = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S')
    
    query = """
        SELECT id, signal_time, timeframe, symbol, signal_type, 
               entry_price, stop_loss, take_profit_1, take_profit_2,
               entry_model, score
        FROM trading_signals
        WHERE signal_time >= ?
        ORDER BY signal_time DESC
    """
    
    signals = conn.execute(query, [three_days_ago]).fetchall()
    
    if not signals:
        print("⚠️  最近3天内没有信号")
        db.close()
        return
    
    print(f"找到 {len(signals)} 个最近3天内的信号")
    print()
    
    # 按时间框架分组
    by_tf = {}
    for sig in signals:
        tf = sig[2]
        if tf not in by_tf:
            by_tf[tf] = []
        by_tf[tf].append(sig)
    
    total_issues = 0
    problem_count = 0
    
    for tf in ['5m', '15m', '1h', '4h']:
        if tf not in by_tf:
            continue
        
        print("=" * 80)
        print(f"{tf} 时间框架: {len(by_tf[tf])} 个信号")
        print("=" * 80)
        
        valid_count = 0
        problem_signals = []
        
        for sig in by_tf[tf]:
            sig_dict = {
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
                'score': sig[10]
            }
            
            is_valid, quality_issues = validate_signal(sig_dict)
            pattern_source, source_issues = check_pattern_source(sig_dict['entry_model'])
            
            all_issues = quality_issues + source_issues
            
            if all_issues:
                problem_count += 1
                total_issues += len(all_issues)
                problem_signals.append((sig_dict, all_issues, pattern_source))
            else:
                valid_count += 1
        
        print(f"✓ 有效信号: {valid_count} 个")
        if problem_signals:
            print(f"⚠️  有问题信号: {len(problem_signals)} 个")
            print()
            for sig_dict, issues, source in problem_signals[:5]:  # 只显示前5个
                direction_cn = "做多" if sig_dict['signal_type'].lower() == 'long' else "做空"
                print(f"  {sig_dict['symbol']} {direction_cn} (ID:{sig_dict['id']}, 评分:{sig_dict['score']:.2f})")
                print(f"    Entry:{sig_dict['entry_price']:.4f} SL:{sig_dict['stop_loss']:.4f} TP1:{sig_dict['take_profit_1']:.4f}")
                print(f"    模式: {source}")
                print(f"    问题: {'; '.join(issues[:2])}")
                print()
        
        print()
    
    # 总结
    print("=" * 80)
    print("验证总结")
    print("=" * 80)
    print(f"总信号数: {len(signals)}")
    print(f"有问题信号: {problem_count} 个 ({problem_count/len(signals)*100:.1f}%)")
    print(f"总问题数: {total_issues}")
    print()
    
    # 统计问题页面
    problem_pages_count = {}
    for sig in signals:
        entry_model = sig[9] or ''
        page_match = re.search(r'page\s+(\d+)', entry_model, re.IGNORECASE)
        if page_match:
            page_num = int(page_match.group(1))
            if page_num in PROBLEM_PAGES:
                if page_num not in problem_pages_count:
                    problem_pages_count[page_num] = 0
                problem_pages_count[page_num] += 1
    
    if problem_pages_count:
        print("问题页面信号统计:")
        for page_num, count in problem_pages_count.items():
            print(f"  第{page_num}页: {count} 个信号 - {PROBLEM_PAGES[page_num]}")
        print()
    
    db.close()

if __name__ == '__main__':
    main()



