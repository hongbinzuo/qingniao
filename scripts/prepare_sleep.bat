@echo off
chcp 65001 >nul
setlocal
REM Ensure we run from repo root
pushd "%~dp0\.."
echo [Prepare Sleep] Flushing pending conversations, learning, and echoing status...
python scripts\prepare_sleep.py
popd
endlocal

