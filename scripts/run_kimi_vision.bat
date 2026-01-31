@echo off
set SCRIPT_DIR=%~dp0
pushd "%SCRIPT_DIR%\.."
chcp 65001 >nul
cd /d "C:\Users\zuoho\code\qingniao"

REM Set API Key (replace with your valid key)
set KIMI_API_KEY=sk-kimi-YOUR_NEW_KEY_HERE

REM Run batch processing
echo Starting Kimi Vision batch processing...
echo Processing images 601-1000
python scripts/batch_process_601_1000.py

pause
