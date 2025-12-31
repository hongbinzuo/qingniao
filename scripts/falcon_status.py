#!/usr/bin/env python3
"""
Falcon 状态检查
- 读取 trading_signals/.falcon_state.json
- 检查 PID 是否存活（Windows: tasklist；Linux/WSL: ps -p）
- 显示最近错误与最近生成文件
"""
import json
import os
import sys
import subprocess
from pathlib import Path

STATE_FILE = Path('trading_signals') / '.falcon_state.json'

def is_process_alive(pid: int) -> bool:
    if not pid:
        return False
    try:
        if os.name == 'nt':
            # Windows: tasklist 过滤 PID
            r = subprocess.run(['cmd','/c', f'tasklist /FI "PID eq {pid}"'], capture_output=True, text=True)
            return str(pid) in (r.stdout or '')
        else:
            r = subprocess.run(['bash','-lc', f'ps -p {pid} -o pid='], capture_output=True, text=True)
            return str(pid) in (r.stdout or '')
    except Exception:
        return False

def main():
    if not STATE_FILE.exists():
        print('Falcon: 未检测到状态文件（可能未启动或从未运行）')
        sys.exit(1)
    try:
        state = json.loads(STATE_FILE.read_text(encoding='utf-8'))
    except Exception as e:
        print(f'Falcon: 状态文件损坏: {e}')
        sys.exit(2)
    running = state.get('running', False)
    pid = state.get('pid')
    alive = is_process_alive(pid) if pid else False
    last_run = state.get('last_run')
    ok = state.get('last_ok')
    print(f"Falcon 状态: running={running}, pid={pid}, alive={alive}, last_ok={ok}, last_run={last_run}")

    # 可选字段：最近错误与最近生成的文件
    last_errors = state.get('last_errors')
    last_files = state.get('last_files')
    if last_errors:
        print('最近错误:')
        for e in last_errors:
            print(f'- {e}')
    if last_files:
        print('最近生成文件:')
        for f in last_files:
            print(f'- {f}')

if __name__ == '__main__':
    main()
