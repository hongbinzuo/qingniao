@echo off
chcp 65001 >nul
echo ========================================
echo De.数据管理统一入口
echo ========================================
echo.

python src/de_data_manager.py %*

pause


