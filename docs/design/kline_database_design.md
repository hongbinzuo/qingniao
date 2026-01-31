# K线数据库设计方案

**设计日期**: 2025-01-11  
**目标**: 使用Go获取K线数据，存储在独立的时序数据库中，支持增量获取

---

## 📊 数据库选择

### 候选方案对比

| 数据库 | 类型 | 优点 | 缺点 | 推荐度 |
|--------|------|------|------|--------|
| **QuestDB** | 时序数据库 | ✅ 高性能写入/查询<br>✅ 支持PostgreSQL协议<br>✅ 单文件部署简单<br>✅ Go和Python都有客户端 | ⚠️ 社区相对较小 | ⭐⭐⭐⭐⭐ |
| **InfluxDB** | 时序数据库 | ✅ 生态成熟<br>✅ 功能丰富 | ⚠️ 需要单独服务<br>⚠️ 配置较复杂 | ⭐⭐⭐⭐ |
| **TimescaleDB** | PostgreSQL扩展 | ✅ SQL兼容性好<br>✅ 功能强大 | ⚠️ 需要PostgreSQL<br>⚠️ 部署较复杂 | ⭐⭐⭐ |
| **DuckDB** | 分析型数据库 | ✅ 零配置<br>✅ 已在使用<br>✅ 轻量级 | ⚠️ 不是专门为时序设计 | ⭐⭐⭐⭐ |

### 推荐方案：QuestDB ⭐

**理由**：
1. ✅ **高性能**：专为时序数据设计，写入和查询性能优秀
2. ✅ **简单部署**：单文件部署，不需要额外服务
3. ✅ **PostgreSQL协议**：可以使用标准SQL和PostgreSQL客户端
4. ✅ **跨语言支持**：Go和Python都有成熟的客户端库
5. ✅ **增量获取友好**：时间序列查询性能优秀

**如果不想安装新数据库**：使用DuckDB（已有，零配置，性能足够）

---

## 🗄️ 数据库Schema设计

### 方案1：QuestDB（推荐）

```sql
CREATE TABLE klines (
    timestamp TIMESTAMP,
    exchange SYMBOL,
    symbol SYMBOL,
    timeframe SYMBOL,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume DOUBLE,
    PRIMARY KEY (timestamp, exchange, symbol, timeframe)
) TIMESTAMP(timestamp) PARTITION BY DAY;
```

**索引**：
- 主键：(timestamp, exchange, symbol, timeframe)
- 自动按时间分区（按天）

### 方案2：DuckDB（备选）

```sql
CREATE TABLE klines (
    timestamp BIGINT,
    exchange TEXT,
    symbol TEXT,
    timeframe TEXT,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume DOUBLE,
    created_at TEXT,
    PRIMARY KEY (timestamp, exchange, symbol, timeframe)
);

CREATE INDEX idx_klines_symbol_tf ON klines(symbol, timeframe);
CREATE INDEX idx_klines_timestamp ON klines(timestamp);
```

---

## 📁 数据库文件位置

**推荐**：`data/kline_data/`

- QuestDB: `data/kline_data/questdb/` (目录)
- DuckDB: `data/kline_data/klines.duckdb` (文件)

---

## 🔄 增量获取逻辑

### 流程

1. **查询数据库中最新的时间戳**
   ```sql
   SELECT MAX(timestamp) FROM klines 
   WHERE exchange='gate' AND symbol='BTC' AND timeframe='15m'
   ```

2. **计算需要获取的时间范围**
   - 如果数据库为空：获取90天数据（或其他默认值）
   - 如果数据库有数据：从最新时间戳开始，获取到现在

3. **从Gate.io获取增量数据**
   - 使用from/to参数获取指定时间范围
   - 并发获取多个币种

4. **写入数据库（UPSERT）**
   - 如果数据已存在（主键冲突），跳过或更新
   - 只插入新数据

---

## 🚀 Go程序设计

### 功能模块

1. **数据库管理**
   - 连接QuestDB/DuckDB
   - 创建表和索引
   - 查询最新时间戳
   - 插入/更新数据

2. **Gate.io API客户端**
   - 并发获取多个币种
   - 支持from/to参数（增量获取）
   - 错误处理和重试

3. **增量获取逻辑**
   - 查询数据库
   - 计算时间范围
   - 获取增量数据
   - 写入数据库

4. **命令行接口**
   ```bash
   go run scripts/abu/abu_kline_fetcher.go \
     --symbols BTC,ETH,SOL \
     --timeframe 15m \
     --days 90 \
     --incremental \
     --concurrency 20
   ```

---

## 🐍 Python集成

### 读取K线数据

```python
# 使用QuestDB
from questdb.ingress import Sender
import psycopg2

# 或使用DuckDB（如果选择DuckDB）
import duckdb

def load_klines(symbol, timeframe, limit=200):
    # 从数据库读取
    ...
```

---

## 📈 性能预期

### 数据获取

- **300个币种，15分钟K线（90天）**：
  - 串行：~60-120秒
  - Go并发（20线程）：~10-20秒
  - **提升：5-10倍**

### 数据库查询

- **查询单个币种最新时间戳**：<1ms
- **查询300个币种K线数据**：~50-100ms
- **增量写入**：~100-500ms（取决于数据量）

---

## 🔧 实施步骤

1. ✅ 评估数据库选择
2. ⏳ 安装QuestDB（或使用DuckDB）
3. ⏳ 设计数据库Schema
4. ⏳ 实现Go程序（数据库管理 + Gate.io API）
5. ⏳ 实现增量获取逻辑
6. ⏳ 测试和优化
7. ⏳ Python集成（读取数据）

---

## 📝 配置建议

### QuestDB配置

- **端口**：9000 (PostgreSQL), 9009 (HTTP), 8812 (ILP)
- **数据目录**：`data/kline_data/questdb/`
- **内存限制**：根据数据量调整（默认足够）

### DuckDB配置（如果选择）

- **文件路径**：`data/kline_data/klines.duckdb`
- **内存模式**：默认（足够）



