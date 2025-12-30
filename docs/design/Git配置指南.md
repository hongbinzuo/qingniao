# Git配置指南

## 🎯 初始化Git仓库需要的信息

### 本地初始化（不需要远程仓库）

**只需要**:
- ✅ Git已安装（已完成 ✅）
- ✅ 用户信息（姓名和邮箱）

**不需要**:
- ❌ GitHub SSH key（本地仓库不需要）
- ❌ Repo地址（本地仓库不需要）
- ❌ 远程仓库（可以稍后添加）

---

## 📝 必需配置：用户信息

### 方式1: 全局配置（推荐）

```bash
# 配置全局用户信息（所有Git仓库使用）
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### 方式2: 仅当前项目配置

```bash
# 仅配置当前项目
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

### 检查配置

```bash
# 查看配置
git config user.name
git config user.email

# 查看所有配置
git config --list
```

---

## 🔗 远程仓库配置（可选）

### 如果不需要远程仓库

**可以跳过**，本地Git仓库完全可以独立工作。

### 如果需要推送到远程仓库

#### 选项1: GitHub（推荐）

**需要的信息**:
1. GitHub账号
2. 仓库地址（如果已创建）
   - HTTPS: `https://github.com/username/qingniao.git`
   - SSH: `git@github.com:username/qingniao.git`

**配置步骤**:

1. **创建GitHub仓库**（如果还没有）
   - 登录GitHub
   - 点击 "New repository"
   - 仓库名: `qingniao`
   - 选择 Private（推荐，因为可能包含敏感信息）

2. **添加远程仓库**

   **使用HTTPS**（简单，需要输入密码或token）:
   ```bash
   git remote add origin https://github.com/username/qingniao.git
   ```

   **使用SSH**（需要配置SSH key，但更安全）:
   ```bash
   git remote add origin git@github.com:username/qimeng2.git
   ```

3. **配置SSH key**（如果使用SSH）

   **检查是否已有SSH key**:
   ```bash
   ls ~/.ssh/id_rsa.pub
   # Windows: type %USERPROFILE%\.ssh\id_rsa.pub
   ```

   **如果没有，生成新的SSH key**:
   ```bash
   ssh-keygen -t ed25519 -C "your.email@example.com"
   # 按回车使用默认路径
   # 设置密码（可选，但推荐）
   ```

   **复制公钥**:
   ```bash
   # Windows PowerShell
   cat ~/.ssh/id_ed25519.pub
   # 或
   type %USERPROFILE%\.ssh\id_ed25519.pub
   ```

   **添加到GitHub**:
   - 登录GitHub
   - Settings → SSH and GPG keys → New SSH key
   - 粘贴公钥内容
   - 保存

4. **测试SSH连接**:
   ```bash
   ssh -T git@github.com
   ```

#### 选项2: GitLab

类似GitHub，使用GitLab的仓库地址。

#### 选项3: Gitee（国内）

类似GitHub，使用Gitee的仓库地址。

---

## 🚀 完整初始化流程

### 步骤1: 配置用户信息（必需）

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### 步骤2: 初始化本地仓库

```bash
# 运行初始化脚本
init_git_repo.bat

# 或手动初始化
git init
git checkout -b develop
git add .
git commit -m "feat: 初始化青鸟交易系统项目"
```

### 步骤3: 配置远程仓库（可选）

**如果使用GitHub HTTPS**:
```bash
git remote add origin https://github.com/username/qimeng2.git
git push -u origin develop
```

**如果使用GitHub SSH**:
```bash
# 先配置SSH key（见上方）
git remote add origin git@github.com:username/qimeng2.git
git push -u origin develop
```

---

## 📋 初始化前检查清单

### 必需项
- [ ] Git已安装 ✅
- [ ] 配置用户姓名和邮箱
- [ ] 检查.gitignore文件

### 可选项（如果需要远程仓库）
- [ ] GitHub/GitLab账号
- [ ] 创建远程仓库
- [ ] 配置SSH key（如果使用SSH）
- [ ] 添加远程仓库地址

---

## 💡 建议

### 对于你的项目

**推荐方案**:
1. **先本地初始化** - 不需要任何远程信息
2. **稍后添加远程** - 如果需要备份或协作时再添加
3. **使用Private仓库** - 因为可能包含敏感信息

**安全建议**:
- ✅ 使用Private仓库
- ✅ 不要提交敏感信息（已在.gitignore中排除）
- ✅ 使用SSH key（比HTTPS更安全）
- ✅ 定期备份数据库文件（不提交到Git）

---

## 🔧 快速配置脚本

### Windows PowerShell脚本

创建 `setup_git_config.ps1`:

```powershell
# 配置Git用户信息
$name = Read-Host "请输入您的姓名"
$email = Read-Host "请输入您的邮箱"

git config --global user.name $name
git config --global user.email $email

Write-Host "Git配置完成！"
Write-Host "姓名: $name"
Write-Host "邮箱: $email"
```

---

## ❓ 常见问题

### Q1: 必须要有GitHub账号吗？
**A**: 不需要。本地Git仓库完全可以独立工作，不需要远程仓库。

### Q2: 什么时候需要远程仓库？
**A**: 
- 需要备份代码时
- 需要多设备同步时
- 需要团队协作时
- 需要版本发布时

### Q3: SSH key是必需的吗？
**A**: 不是。如果使用HTTPS，只需要GitHub账号和密码（或Personal Access Token）。

### Q4: 可以稍后添加远程仓库吗？
**A**: 可以。任何时候都可以添加远程仓库：
```bash
git remote add origin <repository-url>
git push -u origin develop
```

---

## 🎯 推荐流程

### 方案1: 仅本地（最简单）

```bash
# 1. 配置用户信息
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# 2. 初始化
init_git_repo.bat
```

**完成！** 不需要其他信息。

### 方案2: 本地 + 远程（推荐）

```bash
# 1. 配置用户信息
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# 2. 初始化本地
init_git_repo.bat

# 3. 创建GitHub仓库（在GitHub网站）

# 4. 添加远程（使用HTTPS）
git remote add origin https://github.com/username/qimeng2.git

# 5. 推送
git push -u origin develop
```

---

**创建时间**: 2025-12-30

