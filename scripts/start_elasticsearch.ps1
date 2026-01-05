# 快速启动Elasticsearch脚本

Write-Host "启动Elasticsearch..." -ForegroundColor Cyan

# 检查容器是否存在
$container = docker ps -a --filter "name=elasticsearch" --format "{{.Names}}" 2>&1
if ($container -and $container -ne "") {
    # 检查是否在运行
    $running = docker ps --filter "name=elasticsearch" --format "{{.Names}}" 2>&1
    if ($running -and $running -ne "") {
        Write-Host "✓ Elasticsearch已在运行" -ForegroundColor Green
    } else {
        Write-Host "启动Elasticsearch容器..."
        docker start elasticsearch
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Elasticsearch已启动" -ForegroundColor Green
            Write-Host "等待10秒..."
            Start-Sleep -Seconds 10
        } else {
            Write-Host "❌ 启动失败" -ForegroundColor Red
            exit 1
        }
    }
} else {
    Write-Host "❌ Elasticsearch容器不存在，请先运行 install_elasticsearch.ps1" -ForegroundColor Red
    exit 1
}

# 测试连接
Write-Host "测试连接..."
try {
    $response = Invoke-WebRequest -Uri "http://localhost:9200" -TimeoutSec 5 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "✓ Elasticsearch运行正常: http://localhost:9200" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️ 连接测试失败，但容器已启动，请稍后重试" -ForegroundColor Yellow
}



