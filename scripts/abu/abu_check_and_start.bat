@echo off
set SCRIPT_DIR=%~dp0
pushd "%SCRIPT_DIR%\..\.."
chcp 65001 >nul
echo ========================================
echo ABU系统检查与启动
echo ========================================
echo.

cd /d "%SCRIPT_DIR%\..\.."

echo 正在检查系统状态...
python scripts\abu\check_and_start_abu_system.py

echo.
echo 按任意键退出...
pause >nul
