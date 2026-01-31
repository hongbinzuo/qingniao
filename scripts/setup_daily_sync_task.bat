@echo off
set SCRIPT_DIR=%~dp0
pushd "%SCRIPT_DIR%\.."
chcp 65001 >nul
echo ========================================
echo BTC价格数据每日同步任务 - 安装脚本
echo ========================================
echo.

REM 检查是否以管理员身份运行
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ 错误: 请以管理员身份运行此脚本
    echo.
    echo 右键点击此文件，选择"以管理员身份运行"
    pause
    exit /b 1
)

echo ✓ 检测到管理员权限
echo.

REM 运行PowerShell脚本
echo 正在配置Windows任务计划程序...
echo.

powershell.exe -ExecutionPolicy Bypass -File "%~dp0setup_daily_price_sync_task.ps1"

if %errorLevel% equ 0 (
    echo.
    echo ========================================
    echo ✓ 任务配置完成！
    echo ========================================
    echo.
    echo 任务已配置为：
    echo   1. 系统启动后30分钟自动运行
    echo   2. 每天凌晨2:00自动运行
    echo.
    echo 您可以在"任务计划程序"中查看和管理此任务
    echo.
) else (
    echo.
    echo ❌ 任务配置失败，请检查错误信息
    echo.
)

pause










