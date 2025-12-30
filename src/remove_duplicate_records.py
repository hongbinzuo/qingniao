#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理数据库中的重复记录
保留最早的记录，删除重复的
"""

import sys
from pathlib import Path

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from db_manager_trader import TraderDBManager

def remove_duplicates():
    """删除重复记录"""
    print("=" * 80)
    print("清理数据库中的重复记录")
    print("=" * 80)
    print()
    
    try:
        db = TraderDBManager('de')
        conn = db._get_connection()
        
        # 检查总记录数
        total_before = conn.execute("SELECT COUNT(*) FROM trader_viewpoints").fetchone()[0]
        print(f"📊 清理前记录数: {total_before} 条")
        print()
        
        # 查找重复记录，保留ID最小的
        duplicates = conn.execute('''
            SELECT content, timestamp, MIN(id) as keep_id, COUNT(*) as count
            FROM trader_viewpoints
            GROUP BY content, timestamp
            HAVING COUNT(*) > 1
        ''').fetchall()
        
        if duplicates:
            print(f"⚠️  发现 {len(duplicates)} 组重复记录")
            print()
            
            deleted_count = 0
            
            for dup in duplicates:
                keep_id = dup[2]
                count = dup[3]
                to_delete = count - 1
                
                # 删除重复记录（保留ID最小的）
                result = conn.execute('''
                    DELETE FROM trader_viewpoints
                    WHERE content = ? AND timestamp = ? AND id != ?
                ''', (dup[0], dup[1], keep_id))
                
                deleted_count += result.rowcount
            
            conn.commit()
            
            total_after = conn.execute("SELECT COUNT(*) FROM trader_viewpoints").fetchone()[0]
            
            print(f"✅ 已删除 {deleted_count} 条重复记录")
            print(f"📊 清理后记录数: {total_after} 条")
            print(f"📊 保留的唯一记录: {total_after} 条")
        else:
            print("✅ 未发现重复记录，无需清理")
        
        print()
        
        # 显示清理后的统计
        categories = conn.execute('''
            SELECT category, COUNT(*) as count
            FROM trader_viewpoints
            GROUP BY category
        ''').fetchall()
        
        print("📊 按分类统计:")
        for cat in categories:
            print(f"  {cat[0]}: {cat[1]} 条")
        
        db.close()
        
    except Exception as e:
        print(f"❌ 清理失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    remove_duplicates()

