#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量处理所有Dream的Discord导出文件
自动查找并处理所有包含Dream消息的JSON文件
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

SRC = Path(__file__).resolve().parent.parent / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# 查找所有Discord导出文件
discord_dir = Path(r'C:\Users\zuoho\Downloads\discord-msg')
json_files = list(discord_dir.glob('*.json'))

print(f"找到 {len(json_files)} 个JSON文件")
print("准备处理的文件：")
for f in json_files:
    print(f"  - {f.name} ({f.stat().st_size / 1024 / 1024:.2f} MB)")

# 构建文件路径列表（使用绝对路径）
file_paths = [str(f.resolve()) for f in json_files]
files_arg = ','.join(file_paths)

print(f"\n运行流水线处理 {len(file_paths)} 个文件...")
print("=" * 80)

# 导入并运行主函数
from dream_run_pipeline import main
import sys as _sys

# 模拟命令行参数
class Args:
    def __init__(self):
        self.files = files_arg
        self.exchange = 'bitget'
        self.tf = '15m'
        self.horizon = '288h'
        self.tz = 'Asia/Shanghai'
        self.conflict = 'conservative'

# 临时替换sys.argv
old_argv = _sys.argv
_sys.argv = ['dream_run_pipeline.py', '--files', files_arg, '--exchange', 'bitget', '--tf', '15m', '--horizon', '288h']

try:
    main()
finally:
    _sys.argv = old_argv

