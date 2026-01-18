# 自动化回测任务 (PowerShell)
# 用法: .\scripts\auto_backtest_daily.ps1

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir

Set-Location $projectRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "自动化回测任务" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

try {
    python scripts/auto_backtest_trading_plans.py
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "回测完成" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
}
catch {
    Write-Host "回测失败: $_" -ForegroundColor Red
    exit 1
}
