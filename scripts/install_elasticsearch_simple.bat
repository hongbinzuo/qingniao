@echo off
chcp 65001 >nul
echo ================================================================
echo Elasticsearch安装和启动脚本
echo ================================================================
echo.

echo 检查Docker...
docker --version >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ Docker已安装
    goto :check_container
) else (
    echo ❌ Docker未安装
    echo.
    echo 请先安装Docker Desktop:
    echo   1. 下载: https://www.docker.com/products/docker-desktop
    echo   2. 安装并启动Docker Desktop
    echo   3. 重新运行此脚本
    pause
    exit /b 1
)

:check_container
echo.
echo 检查Elasticsearch容器...
docker ps -a --filter "name=elasticsearch" --format "{{.Names}}" >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ 找到已存在的Elasticsearch容器
    docker ps --filter "name=elasticsearch" --format "{{.Names}}" >nul 2>&1
    if %errorlevel% equ 0 (
        echo ✓ Elasticsearch已在运行
        goto :test_connection
    ) else (
        echo 启动Elasticsearch容器...
        docker start elasticsearch
        if %errorlevel% equ 0 (
            echo ✓ Elasticsearch已启动
            timeout /t 10 /nobreak >nul
            goto :test_connection
        ) else (
            echo ❌ 启动失败
            pause
            exit /b 1
        )
    )
) else (
    echo 创建新的Elasticsearch容器...
    docker run -d --name elasticsearch -p 9200:9200 -p 9300:9300 -e "discovery.type=single-node" -e "xpack.security.enabled=false" -e "ES_JAVA_OPTS=-Xms512m -Xmx512m" elasticsearch:8.11.0
    if %errorlevel% equ 0 (
        echo ✓ Elasticsearch容器已创建并启动
        echo 等待30秒让Elasticsearch启动...
        timeout /t 30 /nobreak >nul
        goto :test_connection
    ) else (
        echo ❌ 创建失败
        pause
        exit /b 1
    )
)

:test_connection
echo.
echo 测试Elasticsearch连接...
python -c "import requests; r = requests.get('http://localhost:9200', timeout=5); print('✓ Elasticsearch连接成功！' if r.status_code == 200 else '❌ 连接失败'); import json; data = r.json(); print(f\"  名称: {data['name']}\"); print(f\"  版本: {data['version']['number']}\"); print(f\"  集群: {data['cluster_name']}\")" 2>nul
if %errorlevel% neq 0 (
    echo ⚠️ Python测试失败，请手动测试: curl http://localhost:9200
    echo 或访问浏览器: http://localhost:9200
)

echo.
echo ================================================================
echo ✓ 安装完成！
echo ================================================================
echo.
echo 下一步:
echo   1. 安装Python客户端: pip install elasticsearch
echo   2. 测试连接: python src/elasticsearch_logger.py
echo.
pause

