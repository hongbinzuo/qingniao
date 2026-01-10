#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prepare-for-sleep (LIGHT):
- Do NOT execute heavy/background jobs after GN.
- Persist a status snapshot and write a TODO list for resuming after wake.

Outputs:
- trading_signals/.sleep_snapshots/snapshot_YYYYMMDD_HHMMSS.json/.txt
- trading_signals/.todos/gn_todo_YYYYMMDD_HHMMSS.json
"""
import subprocess, sys, json, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
        sys.stderr.reconfigure(encoding='utf-8', errors='ignore')
    except Exception:
        pass

def _snapshot_status() -> dict:
    """Collect minimal status (latest signal times and counts)."""
    sys.path.insert(0, str(ROOT/'src'))
    from db_manager_trader import TraderDBManager  # type: ignore
    snap = {"ts": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    for t in ('abu','de'):
        try:
            db = TraderDBManager(t)
            con = db._get_connection()
            last = con.execute("SELECT MAX(signal_time) FROM trading_signals").fetchone()[0]
            cnt = con.execute("SELECT COUNT(*) FROM trading_signals").fetchone()[0]
            snap[t] = {"latest": last, "count": int(cnt)}
            if t == 'de':
                last_w = con.execute("SELECT MAX(signal_time) FROM trading_signals WHERE system_name='de_watcher'").fetchone()[0]
                snap['de_watcher'] = {"latest": last_w}
            db.close()
        except Exception as e:
            snap[t] = {"error": str(e)}
    return snap

def main():
    # Only snapshot + write TODOs; don't execute heavy jobs.
    ss_dir = ROOT/'trading_signals'/'/.sleep_snapshots'.replace('//','/')
    td_dir = ROOT/'trading_signals'/'/.todos'.replace('//','/')
    ss_dir = Path(ss_dir); td_dir = Path(td_dir)
    ss_dir.mkdir(parents=True, exist_ok=True)
    td_dir.mkdir(parents=True, exist_ok=True)

    snap = _snapshot_status()
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    (ss_dir/f'snapshot_{ts}.json').write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding='utf-8')
    (ss_dir/f'snapshot_{ts}.txt').write_text(json.dumps(snap, ensure_ascii=False), encoding='utf-8')

    todos = [
        {"task":"start_api", "cmd":"scripts\\start_qingniao_be_api.bat", "port":8090, "status":"pending"},
        {"task":"resume_abu_scan_scheduler", "cmd":"schtasks /Run /TN \"Qingniao-Abu-15m\"", "status":"pending"},
        {"task":"optional_pdf_ingestion", "cmd":"set PDF_IN=<your_pdf> && set PDF_PAGES=1000 && scripts\\abu_upgrade_and_run.bat", "status":"pending"}
    ]
    (td_dir/f'gn_todo_{ts}.json').write_text(json.dumps({"created_at": snap['ts'], "todos": todos}, ensure_ascii=False, indent=2), encoding='utf-8')

    print('Sleep snapshot saved. TODOs queued.')
    
    # 同时更新GM全局状态
    try:
        sys.path.insert(0, str(ROOT / 'scripts'))
        from gm_status import save_status
        save_status()
        print('GM status updated.')
    except Exception as e:
        print(f'Warning: GM status update failed: {e}')
    
    # 确认Git状态并提醒推送
    try:
        import subprocess
        result = subprocess.run(['git', 'status', '--short'], 
                              capture_output=True, text=True, cwd=ROOT)
        if result.stdout.strip():
            print('\n⚠️  有未提交的更改:')
            print(result.stdout)
            print('提示: 运行以下命令提交并推送:')
            print('  git add .')
            print('  git commit -m "更新系统状态和任务"')
            print('  git push')
        else:
            print('✓ Git工作区干净')
    except Exception as e:
        print(f'Warning: Git status check failed: {e}')
    
    print('\nSafe to sleep. 💤')

if __name__ == '__main__':
    main()
