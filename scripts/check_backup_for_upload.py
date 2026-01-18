#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查备份文件，准备上传到百度网盘
"""
import sys
import json
from pathlib import Path
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent

def main():
    backup_base = ROOT / 'backups'
    
    if not backup_base.exists():
        print("❌ 备份目录不存在")
        return
    
    # 找到最新备份
    backups = sorted([d for d in backup_base.iterdir() if d.is_dir() and d.name.startswith('backup_')], 
                     key=lambda x: x.stat().st_mtime, reverse=True)
    
    if not backups:
        print("❌ 没有找到备份文件")
        return
    
    latest_backup = backups[0]
    manifest_file = latest_backup / 'backup_manifest.json'
    
    print("=" * 80)
    print("备份文件检查 - 准备上传到百度网盘")
    print("=" * 80)
    print(f"\n📦 最新备份: {latest_backup.name}")
    print(f"📅 备份时间: {datetime.fromtimestamp(latest_backup.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 读取备份清单
    if manifest_file.exists():
        with open(manifest_file, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        summary = manifest.get('summary', {})
        print(f"\n📊 备份统计:")
        print(f"   数据库文件: {len(manifest.get('databases', []))} 个")
        print(f"   数据目录: {len(manifest.get('data_dirs', []))} 个")
        print(f"   原始大小: {summary.get('total_size', 0) / 1024 / 1024:.2f} MB")
        print(f"   压缩后大小: {summary.get('total_compressed', 0) / 1024 / 1024:.2f} MB")
        print(f"   压缩率: {summary.get('compression_ratio', 0) * 100:.1f}%")
    
    # 列出所有文件
    print(f"\n📁 备份文件列表:")
    total_size = 0
    file_count = 0
    
    for file_path in sorted(latest_backup.rglob('*')):
        if file_path.is_file():
            size = file_path.stat().st_size
            total_size += size
            file_count += 1
            rel_path = file_path.relative_to(latest_backup)
            print(f"   {rel_path} ({size/1024/1024:.2f} MB)")
    
    print(f"\n📋 总计: {file_count} 个文件, {total_size/1024/1024:.2f} MB")
    
    # 上传建议
    print("\n" + "=" * 80)
    print("📤 上传到百度网盘步骤:")
    print("=" * 80)
    print(f"\n1. 打开百度网盘（网页版或客户端）")
    print(f"2. 创建文件夹: qingniao_backups/{datetime.now().strftime('%Y-%m-%d')}")
    print(f"3. 上传整个文件夹: {latest_backup.name}")
    print(f"4. 等待上传完成（预计时间: {total_size/1024/1024/5:.0f}-{total_size/1024/1024/2:.0f} 分钟，取决于网速）")
    print(f"\n💡 提示:")
    print(f"   - 使用客户端上传速度更快")
    print(f"   - 可以分批上传（先上传数据库文件，再上传数据目录）")
    print(f"   - 上传完成后验证文件数量是否一致")
    print("=" * 80)
    
    # 生成上传清单
    upload_list_file = latest_backup / 'upload_checklist.txt'
    with open(upload_list_file, 'w', encoding='utf-8') as f:
        f.write("百度网盘上传检查清单\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"备份时间: {datetime.fromtimestamp(latest_backup.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"备份目录: {latest_backup.name}\n\n")
        f.write("文件列表:\n")
        for file_path in sorted(latest_backup.rglob('*')):
            if file_path.is_file():
                rel_path = file_path.relative_to(latest_backup)
                size = file_path.stat().st_size
                f.write(f"  - {rel_path} ({size/1024/1024:.2f} MB)\n")
        f.write(f"\n总计: {file_count} 个文件, {total_size/1024/1024:.2f} MB\n")
        f.write("\n上传后检查:\n")
        f.write("  [ ] 文件数量一致\n")
        f.write("  [ ] 文件大小一致\n")
        f.write("  [ ] 可以正常下载\n")
        f.write("  [ ] backup_manifest.json 已上传\n")
    
    print(f"\n✅ 已生成上传检查清单: {upload_list_file.name}")

if __name__ == '__main__':
    main()



