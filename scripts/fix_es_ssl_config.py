# -*- coding: utf-8 -*-
"""
修复Elasticsearch SSL配置问题
当禁用SSL时，需要确保keystore中没有SSL相关密码
"""
import sys
import shutil
from pathlib import Path

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def fix_es_config():
    """修复Elasticsearch配置"""
    es_dir = Path(__file__).parent.parent / "elasticsearch-8.11.0"
    config_file = es_dir / "config" / "elasticsearch.yml"
    keystore_file = es_dir / "config" / "elasticsearch.keystore"
    
    if not config_file.exists():
        print(f"❌ 配置文件不存在: {config_file}")
        return False
    
    print("=" * 60)
    print("修复Elasticsearch SSL配置")
    print("=" * 60)
    print()
    
    # 1. 备份keystore（如果存在）
    if keystore_file.exists():
        backup_keystore = keystore_file.with_suffix('.keystore.backup')
        if not backup_keystore.exists():
            shutil.copy2(keystore_file, backup_keystore)
            print(f"✓ 已备份keystore到: {backup_keystore}")
        
        # 删除keystore（当security禁用时不需要）
        print("   删除keystore文件（禁用security时不需要）...")
        keystore_file.unlink()
        print("   ✓ keystore已删除")
    
    # 2. 确保配置文件中security完全禁用
    with open(config_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 确保security.enabled是false
    if 'xpack.security.enabled: true' in content:
        content = content.replace('xpack.security.enabled: true', 'xpack.security.enabled: false')
    
    # 也禁用enrollment（当security禁用时也应该禁用）
    if 'xpack.security.enrollment.enabled: true' in content:
        content = content.replace('xpack.security.enrollment.enabled: true', 'xpack.security.enrollment.enabled: false')
    
    # 写入修改后的配置
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✓ 配置文件已更新")
    print()
    print("✅ 修复完成！")
    print()
    print("⚠️  重要提示:")
    print("   1. Elasticsearch必须重新启动才能生效")
    print("   2. 如果Elasticsearch正在运行，请先停止它")
    print("   3. 然后重新启动: 启动Elasticsearch.bat")
    print("   4. 启动后，Elasticsearch将使用HTTP（无SSL）")
    
    return True

if __name__ == '__main__':
    try:
        fix_es_config()
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()


