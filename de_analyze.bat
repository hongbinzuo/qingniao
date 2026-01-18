@echo off
chcp 65001 >nul
echo ========================================
echo De.策略分析报告生成
echo ========================================
echo.

set /p days="请输入分析天数（默认7天）: "
if "%days%"=="" set days=7

python src/de_data_manager.py analyze-strategy --days %days% --output De策略分析报告_%date:~0,4%%date:~5,2%%date:~8,2%.md

pause







