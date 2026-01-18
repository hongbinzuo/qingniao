@echo off
chcp 65001 >nul
cd /d C:\Users\zuoho\code\qingniao
echo ========================================
echo 自动化回测任务
echo ========================================
echo.
python scripts/auto_backtest_trading_plans.py
echo.
echo ========================================
echo 回测完成
echo ========================================
pause
