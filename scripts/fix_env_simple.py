#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的 .env 文件修复
"""

from pathlib import Path

ENV_FILE = Path(__file__).parent.parent / '.env'

# 读取当前内容
with open(ENV_FILE, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

# 过滤掉损坏的 PostgreSQL 配置
clean_lines = []
pg_section_found = False

for line in lines:
    stripped = line.strip()
    
    # 跳过损坏的配置行
    if stripped and '=' in stripped:
        key = stripped.split('=')[0].strip()
        # 跳过所有 PG_ 开头的配置（稍后重新添加）
        if key.startswith('PG_'):
            continue
        # 跳过损坏的行（键名不以字母开头）
        if key and not key[0].isalpha() and not key.startswith('_'):
            continue
    
    clean_lines.append(line)

# 删除尾部空行
while clean_lines and not clean_lines[-1].strip():
    clean_lines.pop()

# 添加正确的 PostgreSQL 配置
clean_lines.append('\n')
clean_lines.append('# PostgreSQL Configuration\n')
clean_lines.append('PG_HOST=127.0.0.1\n')
clean_lines.append('PG_PORT=5432\n')
clean_lines.append('PG_DATABASE=qingniao_abu\n')
clean_lines.append('PG_USER=abu_user\n')
clean_lines.append('PG_PASSWORD=Abu2026!Secure\n')
clean_lines.append('PG_POOL_MIN_SIZE=2\n')
clean_lines.append('PG_POOL_MAX_SIZE=10\n')

# 备份原文件
backup_file = ENV_FILE.with_suffix('.env.old')
with open(ENV_FILE, 'rb') as f_src:
    with open(backup_file, 'wb') as f_dst:
        f_dst.write(f_src.read())

print(f"[OK] 原文件已备份到: {backup_file.name}")

# 写入修复后的内容
with open(ENV_FILE, 'w', encoding='utf-8') as f:
    f.writelines(clean_lines)

print(f"[OK] .env 文件已修复")
print("\nPostgreSQL 配置:")
print("  PG_HOST=127.0.0.1")
print("  PG_PORT=5432")
print("  PG_DATABASE=qingniao_abu")
print("  PG_USER=abu_user")
print("  PG_PASSWORD=***")
print("  PG_POOL_MIN_SIZE=2")
print("  PG_POOL_MAX_SIZE=10")
