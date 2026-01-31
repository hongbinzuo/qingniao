@echo off
set SCRIPT_DIR=%~dp0
pushd "%SCRIPT_DIR%\..\.."
REM Abu跑批（单次） - 运行一次信号生成和评估
REM 可以在任何会话窗口运行，不依赖当前会话

REM 切换到脚本所在目录（项目根目录）
cd /d "%SCRIPT_DIR%\..\.."

echo ========================================
echo Abu跑批（单次运行）
echo ========================================
echo.
echo 将生成Top 30币种的5分钟和15分钟信号
echo 然后进行评估和回测
echo.
echo ========================================
echo.

python scripts\auto_signal_generator.py --once --coins 30

pause
