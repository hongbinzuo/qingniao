# 系统操作日志说明

## 📋 概述

系统现在会记录所有关键操作到Elasticsearch日志系统，包括：
- 对话记录（原始录入）
- 交易信号生成
- 交易记录操作（添加、提取、更新）
- 价格数据同步
- 策略提取和分析
- 价格验证（包括警告）
- 错误和异常
- 性能指标

所有日志至少保留3个月（90天）。

## ✅ 已记录的操作类型

### 1. 对话记录 (`conversation`)
- 用户消息
- 助手回复
- 交易员消息（De.的消息）
- 用户评价
- 价格验证结果

### 2. 交易信号生成 (`signal_generation`)
- 信号数量
- 时间框架
- 系统名称
- 当前价格
- 生成详情

### 3. 交易记录操作 (`trade_record_add`, `trade_record_extract`, `trade_record_update`)
- 操作类型（添加/提取/更新）
- 交易ID
- 对话ID
- 操作详情

### 4. 价格数据同步 (`price_sync`)
- 时间框架
- 同步记录数
- 开始/结束时间
- 成功/失败状态
- 错误信息

### 5. 策略提取 (`strategy_extraction`)
- 对话ID
- 策略信息
- 提取结果

### 6. 价格验证 (`price_validation`, `price_warning`)
- 价格值
- 时间戳
- 验证结果
- 价格范围
- 修正建议

### 7. 错误和警告 (`error`, `warning`)
- 错误类型
- 错误消息
- 错误详情
- 堆栈跟踪

### 8. 性能指标 (`performance_metric`)
- 指标名称
- 指标值
- 单位
- 详情

## 🔍 日志级别

- `info`: 一般信息（默认）
- `warning`: 警告信息
- `error`: 错误信息
- `critical`: 严重错误

## 📊 使用示例

### 1. 记录信号生成

```python
from system_logger import log_signal_generation

log_signal_generation(
    signals_count=5,
    timeframe='15m',
    system_name='de',
    current_price=88710.0,
    details={'signals': [...]}
)
```

### 2. 记录交易记录操作

```python
from system_logger import log_trade_record

log_trade_record(
    action='add',  # 或 'extract', 'update'
    trade_id=123,
    conversation_id=456,
    details={'entry_price': 88710.0}
)
```

### 3. 记录价格同步

```python
from system_logger import log_price_sync

log_price_sync(
    timeframe='5m',
    records_synced=100,
    start_time='2025-12-31 00:00:00',
    end_time='2025-12-31 01:00:00',
    success=True
)
```

### 4. 记录价格验证

```python
from system_logger import log_price_validation

log_price_validation(
    price=81800.0,
    timestamp='2025-12-31 00:23:00',
    is_valid=False,
    price_range='$88,000 - $89,000',
    suggestion=88100.0
)
```

### 5. 记录错误

```python
from system_logger import log_error

log_error(
    error_type='APIError',
    error_message='无法获取价格数据',
    error_details={'api': 'gate.io'},
    traceback='...'
)
```

### 6. 记录警告

```python
from system_logger import log_warning

log_warning(
    warning_type='PriceValidation',
    warning_message='价格不在合理范围内',
    warning_details={'price': 81800.0}
)
```

## 🔧 自动集成

以下操作已自动集成日志记录：

1. ✅ **对话录入** (`src/add_de_conversation.py`)
   - 自动记录对话
   - 自动记录策略提取
   - 自动记录价格验证

2. ✅ **交易记录提取** (`src/extract_trades_from_conversations.py`)
   - 自动记录提取操作

3. ✅ **价格同步** (`src/sync_btc_prices_daily.py`)
   - 自动记录同步操作
   - 自动记录错误

## 📈 查询日志

### 搜索操作日志

```python
from elasticsearch_logger import get_es_logger

logger = get_es_logger()

# 搜索操作日志
results = logger.search(
    query='signal_generation',
    start_date='2025-12-01',
    end_date='2025-12-31',
    limit=100
)
```

### 按操作类型过滤

```python
# 搜索特定操作类型
results = logger.es.search(
    index='qingniao_conversations-*',
    body={
        "query": {
            "term": {"operation_type": "signal_generation"}
        },
        "sort": [{"timestamp": {"order": "desc"}}]
    }
)
```

### 按日志级别过滤

```python
# 搜索错误日志
results = logger.es.search(
    index='qingniao_conversations-*',
    body={
        "query": {
            "term": {"log_level": "error"}
        },
        "sort": [{"timestamp": {"order": "desc"}}]
    }
)
```

## 📝 日志结构

### 对话日志结构

```json
{
  "log_id": "uuid",
  "log_type": "conversation",
  "log_level": "info",
  "timestamp": "2025-12-31T00:34:00",
  "user_message": "...",
  "trader_message": "...",
  "source": "discord",
  "btc_price": 88710.0,
  "has_trading_info": true,
  "has_evaluation": true
}
```

### 操作日志结构

```json
{
  "log_id": "uuid",
  "log_type": "operation",
  "log_level": "info",
  "operation_type": "signal_generation",
  "timestamp": "2025-12-31T00:34:00",
  "btc_price": 88710.0,
  "operation_details": {
    "signals_count": 5,
    "timeframe": "15m",
    "system_name": "de"
  }
}
```

## 🔗 相关文件

- `src/system_logger.py` - 系统操作日志记录器
- `src/elasticsearch_logger.py` - Elasticsearch日志记录器
- `README_Elasticsearch日志系统说明.md` - Elasticsearch系统说明

## ✅ 检查清单

- [x] 系统操作日志记录器已创建
- [x] 对话录入已集成
- [x] 交易记录提取已集成
- [x] 价格同步已集成
- [x] 价格验证已集成
- [x] 错误和警告记录已支持
- [ ] 信号生成已集成（需要更新generate_btc_de_signals.py）
- [ ] 性能监控已集成（可选）

## 📌 注意事项

1. **容错机制**：Elasticsearch不可用时不影响主流程
2. **至少保留3个月**：默认保留90天
3. **原始记录**：所有原始数据都会完整保存
4. **性能考虑**：大量操作时建议使用Elasticsearch集群


