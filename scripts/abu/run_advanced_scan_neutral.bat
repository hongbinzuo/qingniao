@echo off
set SCRIPT_DIR=%~dp0
pushd "%SCRIPT_DIR%\..\.."
REM Advanced PA Scanner - Neutral Mode Only
REM Balanced approach - recommended for most users

echo ========================================
echo Advanced PA Scanner - NEUTRAL MODE
echo ========================================
echo.
echo Configuration:
echo - Timeframes: 5m, 15m, 1h
echo - Top 20 coins by market cap
echo - Signal mode: Neutral (balanced)
echo - Audit reports every 4 hours
echo - Duration: 6 hours
echo - Scan interval: 15 minutes
echo.

echo Running health check...
python scripts\health_check.py
if errorlevel 1 (
  echo Health check failed. Please fix issues and rerun.
  pause
  exit /b 1
)

python scripts\advanced_continuous_scan.py --top 20 --interval 15 --duration 360 --mode neutral --audit-interval 240

pause
