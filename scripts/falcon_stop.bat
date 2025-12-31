@echo off
chcp 65001 >nul
set PIDFILE=trading_signals\.falcon.pid
if not exist %PIDFILE% (
  echo 未找到 PID 文件，Falcon 可能未运行。
  exit /b 1
)
set /p PID=<%PIDFILE%
echo 停止 Falcon (PID=%PID%)...
taskkill /PID %PID% /F >nul 2>nul
del /f /q %PIDFILE% >nul 2>nul
echo 已尝试停止 Falcon。

