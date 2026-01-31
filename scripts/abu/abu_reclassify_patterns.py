#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新分类模式库中的模式类型
从上下文文本中提取模式类型信息
"""
from __future__ import annotations
import sys
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager


def infer_pattern_type_from_context(context_text: str, pattern_name: str) -> str:
    """从上下文文本推断模式类型"""
    if not context_text:
        return 'other'
    
    text_lower = context_text.lower()
    
    # 价格行为模式关键词（优先级高）
    price_action_keywords = [
        'inside bar', 'insidebar', '内包',
        'engulfing', '吞没',
        'pin bar', 'pinbar', 'pin bar',
        'key level', 'keylevel', '关键位',
        'support', 'resistance', '支撑', '阻力',
        'breakout', '突破',
        'reversal', '反转',
    ]
    
    # 图表形态关键词
    chart_pattern_keywords = [
        'head and shoulder', 'head shoulder', '头肩',
        'triangle', '三角形',
        'flag', '旗形',
        'wedge', '楔形',
        'double top', 'double bottom', '双顶', '双底',
        'cup and handle', '杯柄',
    ]
    
    # 检查价格行为关键词
    for keyword in price_action_keywords:
        if keyword in text_lower:
            return 'price_action'
    
    # 检查图表形态关键词
    for keyword in chart_pattern_keywords:
        if keyword in text_lower:
            return 'chart_pattern'
    
    return 'other'


def main():
    import argparse
    ap = argparse.ArgumentParser(description='重新分类模式类型')
    ap.add_argument('--dry-run', action='store_true', help='仅显示，不实际更新')
    ap.add_argument('--update-all', action='store_true', help='更新所有模式（默认只更新other类型）')
    args = ap.parse_args()
    
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    
    db = TraderDBManager('abu')
    conn = db._get_connection()
    
    # 查询模式
    if args.update_all:
        query = 'SELECT id, pattern_name, pattern_type, context_text FROM pattern_library'
    else:
        query = "SELECT id, pattern_name, pattern_type, context_text FROM pattern_library WHERE pattern_type = 'other'"
    
    patterns = conn.execute(query).fetchall()
    
    print(f'找到 {len(patterns)} 个模式需要分类\n', flush=True)
    
    stats = {'price_action': 0, 'chart_pattern': 0, 'other': 0, 'unchanged': 0}
    
    for id_val, name, old_type, context in patterns:
        new_type = infer_pattern_type_from_context(context or '', name)
        
        if new_type == old_type:
            stats['unchanged'] += 1
            if not args.dry_run:
                continue
        
        stats[new_type] = stats.get(new_type, 0) + 1
        
        print(f'ID {id_val}: {name[:30]}...', flush=True)
        print(f'  旧类型: {old_type} → 新类型: {new_type}', flush=True)
        
        if not args.dry_run:
            conn.execute(
                'UPDATE pattern_library SET pattern_type = ? WHERE id = ?',
                [new_type, id_val]
            )
    
    if not args.dry_run:
        db.close()
        print(f'\n✓ 更新完成！', flush=True)
    else:
        print(f'\n[DRY RUN] 未实际更新', flush=True)
    
    print(f'\n统计:', flush=True)
    print(f'  price_action: {stats["price_action"]}', flush=True)
    print(f'  chart_pattern: {stats["chart_pattern"]}', flush=True)
    print(f'  other: {stats["other"]}', flush=True)
    print(f'  未变化: {stats["unchanged"]}', flush=True)
    
    if not args.dry_run:
        db.close()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

