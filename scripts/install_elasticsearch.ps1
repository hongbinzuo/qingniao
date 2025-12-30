# Elasticsearch安装和启动脚本（Windows）
# 使用Docker方式（推荐）

Write-Host "================================================================"
Write-Host "Elasticsearch安装和启动脚本"
Write-Host "================================================================"
Write-Host ""

# 检查Docker
Write-Host "检查Docker..."
try {
    $dockerVersion = docker --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Docker已安装: $dockerVersion" -ForegroundColor Green
    } else {
        Write-Host "❌ Docker未安装" -ForegroundColor Red
        Write-Host ""
        Write-Host "请先安装Docker Desktop:"
        Write-Host "  1. 下载: https://www.docker.com/products/docker-desktop"
        Write-Host "  2. 安装并启动Docker Desktop"
        Write-Host "  3. 重新运行此脚本"
        exit 1
    }
} catch {
    Write-Host "❌ Docker未安装" -ForegroundColor Red
    Write-Host ""
    Write-Host "请先安装Docker Desktop:"
    Write-Host "  1. 下载: https://www.docker.com/products/docker-desktop"
    Write-Host "  2. 安装并启动Docker Desktop"
    Write-Host "  3. 重新运行此脚本"
    exit 1
}

Write-Host ""

# 检查Elasticsearch容器是否已存在
Write-Host "检查Elasticsearch容器..."
$existingContainer = docker ps -a --filter "name=elasticsearch" --format "{{.Names}}" 2>&1
if ($existingContainer -and $existingContainer -ne "") {
    Write-Host "✓ 找到已存在的Elasticsearch容器: $existingContainer" -ForegroundColor Yellow
    
    # 检查是否在运行
    $running = docker ps --filter "name=elasticsearch" --format "{{.Names}}" 2>&1
    if ($running -and $running -ne "") {
        Write-Host "✓ Elasticsearch已在运行" -ForegroundColor Green
    } else {
        Write-Host "启动Elasticsearch容器..."
        docker start elasticsearch
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Elasticsearch已启动" -ForegroundColor Green
        } else {
            Write-Host "❌ 启动失败" -ForegroundColor Red
            exit 1
        }
    }
} else {
    Write-Host "创建新的Elasticsearch容器..."
    docker run -d --name elasticsearch -p 9200:9200 -p 9300:9300 -e "discovery.type=single-node" -e "xpack.security.enabled=false" -e "ES_JAVA_OPTS=-Xms512m -Xmx512m" elasticsearch:8.11.0
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Elasticsearch容器已创建并启动" -ForegroundColor Green
    } else {
        Write-Host "❌ 创建失败" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "等待Elasticsearch启动（30秒）..."
Start-Sleep -Seconds 30

# 测试连接
Write-Host ""
Write-Host "测试Elasticsearch连接..."
try {
    $response = Invoke-WebRequest -Uri "http://localhost:9200" -TimeoutSec 5 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "✓ Elasticsearch连接成功！" -ForegroundColor Green
        Write-Host ""
        Write-Host "Elasticsearch信息:"
        $json = $response.Content | ConvertFrom-Json
        Write-Host "  名称: $($json.name)"
        Write-Host "  版本: $($json.version.number)"
        Write-Host "  集群: $($json.cluster_name)"
        Write-Host ""
        Write-Host "================================================================"
        Write-Host "✓ Elasticsearch已成功启动并运行在 http://localhost:9200" -ForegroundColor Green
        Write-Host "================================================================"
    } else {
        Write-Host "❌ 连接失败，状态码: $($response.StatusCode)" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ 连接失败: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "提示: Elasticsearch可能需要更多时间启动，请稍后手动测试:"
    Write-Host "  curl http://localhost:9200"
    Write-Host "  或访问浏览器: http://localhost:9200"
}
