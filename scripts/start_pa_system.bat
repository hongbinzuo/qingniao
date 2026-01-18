@echo off
setlocal ENABLEDELAYEDEXECUTION

REM Start Qingniao-Abu system: 15m scanner (daemonized via schtasks recommended)
set "PY=py -3"
set "ROOT=%~dp0.."
cd /d "%ROOT%"

echo Running 15m Abu scan once...
%PY% scripts\pa_scan_15m_top10.py --top 10 --exchange binance --write-db 1

echo Tip: schedule this command every 15 minutes via Windows Task Scheduler for continuous updates.
echo Done.
pause
