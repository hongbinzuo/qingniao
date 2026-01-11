#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查模式库详细信息"""
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    
    db = TraderDBManager('abu')
    conn = db._get_connection()
    
    # 查看几个样本
    print('=== 模式样本（前5个）===\n', flush=True)
    result = conn.execute('''
        SELECT id, pattern_name, pattern_type, gemini_annotation_json, context_text
        FROM pattern_library 
        LIMIT 5
    ''').fetchall()
    
    for id_val, name, ptype, gemini_json, context in result:
        print(f'ID: {id_val}', flush=True)
        print(f'  名称: {name}', flush=True)
        print(f'  类型: {ptype}', flush=True)
        
        if gemini_json:
            try:
                gemini = json.loads(gemini_json)
                print(f'  Gemini标注: {json.dumps(gemini, ensure_ascii=False, indent=2)[:200]}...', flush=True)
            except Exception:
                print(f'  Gemini标注: (解析失败)', flush=True)
        else:
            print(f'  Gemini标注: (无)', flush=True)
        
        if context:
            print(f'  上下文: {context[:100]}...', flush=True)
        else:
            print(f'  上下文: (无)', flush=True)
        print('', flush=True)
    
    # 统计
    print('\n=== 统计信息 ===\n', flush=True)
    
    # 有Gemini标注的数量
    gemini_count = conn.execute('''
        SELECT COUNT(*) FROM pattern_library 
        WHERE gemini_annotation_json IS NOT NULL AND gemini_annotation_json != ''
    ''').fetchone()[0]
    
    print(f'有Gemini标注的模式: {gemini_count}/{conn.execute("SELECT COUNT(*) FROM pattern_library").fetchone()[0]}', flush=True)
    
    # 模式名称样本
    print('\n模式名称样本:', flush=True)
    names = conn.execute('SELECT DISTINCT pattern_name FROM pattern_library LIMIT 10').fetchall()
    for (name,) in names:
        print(f'  - {name}', flush=True)
    
    db.close()

if __name__ == '__main__':
    main()

