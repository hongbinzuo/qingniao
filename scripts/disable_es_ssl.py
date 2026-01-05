# -*- coding: utf-8 -*-
"""
禁用Elasticsearch SSL配置（仅用于开发环境）
"""
import sys
import shutil
from pathlib import Path
from datetime import datetime

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def disable_ssl():
    """禁用Elasticsearch的SSL配置"""
    es_config_file = Path(__file__).parent.parent / "elasticsearch-8.11.0" / "config" / "elasticsearch.yml"
    
    if not es_config_file.exists():
        print(f"❌ 配置文件不存在: {es_config_file}")
        return False
    
    # 备份原配置文件
    backup_file = es_config_file.with_suffix('.yml.backup')
    if not backup_file.exists():
        shutil.copy2(es_config_file, backup_file)
        print(f"✓ 已备份配置文件到: {backup_file}")
    
    # 读取配置文件
    with open(es_config_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修改配置：禁用SSL和Security
    changes = []
    
    # 1. 禁用Security（同时会禁用SSL）
    if 'xpack.security.enabled: true' in content:
        content = content.replace('xpack.security.enabled: true', 'xpack.security.enabled: false')
        changes.append("禁用 xpack.security")
    
    # 2. 禁用HTTP SSL
    if 'xpack.security.http.ssl:' in content:
        # 查找并注释掉整个SSL配置块
        lines = content.split('\n')
        new_lines = []
        skip_ssl_block = False
        for i, line in enumerate(lines):
            if 'xpack.security.http.ssl:' in line:
                skip_ssl_block = True
                new_lines.append('# ' + line + '  # 已禁用（开发环境）')
                changes.append("禁用 xpack.security.http.ssl")
            elif skip_ssl_block:
                if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                    skip_ssl_block = False
                    new_lines.append(line)
                else:
                    new_lines.append('# ' + line)
            else:
                new_lines.append(line)
        content = '\n'.join(new_lines)
    
    # 3. 禁用Transport SSL（可选，但为了完全禁用，也注释掉）
    if 'xpack.security.transport.ssl:' in content:
        lines = content.split('\n')
        new_lines = []
        skip_ssl_block = False
        for i, line in enumerate(lines):
            if 'xpack.security.transport.ssl:' in line:
                skip_ssl_block = True
                new_lines.append('# ' + line + '  # 已禁用（开发环境）')
                changes.append("禁用 xpack.security.transport.ssl")
            elif skip_ssl_block:
                if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                    skip_ssl_block = False
                    new_lines.append(line)
                else:
                    new_lines.append('# ' + line)
            else:
                new_lines.append(line)
        content = '\n'.join(new_lines)
    
    # 写入修改后的配置
    with open(es_config_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    if changes:
        print("\n✅ 配置已修改:")
        for change in changes:
            print(f"   - {change}")
        print(f"\n📝 配置文件: {es_config_file}")
        print("\n⚠️  重要提示:")
        print("   1. Elasticsearch必须重新启动才能生效")
        print("   2. 关闭当前运行的Elasticsearch窗口")
        print("   3. 重新运行: 启动Elasticsearch.bat")
        print("   4. 配置修改后，将使用HTTP（而非HTTPS）连接")
        return True
    else:
        print("⚠️  配置文件中未找到需要修改的SSL设置")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("禁用Elasticsearch SSL配置（开发环境）")
    print("=" * 60)
    print()
    
    result = disable_ssl()
    
    if result:
        print("\n" + "=" * 60)
        print("✅ 完成！请重启Elasticsearch")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ 配置修改失败")
        print("=" * 60)



