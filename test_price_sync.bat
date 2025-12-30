@echo off
chcp 65001 >nul
echo ========================================
echo BTC价格数据同步 - 测试运行
echo ========================================
echo.
echo 正在运行同步脚本...
echo.

python src/sync_btc_prices_daily.py

if %errorLevel% equ 0 (
    echo.
    echo ========================================
    echo ✓ 测试完成
    echo ========================================
) else (
    echo.
    echo ========================================
    echo ❌ 测试失败
    echo ========================================
)

echo.
pause




