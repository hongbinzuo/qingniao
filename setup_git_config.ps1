# Git配置脚本
# 配置用户信息

Write-Host "================================================================================"
Write-Host "Git用户信息配置"
Write-Host "================================================================================"
Write-Host ""

# 检查是否已配置
$current_name = git config --global user.name
$current_email = git config --global user.email

if ($current_name -and $current_email) {
    Write-Host "当前配置:"
    Write-Host "  姓名: $current_name"
    Write-Host "  邮箱: $current_email"
    Write-Host ""
    $change = Read-Host "是否要修改配置? (y/n)"
    if ($change -ne 'y' -and $change -ne 'Y') {
        Write-Host "保持当前配置"
        exit
    }
}

# 输入用户信息
Write-Host "请输入Git用户信息:"
$name = Read-Host "姓名"
$email = Read-Host "邮箱"

# 配置
git config --global user.name $name
git config --global user.email $email

Write-Host ""
Write-Host "================================================================================"
Write-Host "配置完成！"
Write-Host "================================================================================"
Write-Host ""
Write-Host "配置信息:"
Write-Host "  姓名: $name"
Write-Host "  邮箱: $email"
Write-Host ""
Write-Host "下一步:"
Write-Host "  运行 init_git_repo.bat 初始化Git仓库"
Write-Host ""

