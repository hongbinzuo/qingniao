@echo off
REM 启动全自动信号生成与评估系统（后台运行）
REM 每小时生成Top 30币种的5分钟和15分钟信号

echo ========================================
echo 启动全自动信号生成与评估系统
echo ========================================
echo.
echo 配置:
echo   - 生成间隔: 1小时
echo   - 币种数量: Top 30（按市值）
echo   - 时间框架: 5分钟, 15分钟
echo   - 每小时信号数: 60个（30币种 x 2时间框架）
echo.
echo 系统将每小时自动:
echo   1. 生成交易信号
echo   2. 评估信号质量
echo   3. 运行回测
echo   4. 生成总结报告
echo.
echo 输出位置:
echo   - 交易计划: outputs\trading_plans\auto_generated_*.md
echo   - 总结报告: outputs\auto_signal_status\summary_*.md
echo   - 状态文件: outputs\auto_signal_status\current_status.json
echo.
echo ========================================
echo.

REM 切换到脚本目录
cd /d %~dp0\..

REM 启动Python进程（后台运行）
start /B python scripts\auto_signal_generator.py --interval 1.0 --coins 30

echo 系统已启动！
echo.
echo 查看状态: python scripts\show_auto_signal_status.py
echo 查看日志: outputs\logs\auto_signal_generator.log
echo.
echo 按任意键退出...
pause >nul
