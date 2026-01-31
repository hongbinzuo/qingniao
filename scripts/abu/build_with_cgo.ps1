# PowerShell script to build Go program with CGO enabled
# Usage: .\scripts\abu\build_with_cgo.ps1

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "Building abu_kline_fetcher with CGO enabled..." -ForegroundColor Green

# Enable CGO
$env:CGO_ENABLED = "1"

# Check if gcc is available
$gccPath = Get-Command gcc -ErrorAction SilentlyContinue
if (-not $gccPath) {
    Write-Host "ERROR: gcc not found in PATH!" -ForegroundColor Red
    Write-Host "Please install TDM-GCC or MinGW-w64" -ForegroundColor Yellow
    Write-Host "See scripts/INSTALL_CGO.md for instructions" -ForegroundColor Yellow
    exit 1
}

Write-Host "Found gcc: $($gccPath.Source)" -ForegroundColor Green
Write-Host "Version: $(gcc --version | Select-Object -First 1)" -ForegroundColor Green

# Build
Write-Host "`nBuilding..." -ForegroundColor Cyan
go build -o abu_kline_fetcher.exe abu_kline_fetcher.go

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nBuild successful! Output: abu_kline_fetcher.exe" -ForegroundColor Green
} else {
    Write-Host "`nBuild failed!" -ForegroundColor Red
    exit 1
}


