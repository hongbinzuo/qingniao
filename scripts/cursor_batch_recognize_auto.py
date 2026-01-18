#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cursor AI自动批量识别脚本（改进版）

自动读取图片，使用Cursor AI识别，保存结果。
支持批量处理，断点续传。
"""
from __future__ import annotations
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

ROOT = Path(__file__).resolve().parent.parent
IMAGES_DIR = ROOT / 'data' / 'abu' / 'images'
OUTPUT_DIR = ROOT / 'outputs' / 'cursor_ai_recognition'
RESULTS_DIR = OUTPUT_DIR / 'results'
STATE_FILE = OUTPUT_DIR / 'state.json'

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

def load_state() -> Dict:
    """加载处理状态"""
    if STATE_FILE.exists():
        try:
            with STATE_FILE.open('r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载状态文件失败: {e}", file=sys.stderr)
    return {
        'processed': [],
        'failed': [],
        'start_time': datetime.now().isoformat(),
        'last_update': datetime.now().isoformat()
    }

def save_state(state: Dict):
    """保存处理状态"""
    state['last_update'] = datetime.now().isoformat()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with STATE_FILE.open('w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"保存状态文件失败: {e}", file=sys.stderr)

def get_image_list() -> List[Path]:
    """获取所有待处理的图片列表"""
    if not IMAGES_DIR.exists():
        print(f"错误: 图片目录不存在: {IMAGES_DIR}", file=sys.stderr)
        return []
    
    images = sorted(list(IMAGES_DIR.glob('*.png')) + list(IMAGES_DIR.glob('*.jpg')))
    return [img for img in images if img.is_file()]

def check_already_processed(image_path: Path, state: Dict) -> bool:
    """检查图片是否已处理"""
    image_name = image_path.name
    image_stem = image_path.stem
    
    # 检查结果文件是否存在且非空（支持两种命名格式）
    result_file1 = RESULTS_DIR / f"{image_stem}.txt"
    result_file2 = RESULTS_DIR / f"{image_name}.txt"
    
    # 检查结果文件是否存在且非空
    if result_file1.exists() and result_file1.stat().st_size > 100:  # 至少100字节
        return True
    if result_file2.exists() and result_file2.stat().st_size > 100:  # 至少100字节
        return True
    
    # 检查状态记录
    if image_name in state.get('processed', []):
        return True
    
    return False

def save_result(image_path: Path, result_text: str):
    """保存识别结果"""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    result_file = RESULTS_DIR / f"{image_path.stem}.txt"
    
    try:
        with result_file.open('w', encoding='utf-8') as f:
            f.write(result_text)
        return True
    except Exception as e:
        print(f"保存结果失败 {image_path.name}: {e}", file=sys.stderr)
        return False

def get_pending_images(batch_size: Optional[int] = None) -> List[Path]:
    """获取待处理的图片列表"""
    all_images = get_image_list()
    state = load_state()
    
    pending = []
    for img_path in all_images:
        if not check_already_processed(img_path, state):
            pending.append(img_path)
    
    if batch_size:
        pending = pending[:batch_size]
    
    return pending

def main():
    """主函数 - 生成待处理图片列表"""
    print("=" * 80)
    print("Cursor AI批量识别 - 待处理图片列表生成器")
    print("=" * 80)
    print()
    
    # 获取待处理图片
    pending = get_pending_images()
    
    print(f"总图片数: {len(get_image_list())}")
    print(f"已处理: {len(load_state().get('processed', []))}")
    print(f"待处理: {len(pending)}")
    print()
    
    if not pending:
        print("✅ 所有图片已处理完成！")
        return 0
    
    # 显示待处理图片列表
    print("待处理图片列表（前20张）:")
    for i, img in enumerate(pending[:20], 1):
        print(f"  {i}. {img.name}")
    if len(pending) > 20:
        print(f"  ... 还有 {len(pending) - 20} 张")
    print()
    
    # 保存待处理列表到JSON文件
    pending_list_file = OUTPUT_DIR / 'pending_images.json'
    pending_data = [{'index': i, 'path': str(img), 'name': img.name} 
                    for i, img in enumerate(pending, 1)]
    
    try:
        with pending_list_file.open('w', encoding='utf-8') as f:
            json.dump(pending_data, f, indent=2, ensure_ascii=False)
        print(f"✅ 待处理列表已保存: {pending_list_file}")
        print(f"   共 {len(pending_data)} 张图片")
    except Exception as e:
        print(f"⚠️  保存列表失败: {e}", file=sys.stderr)
    
    print()
    print("=" * 80)
    print("使用说明:")
    print("=" * 80)
    print("1. 我会逐张读取并识别这些图片")
    print("2. 识别结果会自动保存到输出目录")
    print(f"3. 结果保存位置: {RESULTS_DIR}")
    print()
    print("提示: 现在可以开始批量识别了！")
    print("=" * 80)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

