@echo off
REM 停止持续信号评估后台进程

set PIDFILE=outputs\logs\continuous_evaluator.pid

if exist "%PIDFILE%" (
    for /f %%i in (%PIDFILE%) do set PID=%%i
    echo 正在停止进程 PID: %PID%
    taskkill /PID %PID% /F >nul 2>&1
    del "%PIDFILE%"
    echo 进程已停止
) else (
    echo 未找到PID文件，进程可能未运行
    echo 请手动在任务管理器中结束 python.exe 进程（命令行包含 continuous_signal_evaluator.py）
)
