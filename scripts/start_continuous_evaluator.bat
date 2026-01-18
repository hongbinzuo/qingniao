@echo off
REM 启动持续信号评估后台进程

set PY=py -3
set SCRIPT=scripts\continuous_signal_evaluator.py
set LOGDIR=outputs\logs
set LOGFILE=%LOGDIR%\continuous_evaluator.log
set ERRLOG=%LOGDIR%\continuous_evaluator_error.log
set PIDFILE=%LOGDIR%\continuous_evaluator.pid

REM 创建日志目录
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

REM 启动后台进程
echo 启动持续信号评估后台进程...
powershell -NoProfile -Command "$p = Start-Process -FilePath '%PY%' -ArgumentList '%SCRIPT%' -WindowStyle Hidden -RedirectStandardOutput '%CD%\%LOGFILE%' -RedirectStandardError '%CD%\%ERRLOG%' -PassThru; $p.Id | Out-File -Encoding ascii '%CD%\%PIDFILE%'"

if exist "%PIDFILE%" (
    for /f %%i in (%PIDFILE%) do set PID=%%i
    echo 进程已启动，PID: %PID%
    echo 日志文件: %LOGFILE%
    echo 错误日志: %ERRLOG%
) else (
    echo 启动失败，请检查错误日志: %ERRLOG%
)
