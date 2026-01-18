@echo off
chcp 65001 >nul
echo ================================================================================
echo 设置自动备份任务 - Windows任务计划程序
echo ================================================================================
echo.

REM 获取当前脚本所在目录
set SCRIPT_DIR=%~dp0
set PYTHON_SCRIPT=%SCRIPT_DIR%backup_data.py

REM 检查Python脚本是否存在
if not exist "%PYTHON_SCRIPT%" (
    echo ❌ 备份脚本不存在: %PYTHON_SCRIPT%
    pause
    exit /b 1
)

echo 📋 自动备份配置:
echo    脚本: %PYTHON_SCRIPT%
echo    频率: 每天 02:00
echo    保留: 7天
echo.

REM 创建任务计划
echo 正在创建任务计划...
schtasks /Create /TN "QingNiao_AutoBackup" /TR "python \"%PYTHON_SCRIPT%\"" /SC DAILY /ST 02:00 /F

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ 自动备份任务创建成功！
    echo.
    echo 📅 任务详情:
    echo    任务名称: QingNiao_AutoBackup
    echo    运行时间: 每天 02:00
    echo    运行命令: python "%PYTHON_SCRIPT%"
    echo.
    echo 💡 管理任务:
    echo    - 查看任务: schtasks /Query /TN "QingNiao_AutoBackup"
    echo    - 运行任务: schtasks /Run /TN "QingNiao_AutoBackup"
    echo    - 删除任务: schtasks /Delete /TN "QingNiao_AutoBackup" /F
    echo.
    echo 📖 也可以在"任务计划程序"中手动管理
) else (
    echo.
    echo ⚠️  任务创建失败，可能需要管理员权限
    echo    请右键"以管理员身份运行"此脚本
)

echo.
pause



