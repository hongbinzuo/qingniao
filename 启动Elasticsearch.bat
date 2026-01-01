@echo off
chcp 65001 >nul
title 启动Elasticsearch

echo ================================================================
echo 启动Elasticsearch
echo ================================================================
echo.

if not exist "elasticsearch-8.11.0\bin\elasticsearch.bat" (
    echo ❌ Elasticsearch未安装
    echo.
    echo 请先运行: scripts\download_and_run_elasticsearch.bat
    pause
    exit /b 1
)

echo 正在启动Elasticsearch...
echo 注意: Elasticsearch将在新窗口中运行
echo 请保持Elasticsearch窗口打开，不要关闭
echo.

cd elasticsearch-8.11.0\bin
start "Elasticsearch" cmd /k "elasticsearch.bat"
cd ..\..

echo.
echo ✓ Elasticsearch启动命令已执行
echo.
echo 等待30秒让Elasticsearch启动...
timeout /t 30 /nobreak >nul

echo.
echo 测试连接...
python -c "import requests; r = requests.get('http://localhost:9200', timeout=5); print('✓ Elasticsearch连接成功！' if r.status_code == 200 else '❌ 连接失败，请再等一会儿'); import json; data = r.json(); print(f\"  名称: {data['name']}\"); print(f\"  版本: {data['version']['number']}\"); print(f\"  集群: {data['cluster_name']}\")" 2>nul

echo.
echo ================================================================
echo 如果连接失败，请：
echo   1. 检查Elasticsearch窗口是否已打开
echo   2. 等待更长时间（Elasticsearch启动需要30-60秒）
echo   3. 访问浏览器: http://localhost:9200
echo ================================================================
echo.
pause

