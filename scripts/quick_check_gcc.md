# 快速检查 gcc 安装

## 方法1：使用批处理脚本（无需执行策略）

直接运行：
```cmd
cd C:\Users\zuoho\code\qingniao\scripts
abu\check_gcc.bat
```

## 方法2：在PowerShell中临时绕过执行策略

```powershell
cd C:\Users\zuoho\code\qingniao\scripts
PowerShell -ExecutionPolicy Bypass -File .\abu\install_gcc.ps1
```

## 方法3：直接运行命令

```powershell
# 检查 gcc
where.exe gcc

# 如果找到，查看版本
gcc --version

# 如果没有找到，需要安装
# 推荐：TDM-GCC - https://jmeubank.github.io/tdm-gcc/download/
```

## 方法4：修改执行策略（永久，需要管理员）

以管理员身份运行PowerShell：

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

然后就可以运行：
```powershell
.\abu\install_gcc.ps1
```


