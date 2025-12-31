@echo off
chcp 65001 >nul
if not exist trading_signals mkdir trading_signals
set OUTLOG=trading_signals\.falcon.out.log
set ERRLOG=trading_signals\.falcon.err.log
set PIDFILE=trading_signals\.falcon.pid
echo Starting Falcon (Windows)...
powershell -NoProfile -Command "$p = Start-Process -FilePath 'python' -ArgumentList 'scripts\\falcon.py','--daemon' -WindowStyle Hidden -RedirectStandardOutput '%CD%\\%OUTLOG%' -RedirectStandardError '%CD%\\%ERRLOG%' -PassThru; $p.Id | Out-File -Encoding ascii '%CD%\\%PIDFILE%'"
echo Falcon started. PID: 
type %PIDFILE%
echo Stdout: %OUTLOG%
echo Stderr: %ERRLOG%
