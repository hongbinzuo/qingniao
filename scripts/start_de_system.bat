@echo off
setlocal ENABLEDELAYEDEXPANSION

REM One-click startup for De. system (Windows)
REM - API (FastAPI) on port 8090
REM - Watcher (5m cadence)
REM - Falcon daemon (hourly)

set "SCRIPT_DIR=%~dp0"
set "ROOT=%SCRIPT_DIR%.."
cd /d "%ROOT%"

set "PORT=8090"
set "PY=py -3"

echo Starting De. API on port %PORT% ...
start "De API %PORT%" %PY% -m uvicorn scripts.sherlock_api:app --host 0.0.0.0 --port %PORT% --reload
timeout /t 2 /nobreak >NUL

echo Starting De watcher (5m)...
start "De Watcher" %PY% scripts\de_watcher.py

echo Starting Falcon daemon (hourly)...
start "De Falcon" %PY% scripts\falcon.py --daemon --interval 3600

echo.
echo De. system started.
echo - Web:   http://localhost:%PORT%/de
echo - API:   http://localhost:%PORT%/api/de/status
echo.
echo Close this window; components run in separate windows.
pause

