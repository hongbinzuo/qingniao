@echo off
set SCRIPT_DIR=%~dp0
pushd "%SCRIPT_DIR%\.."
REM 初始化Git仓库脚本（Windows）

echo ================================================================================
echo 初始化青鸟交易系统Git仓库
echo ================================================================================
echo.

REM 检查是否已存在Git仓库
if exist .git (
    echo [警告] Git仓库已存在
    echo.
    choice /C YN /M "是否重新初始化"
    if errorlevel 2 goto :end
    echo 删除现有Git仓库...
    rmdir /s /q .git
)

REM 初始化Git仓库
echo [1/5] 初始化Git仓库...
git init
if errorlevel 1 (
    echo [错误] Git初始化失败，请确保已安装Git
    goto :end
)
echo [OK] Git仓库初始化完成
echo.

REM 检查.gitignore
echo [2/5] 检查.gitignore文件...
if not exist .gitignore (
    echo [警告] .gitignore文件不存在，将使用增强版本
    copy .gitignore.enhanced .gitignore
) else (
    echo [OK] .gitignore文件已存在
)
echo.

REM 创建develop分支
echo [3/5] 创建develop分支...
git checkout -b develop
echo [OK] develop分支创建完成
echo.

REM 添加文件
echo [4/5] 添加文件到Git...
git add .
echo [OK] 文件添加完成
echo.

REM 首次提交
echo [5/5] 创建首次提交...
git commit -m "feat: 初始化青鸟交易系统项目

- 添加核心交易系统代码
- 添加数据库设计（按交易员分库）
- 添加设计文档
- 配置.gitignore"
echo [OK] 首次提交完成
echo.

echo ================================================================================
echo Git仓库初始化完成！
echo ================================================================================
echo.
echo 下一步:
echo 1. 配置远程仓库（可选）:
echo    git remote add origin https://github.com/yourusername/qimeng2.git
echo.
echo 2. 推送到远程（可选）:
echo    git push -u origin develop
echo.
echo 3. 查看状态:
echo    git status
echo.

:end
pause

