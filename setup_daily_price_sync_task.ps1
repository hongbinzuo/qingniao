# PowerShell脚本：配置BTC价格数据每日同步任务
# 在Windows任务计划程序中创建定时任务

$ErrorActionPreference = "Stop"

# 获取脚本所在目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = $ScriptDir

# Python脚本路径
$PythonScript = Join-Path $ProjectRoot "src\sync_btc_prices_daily.py"

# 检查Python脚本是否存在
if (-not (Test-Path $PythonScript)) {
    Write-Host "❌ 错误: 找不到Python脚本: $PythonScript" -ForegroundColor Red
    exit 1
}

# 获取Python解释器路径
$PythonCmd = Get-Command python -ErrorAction SilentlyContinue
if ($PythonCmd) {
    $PythonExe = $PythonCmd.Source
} else {
    $PythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
    if ($PythonCmd) {
        $PythonExe = $PythonCmd.Source
    } else {
        Write-Host "❌ 错误: 找不到Python解释器，请确保Python已安装并在PATH中" -ForegroundColor Red
        exit 1
    }
}

Write-Host "✓ 找到Python解释器: $PythonExe" -ForegroundColor Green

# 任务名称
$TaskName = "BTC价格数据每日同步"

# 检查任务是否已存在
$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

if ($ExistingTask) {
    Write-Host "⚠️  任务已存在，将删除旧任务..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# 创建任务操作
$Action = New-ScheduledTaskAction -Execute $PythonExe -Argument "`"$PythonScript`"" -WorkingDirectory $ProjectRoot

# 创建任务触发器：每天运行一次（在系统启动后30分钟）
$Trigger1 = New-ScheduledTaskTrigger -AtStartup
$Trigger1.Delay = "PT30M"  # 延迟30分钟

# 创建任务触发器：每天下午2点运行
$Trigger2 = New-ScheduledTaskTrigger -Daily -At "14:00"

# 创建任务设置
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 10)

# 创建任务主体（以当前用户身份运行）
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest

# 创建任务描述
$Description = "每日同步BTC价格数据到时序数据库（5分钟、15分钟、1小时、4小时、1天）"

# 注册任务
try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger @($Trigger1, $Trigger2) `
        -Settings $Settings `
        -Principal $Principal `
        -Description $Description `
        -Force | Out-Null
    
    Write-Host ""
    Write-Host "✓ 任务创建成功！" -ForegroundColor Green
    Write-Host ""
    Write-Host "任务名称: $TaskName" -ForegroundColor Cyan
    Write-Host "Python脚本: $PythonScript" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "触发器配置:" -ForegroundColor Cyan
    Write-Host "  1. 系统启动后30分钟运行" -ForegroundColor White
    Write-Host "  2. 每天下午2:00运行" -ForegroundColor White
    Write-Host ""
    Write-Host "查看任务: 任务计划程序 -> 任务计划程序库 -> $TaskName" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "手动运行任务:" -ForegroundColor Yellow
    Write-Host "  Start-ScheduledTask -TaskName `"$TaskName`"" -ForegroundColor White
    Write-Host ""
    
} catch {
    Write-Host "❌ 创建任务失败: $_" -ForegroundColor Red
    exit 1
}

