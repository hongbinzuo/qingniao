#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
显示自动信号生成系统状态
"""

import sys
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
STATUS_DIR = ROOT / 'outputs' / 'auto_signal_status'

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

def show_status():
    """显示当前状态"""
    status_file = STATUS_DIR / 'current_status.json'
    history_file = STATUS_DIR / 'generation_history.json'
    
    print("=" * 80)
    print("📊 全自动信号生成系统状态")
    print("=" * 80)
    print()
    
    # 当前状态
    if status_file.exists():
        try:
            with open(status_file, 'r', encoding='utf-8') as f:
                status = json.load(f)
            
            print("🔄 当前状态:")
            print(f"  运行中: {'是' if status.get('running') else '否'}")
            if status.get('last_cycle_start'):
                last_cycle = datetime.fromisoformat(status['last_cycle_start'])
                print(f"  上次生成: {last_cycle.strftime('%Y-%m-%d %H:%M:%S')}")
            if status.get('next_cycle_at'):
                next_cycle = datetime.fromisoformat(status['next_cycle_at'])
                print(f"  下次生成: {next_cycle.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  总周期数: {status.get('total_cycles', 0)}")
        except Exception as e:
            print(f"  [ERROR] 读取状态失败: {e}")
    else:
        print("  ⚠️  系统未运行或状态文件不存在")
    
    print()
    
    # 历史记录
    if history_file.exists():
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            print(f"📜 生成历史 (最近 {len(history)} 次):")
            print()
            
            for i, cycle in enumerate(history[-10:], 1):  # 显示最近10次
                cycle_start = datetime.fromisoformat(cycle['cycle_start'])
                gen_result = cycle.get('generation', {})
                eval_result = cycle.get('evaluation', {})
                
                print(f"  {i}. {cycle_start.strftime('%Y-%m-%d %H:%M:%S')}")
                if gen_result.get('success'):
                    print(f"     生成: ✅ {gen_result.get('signals_count', 0)} 个信号")
                else:
                    print(f"     生成: ❌ {gen_result.get('error', 'Unknown')}")
                
                if eval_result.get('success'):
                    eval_stats = eval_result.get('evaluation_stats', {})
                    print(f"     评估: ✅ {eval_stats.get('evaluated_signals', 0)} 个信号，平均 {eval_stats.get('average_score', 0):.1f}分")
                else:
                    print(f"     评估: ❌ {eval_result.get('error', 'Unknown')}")
                print()
        except json.JSONDecodeError as e:
            print(f"  [ERROR] JSON解析失败: {e}")
            print(f"  [INFO] 历史记录文件可能已损坏，尝试修复...")
            # 尝试备份损坏的文件
            try:
                import shutil
                from datetime import datetime
                backup_file = history_file.with_suffix(f'.json.bak_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
                shutil.copy2(history_file, backup_file)
                print(f"  [INFO] 已备份损坏文件到: {backup_file.name}")
                print(f"  [INFO] 建议删除损坏文件或手动修复后重试")
            except Exception as backup_error:
                print(f"  [WARN] 备份失败: {backup_error}")
        except Exception as e:
            print(f"  [ERROR] 读取历史失败: {e}")
            print(f"  [INFO] 错误类型: {type(e).__name__}")
    else:
        print("  ⚠️  历史记录文件不存在")
    
    print("=" * 80)

if __name__ == '__main__':
    show_status()
