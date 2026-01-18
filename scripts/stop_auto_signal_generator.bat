@echo off
REM 停止全自动信号生成与评估系统

set PIDFILE=outputs\logs\auto_signal_generator.pid

if exist "%PIDFILE%" (
    for /f %%i in (%PIDFILE%) do set PID=%%i
    echo 正在停止进程 PID: %PID%
    taskkill /PID %PID% /F >nul 2>&1
    del "%PIDFILE%"
    echo 进程已停止
) else (
    echo 未找到PID文件，进程可能未运行
    echo 请手动在任务管理器中结束 python.exe 进程（命令行包含 auto_signal_generator.py）
)
