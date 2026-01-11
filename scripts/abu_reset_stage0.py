#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重置阶段0的数据（完全清空，重新开始）
"""

import sys
from pathlib import Path

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent

def main():
    print("重置阶段0数据...")
    print()
    
    files_to_delete = [
        ROOT / 'outputs' / 'abu_gemini_annotations_enhanced.jsonl',
        ROOT / 'outputs' / 'abu_gemini_analysis_state.json',
    ]
    
    dirs_to_delete = [
        ROOT / 'outputs' / '.cache' / 'abu_gemini',
        ROOT / 'outputs' / 'abu_gemini',
    ]
    
    deleted_files = []
    deleted_dirs = []
    
    for file_path in files_to_delete:
        if file_path.exists():
            file_path.unlink()
            deleted_files.append(str(file_path))
            print(f"✅ 已删除: {file_path.name}")
    
    for dir_path in dirs_to_delete:
        if dir_path.exists():
            import shutil
            shutil.rmtree(dir_path)
            deleted_dirs.append(str(dir_path))
            print(f"✅ 已删除目录: {dir_path.name}")
    
    if not deleted_files and not deleted_dirs:
        print("ℹ️  没有找到需要删除的文件或目录（可能已经清空）")
    else:
        print()
        print(f"✅ 重置完成:")
        print(f"   - 删除文件: {len(deleted_files)} 个")
        print(f"   - 删除目录: {len(deleted_dirs)} 个")
    
    print()
    print("现在可以重新开始测试:")
    print("  python scripts/abu_run_stage0_test.py")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

