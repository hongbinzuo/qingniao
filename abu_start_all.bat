@echo off
chcp 65001 >nul
echo ========================================
echo ABU系统自动启动脚本
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] 启动模式匹配信号生成系统（每小时运行）...
start "ABU模式匹配" cmd /k "python scripts\auto_signal_generator.py --interval 1.0 --coins 30"
timeout /t 2 /nobreak >nul

echo [2/3] 启动视觉匹配系统（每4小时运行，Top 10币种）...
start "ABU视觉匹配" cmd /k "python scripts\abu_vision_scanner_4h.py --interval 14400 --symbols 10"
timeout /t 2 /nobreak >nul

echo [3/3] 启动每日报告生成（每天00:05运行）...
echo 注意：每日报告需要手动运行或设置Windows任务计划程序
echo 运行命令：python scripts\generate_daily_summary_report.py
echo.

echo ========================================
echo ✅ 系统启动完成！
echo ========================================
echo.
echo 运行中的窗口：
echo   - ABU模式匹配：每小时生成信号
echo   - ABU视觉匹配：每4小时进行视觉匹配
echo.
echo 查看状态：
echo   python scripts\show_auto_signal_status.py
echo.
echo 生成每日报告：
echo   python scripts\generate_daily_summary_report.py
echo.
echo 按任意键退出...
pause >nul
