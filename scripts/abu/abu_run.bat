@echo off
set SCRIPT_DIR=%~dp0
pushd "%SCRIPT_DIR%\..\.."
REM Abu跑批 - 快速启动自动信号生成与评估系统
REM 可以在任何会话窗口运行，不依赖当前会话

REM 切换到脚本所在目录（项目根目录）
cd /d "%SCRIPT_DIR%\..\.."

echo ========================================
echo Abu跑批 - 自动信号生成系统
echo ========================================
echo.
echo 配置:
echo   - 生成间隔: 1小时
echo   - 币种数量: Top 30（按市值）
echo   - 时间框架: 5分钟, 15分钟
echo.
echo 系统将每小时自动生成信号并评估
echo 按 Ctrl+C 可停止
echo.
echo ========================================
echo.

python scripts\auto_signal_generator.py --interval 1.0 --coins 30

pause
