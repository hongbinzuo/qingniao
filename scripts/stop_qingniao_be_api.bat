@echo off
setlocal
set PORT=8090
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%PORT% ^| findstr LISTENING') do (
  set PID=%%a
)
if not defined PID (
  echo No process listening on %PORT%.
  goto :eof
)
echo Killing PID %PID% on port %PORT% ...
taskkill /PID %PID% /F
endlocal
