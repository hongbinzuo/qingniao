# Abu跑批 - 快速使用指南

## 快速启动

### 持续运行（每4小时自动生成）
```cmd
abu_run.bat
```

### 单次运行（运行一次后退出）
```cmd
abu_run_once.bat
```

## 重要说明

✅ **可以在任何会话窗口运行**
- 可以在新的命令提示符窗口运行
- 可以在新的PowerShell窗口运行
- 可以在任何终端窗口运行
- 不依赖当前会话

### 使用方法

**方法1: 双击运行**
- 直接双击 `abu_run.bat` 或 `abu_run_once.bat` 文件

**方法2: 新窗口运行**
- 打开新的命令提示符（Win+R，输入 `cmd`）
- 切换到项目目录：
  ```cmd
  cd C:\Users\zuoho\code\qingniao
  ```
- 运行命令：
  ```cmd
  abu_run.bat
  ```

**方法3: PowerShell运行**
- 打开PowerShell
- 切换到项目目录：
  ```powershell
  cd C:\Users\zuoho\code\qingniao
  ```
- 运行命令：
  ```powershell
  .\abu_run.bat
  ```

## 功能说明

### abu_run.bat
- **功能**: 启动持续运行的自动信号生成系统
- **配置**: 
  - 每4小时自动生成一次
  - Top 10币种（按市值）
  - 5分钟和15分钟时间框架
  - 每4小时约20个信号（10币种 × 2时间框架）
- **停止**: 按 `Ctrl+C` 或关闭窗口

### abu_run_once.bat
- **功能**: 运行一次信号生成和评估
- **用途**: 测试或手动触发一次生成
- **退出**: 完成后自动退出

## 输出文件

- **交易计划**: `outputs/trading_plans/auto_generated_*.md`
- **总结报告**: `outputs/auto_signal_status/summary_*.md`
- **状态文件**: `outputs/auto_signal_status/current_status.json`
- **日志文件**: `outputs/logs/auto_signal_generator.log`

## 查看状态

在任何会话窗口运行：
```cmd
python scripts\show_auto_signal_status.py
```

## 停止运行

如果使用 `abu_run.bat` 启动：
- 按 `Ctrl+C` 停止
- 或关闭运行窗口

如果使用后台方式启动：
```cmd
scripts\stop_auto_signal_generator.bat
```

## 注意事项

1. **路径问题**: 批处理文件会自动切换到项目目录，所以可以在任何位置运行
2. **数据库**: 系统已迁移到 PostgreSQL，支持多进程并发运行，不会有数据库锁定问题
3. **检查运行状态**: 运行前可以先用 `python scripts\show_auto_signal_status.py` 检查是否已有实例在运行
