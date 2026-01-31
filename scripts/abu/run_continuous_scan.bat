@echo off
set SCRIPT_DIR=%~dp0
pushd "%SCRIPT_DIR%\..\.."
REM Continuous PA Scanner - Windows Batch Script
REM Run this to start continuous scanning

echo ========================================
echo Qingniao Continuous PA Scanner
echo ========================================
echo.

echo Running health check...
python scripts\health_check.py
if errorlevel 1 (
  echo Health check failed. Please fix issues and rerun.
  pause
  exit /b 1
)

REM Default: 15m timeframe, 20 coins, 3 hours, every 15 minutes
python scripts\continuous_scan.py --timeframe 15m --top 20 --interval 15 --duration 180 --exchange gate

pause
