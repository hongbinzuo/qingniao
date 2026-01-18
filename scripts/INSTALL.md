# K线数据获取工具安装说明

## 📋 前置要求

- Go 1.21+ （已安装：go1.25.5）
- DuckDB（Python端已安装）

## 🔧 安装步骤

### 1. 初始化Go模块

```bash
cd scripts
go mod init abu-kline-fetcher
```

### 2. 安装DuckDB Go驱动

**选项1：使用go-duckdb（推荐）**

```bash
go get github.com/marcboeker/go-duckdb
```

**选项2：如果go-duckdb不可用，可以使用SQLite驱动（DuckDB支持SQLite兼容）**

编辑`scripts/abu_kline_fetcher.go`，修改导入：
```go
// 将
_ "github.com/marcboeker/go-duckdb"

// 改为（如果go-duckdb不可用）
_ "modernc.org/sqlite"
```

然后修改连接字符串：
```go
// 将
db, err := sql.Open("duckdb", dbPath)

// 改为
db, err := sql.Open("sqlite", dbPath)
```

**选项3：使用纯Go实现（最可靠）**

如果上述方案都不可用，可以使用标准库+文件操作，或使用HTTP接口与Python交互。

### 3. 验证安装

```bash
cd scripts
go mod tidy
go build -o abu_kline_fetcher.exe abu_kline_fetcher.go
```

如果编译成功，说明依赖已安装。

## 🚀 使用

### 基本使用

```bash
# Windows
.\abu_kline_fetcher.exe --symbols BTC,ETH,SOL --timeframe 15m --days 90

# 或直接运行
go run abu_kline_fetcher.go --symbols BTC,ETH,SOL --timeframe 15m --days 90
```

### 增量获取

```bash
go run abu_kline_fetcher.go --symbols BTC,ETH,SOL --timeframe 15m --incremental
```

## ⚠️ 常见问题

### 1. go-duckdb包找不到

如果`go get github.com/marcboeker/go-duckdb`失败，可以：
- 检查网络连接
- 使用Go代理：`go env -w GOPROXY=https://goproxy.cn,direct`
- 使用SQLite驱动作为备选方案

### 2. 编译错误

如果遇到编译错误：
- 确保Go版本>=1.21
- 运行`go mod tidy`清理依赖
- 检查导入路径是否正确

### 3. 运行时错误

如果运行时出错：
- 检查数据库目录是否存在（`data/kline_data/`）
- 检查文件权限
- 查看错误日志

## 📝 备选方案

如果Go依赖安装有问题，可以考虑：

1. **使用Python实现**（参考`src/get_extended_gateio_klines.py`）
2. **使用HTTP API**：Go获取数据，通过HTTP API写入
3. **使用文件系统**：Go写入JSON文件，Python读取



