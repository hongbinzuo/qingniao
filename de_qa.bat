@echo off
chcp 65001 >nul
echo ========================================
echo De.策略问答系统
echo ========================================
echo.

python src/de_data_manager.py ask-strategy --interactive

pause



