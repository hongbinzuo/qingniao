# BTC价格数据每日同步任务说明

## 功能说明

这个定时任务会自动检查时序数据库的最新时间戳，获取缺失的BTC价格数据并补充到数据库中。

### 支持的时间框架
- **5分钟** (5m)
- **15分钟** (15m)
- **1小时** (1h)
- **4小时** (4h)
- **1天** (1d)

### 工作流程
1. 检查每个时间框架表的最新时间戳
2. 从Gate.io API获取缺失的数据
3. 将新数据存储到时序数据库
4. 自动创建不存在的表

## 安装和配置

### 1. 手动运行测试

首先测试脚本是否正常工作：

```bash
python src/sync_btc_prices_daily.py
```

### 2. 配置Windows任务计划程序

运行PowerShell脚本（需要管理员权限）：

```powershell
# 以管理员身份运行PowerShell
.\setup_daily_price_sync_task.ps1
```

或者手动配置：

1. 打开"任务计划程序" (Task Scheduler)
2. 创建基本任务
3. 设置触发器：
   - 系统启动时（延迟30分钟）
   - 每天下午2:00
4. 设置操作：
   - 程序：`python` 或 `python3`
   - 参数：`"C:\Users\zuoho\code\qingniao\src\sync_btc_prices_daily.py"`
   - 起始于：`C:\Users\zuoho\code\qingniao`

## 任务配置详情

### 触发器
- **系统启动后30分钟**：确保系统启动后自动开始同步
- **每天下午2:00**：每天定时同步一次

### 任务设置
- ✅ 允许在电池供电时启动
- ✅ 如果正在使用电池，不停止任务
- ✅ 网络可用时运行
- ✅ 失败后自动重试（最多3次，间隔10分钟）

## 手动操作

### 查看任务状态
```powershell
Get-ScheduledTask -TaskName "BTC价格数据每日同步"
```

### 手动运行任务
```powershell
Start-ScheduledTask -TaskName "BTC价格数据每日同步"
```

### 查看任务历史
1. 打开"任务计划程序"
2. 找到任务 "BTC价格数据每日同步"
3. 查看"历史记录"标签

### 删除任务
```powershell
Unregister-ScheduledTask -TaskName "BTC价格数据每日同步" -Confirm:$false
```

## 日志和调试

### 查看输出
任务运行时会在控制台输出详细信息，包括：
- 每个时间框架的同步状态
- 新增和跳过的记录数
- 错误信息（如果有）

### 常见问题

1. **任务没有运行**
   - 检查任务计划程序中的任务状态
   - 确认Python已正确安装
   - 检查脚本路径是否正确

2. **API请求失败**
   - 检查网络连接
   - 确认Gate.io API可访问
   - 查看任务历史记录中的错误信息

3. **数据库连接失败**
   - 确认时序数据库文件存在：`data/btc_price_timeseries.duckdb`
   - 检查文件权限

## 数据存储位置

时序数据库文件：
```
data/btc_price_timeseries.duckdb
```

表结构：
- `btc_price_5m` - 5分钟K线
- `btc_price_15m` - 15分钟K线
- `btc_price_1h` - 1小时K线
- `btc_price_4h` - 4小时K线
- `btc_price_1d` - 1天K线

## 注意事项

1. **API限制**：Gate.io API有请求频率限制，脚本已包含延迟以避免触发限制
2. **数据完整性**：如果表为空，会获取最近7天的数据
3. **去重处理**：脚本会自动跳过已存在的记录
4. **错误处理**：如果某个时间框架同步失败，其他时间框架仍会继续同步

## 更新日志

- **2025-12-30**: 初始版本，支持5个时间框架的自动同步

