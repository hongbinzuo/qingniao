@echo off
set SCRIPT_DIR=%~dp0
pushd "%SCRIPT_DIR%\..\.."
REM View Recent Trading Signals - Windows Batch Script

echo ========================================
echo View Recent Trading Signals
echo ========================================
echo.

REM Show signals from last 24 hours
python scripts\view_recent_signals.py --hours 24 --limit 20

pause
