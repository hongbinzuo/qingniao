# PowerShell脚本：设置每日报告生成任务
# 每天00:05自动生成报告

$TaskName = "ABU_Daily_Report"
$ScriptPath = Join-Path $PSScriptRoot "generate_daily_summary_report.py"
$PythonPath = (Get-Command python).Source

# 检查任务是否已存在
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

if ($existingTask) {
    Write-Host "任务已存在，正在更新..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# 创建任务动作
$action = New-ScheduledTaskAction -Execute $PythonPath -Argument "`"$ScriptPath`""

# 创建任务触发器（每天00:05）
$trigger = New-ScheduledTaskTrigger -Daily -At "00:05"

# 创建任务设置
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# 注册任务
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "ABU系统每日报告生成" | Out-Null

Write-Host "每日报告任务已设置！" -ForegroundColor Green
Write-Host "任务名称: $TaskName" -ForegroundColor Cyan
Write-Host "运行时间: 每天 00:05" -ForegroundColor Cyan
Write-Host ""
Write-Host "查看任务: Get-ScheduledTask -TaskName $TaskName" -ForegroundColor Yellow
Write-Host "删除任务: Unregister-ScheduledTask -TaskName $TaskName" -ForegroundColor Yellow
