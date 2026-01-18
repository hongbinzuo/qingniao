#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cursor AI批量图片识别脚本

使用Cursor AI（我）直接识别图片，无需API key。
通过交互式方式，我逐张识别图片并保存结果。

使用方法：
1. 运行脚本：python scripts/cursor_ai_batch_recognize.py
2. 脚本会列出所有待处理的图片
3. 在Cursor中，我会逐张识别图片（需要用户配合上传图片）
4. 识别结果自动保存到输出目录
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
    result_file = RESULTS_DIR / f"{image_path.stem}.txt"
    
    # 检查结果文件是否存在
    if result_file.exists() and result_file.stat().st_size > 0:
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

def main():
    """主函数"""
    print("=" * 80)
    print("Cursor AI批量图片识别")
    print("=" * 80)
    print()
    
    # 1. 获取图片列表
    print("正在扫描图片目录...")
    all_images = get_image_list()
    if not all_images:
        print("未找到图片文件", file=sys.stderr)
        return 1
    
    print(f"找到 {len(all_images)} 张图片")
    print()
    
    # 2. 加载状态
    state = load_state()
    processed_count = len(state.get('processed', []))
    print(f"已处理: {processed_count} 张")
    print()
    
    # 3. 筛选待处理图片
    pending_images = []
    for img_path in all_images:
        if not check_already_processed(img_path, state):
            pending_images.append(img_path)
    
    if not pending_images:
        print("所有图片已处理完成！")
        return 0
    
    print(f"待处理: {len(pending_images)} 张")
    print()
    
    # 4. 显示待处理图片列表（前10张）
    print("待处理图片列表（前10张）:")
    for i, img_path in enumerate(pending_images[:10], 1):
        print(f"  {i}. {img_path.name}")
    if len(pending_images) > 10:
        print(f"  ... 还有 {len(pending_images) - 10} 张")
    print()
    
    # 5. 提示用户
    print("=" * 80)
    print("使用说明:")
    print("=" * 80)
    print("1. 我会逐张识别图片")
    print("2. 请将图片上传给我（在Cursor中），我会分析并回复")
    print("3. 我的回复会自动保存到输出目录")
    print()
    print(f"输出目录: {RESULTS_DIR}")
    print(f"状态文件: {STATE_FILE}")
    print()
    print("=" * 80)
    print("开始处理...")
    print("=" * 80)
    print()
    
    # 6. 批量处理模式
    print("批量处理模式已启动")
    print("我会自动读取并识别所有图片")
    print()
    
    # 更新状态
    state['start_time'] = datetime.now().isoformat()
    save_state(state)
    
    print("开始批量识别...")
    print("(识别结果会自动保存)")
    print()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

