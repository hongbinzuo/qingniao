@echo off
REM 启动 Sherlock 守护（Windows），确保工作目录为仓库根目录
setlocal
cd /d "%~dp0.."
start "Sherlock Daemon" cmd /c "py -3 scripts\sherlock_daemon.py"
echo Sherlock daemon started.
endlocal
