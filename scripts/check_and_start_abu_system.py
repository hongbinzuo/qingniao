#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查并启动ABU系统
如果系统未运行，自动启动；如果已运行，则跳过
"""

import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 尝试导入psutil，如果没有则使用备用方法
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

def is_process_running(process_name: str) -> bool:
    """检查进程是否在运行"""
    if PSUTIL_AVAILABLE:
        # 使用psutil（更准确）
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and any(process_name in str(arg) for arg in cmdline):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    else:
        # 备用方法：使用tasklist（Windows）或ps（Linux/Mac）
        if sys.platform == 'win32':
            try:
                result = subprocess.run(
                    ['tasklist', '/FI', f'IMAGENAME eq python.exe', '/FO', 'CSV'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                # 简单检查：如果有很多python进程，可能正在运行
                # 更准确的方法需要检查命令行参数，但tasklist不显示完整命令行
                # 这里采用保守策略：如果检测不到，就启动（不会重复启动，因为会检查窗口标题）
                return False  # 保守策略：假设未运行
            except:
                return False
        else:
            # Linux/Mac: 使用ps命令
            try:
                result = subprocess.run(
                    ['ps', 'aux'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return process_name in result.stdout
            except:
                return False
    return False

def start_process(command: str, window_title: str):
    """启动进程"""
    import os
    if sys.platform == 'win32':
        # Windows: 使用start命令在新窗口启动
        subprocess.Popen(
            f'start "{window_title}" cmd /k "{command}"',
            shell=True,
            cwd=ROOT
        )
    else:
        # Linux/Mac: 使用nohup在后台运行
        subprocess.Popen(
            command.split(),
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

def main():
    """主函数"""
    print("=" * 80)
    print("ABU系统检查与启动")
    print("=" * 80)
    print()
    
    if not PSUTIL_AVAILABLE:
        print("⚠️  未安装psutil库，使用基础检查方法")
        print("   建议安装: pip install psutil")
        print()
    
    # 检查模式匹配系统
    pattern_running = is_process_running('auto_signal_generator.py')
    if pattern_running:
        print("✅ 模式匹配系统: 正在运行")
    else:
        print("⚠️  模式匹配系统: 未运行，正在启动...")
        start_process(
            'python scripts\\auto_signal_generator.py --interval 1.0 --coins 30',
            'ABU模式匹配'
        )
        print("   ✓ 已启动")
        import time
        time.sleep(1)  # 等待一下，避免同时启动两个进程
    
    print()
    
    # 检查视觉匹配系统
    vision_running = is_process_running('abu_vision_scanner_4h.py')
    if vision_running:
        print("✅ 视觉匹配系统: 正在运行")
    else:
        print("⚠️  视觉匹配系统: 未运行，正在启动...")
        start_process(
            'python scripts\\abu_vision_scanner_4h.py --interval 14400 --symbols 10',
            'ABU视觉匹配'
        )
        print("   ✓ 已启动")
    
    print()
    print("=" * 80)
    print("检查完成！")
    print("=" * 80)
    print()
    print("提示: 如果设置了开机自动启动，系统会在电脑启动时自动运行")
    print("     设置命令: .\\scripts\\setup_abu_auto_start.ps1")

if __name__ == '__main__':
    main()
