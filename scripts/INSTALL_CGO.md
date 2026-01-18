# Go DuckDB CGO 安装说明（Windows）

## 问题

go-duckdb 需要 CGO 支持，在 Windows 上需要安装 C 编译器（gcc）。

## 解决方案

### 方案1：安装 TDM-GCC（推荐）

1. **下载 TDM-GCC**
   - 访问：https://jmeubank.github.io/tdm-gcc/
   - 下载并安装 TDM-GCC-64（推荐版本 10.x 或更新）

2. **安装后验证**
   ```bash
   gcc --version
   ```

3. **设置环境变量**
   - 安装程序通常会自动添加到 PATH
   - 如果没有，手动添加到 PATH：`C:\TDM-GCC-64\bin`

4. **启用 CGO 并编译**
   ```bash
   $env:CGO_ENABLED=1
   cd scripts
   go build -o abu_kline_fetcher.exe abu_kline_fetcher.go
   ```

### 方案2：使用 MSYS2 + MinGW-w64

1. **安装 MSYS2**
   - 访问：https://www.msys2.org/
   - 下载并安装

2. **在 MSYS2 中安装 MinGW-w64**
   ```bash
   pacman -S mingw-w64-x86_64-gcc
   ```

3. **添加到 PATH**
   - 添加到 PATH：`C:\msys64\mingw64\bin`

### 方案3：使用 Chocolatey（如果已安装）

```bash
choco install mingw
```

## 验证安装

```bash
# 检查 gcc
gcc --version

# 启用 CGO
$env:CGO_ENABLED=1

# 测试编译
cd scripts
go build -o abu_kline_fetcher.exe abu_kline_fetcher.go
```

## 永久启用 CGO（可选）

如果需要永久启用 CGO，可以设置环境变量：

```powershell
# 用户级别
[Environment]::SetEnvironmentVariable("CGO_ENABLED", "1", "User")

# 或系统级别（需要管理员权限）
[Environment]::SetEnvironmentVariable("CGO_ENABLED", "1", "Machine")
```

## 注意事项

1. **重启终端**：安装 gcc 后，需要重启 PowerShell 或 CMD
2. **PATH 环境变量**：确保 gcc 的路径在 PATH 中
3. **编译时间**：首次编译可能需要较长时间（下载和编译依赖）

## 备选方案

如果无法安装 C 编译器，可以考虑：
- 使用 Python 实现（已有 `src/get_extended_gateio_klines.py`）
- 使用 JSON 文件作为中间格式（Go 输出 JSON，Python 导入数据库）



