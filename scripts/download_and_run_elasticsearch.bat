@echo off
chcp 65001 >nul
echo ================================================================
echo Elasticsearch Windows直接安装脚本
echo ================================================================
echo.

set ES_VERSION=8.11.0
set ES_DIR=elasticsearch-%ES_VERSION%

echo 检查Elasticsearch是否已安装...
if exist "%ES_DIR%\bin\elasticsearch.bat" (
    echo ✓ Elasticsearch已存在
    goto :start_elasticsearch
)

echo 下载Elasticsearch %ES_VERSION%...
echo 这可能需要几分钟，请耐心等待...
echo.

powershell -Command "Invoke-WebRequest -Uri 'https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-%ES_VERSION%-windows-x86_64.zip' -OutFile 'elasticsearch.zip'"

if %errorlevel% neq 0 (
    echo ❌ 下载失败
    echo 请手动下载: https://www.elastic.co/downloads/elasticsearch
    pause
    exit /b 1
)

echo.
echo 解压Elasticsearch...
powershell -Command "Expand-Archive -Path 'elasticsearch.zip' -DestinationPath '.' -Force"

if %errorlevel% neq 0 (
    echo ❌ 解压失败
    pause
    exit /b 1
)

del elasticsearch.zip
echo ✓ Elasticsearch已下载并解压

:start_elasticsearch
echo.
echo 启动Elasticsearch...
echo 注意: Elasticsearch将在新窗口中运行
echo 请保持窗口打开，不要关闭
echo.

cd %ES_DIR%\bin
start "Elasticsearch" cmd /k elasticsearch.bat
cd ..\..

echo.
echo 等待30秒让Elasticsearch启动...
timeout /t 30 /nobreak >nul

echo.
echo 测试Elasticsearch连接...
python -c "import requests; import time; time.sleep(5); r = requests.get('http://localhost:9200', timeout=5); print('✓ Elasticsearch连接成功！' if r.status_code == 200 else '❌ 连接失败'); import json; data = r.json(); print(f\"  名称: {data['name']}\"); print(f\"  版本: {data['version']['number']}\"); print(f\"  集群: {data['cluster_name']}\")" 2>nul
if %errorlevel% neq 0 (
    echo ⚠️ Python测试失败，请手动测试: curl http://localhost:9200
    echo 或访问浏览器: http://localhost:9200
    echo.
    echo 提示: Elasticsearch可能需要更多时间启动，请稍后重试
)

echo.
echo ================================================================
echo ✓ 安装完成！
echo ================================================================
echo.
echo Elasticsearch正在运行，请保持Elasticsearch窗口打开
echo 访问: http://localhost:9200
echo.
echo 下一步:
echo   1. 测试连接: python src/elasticsearch_logger.py
echo   2. 停止Elasticsearch: 关闭Elasticsearch窗口
echo.
pause

