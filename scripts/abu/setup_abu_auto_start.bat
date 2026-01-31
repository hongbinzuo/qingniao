@echo off
set SCRIPT_DIR=%~dp0
pushd "%SCRIPT_DIR%\..\.."
chcp 65001 >nul
echo ========================================
echo 设置ABU系统开机自动启动
echo ========================================
echo.

cd /d "%SCRIPT_DIR%\..\.."

echo 正在设置开机自动启动任务...
echo.

REM 使用内联PowerShell命令，避免编码问题
powershell -ExecutionPolicy Bypass -NoProfile -Command "$ErrorActionPreference = 'Stop'; try { $TaskName = 'ABU_Auto_Start'; $ScriptPath = Join-Path '%CD%\scripts\abu' 'check_and_start_abu_system.py'; if (-not (Test-Path $ScriptPath)) { Write-Host '错误: 找不到脚本文件: ' $ScriptPath -ForegroundColor Red; exit 1 }; $PythonPath = (Get-Command python).Source; if (-not $PythonPath) { Write-Host '错误: 找不到Python，请确保Python已安装并在PATH中' -ForegroundColor Red; exit 1 }; $existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue; if ($existingTask) { Write-Host '任务已存在，正在更新...' -ForegroundColor Yellow; Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false }; $action = New-ScheduledTaskAction -Execute $PythonPath -Argument \"`\"$ScriptPath`\"\"; $trigger = New-ScheduledTaskTrigger -AtStartup; $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable; $principal = New-ScheduledTaskPrincipal -UserId \"$env:USERDOMAIN\$env:USERNAME\" -LogonType Interactive -RunLevel Highest; Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'ABU系统开机自动启动' | Out-Null; Write-Host 'ABU系统开机自动启动任务已设置!' -ForegroundColor Green; Write-Host \"任务名称: $TaskName\" -ForegroundColor Cyan; Write-Host '触发条件: 系统启动时' -ForegroundColor Cyan } catch { Write-Host '错误: ' $_.Exception.Message -ForegroundColor Red; exit 1 }"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 设置失败！请检查上面的错误信息。
    echo.
    echo 常见问题：
    echo 1. 请确保以管理员身份运行此脚本
    echo 2. 请确保Python已安装并在PATH中
    echo 3. 请确保scripts\abu\check_and_start_abu_system.py文件存在
    echo.
) else (
    echo.
    echo 设置成功！
    echo.
)

echo 按任意键退出...
pause >nul
