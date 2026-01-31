@echo off
REM Quick batch script to check for gcc (no execution policy issues)
echo Checking for gcc...

where gcc >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo ✅ gcc found!
    gcc --version | findstr /C:"gcc"
    echo.
    echo You can now compile with:
    echo   set CGO_ENABLED=1
    echo   go build -o abu_kline_fetcher.exe abu_kline_fetcher.go
) else (
    echo ❌ gcc not found in PATH
    echo.
    echo Please install a C compiler:
    echo.
    echo Option 1: TDM-GCC (Recommended, no admin needed)
    echo   1. Download from: https://jmeubank.github.io/tdm-gcc/download/
    echo   2. Install with 'Add to PATH' option checked
    echo   3. Restart PowerShell/CMD and run this script again
    echo.
    echo Option 2: Chocolatey (Requires admin)
    echo   Run PowerShell as Administrator, then:
    echo   choco install mingw -y
    echo.
    echo See scripts\FIX_CGO_WINDOWS.md for detailed instructions
)

pause



