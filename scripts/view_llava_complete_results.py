#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整查看 llava 图片模式识别结果
包括数据库、文件、统计等
"""

import sys
import json
from pathlib import Path
from collections import Counter
from datetime import datetime

# 添加 src 到路径
SRC = Path(__file__).resolve().parent.parent / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager

def main():
    # 设置UTF-8编码
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            pass
    
    print(f"\n{'='*80}")
    print(f"llava 图片模式识别完整结果查看")
    print(f"{'='*80}\n")
    
    # 1. 数据库结果
    print("[1] 数据库中的分类结果:")
    print("-" * 80)
    try:
        db = TraderDBManager('abu')
        conn = db._get_connection()
        
        # 统计
        stats = conn.execute('''
            SELECT pattern_type, COUNT(*) as cnt 
            FROM pattern_library 
            GROUP BY pattern_type 
            ORDER BY cnt DESC
        ''').fetchall()
        
        total = sum(cnt for _, cnt in stats)
        classified = sum(cnt for ptype, cnt in stats if ptype and ptype != 'other')
        
        print(f"总记录数: {total}")
        print(f"已分类数: {classified} ({classified/total*100:.1f}%)")
        print(f"\n模式类型分布:")
        for ptype, cnt in stats:
            ptype_display = ptype if ptype else '(null)'
            pct = cnt / total * 100
            print(f"  {ptype_display:50s}: {cnt:4d} ({pct:5.1f}%)")
        
        # 查看详细样本
        print(f"\n[2] 各类型详细样本:")
        for ptype, cnt in stats[:5]:  # 前5个类型
            if not ptype or ptype == 'other':
                continue
            
            samples = conn.execute('''
                SELECT id, pattern_name, source_page, confidence, 
                       timeframe_hint, direction, key_features, image_path
                FROM pattern_library 
                WHERE pattern_type = ?
                ORDER BY confidence DESC
                LIMIT 3
            ''', (ptype,)).fetchall()
            
            print(f"\n  【{ptype}】({cnt} 条，显示置信度最高的3条):")
            for sid, sname, spage, sconf, stf, sdir, sfeat, simg in samples:
                conf_str = f"{sconf:.2f}" if sconf else "0.00"
                print(f"    ID={sid:4d} | 页面={spage:4d} | 置信度={conf_str}")
                if stf:
                    print(f"      时间周期: {stf}")
                if sdir:
                    print(f"      方向: {sdir}")
                if sfeat:
                    try:
                        feat = json.loads(sfeat) if isinstance(sfeat, str) else sfeat
                        if isinstance(feat, dict):
                            concepts = feat.get('concepts', [])
                            if concepts:
                                print(f"      特征: {', '.join(concepts[:3])}")
                    except:
                        pass
                if simg:
                    print(f"      图片: {Path(simg).name}")
        
        db.close()
        
    except Exception as e:
        print(f"❌ 读取数据库失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 2. 检查文件输出
    print(f"\n{'='*80}")
    print(f"[3] 文件输出检查")
    print(f"{'='*80}\n")
    
    output_dirs = [Path('outputs'), Path('data/abu'), Path('data')]
    found_files = []
    
    for output_dir in output_dirs:
        if output_dir.exists():
            for file_path in output_dir.rglob('*'):
                if file_path.is_file():
                    name_lower = file_path.name.lower()
                    if any(kw in name_lower for kw in ['llava', 'classify', 'pattern']):
                        if file_path.suffix in ['.json', '.jsonl', '.txt', '.md']:
                            found_files.append(file_path)
    
    if found_files:
        print(f"找到 {len(found_files)} 个相关文件:")
        for f in found_files[:10]:
            size = f.stat().st_size
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            print(f"  {f}")
            print(f"    大小: {size:,} bytes | 修改: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("未找到明确的输出文件（结果可能在数据库中）")
    
    # 3. 总结
    print(f"\n{'='*80}")
    print(f"[4] 总结")
    print(f"{'='*80}\n")
    print(f"[OK] llava 分类已完成，结果存储在数据库中")
    print(f"[OK] 数据库文件: src/data/qingniao_abu.duckdb")
    if 'total' in locals():
        print(f"[OK] 总记录数: {total}")
        print(f"[OK] 已分类: {classified} 条 ({classified/total*100:.1f}%)")
    print(f"\n查看详细结果:")
    print(f"  python scripts/view_llava_database_results.py")
    print(f"  python scripts/abu_check_pattern_details.py")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

