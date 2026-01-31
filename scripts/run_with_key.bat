@echo off
set SCRIPT_DIR=%~dp0
pushd "%SCRIPT_DIR%\.."
chcp 65001 >nul
cd /d "C:\Users\zuoho\code\qingniao"

REM ===== REPLACE THIS WITH YOUR ACTUAL KEY =====
set MOONSHOT_API_KEY=sk-REPLACE_WITH_YOUR_KEY
REM =============================================

echo Testing Moonshot API connection...
python scripts/test_moonshot_api.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo API test passed! Starting batch processing...
    python scripts/batch_process_601_1000.py
) else (
    echo.
    echo API test failed! Please check your key.
)

pause
