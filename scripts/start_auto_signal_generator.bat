@echo off
REM 启动全自动信号生成与评估系统

set PY=py -3
set SCRIPT=scripts\auto_signal_generator.py
set LOGDIR=outputs\logs
set LOGFILE=%LOGDIR%\auto_signal_generator.log
set ERRLOG=%LOGDIR%\auto_signal_generator_error.log
set PIDFILE=%LOGDIR%\auto_signal_generator.pid

REM 创建日志目录
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

REM 启动后台进程（每小时生成一次）
echo 启动全自动信号生成与评估系统...
echo 生成间隔: 1小时
echo 币种数量: 30（Top 30市值币种，每小时生成5分钟和15分钟信号）
echo 时间框架: 5m, 15m
echo.
powershell -NoProfile -Command "$p = Start-Process -FilePath '%PY%' -ArgumentList '%SCRIPT%','--interval','1.0','--coins','30' -WindowStyle Hidden -RedirectStandardOutput '%CD%\%LOGFILE%' -RedirectStandardError '%CD%\%ERRLOG%' -PassThru; $p.Id | Out-File -Encoding ascii '%CD%\%PIDFILE%'"

if exist "%PIDFILE%" (
    for /f %%i in (%PIDFILE%) do set PID=%%i
    echo 进程已启动，PID: %PID%
    echo 日志文件: %LOGFILE%
    echo 错误日志: %ERRLOG%
    echo.
    echo 系统将每小时自动生成信号并评估
    echo 状态文件: outputs\auto_signal_status\current_status.json
) else (
    echo 启动失败，请检查错误日志: %ERRLOG%
)
