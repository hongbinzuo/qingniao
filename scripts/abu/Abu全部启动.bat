@echo off
set SCRIPT_DIR=%~dp0
pushd "%SCRIPT_DIR%\..\.."
chcp 65001 >nul
echo ========================================
echo Abu全部启动
echo ========================================
echo.

cd /d "%SCRIPT_DIR%\..\.."

REM 检查进程是否已运行
echo 正在检查系统状态...
echo.

setlocal enabledelayedexpansion

REM 检查模式匹配系统
set PATTERN_RUNNING=0
wmic process where "name='python.exe'" get commandline 2>nul | findstr /I "auto_signal_generator.py" >nul
if %ERRORLEVEL% EQU 0 (
    echo [检查] 模式匹配系统: 已在运行
    set PATTERN_RUNNING=1
) else (
    echo [检查] 模式匹配系统: 未运行
)

REM 检查视觉匹配系统
set VISION_RUNNING=0
wmic process where "name='python.exe'" get commandline 2>nul | findstr /I "abu_vision_scanner_4h.py" >nul
if %ERRORLEVEL% EQU 0 (
    echo [检查] 视觉匹配系统: 已在运行
    set VISION_RUNNING=1
) else (
    echo [检查] 视觉匹配系统: 未运行
)

echo.

REM 如果都在运行，提示用户
if !PATTERN_RUNNING! EQU 1 if !VISION_RUNNING! EQU 1 (
    echo.
    echo ========================================
    echo 系统已在运行！
    echo ========================================
    echo.
    echo 模式匹配系统和视觉匹配系统都已启动，无需重复启动。
    echo.
    echo 如果遇到问题，请先运行 "scripts/abu/Abu停止所有.bat" 停止现有进程，然后重新运行此脚本。
    echo.
    pause
    exit /b 0
)

echo 正在启动系统...
echo.

REM 启动模式匹配系统
echo [1/2] 模式匹配系统...
if !PATTERN_RUNNING! EQU 1 (
    echo    检测到旧进程，先停止...
    REM 停止旧进程
    for /f "tokens=2" %%i in ('wmic process where "name='python.exe'" get processid^,commandline 2^>nul ^| findstr /I "auto_signal_generator.py"') do (
        for /f "tokens=1" %%j in ("%%i") do (
            taskkill /PID %%j /F >nul 2>&1
            if !ERRORLEVEL! EQU 0 (
                echo    ✓ 已停止旧进程（PID: %%j）
            )
        )
    )
    timeout /t 3 /nobreak >nul
)
echo    启动模式匹配系统（每4小时运行，Top 10币种）...
start "ABU模式匹配" cmd /k "python scripts\auto_signal_generator.py --interval 4.0 --coins 10"
timeout /t 2 /nobreak >nul
echo    ✓ 已启动
echo    日志文件: outputs\logs\auto_signal_generator_*.log
echo.

REM 启动视觉匹配系统
echo [2/2] 视觉匹配系统...
if !VISION_RUNNING! EQU 1 (
    echo    检测到旧进程，先停止...
    REM 停止旧进程
    for /f "tokens=2" %%i in ('wmic process where "name='python.exe'" get processid^,commandline 2^>nul ^| findstr /I "abu_vision_scanner_4h.py"') do (
        for /f "tokens=1" %%j in ("%%i") do (
            taskkill /PID %%j /F >nul 2>&1
            if !ERRORLEVEL! EQU 0 (
                echo    ✓ 已停止旧进程（PID: %%j）
            )
        )
    )
    timeout /t 3 /nobreak >nul
)
echo    启动视觉匹配系统（每4小时运行，Top 10币种）...
start "ABU视觉匹配" cmd /k "python scripts\abu\abu_vision_scanner_4h.py --interval 14400 --symbols 10"
timeout /t 2 /nobreak >nul
echo    ✓ 已启动
echo.

echo.
echo ========================================
echo 启动完成！
echo ========================================
echo.
echo 系统状态：
echo   ○ ABU模式匹配：已启动（每4小时运行，Top 10币种）
echo   ○ ABU视觉匹配：已启动（每4小时运行，Top 10币种）
echo.
echo 日志文件位置：
echo   - 模式匹配日志: outputs\logs\auto_signal_generator_YYYYMMDD.log
echo   - 错误日志: outputs\logs\auto_signal_generator_error_YYYYMMDD.log
echo.
echo 提示：
echo   - 不要关闭这两个窗口，让它们持续运行
echo   - 如果遇到问题，查看日志文件了解详情
echo   - 运行 "scripts/abu/Abu停止所有.bat" 可以停止所有系统
echo.
pause
