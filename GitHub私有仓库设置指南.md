# GitHub私有仓库设置指南

## ✅ GitHub免费账户支持私有仓库

**好消息**: 从2019年1月开始，GitHub免费账户支持**无限私有仓库**！

- ✅ 免费账户可以创建私有仓库
- ✅ 私有仓库数量无限制
- ✅ 每个私有仓库最多3个协作者（免费账户）
- ✅ 如果需要更多协作者，可以升级到付费计划

---

## 🚀 设置步骤

### 步骤1: 在GitHub创建私有仓库

1. **登录GitHub**
   - 访问 https://github.com
   - 登录你的账户

2. **创建新仓库**
   - 点击右上角 "+" → "New repository"
   - 或访问: https://github.com/new

3. **配置仓库**
   - **Repository name**: `qingniao` (或你喜欢的名字)
   - **Description**: `青鸟交易系统 - 基于De.交易策略的BTC信号生成系统`
   - **Visibility**: 选择 **Private** ⭐ (重要！)
   - **不要**勾选 "Initialize this repository with a README" (我们已经有了)
   - **不要**选择 .gitignore 或 license (我们已经有了)

4. **点击 "Create repository"**

---

### 步骤2: 添加远程仓库

创建仓库后，GitHub会显示设置说明。使用以下命令：

```bash
# 添加远程仓库（替换yourusername为你的GitHub用户名）
git remote add origin https://github.com/yourusername/qingniao.git

# 或者使用SSH（如果已配置SSH key）
git remote add origin git@github.com:yourusername/qingniao.git
```

---

### 步骤3: 推送代码

```bash
# 推送到GitHub（首次推送）
git push -u origin develop
```

---

## 🔐 认证方式

### 方式1: HTTPS + Personal Access Token (推荐)

**优点**: 简单，不需要配置SSH key

**步骤**:
1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. 点击 "Generate new token (classic)"
3. 设置权限:
   - ✅ `repo` (完整仓库访问权限)
4. 生成token并**保存**（只显示一次）
5. 推送时使用token作为密码:
   ```bash
   git push -u origin develop
   # Username: 你的GitHub用户名
   # Password: 粘贴你的token（不是GitHub密码）
   ```

### 方式2: SSH Key (更安全)

**优点**: 不需要每次输入密码

**步骤**:
1. **检查是否已有SSH key**:
   ```bash
   ls ~/.ssh/id_ed25519.pub
   # Windows: type %USERPROFILE%\.ssh\id_ed25519.pub
   ```

2. **如果没有，生成新的SSH key**:
   ```bash
   ssh-keygen -t ed25519 -C "your.email@example.com"
   # 按回车使用默认路径
   # 设置密码（可选，但推荐）
   ```

3. **复制公钥**:
   ```bash
   # Windows PowerShell
   cat ~/.ssh/id_ed25519.pub
   # 或
   type %USERPROFILE%\.ssh\id_ed25519.pub
   ```

4. **添加到GitHub**:
   - GitHub → Settings → SSH and GPG keys → New SSH key
   - 粘贴公钥内容
   - 保存

5. **测试连接**:
   ```bash
   ssh -T git@github.com
   ```

6. **使用SSH URL添加远程仓库**:
   ```bash
   git remote set-url origin git@github.com:yourusername/qingniao.git
   ```

---

## 📋 完整操作流程

### 使用HTTPS (最简单)

```bash
# 1. 在GitHub创建私有仓库（在网页上完成）

# 2. 添加远程仓库
git remote add origin https://github.com/yourusername/qingniao.git

# 3. 查看远程仓库
git remote -v

# 4. 推送代码
git push -u origin develop
```

### 使用SSH (推荐，更安全)

```bash
# 1. 在GitHub创建私有仓库（在网页上完成）

# 2. 配置SSH key（如果还没有）

# 3. 添加远程仓库
git remote add origin git@github.com:yourusername/qingniao.git

# 4. 推送代码
git push -u origin develop
```

---

## 🔍 验证设置

### 检查远程仓库

```bash
# 查看远程仓库
git remote -v

# 应该显示:
# origin  https://github.com/yourusername/qingniao.git (fetch)
# origin  https://github.com/yourusername/qingniao.git (push)
```

### 测试推送

```bash
# 推送测试
git push -u origin develop

# 如果成功，会显示:
# Branch 'develop' set up to track remote branch 'develop' from 'origin'.
```

---

## ⚠️ 注意事项

### 1. 私有仓库限制

- ✅ 免费账户支持无限私有仓库
- ⚠️ 每个私有仓库最多3个协作者（免费账户）
- ✅ 如果需要更多协作者，可以升级到付费计划

### 2. 敏感信息

- ❌ **不要提交**数据库文件（`.duckdb`）- 已在`.gitignore`中排除
- ❌ **不要提交**API密钥或密码
- ❌ **不要提交**个人敏感信息

### 3. 推送大小

- GitHub单个文件限制: 100MB
- 仓库大小建议: 小于1GB
- 如果文件太大，考虑使用Git LFS

---

## 🛠️ 常见问题

### Q1: 推送时要求输入密码

**A**: 使用Personal Access Token代替GitHub密码，或配置SSH key。

### Q2: 如何更改远程仓库URL

```bash
# 查看当前URL
git remote -v

# 更改URL
git remote set-url origin https://github.com/yourusername/new-repo.git
```

### Q3: 如何删除远程仓库

```bash
git remote remove origin
```

### Q4: 如何验证仓库是私有的

- 在GitHub网页上查看仓库设置
- 私有仓库会显示 "Private" 标签
- 只有你（和协作者）可以访问

---

## 📝 快速命令参考

```bash
# 添加远程仓库
git remote add origin https://github.com/yourusername/qingniao.git

# 查看远程仓库
git remote -v

# 推送代码
git push -u origin develop

# 拉取代码
git pull origin develop

# 查看分支
git branch -a
```

---

## 🎯 推荐流程

1. ✅ 在GitHub创建私有仓库
2. ✅ 添加远程仓库（使用HTTPS或SSH）
3. ✅ 推送代码到GitHub
4. ✅ 验证仓库是私有的

---

**创建时间**: 2025-12-30

