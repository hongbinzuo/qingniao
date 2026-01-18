#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cursor AI自动批量识别脚本

自动读取图片，使用Cursor AI识别，保存结果。
由于Cursor AI可以读取图片，这个脚本会逐张处理。
"""
from __future__ import annotations
import sys
import json
from pathlib import Path
from datetime import datetime

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

def load_state() -> dict:
    """加载处理状态"""
    if STATE_FILE.exists():
        try:
            with STATE_FILE.open('r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {'processed': [], 'failed': []}
    return {'processed': [], 'failed': []}

def save_state(state: dict):
    """保存处理状态"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    state['last_update'] = datetime.now().isoformat()
    try:
        with STATE_FILE.open('w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"保存状态失败: {e}", file=sys.stderr)

def get_image_list() -> list[Path]:
    """获取所有图片"""
    if not IMAGES_DIR.exists():
        return []
    images = sorted(list(IMAGES_DIR.glob('*.png')) + list(IMAGES_DIR.glob('*.jpg')))
    return [img for img in images if img.is_file()]

def is_processed(image_path: Path, state: dict) -> bool:
    """检查是否已处理"""
    image_name = image_path.name
    result_file = RESULTS_DIR / f"{image_path.stem}.txt"
    return (result_file.exists() and result_file.stat().st_size > 0) or image_name in state.get('processed', [])

def main():
    """主函数 - 生成处理清单"""
    print("=" * 80)
    print("Cursor AI自动批量识别 - 处理清单生成器")
    print("=" * 80)
    print()
    
    all_images = get_image_list()
    if not all_images:
        print("未找到图片", file=sys.stderr)
        return 1
    
    state = load_state()
    pending = [img for img in all_images if not is_processed(img, state)]
    
    print(f"总图片数: {len(all_images)}")
    print(f"已处理: {len(state.get('processed', []))}")
    print(f"待处理: {len(pending)}")
    print()
    
    if pending:
        print("待处理图片列表（前20张）:")
        for i, img in enumerate(pending[:20], 1):
            print(f"  {i}. {img.name}")
        if len(pending) > 20:
            print(f"  ... 还有 {len(pending) - 20} 张")
        print()
        print("提示: 我会逐张读取并识别这些图片")
        print(f"结果保存到: {RESULTS_DIR}")
    else:
        print("所有图片已处理完成！")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())



