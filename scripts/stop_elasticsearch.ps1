# 停止Elasticsearch脚本

Write-Host "停止Elasticsearch..." -ForegroundColor Cyan

$container = docker ps --filter "name=elasticsearch" --format "{{.Names}}" 2>&1
if ($container -and $container -ne "") {
    docker stop elasticsearch
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Elasticsearch已停止" -ForegroundColor Green
    } else {
        Write-Host "❌ 停止失败" -ForegroundColor Red
    }
} else {
    Write-Host "⚠️ Elasticsearch未运行" -ForegroundColor Yellow
}



