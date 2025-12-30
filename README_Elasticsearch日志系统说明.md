# Elasticsearch日志系统说明

## 📋 概述

本系统使用Elasticsearch保存**所有用户和AI之间的对话记录**（无论关于什么内容），确保数据完整性和可检索性。所有对话记录都会同时保存到数据库和Elasticsearch，至少保留3个月。

**重要说明**：
- ✅ 记录**所有对话**，不仅仅是De.相关的对话
- ✅ 记录**所有话题**，包括技术问题、系统操作、策略讨论、错误处理等
- ✅ 记录**原始内容**，完整保存用户消息和AI回复

## ✅ 功能特性

1. **双重保存**：对话记录同时保存到数据库（DuckDB）和Elasticsearch
2. **原始记录**：保存完整的原始对话内容，包括用户评价、价格验证等元数据
3. **自动索引**：按月自动创建索引，便于管理和清理
4. **保留策略**：默认保留90天（3个月），可配置
5. **全文搜索**：支持全文搜索对话内容
6. **容错机制**：Elasticsearch不可用时不影响数据库保存

## 🚀 快速开始

### 1. 安装Elasticsearch

#### 方式一：使用Docker（推荐）

```bash
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -p 9300:9300 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  elasticsearch:8.11.0
```

#### 方式二：本地安装

1. 下载Elasticsearch：https://www.elastic.co/downloads/elasticsearch
2. 解压并运行：
   ```bash
   bin/elasticsearch
   ```

### 2. 安装Python客户端

```bash
pip install elasticsearch
```

### 3. 配置

编辑 `config/elasticsearch_config.json`：

```json
{
  "hosts": ["localhost:9200"],
  "index_prefix": "qingniao_conversations",
  "retention_days": 90
}
```

### 4. 测试连接

```bash
python src/elasticsearch_logger.py
```

## 📊 数据结构

### 索引结构

索引按月分片，格式：`qingniao_conversations-YYYY.MM`

例如：
- `qingniao_conversations-2025.01`
- `qingniao_conversations-2025.02`

### 文档结构

```json
{
  "log_id": "uuid",
  "session_id": "session-uuid",
  "timestamp": "2025-12-31T00:34:00",
  "user_message": "用户消息",
  "assistant_message": "助手回复",
  "trader_message": "De.的消息",
  "source": "discord",
  "btc_price": 88710.0,
  "has_trading_info": true,
  "has_evaluation": true,
  "evaluation_content": "用户评价内容",
  "raw_data": {
    "conversation_id": 4686,
    "extracted_content": "提取的内容",
    "original_trader_message": "原始消息",
    "original_user_message": "原始用户消息"
  },
  "created_at": "2025-12-31T00:34:00"
}
```

## 🔍 使用示例

### 1. 自动记录（已集成）

#### De.对话录入
所有通过 `add_de_conversation.py` 录入的对话都会自动保存到Elasticsearch：

```bash
python src/add_de_conversation.py "0:34" "止损8871 或者886下面一点"
```

#### 所有对话记录
使用 `conversation_logger.py` 记录所有用户和AI的对话：

```python
from conversation_logger import log_conversation

# 记录任何对话（无论关于什么）
log_conversation(
    user_message="如何生成BTC信号？",
    assistant_message="使用 generate_btc_de_signals.py 脚本...",
    conversation_type='trading'  # 或 'general', 'system', 'error' 等
)
```

#### 通用对话记录器
使用 `universal_conversation_logger.py` 在任何地方记录对话：

```python
from universal_conversation_logger import log_user_assistant_conversation

# 记录任何对话
log_user_assistant_conversation(
    "这个功能怎么用？",
    "这个功能用于...",
    conversation_type='general'
)
```

### 2. 手动记录

```python
from elasticsearch_logger import get_es_logger

logger = get_es_logger()

# 记录对话
doc_id = logger.log_conversation(
    user_message="用户消息",
    assistant_message="助手回复",
    trader_message="De.的消息",
    timestamp="2025-12-31 00:34:00",
    source="discord",
    btc_price=88710.0
)
```

### 3. 搜索对话

```python
from elasticsearch_logger import get_es_logger

logger = get_es_logger()

# 搜索关键词
results = logger.search(
    query="止损",
    start_date="2025-12-01",
    end_date="2025-12-31",
    limit=100
)

for result in results:
    print(result['trader_message'])
```

### 4. 清理旧数据

```python
from elasticsearch_logger import get_es_logger

logger = get_es_logger()

# 清理90天前的数据
logger.cleanup_old_indices(days=90)
```

## 📈 监控和维护

### 查看统计信息

```python
from elasticsearch_logger import get_es_logger

logger = get_es_logger()
stats = logger.get_stats()
print(stats)
```

输出示例：
```json
{
  "available": true,
  "total_docs": 1234,
  "indices": [
    "qingniao_conversations-2025.01",
    "qingniao_conversations-2025.02"
  ],
  "retention_days": 90
}
```

### 定期清理（建议设置定时任务）

创建 `scripts/cleanup_es_logs.py`：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""定期清理Elasticsearch旧日志"""

from elasticsearch_logger import get_es_logger

if __name__ == '__main__':
    logger = get_es_logger()
    if logger.available:
        logger.cleanup_old_indices()
    else:
        print("Elasticsearch不可用，跳过清理")
```

## ⚙️ 配置说明

### 配置文件位置

`config/elasticsearch_config.json`

### 配置项说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `hosts` | Elasticsearch服务器地址列表 | `["localhost:9200"]` |
| `index_prefix` | 索引前缀 | `"qingniao_conversations"` |
| `retention_days` | 保留天数（至少3个月=90天） | `90` |

### 多服务器配置

```json
{
  "hosts": [
    "es1.example.com:9200",
    "es2.example.com:9200",
    "es3.example.com:9200"
  ],
  "index_prefix": "qingniao_conversations",
  "retention_days": 90
}
```

## 🔧 故障处理

### Elasticsearch不可用

如果Elasticsearch不可用：
1. 系统会继续正常工作，对话记录仍会保存到数据库
2. 会显示警告信息，但不影响主流程
3. 恢复连接后，可以手动同步数据

### 手动同步数据

如果需要将数据库中的历史数据同步到Elasticsearch：

```python
from db_manager_trader import TraderDBManager
from elasticsearch_logger import get_es_logger

db = TraderDBManager('de')
es_logger = get_es_logger()

# 获取所有对话记录
conversations = db.get_conversations(limit=None)

# 同步到Elasticsearch
for conv in conversations:
    es_logger.log_de_conversation(
        timestamp=conv['timestamp'],
        trader_message=conv['trader_message'],
        user_message=conv['user_message'],
        source=conv['source'],
        btc_price=conv['btc_price'],
        conversation_id=conv['id'],
        has_trading_info=bool(conv.get('extracted_content')),
        has_evaluation=bool(conv.get('user_evaluation')),
        evaluation_content=conv.get('user_evaluation'),
        extracted_content=conv.get('extracted_content')
    )
```

## 📝 注意事项

1. **至少保留3个月**：根据用户要求，默认保留90天，可根据需要调整
2. **原始记录**：保存完整的原始对话内容，包括所有元数据
3. **容错机制**：Elasticsearch不可用时不影响数据库保存
4. **索引管理**：按月自动创建索引，便于管理和清理
5. **性能考虑**：大量数据时建议使用Elasticsearch集群

## 🔗 相关文档

- [Elasticsearch官方文档](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Python Elasticsearch客户端文档](https://elasticsearch-py.readthedocs.io/)

## ✅ 检查清单

- [ ] Elasticsearch已安装并运行
- [ ] Python客户端已安装（`pip install elasticsearch`）
- [ ] 配置文件已创建（`config/elasticsearch_config.json`）
- [ ] 测试连接成功（`python src/elasticsearch_logger.py`）
- [ ] 对话记录自动保存到Elasticsearch
- [ ] 定期清理任务已设置（可选）

