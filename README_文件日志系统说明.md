# 文件日志系统说明

## 📋 概述

这是一个**简单、高效、零依赖**的文件日志系统，用于替代Elasticsearch。

### ✅ 优势

1. **零外部依赖** - 只使用Python标准库（json, pathlib, datetime）
2. **简单易用** - 无需安装和配置复杂服务
3. **高效** - 追加写入，性能优秀
4. **易于查看** - JSON Lines格式，可直接用文本编辑器查看
5. **易于管理** - 按日期分文件，自动清理旧数据
6. **数据兼容** - 可以稍后迁移到Elasticsearch（数据格式兼容）

### 📁 文件格式

- **格式**：JSON Lines (`.jsonl`)，每行一个JSON对象
- **文件命名**：`logs_YYYYMMDD.jsonl`（按日期分文件）
- **存储位置**：`data/logs/` 目录
- **保留策略**：
  - **最近1个月**：保持原始JSON Lines格式（未压缩）
  - **1-3个月**：压缩为`.jsonl.gz`格式（节省空间）
  - **超过3个月**：自动删除

## 🚀 快速开始

### 基本使用

```python
from file_logger import get_file_logger

logger = get_file_logger()

# 记录对话
logger.log_conversation(
    user_message="用户消息",
    assistant_message="助手回复",
    conversation_type='general'
)

# 记录系统操作
logger.log_operation(
    operation_type='signal_generation',
    operation_details={'signal_id': 'BTC_001'},
    log_level='info'
)

# 搜索日志
results = logger.search(query='BTC', limit=10)

# 获取统计信息
stats = logger.get_stats()
```

### API接口

#### 1. 记录对话

```python
logger.log_conversation(
    user_message: str,              # 用户消息
    assistant_message: str,          # 助手回复
    timestamp: str = None,           # 时间戳（格式：YYYY-MM-DD HH:MM:SS）
    session_id: str = None,          # 会话ID
    source: str = 'user_assistant',  # 来源
    conversation_type: str = 'general',  # 对话类型
    metadata: Dict = None            # 额外元数据
) -> str  # 返回日志ID
```

#### 2. 记录De.交易员对话

```python
logger.log_de_conversation(
    timestamp: str,                  # 时间戳
    user_message: str,               # 用户消息
    trader_message: str,             # 交易员消息
    btc_price: float = None,         # BTC价格
    user_evaluation: str = None,     # 用户评价
    evaluation_keywords: str = None, # 评价关键词
    metadata: Dict = None            # 额外元数据
) -> str  # 返回日志ID
```

#### 3. 记录系统操作

```python
logger.log_operation(
    operation_type: str,             # 操作类型
    operation_details: Dict,         # 操作详情
    log_level: str = 'info',         # 日志级别（info/warning/error）
    timestamp: str = None,           # 时间戳
    btc_price: float = None,         # BTC价格
    raw_data: Dict = None            # 原始数据
) -> str  # 返回日志ID
```

#### 4. 搜索日志

```python
results = logger.search(
    query: str = None,               # 搜索关键词
    log_type: str = None,            # 日志类型过滤
    start_date: datetime = None,     # 开始日期
    end_date: datetime = None,       # 结束日期
    limit: int = 100                 # 结果数量限制
) -> List[Dict]  # 返回日志条目列表
```

#### 5. 压缩旧日志

```python
compressed_count = logger.compress_old_logs()  # 压缩1个月之前的日志
# 返回压缩的文件数量
```

#### 6. 清理过期日志

```python
deleted_count = logger.cleanup_old_logs(days: int = None)  # 默认删除超过3个月的日志
# 返回删除的文件数量（包括压缩文件）
```

#### 7. 维护日志（推荐）

```python
result = logger.maintain_logs()  # 自动压缩旧日志并清理过期日志
# 返回: {'compressed': 5, 'deleted': 2}
```

#### 8. 获取统计信息

```python
stats = logger.get_stats()
# 返回: {
#   'available': True,
#   'log_dir': 'data/logs',
#   'retention_days': 90,
#   'total_files': 10,
#   'total_entries': 1234,
#   'oldest_date': '2024-10-01',
#   'newest_date': '2024-12-31'
# }
```

## 📝 日志格式示例

### 对话日志

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-12-31 12:00:00",
  "log_type": "conversation",
  "user_message": "用户消息",
  "assistant_message": "助手回复",
  "source": "user_assistant",
  "conversation_type": "general",
  "session_id": "session_123"
}
```

### 操作日志

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "timestamp": "2024-12-31 12:00:00",
  "log_type": "operation",
  "operation_type": "signal_generation",
  "operation_details": {"signal_id": "BTC_001"},
  "log_level": "info",
  "btc_price": 88000.0
}
```

## 🔄 已集成的模块

以下模块已自动切换到文件日志系统：

1. ✅ `src/system_logger.py` - 系统操作日志
2. ✅ `src/conversation_logger.py` - 对话日志
3. ✅ `src/add_de_conversation.py` - De.交易员对话记录

## 🛠️ 维护操作

### 查看日志

直接打开文件查看（JSON Lines格式）：
```
data/logs/logs_20241231.jsonl
```

或使用Python脚本：
```python
from file_logger import get_file_logger

logger = get_file_logger()
results = logger.search(query='BTC', limit=100)
for entry in results:
    print(entry)
```

### 维护日志（推荐方式）

运行维护脚本：
```cmd
python scripts/maintain_logs.py
```

或在代码中调用：
```python
from file_logger import get_file_logger

logger = get_file_logger()
result = logger.maintain_logs()  # 自动压缩和清理
print(f"压缩: {result['compressed']} 个文件")
print(f"删除: {result['deleted']} 个文件")
```

### 手动压缩旧日志

```python
from file_logger import get_file_logger

logger = get_file_logger()
compressed_count = logger.compress_old_logs()  # 压缩1个月之前的日志
print(f"已压缩 {compressed_count} 个日志文件")
```

### 手动清理过期日志

```python
from file_logger import get_file_logger

logger = get_file_logger()
deleted_count = logger.cleanup_old_logs(days=90)  # 删除超过3个月的日志
print(f"已删除 {deleted_count} 个日志文件")
```

### 统计信息

```python
from file_logger import get_file_logger

logger = get_file_logger()
stats = logger.get_stats()
print(stats)
```

## 📊 性能特点

- **写入性能**：追加写入，O(1)复杂度，非常高效
- **读取性能**：按日期分文件，只读取相关文件；自动处理压缩文件
- **存储空间**：
  - 原始文件：文本格式
  - 压缩文件：gzip压缩，通常可节省70-80%空间
  - 自动压缩1个月之前的日志，平衡性能和存储
- **查询性能**：简单关键词搜索，适合中等规模数据（几万到几十万条）

## 🔄 日志维护策略

### 自动维护

建议定期运行维护脚本（如每日或每周）：
```cmd
python scripts/maintain_logs.py
```

### 维护策略说明

1. **0-1个月**：保持原始`.jsonl`格式，便于快速读取
2. **1-3个月**：压缩为`.jsonl.gz`格式，节省存储空间
3. **超过3个月**：自动删除

这样可以：
- 保证最近数据访问速度
- 节省存储空间（压缩后通常节省70-80%）
- 自动清理过期数据

## 🔮 未来扩展

如果需要更强大的搜索功能，可以：

1. **迁移到Elasticsearch** - 数据格式兼容，可以编写脚本迁移
2. **使用SQLite** - 如果需要SQL查询，可以导入到SQLite
3. **使用全文搜索引擎** - 如Whoosh（Python库，轻量级）

## ⚠️ 注意事项

1. **文件大小** - 单日日志文件可能较大，建议定期清理
2. **并发写入** - 追加写入是原子操作，多进程写入是安全的
3. **备份** - 建议定期备份 `data/logs/` 目录
4. **搜索性能** - 对于大量数据（百万级），搜索可能较慢，建议按日期范围限制

## 📌 与Elasticsearch对比

| 特性 | 文件日志系统 | Elasticsearch |
|------|------------|---------------|
| 依赖 | 零依赖 | 需要安装ES服务 |
| 配置 | 无需配置 | 需要配置SSL/认证 |
| 性能 | 写入极快 | 写入快，搜索极快 |
| 搜索 | 简单关键词 | 全文搜索、复杂查询 |
| 扩展性 | 中等（几十万条） | 极高（百万到亿级） |
| 适用场景 | 开发、小规模生产 | 大规模生产 |

**建议**：先用文件日志系统，等数据量大了或需要复杂搜索时再迁移到Elasticsearch。

