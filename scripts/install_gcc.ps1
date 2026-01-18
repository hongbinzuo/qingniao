# Quick script to check gcc installation
# Usage: .\install_gcc.ps1

Write-Host "Checking for gcc..." -ForegroundColor Cyan

# Check if gcc is already installed
$gccPath = Get-Command gcc -ErrorAction SilentlyContinue
if ($gccPath) {
    Write-Host "✅ gcc already installed!" -ForegroundColor Green
    Write-Host "Location: $($gccPath.Source)" -ForegroundColor Green
    Write-Host "Version:" -ForegroundColor Green
    gcc --version | Select-Object -First 1
    Write-Host ""
    Write-Host "You can now compile with:" -ForegroundColor Cyan
    Write-Host "  `$env:CGO_ENABLED=1" -ForegroundColor Yellow
    Write-Host "  go build -o abu_kline_fetcher.exe abu_kline_fetcher.go" -ForegroundColor Yellow
    exit 0
}

Write-Host "❌ gcc not found in PATH" -ForegroundColor Red
Write-Host ""
Write-Host "Please install a C compiler:" -ForegroundColor Yellow
Write-Host ""
Write-Host "Option 1: TDM-GCC (Recommended, no admin needed)" -ForegroundColor Cyan
Write-Host "  1. Download from: https://jmeubank.github.io/tdm-gcc/download/" -ForegroundColor White
Write-Host "  2. Install with 'Add to PATH' option checked" -ForegroundColor White
Write-Host "  3. Restart PowerShell and run this script again" -ForegroundColor White
Write-Host ""
Write-Host "Option 2: Chocolatey (Requires admin)" -ForegroundColor Cyan
Write-Host "  Run PowerShell as Administrator, then:" -ForegroundColor White
Write-Host "  choco install mingw -y" -ForegroundColor White
Write-Host ""
Write-Host "See scripts/FIX_CGO_WINDOWS.md for detailed instructions" -ForegroundColor Yellow



