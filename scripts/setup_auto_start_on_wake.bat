@echo off
REM 设置系统唤醒后自动启动信号生成器（简化版）
REM 需要以管理员权限运行

echo ========================================
echo 设置系统唤醒后自动启动信号生成器
echo ========================================
echo.
echo 注意: 需要以管理员权限运行此脚本
echo.

REM 检查管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 需要管理员权限！
    echo 请右键点击此文件，选择"以管理员身份运行"
    pause
    exit /b 1
)

set TASKNAME=QingNiao_AutoSignalGenerator_Monitor
set SCRIPT=%CD%\scripts\monitor_auto_signal_generator.bat

echo [信息] 正在创建Windows任务计划...
echo.

REM 删除旧任务（如果存在）
schtasks /Delete /TN "%TASKNAME%" /F >nul 2>&1

REM 创建新任务
REM 触发器1: 系统启动时
REM 触发器2: 用户登录时
REM 触发器3: 每5分钟运行一次（监控进程）

schtasks /Create /TN "%TASKNAME%" /TR "cmd.exe /c \"%SCRIPT%\"" /SC ONSTART /RU "%USERNAME%" /RL HIGHEST /F
if %errorlevel% neq 0 (
    echo [错误] 创建任务失败
    pause
    exit /b 1
)

schtasks /Create /TN "%TASKNAME%_Logon" /TR "cmd.exe /c \"%SCRIPT%\"" /SC ONLOGON /RU "%USERNAME%" /RL HIGHEST /F

REM 创建每5分钟运行一次的监控任务
schtasks /Create /TN "%TASKNAME%_Monitor" /TR "cmd.exe /c \"%SCRIPT%\"" /SC MINUTE /MO 5 /RU "%USERNAME%" /RL HIGHEST /F

echo [成功] 任务已创建！
echo.
echo 任务名称: %TASKNAME%
echo 触发器:
echo   - 系统启动时
echo   - 用户登录时
echo   - 每5分钟监控一次
echo.
echo 查看任务: taskschd.msc
echo 删除任务: schtasks /Delete /TN "%TASKNAME%" /F
echo.
pause
