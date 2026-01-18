#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查看 llava 图片模式识别结果（从数据库）
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
from detailed_logger import get_detailed_logger

def main():
    logger = get_detailed_logger('view_llava_database_results')
    logger.log_startup()
    
    print(f"\n{'='*80}")
    print(f"📊 llava 图片模式识别结果（数据库）")
    print(f"{'='*80}\n")
    
    try:
        db = TraderDBManager('abu')
        conn = db._get_connection()
        
        # 1. 统计模式类型分布
        logger.info("统计模式类型分布")
        pattern_stats = conn.execute('''
            SELECT pattern_type, COUNT(*) as cnt 
            FROM pattern_library 
            GROUP BY pattern_type 
            ORDER BY cnt DESC
        ''').fetchall()
        
        print("模式类型分布:")
        total = 0
        for ptype, cnt in pattern_stats:
            ptype_display = ptype if ptype else '(null)'
            print(f"  {ptype_display}: {cnt}")
            total += cnt
        print(f"  总计: {total}\n")
        
        # 2. 查看已分类的记录（非 other 类型）
        logger.info("查看已分类记录")
        classified = conn.execute('''
            SELECT id, pattern_name, pattern_type, source_page, 
                   timeframe_hint, direction, key_features, confidence,
                   image_path, created_at
            FROM pattern_library 
            WHERE pattern_type IS NOT NULL 
              AND pattern_type != 'other'
              AND pattern_type != ''
            ORDER BY id
            LIMIT 20
        ''').fetchall()
        
        print(f"已分类记录数: {len(classified)} (显示前20条)\n")
        
        if classified:
            print("已分类记录示例:")
            for i, (pid, name, ptype, page, tf, direction, features, conf, img_path, created) in enumerate(classified[:10], 1):
                print(f"\n{i}. ID={pid}, 类型={ptype}, 页面={page}")
                print(f"   名称: {name[:50] if name else 'N/A'}")
                if tf:
                    print(f"   时间周期: {tf}")
                if direction:
                    print(f"   方向: {direction}")
                if features:
                    print(f"   特征: {features[:100]}...")
                if conf:
                    print(f"   置信度: {conf}")
                if img_path:
                    print(f"   图片: {Path(img_path).name}")
                print(f"   创建时间: {created}")
        
        # 3. 检查是否有 llava 相关的字段或注释
        logger.info("检查字段信息")
        columns = conn.execute("PRAGMA table_info(pattern_library)").fetchall()
        print(f"\n表结构字段:")
        llava_fields = []
        for col in columns:
            col_name = col[1]
            print(f"  - {col_name}")
            if 'llava' in col_name.lower():
                llava_fields.append(col_name)
        
        if llava_fields:
            print(f"\n找到 llava 相关字段: {llava_fields}")
        else:
            print(f"\n未找到专门的 llava 字段（可能使用 pattern_type 等通用字段）")
        
        # 4. 查看最近更新的记录
        logger.info("查看最近更新的记录")
        recent = conn.execute('''
            SELECT id, pattern_name, pattern_type, created_at, updated_at
            FROM pattern_library 
            WHERE updated_at IS NOT NULL
            ORDER BY updated_at DESC
            LIMIT 10
        ''').fetchall()
        
        if recent:
            print(f"\n最近更新的记录 (前10条):")
            for pid, name, ptype, created, updated in recent:
                print(f"  ID={pid}, 类型={ptype}, 更新={updated}")
        else:
            print(f"\n未找到有更新时间的记录")
        
        # 5. 统计各类型的详细信息
        logger.info("统计各类型详细信息")
        print(f"\n各类型详细统计:")
        for ptype, cnt in pattern_stats[:10]:  # 显示前10个类型
            if not ptype or ptype == 'other':
                continue
            
            samples = conn.execute('''
                SELECT id, pattern_name, source_page, confidence
                FROM pattern_library 
                WHERE pattern_type = ?
                LIMIT 3
            ''', (ptype,)).fetchall()
            
            print(f"\n  {ptype} ({cnt} 条):")
            for sid, sname, spage, sconf in samples:
                print(f"    - ID={sid}, 页面={spage}, 名称={sname[:40] if sname else 'N/A'}")
                if sconf:
                    print(f"      置信度: {sconf}")
        
        db.close()
        
        print(f"\n{'='*80}")
        print(f"✅ 检查完成")
        print(f"{'='*80}\n")
        
    except Exception as e:
        logger.error("检查数据库失败", error=e)
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    logger.log_shutdown(exit_code=0)
    return 0

if __name__ == '__main__':
    sys.exit(main())



