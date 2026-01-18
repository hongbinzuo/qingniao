# 系统唤醒后自动恢复运行

## 快速设置

### 方法1: 一键设置（推荐）

**以管理员身份运行PowerShell**：
```powershell
cd C:\Users\zuoho\code\qingniao
.\scripts\setup_auto_start_on_wake.ps1
```

**或使用批处理脚本**：
```cmd
# 右键点击，选择"以管理员身份运行"
scripts\setup_auto_start_on_wake.bat
```

### 方法2: 手动设置

1. 打开"任务计划程序"（Win+R，输入 `taskschd.msc`）
2. 创建基本任务
3. 设置触发器：
   - ✅ 系统启动时
   - ✅ 用户登录时
   - ✅ 每5分钟运行一次（监控）
4. 设置操作：
   - 程序：`cmd.exe`
   - 参数：`/c "C:\Users\zuoho\code\qingniao\scripts\monitor_auto_signal_generator.bat"`
5. 完成设置

## 工作原理

1. **监控脚本** (`monitor_auto_signal_generator.bat`)：
   - 每5分钟检查一次进程是否运行
   - 如果未运行，自动启动程序

2. **任务计划程序**：
   - 系统启动时运行监控脚本
   - 用户登录时运行监控脚本
   - 每5分钟运行一次监控脚本

## 验证设置

### 检查任务是否创建
```cmd
schtasks /Query /TN "QingNiao_AutoSignalGenerator_Monitor"
```

### 手动测试监控脚本
```cmd
scripts\monitor_auto_signal_generator.bat
```

### 查看监控日志
```cmd
type outputs\logs\monitor.log
```

## 故障排除

### 程序未自动启动
1. 检查任务计划程序中的"上次运行结果"
2. 查看监控日志：`outputs\logs\monitor.log`
3. 手动运行监控脚本测试

### 需要管理员权限
- 右键点击脚本，选择"以管理员身份运行"

## 相关文件

- `scripts/monitor_auto_signal_generator.bat` - 监控脚本
- `scripts/setup_auto_start_on_wake.ps1` - PowerShell设置脚本
- `scripts/setup_auto_start_on_wake.bat` - 批处理设置脚本
