#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""显示详细处理进度"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

ROOT = Path(__file__).resolve().parent.parent

def main():
    output_file = ROOT / 'outputs' / 'abu_gemini_annotations_enhanced.jsonl'
    state_file = ROOT / 'outputs' / 'abu_gemini_analysis_state.json'
    
    print("=" * 70)
    print("实时处理进度")
    print("=" * 70)
    print()
    
    # 检查输出文件
    if output_file.exists():
        with output_file.open('r', encoding='utf-8') as f:
            lines = sum(1 for line in f if line.strip())
    else:
        lines = 0
    
    # 检查状态文件
    if state_file.exists():
        with state_file.open('r', encoding='utf-8') as f:
            state = json.load(f)
        
        completed = state.get('completed_count', 0)
        failed = state.get('failed_count', 0)
        skipped = state.get('skipped_count', 0)
        total = state.get('total_images', 9000)  # 完整版约9000+张图片
        start_time = state.get('start_time', '')
        last_update = state.get('last_update', '')
        
        pending = total - completed - skipped
        
        # 计算进度
        progress_pct = (completed + skipped) / total * 100 if total > 0 else 0
        
        print(f"📊 总体进度: {progress_pct:.1f}%")
        print(f"   已完成: {completed}/{total} 张")
        print(f"   跳过: {skipped} 张（测试阶段）")
        print(f"   失败: {failed} 张")
        print(f"   待处理: {pending} 张")
        print()
        
        print(f"📁 输出文件: {lines} 条记录")
        print()
        
        if start_time and last_update:
            try:
                start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
                last_dt = datetime.strptime(last_update, '%Y-%m-%d %H:%M:%S')
                elapsed = (last_dt - start_dt).total_seconds()
                
                if completed > skipped:  # 有新处理的图片
                    avg_time_per_img = elapsed / (completed - skipped)
                    remaining_sec = pending * avg_time_per_img
                    remaining_time = timedelta(seconds=int(remaining_sec))
                    
                    print(f"⏱️  处理速度:")
                    print(f"   启动时间: {start_time}")
                    print(f"   最后更新: {last_update}")
                    print(f"   已运行: {elapsed/60:.1f} 分钟")
                    if completed > skipped:
                        print(f"   平均速度: {avg_time_per_img:.1f} 秒/张")
                        print(f"   预计剩余时间: {remaining_time}")
                        eta = datetime.now() + remaining_time
                        print(f"   预计完成时间: {eta.strftime('%Y-%m-%d %H:%M:%S')}")
            except Exception:
                pass
        
        print()
        print(f"💰 成本估算:")
        # 实际成本（修正）：本次运行 $0.6 / 68张 = $0.0088/张
        # 基于实际使用数据：总花费$2.4 - 之前测试$1.8 = $0.6（本次运行）
        cost_per_image = 0.0088
        estimated_cost = (completed - skipped) * cost_per_image
        remaining_cost = pending * cost_per_image
        print(f"   已花费: ${estimated_cost:.2f}")
        print(f"   预计剩余: ${remaining_cost:.2f}")
        print(f"   总预计: ${estimated_cost + remaining_cost:.2f}")
        
    else:
        print(f"状态文件不存在，当前输出: {lines}/1000 ({lines/10:.1f}%)")
    
    print()
    print("=" * 70)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

