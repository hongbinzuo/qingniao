# GitHub远程仓库设置脚本
# 用于配置GitHub私有仓库

Write-Host "================================================================================"
Write-Host "GitHub私有仓库设置"
Write-Host "================================================================================"
Write-Host ""

# 检查是否已有远程仓库
$remote_exists = git remote get-url origin 2>$null
if ($remote_exists) {
    Write-Host "当前远程仓库: $remote_exists"
    Write-Host ""
    $change = Read-Host "是否要更改远程仓库? (y/n)"
    if ($change -ne 'y' -and $change -ne 'Y') {
        Write-Host "保持当前远程仓库"
        exit
    }
    git remote remove origin
}

# 输入GitHub信息
Write-Host "请输入GitHub信息:"
$username = Read-Host "GitHub用户名"
$repo_name = Read-Host "仓库名称 (默认: qingniao)"

if ([string]::IsNullOrWhiteSpace($repo_name)) {
    $repo_name = "qingniao"
}

# 选择认证方式
Write-Host ""
Write-Host "选择认证方式:"
Write-Host "1. HTTPS (需要Personal Access Token)"
Write-Host "2. SSH (需要配置SSH key)"
$auth_choice = Read-Host "请选择 (1/2)"

if ($auth_choice -eq "2") {
    # SSH方式
    $remote_url = "git@github.com:$username/$repo_name.git"
    Write-Host ""
    Write-Host "使用SSH方式: $remote_url"
} else {
    # HTTPS方式
    $remote_url = "https://github.com/$username/$repo_name.git"
    Write-Host ""
    Write-Host "使用HTTPS方式: $remote_url"
    Write-Host ""
    Write-Host "⚠️  注意: 推送时需要输入:"
    Write-Host "   - Username: $username"
    Write-Host "   - Password: 使用Personal Access Token (不是GitHub密码)"
    Write-Host ""
    Write-Host "   如何获取Token:"
    Write-Host "   1. GitHub → Settings → Developer settings → Personal access tokens"
    Write-Host "   2. Generate new token (classic)"
    Write-Host "   3. 选择 'repo' 权限"
    Write-Host "   4. 生成并保存token"
}

# 添加远程仓库
Write-Host ""
Write-Host "添加远程仓库..."
git remote add origin $remote_url

# 验证
Write-Host ""
Write-Host "验证远程仓库配置:"
git remote -v

Write-Host ""
Write-Host "================================================================================"
Write-Host "远程仓库配置完成！"
Write-Host "================================================================================"
Write-Host ""
Write-Host "下一步:"
Write-Host "1. 在GitHub创建私有仓库: https://github.com/new"
Write-Host "   - Repository name: $repo_name"
Write-Host "   - Visibility: Private ⭐"
Write-Host "   - 不要初始化README、.gitignore或license"
Write-Host ""
Write-Host "2. 推送代码到GitHub:"
Write-Host "   git push -u origin develop"
Write-Host ""
Write-Host "3. 如果使用HTTPS，推送时需要:"
Write-Host "   - Username: $username"
Write-Host "   - Password: Personal Access Token"
Write-Host ""


