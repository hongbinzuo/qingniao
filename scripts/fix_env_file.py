#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 .env 文件格式
"""

from pathlib import Path

ENV_FILE = Path(__file__).parent.parent / '.env'

print("修复 .env 文件...")
print()

# 读取当前内容
with open(ENV_FILE, 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

print("当前 .env 内容:")
print("-" * 60)
print(content[:500])  # 只显示前500字符
print("-" * 60)
print()

# 查找需要的配置项
required_configs = {
    'PG_HOST': '127.0.0.1',
    'PG_PORT': '5432',
    'PG_DATABASE': 'qingniao_abu',
    'PG_USER': 'abu_user',
    'PG_PASSWORD': 'Abu2026!Secure',
    'PG_POOL_MIN_SIZE': '2',
    'PG_POOL_MAX_SIZE': '10'
}

# 解析现有配置
existing_configs = {}
lines = content.split('\n')
clean_lines = []

for line in lines:
    line = line.strip()
    if not line or line.startswith('#'):
        clean_lines.append(line)
        continue
    
    if '=' in line:
        # 分割键值对
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip()
        
        # 检查是否是损坏的行（如 '10PG_POOL_MAX_SIZE=10'）
        if key and not key[0].isalpha() and not key.startswith('_'):
            print(f"[WARN] 跳过损坏的配置行: {line}")
            continue
        
        existing_configs[key] = value
        
        # 如果是 PostgreSQL 配置，跳过（稍后重新添加）
        if key.startswith('PG_'):
            print(f"[INFO] 移除旧的 PostgreSQL 配置: {key}={value}")
            continue
        
        clean_lines.append(line)

# 添加 PostgreSQL 配置
clean_lines.append('')
clean_lines.append('# PostgreSQL 配置')
for key, value in required_configs.items():
    clean_lines.append(f'{key}={value}')

# 写回文件
new_content = '\n'.join(clean_lines)

print("\n修复后的 PostgreSQL 配置:")
print("-" * 60)
for key, value in required_configs.items():
    if 'PASSWORD' in key:
        print(f"{key}=***")
    else:
        print(f"{key}={value}")
print("-" * 60)

# 备份原文件
backup_file = ENV_FILE.with_suffix('.env.bak')
with open(backup_file, 'w', encoding='utf-8') as f:
    f.write(content)
print(f"\n[OK] 原文件已备份到: {backup_file}")

# 写入新内容
with open(ENV_FILE, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"[OK] .env 文件已修复")
print("\n请重启 Abu 系统使配置生效")
