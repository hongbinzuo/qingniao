@echo off
chcp 65001 >nul
echo 启动Elasticsearch...

if not exist "elasticsearch-8.11.0\bin\elasticsearch.bat" (
    echo ❌ Elasticsearch未安装
    echo 请先运行: scripts\download_and_run_elasticsearch.bat
    pause
    exit /b 1
)

echo Elasticsearch正在启动...
echo 注意: Elasticsearch将在新窗口中运行
echo 请保持窗口打开，不要关闭
echo.

cd elasticsearch-8.11.0\bin
start "Elasticsearch" cmd /k elasticsearch.bat
cd ..\..

echo.
echo 等待20秒让Elasticsearch启动...
timeout /t 20 /nobreak >nul

echo.
echo 测试连接...
python -c "import requests; r = requests.get('http://localhost:9200', timeout=5); print('✓ Elasticsearch连接成功！' if r.status_code == 200 else '❌ 连接失败'); import json; data = r.json(); print(f\"  名称: {data['name']}\"); print(f\"  版本: {data['version']['number']}\"); print(f\"  集群: {data['cluster_name']}\")" 2>nul

echo.
echo ✓ Elasticsearch已启动
echo 访问: http://localhost:9200
echo.


