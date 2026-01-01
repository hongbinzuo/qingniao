@echo off
chcp 65001 >nul
title Elasticsearch启动器

echo ================================================================
echo Elasticsearch快速启动
echo ================================================================
echo.

REM 检查是否已安装
if not exist "elasticsearch-8.11.0\bin\elasticsearch.bat" (
    echo ❌ Elasticsearch未安装
    echo.
    echo 正在下载并安装Elasticsearch...
    call scripts\download_and_run_elasticsearch.bat
    exit /b
)

REM 检查是否已在运行
echo 检查Elasticsearch是否已运行...
python -c "import requests; r = requests.get('http://localhost:9200', timeout=2); exit(0 if r.status_code == 200 else 1)" 2>nul
if %errorlevel% equ 0 (
    echo ✓ Elasticsearch已在运行
    echo.
    python test_elasticsearch.py
    pause
    exit /b 0
)

echo Elasticsearch未运行，正在启动...
echo.
cd elasticsearch-8.11.0\bin
start "Elasticsearch" cmd /k elasticsearch.bat
cd ..\..

echo.
echo 等待30秒让Elasticsearch启动...
timeout /t 30 /nobreak >nul

echo.
echo 测试连接...
python test_elasticsearch.py

echo.
pause


