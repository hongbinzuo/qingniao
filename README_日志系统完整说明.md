# 日志系统完整说明

## ✅ 已完成

根据用户要求，已实现完整的日志系统，记录所有关键系统操作，至少保留3个月。

## 📋 实现内容

### 1. Elasticsearch日志记录器 (`src/elasticsearch_logger.py`)

- ✅ 支持对话记录和操作日志
- ✅ 自动索引管理（按月分片）
- ✅ 原始数据完整保存
- ✅ 至少保留3个月（90天）
- ✅ 容错机制
- ✅ 全文搜索功能

### 2. 系统操作日志记录器 (`src/system_logger.py`)

- ✅ 统一的日志接口
- ✅ 支持多种操作类型
- ✅ 日志级别管理（info/warning/error/critical）
- ✅ 便捷函数

### 3. 已集成的关键操作

#### ✅ 对话录入 (`src/add_de_conversation.py`)
- 自动记录对话
- 自动记录策略提取
- 自动记录价格验证

#### ✅ 交易记录提取 (`src/extract_trades_from_conversations.py`)
- 自动记录提取操作
- 记录提取的交易详情

#### ✅ 价格同步 (`src/sync_btc_prices_daily.py`)
- 自动记录同步操作
- 记录同步结果和错误

### 4. 支持的操作类型

| 操作类型 | 说明 | 状态 |
|---------|------|------|
| `conversation` | 对话记录 | ✅ 已集成 |
| `signal_generation` | 信号生成 | ✅ 已支持 |
| `trade_record_add` | 交易记录添加 | ✅ 已支持 |
| `trade_record_extract` | 交易记录提取 | ✅ 已集成 |
| `trade_record_update` | 交易记录更新 | ✅ 已支持 |
| `price_sync` | 价格同步 | ✅ 已集成 |
| `strategy_extraction` | 策略提取 | ✅ 已集成 |
| `price_validation` | 价格验证 | ✅ 已集成 |
| `price_warning` | 价格警告 | ✅ 已集成 |
| `error` | 错误 | ✅ 已支持 |
| `warning` | 警告 | ✅ 已支持 |
| `performance_metric` | 性能指标 | ✅ 已支持 |

## 🚀 使用方式

### 基本使用

```python
from system_logger import get_system_logger

logger = get_system_logger()

# 记录信号生成
logger.log_signal_generation(
    signals_count=5,
    timeframe='15m',
    system_name='de',
    current_price=88710.0
)

# 记录交易记录
logger.log_trade_record(
    action='add',
    trade_id=123,
    details={'entry_price': 88710.0}
)

# 记录价格同步
logger.log_price_sync(
    timeframe='5m',
    records_synced=100,
    success=True
)

# 记录价格验证
logger.log_price_validation(
    price=81800.0,
    timestamp='2025-12-31 00:23:00',
    is_valid=False,
    suggestion=88100.0
)

# 记录错误
logger.log_error(
    error_type='APIError',
    error_message='无法获取价格数据'
)
```

### 便捷函数

```python
from system_logger import (
    log_signal_generation,
    log_trade_record,
    log_price_sync,
    log_price_validation,
    log_error,
    log_warning
)

# 使用便捷函数
log_signal_generation(5, '15m', system_name='de', current_price=88710.0)
log_trade_record('add', trade_id=123)
log_price_sync('5m', 100)
log_price_validation(81800.0, '2025-12-31 00:23:00', False)
log_error('APIError', '无法获取价格数据')
```

## 🔍 查询日志

### 搜索对话记录

```python
from elasticsearch_logger import get_es_logger

logger = get_es_logger()

# 搜索对话
results = logger.search(
    query='止损',
    start_date='2025-12-01',
    end_date='2025-12-31'
)
```

### 搜索操作日志

```python
# 搜索操作日志
results = logger.es.search(
    index='qingniao_conversations-*',
    body={
        "query": {
            "bool": {
                "must": [
                    {"term": {"log_type": "operation"}},
                    {"term": {"operation_type": "signal_generation"}}
                ]
            }
        },
        "sort": [{"timestamp": {"order": "desc"}}]
    }
)
```

### 搜索错误日志

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

## 📊 日志结构

### 对话日志

```json
{
  "log_id": "uuid",
  "log_type": "conversation",
  "log_level": "info",
  "timestamp": "2025-12-31T00:34:00",
  "user_message": "用户消息",
  "trader_message": "De.的消息",
  "source": "discord",
  "btc_price": 88710.0,
  "has_trading_info": true,
  "has_evaluation": true,
  "evaluation_content": "用户评价",
  "raw_data": {...}
}
```

### 操作日志

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
  },
  "raw_data": {...}
}
```

## 🔧 配置

配置文件：`config/elasticsearch_config.json`

```json
{
  "hosts": ["localhost:9200"],
  "index_prefix": "qingniao_conversations",
  "retention_days": 90
}
```

## 📝 文档

- `README_Elasticsearch日志系统说明.md` - Elasticsearch系统详细说明
- `README_系统操作日志说明.md` - 系统操作日志详细说明
- `README_对话日志系统集成说明.md` - 对话日志系统集成说明

## ✅ 检查清单

- [x] Elasticsearch日志记录器已创建
- [x] 系统操作日志记录器已创建
- [x] 对话录入已集成日志
- [x] 交易记录提取已集成日志
- [x] 价格同步已集成日志
- [x] 价格验证已集成日志
- [x] 策略提取已集成日志
- [x] 错误和警告记录已支持
- [x] 文档已完善
- [ ] Elasticsearch已安装（需要用户操作）
- [ ] Python客户端已安装（需要用户操作）

## 🔗 相关文件

- `src/elasticsearch_logger.py` - Elasticsearch日志记录器
- `src/system_logger.py` - 系统操作日志记录器
- `src/add_de_conversation.py` - 对话录入（已集成）
- `src/extract_trades_from_conversations.py` - 交易记录提取（已集成）
- `src/sync_btc_prices_daily.py` - 价格同步（已集成）
- `config/elasticsearch_config.json` - 配置文件

## 📌 注意事项

1. **容错机制**：Elasticsearch不可用时不影响主流程
2. **至少保留3个月**：默认保留90天，可配置
3. **原始记录**：所有原始数据都会完整保存
4. **自动集成**：关键操作已自动集成，无需手动调用
5. **性能考虑**：大量操作时建议使用Elasticsearch集群

## 🎯 总结

所有关键系统操作现在都会：
1. ✅ 自动记录到Elasticsearch
2. ✅ 保存完整的原始数据
3. ✅ 至少保留3个月（90天）
4. ✅ 支持全文搜索和过滤
5. ✅ 容错机制，不影响主流程

系统已完全集成，用户只需安装Elasticsearch和Python客户端即可使用。







