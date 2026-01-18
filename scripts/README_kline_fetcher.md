# ABU K线数据获取工具（Go版本）

使用Go语言并发从Gate.io获取K线数据，存储到DuckDB数据库，支持增量获取。

## 📋 功能特性

- ✅ **高性能并发**：使用goroutine并发获取多个币种数据
- ✅ **增量获取**：自动检测数据库中最新的时间戳，只获取增量数据
- ✅ **Gate.io支持**：从Gate.io获取数据（避免币安限制）
- ✅ **DuckDB存储**：使用DuckDB存储K线数据（零配置，高性能）
- ✅ **自动去重**：使用主键自动去重，避免重复数据

## 🚀 使用方法

### 安装依赖

```bash
go mod init abu-kline-fetcher
go get github.com/marcboeker/go-duckdb
```

### 基本使用

```bash
# 获取BTC、ETH、SOL的15分钟K线数据（增量）
go run scripts/abu_kline_fetcher.go \
  --symbols BTC,ETH,SOL \
  --timeframe 15m \
  --days 90 \
  --incremental

# 获取多个币种（使用配置文件中的TOP 50币种）
go run scripts/abu_kline_fetcher.go \
  --symbols BTC,ETH,SOL,BNB,XRP,ADA,AVAX,DOGE,LINK,DOT \
  --timeframe 15m \
  --concurrency 20 \
  --incremental

# 全量获取（覆盖模式，不使用增量）
go run scripts/abu_kline_fetcher.go \
  --symbols BTC,ETH \
  --timeframe 15m \
  --days 90 \
  --incremental=false

# 指定数据库路径
go run scripts/abu_kline_fetcher.go \
  --symbols BTC,ETH \
  --timeframe 15m \
  --db data/kline_data/klines.duckdb
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--symbols` | 币种列表（逗号分隔） | BTC,ETH,SOL |
| `--timeframe` | 时间框架（5m,15m,1h,4h,1d） | 15m |
| `--days` | 获取天数（初始获取或全量获取） | 90 |
| `--db` | 数据库文件路径 | data/kline_data/klines.duckdb |
| `--concurrency` | 最大并发数 | 20 |
| `--incremental` | 是否启用增量获取 | true |
| `--limit` | 每次请求最大K线数 | 1000 |

## 📊 数据库结构

### 表结构

```sql
CREATE TABLE klines (
    timestamp BIGINT NOT NULL,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    open DOUBLE NOT NULL,
    high DOUBLE NOT NULL,
    low DOUBLE NOT NULL,
    close DOUBLE NOT NULL,
    volume DOUBLE NOT NULL,
    created_at TEXT,
    PRIMARY KEY (timestamp, exchange, symbol, timeframe)
);
```

### 索引

- `idx_klines_symbol_tf`: (symbol, timeframe)
- `idx_klines_timestamp`: (timestamp)
- `idx_klines_exchange_symbol_tf`: (exchange, symbol, timeframe)

## 🔄 增量获取逻辑

1. **查询数据库**：获取指定币种和时间框架的最新时间戳
2. **计算时间范围**：
   - 如果数据库为空：获取`--days`天的数据
   - 如果数据库有数据：从最新时间戳开始，获取到现在
3. **获取增量数据**：从Gate.io获取指定时间范围的数据
4. **写入数据库**：使用UPSERT（ON CONFLICT DO NOTHING）插入新数据

## 📈 性能

- **300个币种，15分钟K线（90天）**：
  - 首次获取：~10-20秒（并发20）
  - 增量更新：~2-5秒（只获取新数据）

## 🐍 Python集成

### 读取K线数据

```python
import duckdb

def load_klines(symbol, timeframe, limit=200, exchange='gate'):
    db_path = 'data/kline_data/klines.duckdb'
    conn = duckdb.connect(db_path)
    
    query = '''
        SELECT timestamp, open, high, low, close, volume
        FROM klines
        WHERE exchange = ? AND symbol = ? AND timeframe = ?
        ORDER BY timestamp DESC
        LIMIT ?
    '''
    rows = conn.execute(query, [exchange, symbol, timeframe, limit]).fetchall()
    conn.close()
    
    # 转换为字典列表（从早到晚）
    rows.reverse()
    return [
        {
            'timestamp': int(r[0]),
            'open': float(r[1]),
            'high': float(r[2]),
            'low': float(r[3]),
            'close': float(r[4]),
            'volume': float(r[5])
        }
        for r in rows
    ]

# 使用示例
klines = load_klines('BTC', '15m', limit=200)
```

### 获取最新时间戳

```python
def get_latest_timestamp(symbol, timeframe, exchange='gate'):
    db_path = 'data/kline_data/klines.duckdb'
    conn = duckdb.connect(db_path)
    
    query = '''
        SELECT MAX(timestamp)
        FROM klines
        WHERE exchange = ? AND symbol = ? AND timeframe = ?
    '''
    result = conn.execute(query, [exchange, symbol, timeframe]).fetchone()
    conn.close()
    
    return int(result[0]) if result and result[0] else None
```

## 🔧 编译为可执行文件

```bash
# Windows
go build -o scripts/abu_kline_fetcher.exe scripts/abu_kline_fetcher.go

# Linux/macOS
go build -o scripts/abu_kline_fetcher scripts/abu_kline_fetcher.go
```

## 📝 注意事项

1. **数据库目录**：程序会自动创建数据库目录（如果不存在）
2. **并发控制**：建议并发数不要超过50，避免对Gate.io造成压力
3. **数据去重**：使用主键自动去重，重复运行不会产生重复数据
4. **时间戳格式**：Gate.io返回的时间戳是秒级，统一存储为秒级

## 🔄 后续优化

- [ ] 支持QuestDB（时序数据库）
- [ ] 支持批量查询最新时间戳
- [ ] 添加数据验证和清洗
- [ ] 支持更多交易所（Binance等）



