# PowerShell脚本：设置ABU系统开机自动启动
# 系统启动时自动检查并启动ABU系统

$TaskName = "ABU_Auto_Start"
$ScriptPath = Join-Path $PSScriptRoot "check_and_start_abu_system.py"
$PythonPath = (Get-Command python).Source

# 检查任务是否已存在
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

if ($existingTask) {
    Write-Host "任务已存在，正在更新..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# 创建任务动作
$action = New-ScheduledTaskAction -Execute $PythonPath -Argument "`"$ScriptPath`""

# 创建任务触发器（系统启动时）
$trigger = New-ScheduledTaskTrigger -AtStartup

# 创建任务设置
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# 设置任务运行权限（需要管理员权限）
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Highest

# 注册任务
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "ABU系统开机自动启动" | Out-Null

Write-Host "ABU系统开机自动启动任务已设置!" -ForegroundColor Green
Write-Host "任务名称: $TaskName" -ForegroundColor Cyan
Write-Host "触发条件: 系统启动时" -ForegroundColor Cyan
Write-Host ""
Write-Host "查看任务: Get-ScheduledTask -TaskName $TaskName" -ForegroundColor Yellow
Write-Host "删除任务: Unregister-ScheduledTask -TaskName $TaskName" -ForegroundColor Yellow
Write-Host ""
Write-Host "注意: 系统启动时会自动检查并启动ABU系统" -ForegroundColor Cyan
