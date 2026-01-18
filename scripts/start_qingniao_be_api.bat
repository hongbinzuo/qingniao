@echo off
setlocal
set "PY=py -3"
set "ROOT=%~dp0.."
cd /d "%ROOT%"

echo Starting Qingniao BE API on port 8090 ...
%PY% -m uvicorn scripts.qingniao_be_api:app --host 0.0.0.0 --port 8090

endlocal
