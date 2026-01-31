@echo off
set SCRIPT_DIR=%~dp0
pushd "%SCRIPT_DIR%\..\.."
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo Abu停止所有系统
echo ========================================
echo.

cd /d "%SCRIPT_DIR%\..\.."

echo 正在停止所有ABU系统...
echo.

REM 停止模式匹配系统
echo [1/2] 停止模式匹配系统...
set STOPPED=0
for /f "tokens=2" %%i in ('wmic process where "name='python.exe'" get processid^,commandline 2^>nul ^| findstr /I "auto_signal_generator.py"') do (
    for /f "tokens=1" %%j in ("%%i") do (
        taskkill /PID %%j /F >nul 2>&1
        if !ERRORLEVEL! EQU 0 (
            echo    ✓ 已停止进程（PID: %%j）
            set STOPPED=1
        )
    )
)
if !STOPPED! EQU 0 (
    echo    ○ 未找到运行中的进程
)

REM 停止视觉匹配系统
echo [2/2] 停止视觉匹配系统...
set STOPPED=0
for /f "tokens=2" %%i in ('wmic process where "name='python.exe'" get processid^,commandline 2^>nul ^| findstr /I "abu_vision_scanner_4h.py"') do (
    for /f "tokens=1" %%j in ("%%i") do (
        taskkill /PID %%j /F >nul 2>&1
        if !ERRORLEVEL! EQU 0 (
            echo    ✓ 已停止进程（PID: %%j）
            set STOPPED=1
        )
    )
)
if !STOPPED! EQU 0 (
    echo    ○ 未找到运行中的进程
)

echo.
echo ========================================
echo 停止完成！
echo ========================================
echo.
echo 提示：如果系统仍在运行，请手动关闭对应的窗口
echo.
pause
