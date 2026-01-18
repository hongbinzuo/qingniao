#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重启进程以应用运行/休息机制
"""

import sys
import subprocess
from pathlib import Path

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

def main():
    print("=" * 80)
    print("重启进程以应用运行/休息机制")
    print("=" * 80)
    print()
    
    # 检查当前是否有运行中的进程
    import subprocess
    result = subprocess.run(
        ['powershell', '-NoProfile', '-Command', 
         "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*abu_optimize_speed*' } | Select-Object -ExpandProperty ProcessId"],
        capture_output=True,
        text=True
    )
    
    pids = [pid.strip() for pid in result.stdout.strip().split('\n') if pid.strip().isdigit()]
    
    if pids:
        print(f"发现运行中的进程: {', '.join(pids)}")
        print()
        print("⚠️  注意: 当前进程是旧代码启动的，不包含运行/休息机制")
        print()
        print("选项:")
        print("  1. 立即重启（推荐）- 应用新机制，从断点继续")
        print("  2. 等待自然结束 - 当前进程完成后手动重启")
        print()
        
        choice = input("请选择 (1/2，直接回车默认选择1): ").strip()
        
        if choice == '' or choice == '1':
            print()
            print("正在停止旧进程...")
            for pid in pids:
                try:
                    subprocess.run(['powershell', '-NoProfile', '-Command', f"Stop-Process -Id {pid} -Force"], 
                                 capture_output=True, check=False)
                    print(f"  ✅ 已停止进程 {pid}")
                except Exception as e:
                    print(f"  ⚠️  停止进程 {pid} 失败: {e}")
            
            print()
            print("等待2秒确保进程已停止...")
            import time
            time.sleep(2)
            
            print()
            print("正在启动新进程（包含运行/休息机制）...")
            ROOT = Path(__file__).resolve().parent.parent
            script_path = ROOT / 'scripts' / 'abu_optimize_speed.py'
            
            # 在新窗口启动
            subprocess.Popen(
                ['python', str(script_path)],
                cwd=str(ROOT),
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
            )
            
            print("  ✅ 新进程已启动")
            print()
            print("新进程特性:")
            print("  - 包含运行3小时/休息1小时机制")
            print("  - 自动从断点继续")
            print("  - 达到3小时会自动暂停并休息1小时")
            print()
        else:
            print()
            print("保持当前进程运行，请在完成后手动重启")
    else:
        print("未发现运行中的进程")
        print()
        print("启动新进程（包含运行/休息机制）...")
        ROOT = Path(__file__).resolve().parent.parent
        script_path = ROOT / 'scripts' / 'abu_optimize_speed.py'
        
        subprocess.Popen(
            ['python', str(script_path)],
            cwd=str(ROOT),
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
        )
        
        print("  ✅ 新进程已启动")
    
    print()
    print("=" * 80)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())



