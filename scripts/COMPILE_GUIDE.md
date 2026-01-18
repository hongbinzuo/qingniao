# 编译指南

## ✅ 已修复的问题

- ✅ 未使用的变量错误（已修复）

## ⚠️ 当前状态

代码已修复，但编译仍需要：

1. **gcc 编译器**（用于 CGO）
2. **启用 CGO**

## 编译步骤

### 1. 确保 gcc 已安装

```cmd
where gcc
```

如果没有输出，需要先安装 gcc（见 `FIX_CGO_WINDOWS.md`）

### 2. 启用 CGO 并编译

**PowerShell:**
```powershell
$env:CGO_ENABLED=1
go build -o abu_kline_fetcher.exe abu_kline_fetcher.go
```

**CMD:**
```cmd
set CGO_ENABLED=1
go build -o abu_kline_fetcher.exe abu_kline_fetcher.go
```

### 3. 如果仍然报错 "gcc not found"

**检查步骤：**

1. 确认 gcc 在 PATH 中：
   ```cmd
   where gcc
   gcc --version
   ```

2. 如果没有，需要：
   - 安装 gcc（推荐 TDM-GCC）
   - 重启 PowerShell/CMD
   - 验证 PATH 环境变量

3. 如果已安装但找不到：
   - 检查 PATH 环境变量是否包含 gcc 路径
   - 手动添加到 PATH（如果需要）

## 验证编译

编译成功后，应该生成 `abu_kline_fetcher.exe` 文件。

测试运行：
```cmd
.\abu_kline_fetcher.exe --help
```

## 快速检查脚本

使用批处理脚本检查：
```cmd
cd scripts
check_gcc.bat
```



