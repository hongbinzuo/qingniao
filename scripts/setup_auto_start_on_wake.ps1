# PowerShell脚本：设置系统唤醒后自动启动信号生成器
# 需要以管理员权限运行

Write-Host "========================================"
Write-Host "设置系统唤醒后自动启动信号生成器"
Write-Host "========================================"
Write-Host ""

# 检查管理员权限
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[错误] 需要管理员权限！" -ForegroundColor Red
    Write-Host "请右键点击PowerShell，选择'以管理员身份运行'"
    pause
    exit 1
}

$scriptPath = Join-Path $PSScriptRoot "monitor_auto_signal_generator.bat"
$taskName = "QingNiao_AutoSignalGenerator_Monitor"

# 检查任务是否已存在
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "[信息] 任务已存在，正在删除旧任务..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# 创建任务动作
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$scriptPath`""

# 创建触发器：系统启动时
$trigger1 = New-ScheduledTaskTrigger -AtStartup

# 创建触发器：系统从休眠/睡眠唤醒时
$trigger2 = New-ScheduledTaskTrigger -AtLogOn

# 创建触发器：每5分钟运行一次（监控进程）
$trigger3 = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration (New-TimeSpan -Days 365)

# 创建任务设置
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable

# 创建任务主体（以当前用户身份运行）
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Highest

# 注册任务
try {
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger @($trigger1, $trigger2, $trigger3) -Settings $settings -Principal $principal -Description "监控并自动启动青鸟自动信号生成器" | Out-Null
    Write-Host "[成功] 任务已创建！" -ForegroundColor Green
    Write-Host ""
    Write-Host "任务名称: $taskName"
    Write-Host "触发器:"
    Write-Host "  - 系统启动时"
    Write-Host "  - 用户登录时"
    Write-Host "  - 每5分钟监控一次"
    Write-Host ""
    Write-Host "查看任务: taskschd.msc"
    Write-Host "删除任务: Unregister-ScheduledTask -TaskName $taskName"
} catch {
    Write-Host "[错误] 创建任务失败: $_" -ForegroundColor Red
    pause
    exit 1
}

Write-Host ""
Write-Host "========================================"
Write-Host "设置完成！"
Write-Host "========================================"
pause
