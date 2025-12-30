# 信号评估系统使用说明

## 功能概述

信号评估系统用于评估历史交易信号的实际表现，包括：
- 检查信号是否触及入场价、止盈、止损
- 实现保本止损逻辑（触及止盈1后，止损移动到入场价）
- 验证入场价规则（入场价未到但先到止盈1，信号无效）
- **缓存评估结果，避免重复计算**

## 使用方法

### 基本使用

```bash
# 评估信号（自动使用缓存）
python src/evaluate_signal_results.py
```

### 强制刷新

```bash
# 忽略缓存，重新评估
python src/evaluate_signal_results.py --refresh
```

## 缓存系统

### 缓存位置

评估结果缓存在：
```
trading_signals/.evaluation_cache/
```

### 缓存文件命名

```
evaluation_YYYYMMDD_HHMMSS_all.json
```

例如：
```
evaluation_20251229_105544_all.json
```

### 缓存有效期

默认缓存有效期为 **24小时**。超过24小时的缓存会被视为过期，系统会自动重新评估。

### 缓存内容

每个缓存文件包含：
- `signal_time`: 信号生成时间
- `evaluation_time`: 评估时间
- `metadata`: 元数据（当前价格、信号数量等）
- `results`: 评估结果列表

### 缓存管理

#### 查看缓存列表

```python
from src.signal_evaluation_cache import list_evaluation_cache

# 列出所有缓存
caches = list_evaluation_cache()
for cache in caches:
    print(f"{cache['file']}: {cache['signal_time']} -> {cache['evaluation_time']}")

# 列出特定日期的缓存
caches = list_evaluation_cache('20251229')
```

#### 清理缓存

```python
from src.signal_evaluation_cache import clear_evaluation_cache

# 清理所有缓存
clear_evaluation_cache()

# 清理特定日期的缓存
clear_evaluation_cache('20251229')

# 清理7天前的缓存
clear_evaluation_cache(older_than_days=7)
```

## 评估规则

### 1. 保本止损逻辑

- 当触及第一止盈位后，止损位自动移动到入场价（保本）
- 如果之后触及保本止损，状态为**"部分止盈"**而不是"止损"
- 如果成功触及第二止盈位，状态为**"完全止盈"**

### 2. 入场价验证规则

- **如果入场价未到但先到达第一止盈点，该信号无效撤销**
- 无效信号不计入胜率统计

## 评估结果格式

每个信号的评估结果包含：

```json
{
  "signal_time": "2025-12-29 10:55:44",
  "timeframe": "5m",
  "type": "long",
  "entry": 88093.00,
  "stop_loss": 87800.00,
  "take_profit_1": 89531.00,
  "take_profit_2": 90250.00,
  "status": "stopped",
  "outcome": "stopped",
  "max_profit": 0.00,
  "max_loss": -0.33,
  "reached_tp1": false,
  "reached_tp2": false,
  "hit_stop_loss": true,
  "current_price": 87593.70,
  "current_pnl_pct": -0.57,
  "time_summary": {
    "entry_time": "2025-12-29 20:15:00",
    "tp1_time": null,
    "tp2_time": null,
    "stop_time": "2025-12-29 20:15:00",
    "entry_reached": true,
    "invalid_signal": false
  },
  "details": [...],
  "timeline": [...]
}
```

## 状态说明

- `full_tp`: 完全止盈（触及止盈2）
- `partial_tp`: 部分止盈（触及止盈1，但之后触及保本止损）
- `stopped`: 止损（触及初始止损或保本止损）
- `invalid`: 无效（入场价未到但先到止盈1）
- `open`: 持仓中（未触及任何关键价格）

## 输出文件

评估报告保存在：
```
信号评估报告_YYYYMMDD_HHMMSS.md
```

例如：
```
信号评估报告_20251229_202825.md
```

## 性能优化

### 使用缓存的好处

1. **快速响应**：已评估的信号直接从缓存读取，无需重新计算
2. **节省资源**：避免重复的API调用和计算
3. **一致性**：相同信号的评估结果保持一致

### 何时需要刷新

- 价格数据更新后（需要重新检查是否触及关键价格）
- 评估逻辑修改后
- 需要查看最新评估结果时

## 注意事项

1. **缓存有效期**：默认24小时，超过有效期会自动重新评估
2. **数据来源**：评估基于Gate.io的K线数据
3. **时间对齐**：确保信号生成时间和K线数据时间对齐
4. **时区**：所有时间使用北京时间（UTC+8）

## 示例

### 评估今天的信号

```bash
python src/evaluate_signal_results.py
```

### 强制重新评估

```bash
python src/evaluate_signal_results.py --refresh
```

### 查看缓存

```python
from src.signal_evaluation_cache import list_evaluation_cache

caches = list_evaluation_cache('20251229')
for cache in caches:
    print(f"信号: {cache['signal_time']}, 评估: {cache['evaluation_time']}")
```

### 清理旧缓存

```python
from src.signal_evaluation_cache import clear_evaluation_cache

# 清理7天前的缓存
clear_evaluation_cache(older_than_days=7)
```


