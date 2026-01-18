@echo off
REM 监控自动信号生成器，如果未运行则自动启动
REM 建议使用Windows任务计划程序每5分钟运行一次此脚本

setlocal enabledelayedexpansion

REM 切换到脚本所在目录的父目录
cd /d %~dp0\..

set PY=py -3
set SCRIPT=scripts\auto_signal_generator.py
set PIDFILE=outputs\logs\auto_signal_generator.pid
set LOGDIR=outputs\logs
set LOGFILE=%LOGDIR%\monitor.log

REM 创建日志目录
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

REM 记录监控时间
echo [%date% %time%] 开始监控检查 >> "%LOGFILE%"

REM 检查PID文件是否存在
if not exist "%PIDFILE%" (
    echo [%date% %time%] 未找到PID文件，启动程序... >> "%LOGFILE%"
    call scripts\start_auto_signal_generator.bat >> "%LOGFILE%" 2>&1
    goto :end
)

REM 检查进程是否还在运行
set PID=
for /f %%i in (%PIDFILE%) do set PID=%%i

if "!PID!"=="" (
    echo [%date% %time%] PID文件为空，启动程序... >> "%LOGFILE%"
    del "%PIDFILE%" 2>NUL
    call scripts\start_auto_signal_generator.bat >> "%LOGFILE%" 2>&1
    goto :end
)

tasklist /FI "PID eq !PID!" 2>NUL | find /I "!PID!" >NUL
if errorlevel 1 (
    echo [%date% %time%] 进程 !PID! 未运行，重新启动... >> "%LOGFILE%"
    del "%PIDFILE%" 2>NUL
    call scripts\start_auto_signal_generator.bat >> "%LOGFILE%" 2>&1
) else (
    REM 检查进程命令行是否包含auto_signal_generator.py
    wmic process where "ProcessId=!PID!" get CommandLine 2>NUL | find /I "auto_signal_generator.py" >NUL
    if errorlevel 1 (
        echo [%date% %time%] 进程 !PID! 存在但不是目标程序，重新启动... >> "%LOGFILE%"
        del "%PIDFILE%" 2>NUL
        call scripts\start_auto_signal_generator.bat >> "%LOGFILE%" 2>&1
    ) else (
        echo [%date% %time%] 进程 !PID! 正在运行 >> "%LOGFILE%"
    )
)

:end
endlocal
