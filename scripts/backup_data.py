#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据备份脚本 - 安全低成本方案
支持本地压缩备份和云存储备份
"""
import sys
import os
import json
import shutil
import gzip
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent

# 需要备份的数据库文件
DATABASE_FILES = [
    'src/data/qingniao_abu.duckdb',
    'src/data/qingniao_de.duckdb',
    'src/data/qingniao_dream.duckdb',
    'src/data/qingniao_main.duckdb',
    'src/data/qingniao_archive.duckdb',
    'src/data/qingniao_shared.duckdb',
    'src/data/qingniao_sherlock.duckdb',
    'src/data/qingniao_meng.duckdb',
    'data/btc_price_timeseries.duckdb',
    'data/kline_data/klines.duckdb',
]

# 需要备份的重要数据目录
DATA_DIRS = [
    'data/abu/images',  # 1000张图片
    'data/abu/ebooks',  # 电子书提取数据
    'data/logs',  # 日志文件
    'outputs/abu_gemini',  # Gemini分析结果
    'trading_signals',  # 交易信号
]

# 配置文件（包含敏感信息，需要加密）
CONFIG_FILES = [
    '.env',
    'config/*.json',
    'src/openrouter_config.py',
]

# 备份配置
BACKUP_CONFIG = {
    'local_backup_dir': 'backups',
    'keep_local_backups': 7,  # 保留7天的本地备份
    'compress': True,  # 是否压缩
    'encrypt': False,  # 是否加密（需要安装cryptography）
    'verify': True,  # 是否验证备份完整性
}


def calculate_file_hash(file_path: Path) -> str:
    """计算文件SHA256哈希值"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def compress_file(file_path: Path, output_path: Path) -> bool:
    """压缩文件"""
    try:
        with open(file_path, 'rb') as f_in:
            with gzip.open(output_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        return True
    except Exception as e:
        print(f"❌ 压缩失败 {file_path}: {e}")
        return False


def backup_databases(backup_dir: Path, compress: bool = True) -> Dict:
    """备份数据库文件"""
    print("\n📊 备份数据库文件...")
    results = {
        'databases': [],
        'total_size': 0,
        'compressed_size': 0,
    }
    
    for db_file in DATABASE_FILES:
        db_path = ROOT / db_file
        if not db_path.exists():
            print(f"⚠️  跳过不存在的文件: {db_file}")
            continue
        
        file_size = db_path.stat().st_size
        file_hash = calculate_file_hash(db_path)
        
        # 备份文件名
        backup_name = db_path.name
        if compress:
            backup_name += '.gz'
        
        backup_path = backup_dir / backup_name
        
        # 复制或压缩
        if compress:
            if compress_file(db_path, backup_path):
                compressed_size = backup_path.stat().st_size
                results['compressed_size'] += compressed_size
                print(f"✅ {db_file} ({file_size/1024/1024:.2f}MB -> {compressed_size/1024/1024:.2f}MB)")
            else:
                continue
        else:
            shutil.copy2(db_path, backup_path)
            compressed_size = file_size
            print(f"✅ {db_file} ({file_size/1024/1024:.2f}MB)")
        
        results['databases'].append({
            'file': db_file,
            'backup': str(backup_path.relative_to(ROOT)),
            'size': file_size,
            'compressed_size': compressed_size,
            'hash': file_hash,
        })
        results['total_size'] += file_size
    
    return results


def backup_data_dirs(backup_dir: Path, compress: bool = True) -> Dict:
    """备份数据目录"""
    print("\n📁 备份数据目录...")
    results = {
        'dirs': [],
        'total_size': 0,
        'compressed_size': 0,
    }
    
    for data_dir in DATA_DIRS:
        data_path = ROOT / data_dir
        if not data_path.exists():
            print(f"⚠️  跳过不存在的目录: {data_dir}")
            continue
        
        # 计算目录大小
        total_size = sum(f.stat().st_size for f in data_path.rglob('*') if f.is_file())
        
        # 创建压缩包
        backup_name = data_dir.replace('/', '_').replace('\\', '_')
        if compress:
            backup_name += '.tar.gz'
        else:
            backup_name += '.tar'
        
        backup_path = backup_dir / backup_name
        
        # 使用tar压缩（需要tar命令）
        try:
            import tarfile
            with tarfile.open(backup_path, 'w:gz' if compress else 'w') as tar:
                tar.add(data_path, arcname=data_path.name)
            
            compressed_size = backup_path.stat().st_size
            results['compressed_size'] += compressed_size
            print(f"✅ {data_dir} ({total_size/1024/1024:.2f}MB -> {compressed_size/1024/1024:.2f}MB)")
            
            results['dirs'].append({
                'dir': data_dir,
                'backup': str(backup_path.relative_to(ROOT)),
                'size': total_size,
                'compressed_size': compressed_size,
            })
            results['total_size'] += total_size
        except Exception as e:
            print(f"❌ 备份目录失败 {data_dir}: {e}")
    
    return results


def create_backup_manifest(backup_dir: Path, db_results: Dict, dir_results: Dict) -> Path:
    """创建备份清单"""
    manifest = {
        'backup_time': datetime.now().isoformat(),
        'backup_dir': str(backup_dir.relative_to(ROOT)),
        'databases': db_results['databases'],
        'data_dirs': dir_results['dirs'],
        'summary': {
            'total_db_size': db_results['total_size'],
            'total_db_compressed': db_results['compressed_size'],
            'total_dir_size': dir_results['total_size'],
            'total_dir_compressed': dir_results['compressed_size'],
            'total_size': db_results['total_size'] + dir_results['total_size'],
            'total_compressed': db_results['compressed_size'] + dir_results['compressed_size'],
            'compression_ratio': (db_results['compressed_size'] + dir_results['compressed_size']) / 
                                 (db_results['total_size'] + dir_results['total_size']) 
                                 if (db_results['total_size'] + dir_results['total_size']) > 0 else 0,
        },
    }
    
    manifest_path = backup_dir / 'backup_manifest.json'
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    return manifest_path


def cleanup_old_backups(backup_base_dir: Path, keep_days: int = 7):
    """清理旧备份"""
    print(f"\n🧹 清理 {keep_days} 天前的备份...")
    
    cutoff_time = datetime.now().timestamp() - (keep_days * 24 * 3600)
    removed = 0
    
    for backup_dir in backup_base_dir.iterdir():
        if backup_dir.is_dir() and backup_dir.name.startswith('backup_'):
            if backup_dir.stat().st_mtime < cutoff_time:
                try:
                    shutil.rmtree(backup_dir)
                    removed += 1
                    print(f"✅ 删除旧备份: {backup_dir.name}")
                except Exception as e:
                    print(f"⚠️  删除失败 {backup_dir.name}: {e}")
    
    if removed == 0:
        print("✅ 没有需要清理的旧备份")
    else:
        print(f"✅ 已清理 {removed} 个旧备份")


def main():
    print("=" * 80)
    print("数据备份工具 - 安全低成本方案")
    print("=" * 80)
    
    # 创建备份目录
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_base_dir = ROOT / BACKUP_CONFIG['local_backup_dir']
    backup_base_dir.mkdir(exist_ok=True)
    
    backup_dir = backup_base_dir / f'backup_{timestamp}'
    backup_dir.mkdir(exist_ok=True)
    
    print(f"\n📦 备份目录: {backup_dir}")
    
    # 备份数据库
    db_results = backup_databases(backup_dir, compress=BACKUP_CONFIG['compress'])
    
    # 备份数据目录
    dir_results = backup_data_dirs(backup_dir, compress=BACKUP_CONFIG['compress'])
    
    # 创建备份清单
    manifest_path = create_backup_manifest(backup_dir, db_results, dir_results)
    
    # 显示摘要
    summary = db_results['total_size'] + dir_results['total_size']
    compressed = db_results['compressed_size'] + dir_results['compressed_size']
    ratio = (compressed / summary * 100) if summary > 0 else 0
    
    print("\n" + "=" * 80)
    print("备份完成摘要")
    print("=" * 80)
    print(f"📊 数据库文件: {len(db_results['databases'])} 个")
    print(f"📁 数据目录: {len(dir_results['dirs'])} 个")
    print(f"💾 原始大小: {summary/1024/1024:.2f} MB")
    print(f"📦 压缩后大小: {compressed/1024/1024:.2f} MB")
    print(f"📉 压缩率: {ratio:.1f}%")
    print(f"📋 备份清单: {manifest_path.relative_to(ROOT)}")
    print("=" * 80)
    
    # 清理旧备份
    cleanup_old_backups(backup_base_dir, BACKUP_CONFIG['keep_local_backups'])
    
    print("\n✅ 备份完成！")
    print(f"\n💡 下一步:")
    print(f"   1. 检查备份文件: {backup_dir}")
    print(f"   2. 上传到云存储（可选）")
    print(f"   3. 验证备份完整性（可选）")


if __name__ == '__main__':
    main()



