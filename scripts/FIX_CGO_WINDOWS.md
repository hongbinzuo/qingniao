# 修复 Go DuckDB CGO 问题（Windows）

## 问题诊断

✅ **已确认问题**：
- `go-duckdb` 需要 CGO 支持
- Windows 上需要安装 C 编译器（gcc）
- 当前系统 CGO_ENABLED=0，且没有 gcc

## 解决方案

### 方案1：使用 Chocolatey 安装（推荐，需要管理员权限）

**步骤**：

1. **以管理员身份打开 PowerShell**
   - 右键点击 PowerShell → "以管理员身份运行"

2. **安装 MinGW**
   ```powershell
   choco install mingw -y
   ```

3. **重启 PowerShell**（让 PATH 生效）

4. **验证安装**
   ```powershell
   gcc --version
   ```

5. **编译程序**
   ```powershell
   cd C:\Users\zuoho\code\qingniao\scripts
   $env:CGO_ENABLED=1
   go build -o abu/abu_kline_fetcher.exe abu/abu_kline_fetcher.go
   ```

### 方案2：手动安装 TDM-GCC（不需要管理员权限，推荐）

**步骤**：

1. **下载 TDM-GCC**
   - 访问：https://jmeubank.github.io/tdm-gcc/download/
   - 下载：`tdm64-gcc-10.3.0-2.exe` 或更新版本

2. **安装**
   - 运行安装程序
   - 选择 "MinGW-w64/TDM64 (64-bit)"
   - 安装到默认位置（通常是 `C:\TDM-GCC-64`）
   - **重要**：勾选 "Add to PATH" 选项

3. **重启 PowerShell**

4. **验证安装**
   ```powershell
   gcc --version
   ```

5. **编译程序**
   ```powershell
   cd C:\Users\zuoho\code\qingniao\scripts
   $env:CGO_ENABLED=1
   go build -o abu/abu_kline_fetcher.exe abu/abu_kline_fetcher.go
   ```

### 方案3：使用 MSYS2（如果已安装）

如果已经安装了 MSYS2：

1. **在 MSYS2 中安装 MinGW-w64**
   ```bash
   pacman -S mingw-w64-x86_64-gcc
   ```

2. **添加到 PATH**
   - 添加到系统 PATH：`C:\msys64\mingw64\bin`

3. **重启 PowerShell 并编译**

## 快速安装脚本

创建 `scripts/abu/install_gcc.ps1`：

```powershell
# 检查是否已有 gcc
if (Get-Command gcc -ErrorAction SilentlyContinue) {
    Write-Host "gcc already installed: $(gcc --version | Select-Object -First 1)" -ForegroundColor Green
    exit 0
}

Write-Host "gcc not found. Please install TDM-GCC:" -ForegroundColor Yellow
Write-Host "1. Download from: https://jmeubank.github.io/tdm-gcc/download/" -ForegroundColor Cyan
Write-Host "2. Install with 'Add to PATH' option checked" -ForegroundColor Cyan
Write-Host "3. Restart PowerShell and run this script again" -ForegroundColor Cyan
```

## 验证步骤

完成安装后，运行以下命令验证：

```powershell
# 1. 检查 gcc
gcc --version

# 2. 启用 CGO
$env:CGO_ENABLED=1

# 3. 检查 Go 环境
go env CGO_ENABLED  # 应该输出: 1

# 4. 编译测试
cd C:\Users\zuoho\code\qingniao\scripts
go build -o abu/abu_kline_fetcher.exe abu/abu_kline_fetcher.go

# 5. 如果成功，测试运行
.\abu\abu_kline_fetcher.exe --help
```

## 常见问题

### Q: 安装后仍然找不到 gcc

**A**: 
1. 检查 PATH 环境变量是否包含 gcc 路径
2. 重启 PowerShell/CMD
3. 验证：`$env:PATH -split ';' | Select-String -Pattern 'gcc|mingw|tdm'`

### Q: 编译时仍然报错 "gcc not found"

**A**:
1. 确保 CGO_ENABLED=1：`$env:CGO_ENABLED=1`
2. 验证 gcc 在 PATH 中：`where.exe gcc`
3. 尝试使用完整路径

### Q: 编译时间很长

**A**: 这是正常的，首次编译需要：
- 下载 DuckDB C 库
- 编译 C 绑定
- 可能需要几分钟时间

### Q: 不想安装 C 编译器

**A**: 可以考虑使用 Python 实现（已有 `src/get_extended_gateio_klines.py`）

## 推荐方案

**推荐使用方案2（TDM-GCC）**，因为：
- ✅ 不需要管理员权限
- ✅ 安装简单
- ✅ 独立安装，不影响系统
- ✅ 自动添加到 PATH（如果勾选）

## 下一步

安装 gcc 后：

1. ✅ 验证 gcc 安装
2. ✅ 启用 CGO 并编译
3. ✅ 测试运行程序
4. ✅ 继续实施混合方案



