package main

import (
	"database/sql"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	_ "github.com/marcboeker/go-duckdb"
)

// Kline K线数据结构
type Kline struct {
	Timestamp int64   `json:"timestamp"`
	Open      float64 `json:"open"`
	High      float64 `json:"high"`
	Low       float64 `json:"low"`
	Close     float64 `json:"close"`
	Volume    float64 `json:"volume"`
}

// KlineDB 数据库管理器
type KlineDB struct {
	db     *sql.DB
	dbPath string
}

// NewKlineDB 创建数据库管理器
func NewKlineDB(dbPath string) (*KlineDB, error) {
	// 确保目录存在
	dir := filepath.Dir(dbPath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create directory: %w", err)
	}

	// 连接数据库
	db, err := sql.Open("duckdb", dbPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}

	kdb := &KlineDB{
		db:     db,
		dbPath: dbPath,
	}

	// 初始化表结构
	if err := kdb.initTable(); err != nil {
		db.Close()
		return nil, fmt.Errorf("failed to init table: %w", err)
	}

	return kdb, nil
}

// initTable 初始化表结构
func (k *KlineDB) initTable() error {
	createTableSQL := `
	CREATE TABLE IF NOT EXISTS klines (
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
	`
	if _, err := k.db.Exec(createTableSQL); err != nil {
		return fmt.Errorf("failed to create table: %w", err)
	}

	// 创建索引
	indexes := []string{
		"CREATE INDEX IF NOT EXISTS idx_klines_symbol_tf ON klines(symbol, timeframe)",
		"CREATE INDEX IF NOT EXISTS idx_klines_timestamp ON klines(timestamp)",
		"CREATE INDEX IF NOT EXISTS idx_klines_exchange_symbol_tf ON klines(exchange, symbol, timeframe)",
	}

	for _, idxSQL := range indexes {
		if _, err := k.db.Exec(idxSQL); err != nil {
			log.Printf("Warning: failed to create index: %v", err)
		}
	}

	return nil
}

// GetLatestTimestamp 获取最新的时间戳
func (k *KlineDB) GetLatestTimestamp(exchange, symbol, timeframe string) (int64, error) {
	query := `
		SELECT MAX(timestamp) 
		FROM klines 
		WHERE exchange = ? AND symbol = ? AND timeframe = ?
	`
	var latest sql.NullInt64
	err := k.db.QueryRow(query, exchange, symbol, timeframe).Scan(&latest)
	if err != nil {
		if err == sql.ErrNoRows {
			return 0, nil
		}
		return 0, fmt.Errorf("failed to query latest timestamp: %w", err)
	}

	if !latest.Valid {
		return 0, nil
	}
	return latest.Int64, nil
}

// UpsertKlines 插入或更新K线数据
func (k *KlineDB) UpsertKlines(exchange, symbol, timeframe string, klines []Kline) (int, error) {
	if len(klines) == 0 {
		return 0, nil
	}

	// 使用事务批量插入
	tx, err := k.db.Begin()
	if err != nil {
		return 0, fmt.Errorf("failed to begin transaction: %w", err)
	}
	defer tx.Rollback()

	stmt, err := tx.Prepare(`
		INSERT INTO klines (timestamp, exchange, symbol, timeframe, open, high, low, close, volume, created_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
		ON CONFLICT (timestamp, exchange, symbol, timeframe) DO NOTHING
	`)
	if err != nil {
		return 0, fmt.Errorf("failed to prepare statement: %w", err)
	}
	defer stmt.Close()

	now := time.Now().Format("2006-01-02 15:04:05")
	inserted := 0

	for _, kline := range klines {
		result, err := stmt.Exec(
			kline.Timestamp,
			exchange,
			symbol,
			timeframe,
			kline.Open,
			kline.High,
			kline.Low,
			kline.Close,
			kline.Volume,
			now,
		)
		if err != nil {
			log.Printf("Warning: failed to insert kline %d: %v", kline.Timestamp, err)
			continue
		}

		rowsAffected, _ := result.RowsAffected()
		inserted += int(rowsAffected)
	}

	if err := tx.Commit(); err != nil {
		return 0, fmt.Errorf("failed to commit transaction: %w", err)
	}

	return inserted, nil
}

// Close 关闭数据库连接
func (k *KlineDB) Close() error {
	if k.db != nil {
		return k.db.Close()
	}
	return nil
}

// GateIOClient Gate.io API客户端
type GateIOClient struct {
	baseURL    string
	httpClient *http.Client
}

// NewGateIOClient 创建Gate.io客户端
func NewGateIOClient() *GateIOClient {
	return &GateIOClient{
		baseURL: "https://api.gateio.ws/api/v4/spot/candlesticks",
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// FetchKlines 获取K线数据（支持from/to参数）
func (c *GateIOClient) FetchKlines(symbol, timeframe string, from, to int64, limit int) ([]Kline, error) {
	// 映射时间框架
	intervalMap := map[string]string{
		"5m":  "5m",
		"15m": "15m",
		"1h":  "1h",
		"4h":  "4h",
		"1d":  "1d",
	}
	interval, ok := intervalMap[timeframe]
	if !ok {
		return nil, fmt.Errorf("unsupported timeframe: %s", timeframe)
	}

	// 构建交易对
	pair := symbol + "_USDT"
	if symbol == "BTC" {
		pair = "BTC_USDT"
	}

	// 构建URL
	url := fmt.Sprintf("%s?currency_pair=%s&interval=%s&limit=%d", c.baseURL, pair, interval, limit)
	if from > 0 {
		url += fmt.Sprintf("&from=%d", from)
	}
	if to > 0 {
		url += fmt.Sprintf("&to=%d", to)
	}

	// 发送请求
	resp, err := c.httpClient.Get(url)
	if err != nil {
		return nil, fmt.Errorf("HTTP request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("API error (status %d): %s", resp.StatusCode, string(body))
	}

	// 解析响应
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %w", err)
	}

	// Gate.io格式: [["timestamp", "volume", "close", "high", "low", "open"], ...]
	var rawData [][]string
	if err := json.Unmarshal(body, &rawData); err != nil {
		return nil, fmt.Errorf("failed to parse response: %w", err)
	}

	klines := make([]Kline, 0, len(rawData))
	for _, row := range rawData {
		if len(row) < 6 {
			continue
		}

		timestamp, err := strconv.ParseInt(row[0], 10, 64)
		if err != nil {
			continue
		}

		// Gate.io时间戳：如果小于1e10则是秒，否则是毫秒
		if timestamp > 1e10 {
			timestamp = timestamp / 1000
		}

		volume, _ := strconv.ParseFloat(row[1], 64)
		close, _ := strconv.ParseFloat(row[2], 64)
		high, _ := strconv.ParseFloat(row[3], 64)
		low, _ := strconv.ParseFloat(row[4], 64)
		open, _ := strconv.ParseFloat(row[5], 64)

		klines = append(klines, Kline{
			Timestamp: timestamp,
			Open:      open,
			High:      high,
			Low:       low,
			Close:     close,
			Volume:    volume,
		})
	}

	return klines, nil
}

// FetchKlinesIncremental 增量获取K线数据
func (c *GateIOClient) FetchKlinesIncremental(kdb *KlineDB, symbol, timeframe string, days int, limit int) (int, error) {
	// 查询数据库中最新的时间戳
	latestTS, err := kdb.GetLatestTimestamp("gate", symbol, timeframe)
	if err != nil {
		return 0, fmt.Errorf("failed to get latest timestamp: %w", err)
	}

	var fromTS, toTS int64
	now := time.Now().Unix()

	if latestTS == 0 {
		// 数据库为空，获取days天的数据
		fromTS = now - int64(days*24*3600)
		toTS = now
		log.Printf("Database empty for %s %s, fetching %d days", symbol, timeframe, days)
	} else {
		// 从最新时间戳开始，获取到现在
		fromTS = latestTS
		toTS = now
		log.Printf("Incremental fetch for %s %s from %d to %d", symbol, timeframe, fromTS, toTS)
	}

	// 计算时间范围（如果范围太大，分批获取）
	timeRange := toTS - fromTS
	maxRange := int64(days * 24 * 3600)

	if timeRange > maxRange {
		fromTS = toTS - maxRange
	}

	// 获取K线数据
	klines, err := c.FetchKlines(symbol, timeframe, fromTS, toTS, limit)
	if err != nil {
		return 0, fmt.Errorf("failed to fetch klines: %w", err)
	}

	if len(klines) == 0 {
		log.Printf("No new klines for %s %s", symbol, timeframe)
		return 0, nil
	}

	// 写入数据库
	inserted, err := kdb.UpsertKlines("gate", symbol, timeframe, klines)
	if err != nil {
		return 0, fmt.Errorf("failed to upsert klines: %w", err)
	}

	return inserted, nil
}

func main() {
	var (
		symbolsStr   = flag.String("symbols", "BTC,ETH,SOL", "Comma-separated list of symbols")
		timeframe    = flag.String("timeframe", "15m", "Timeframe (5m,15m,1h,4h)")
		days         = flag.Int("days", 90, "Number of days to fetch (for initial fetch)")
		dbPath       = flag.String("db", "data/kline_data/klines.duckdb", "Database file path")
		concurrency  = flag.Int("concurrency", 20, "Max concurrent requests")
		incremental  = flag.Bool("incremental", true, "Enable incremental fetch")
		limit        = flag.Int("limit", 1000, "Max klines per request")
	)
	flag.Parse()

	// 解析币种列表
	symbols := strings.Split(*symbolsStr, ",")
	for i := range symbols {
		symbols[i] = strings.TrimSpace(strings.ToUpper(symbols[i]))
	}

	// 初始化数据库
	kdb, err := NewKlineDB(*dbPath)
	if err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
	defer kdb.Close()

	log.Printf("Database: %s", *dbPath)
	log.Printf("Symbols: %v", symbols)
	log.Printf("Timeframe: %s", *timeframe)
	log.Printf("Concurrency: %d", *concurrency)
	log.Printf("Incremental: %v", *incremental)

	// 初始化Gate.io客户端
	client := NewGateIOClient()

	// 并发控制
	semaphore := make(chan struct{}, *concurrency)
	var wg sync.WaitGroup
	results := make(map[string]int)
	var mu sync.Mutex

	startTime := time.Now()

	// 并发获取每个币种的K线数据
	for _, symbol := range symbols {
		wg.Add(1)
		go func(sym string) {
			defer wg.Done()

			// 获取信号量
			semaphore <- struct{}{}
			defer func() { <-semaphore }()

			var inserted int
			var err error

			if *incremental {
				inserted, err = client.FetchKlinesIncremental(kdb, sym, *timeframe, *days, *limit)
			} else {
				// 全量获取
				now := time.Now().Unix()
				fromTS := now - int64(*days*24*3600)
				klines, err := client.FetchKlines(sym, *timeframe, fromTS, now, *limit)
				if err == nil {
					inserted, err = kdb.UpsertKlines("gate", sym, *timeframe, klines)
				}
			}

			mu.Lock()
			if err != nil {
				log.Printf("❌ %s: %v", sym, err)
				results[sym] = -1
			} else {
				log.Printf("✅ %s: inserted %d klines", sym, inserted)
				results[sym] = inserted
			}
			mu.Unlock()
		}(symbol)
	}

	wg.Wait()

	elapsed := time.Since(startTime)

	// 统计结果
	totalInserted := 0
	success := 0
	failed := 0

	for _, count := range results {
		if count < 0 {
			failed++
		} else {
			success++
			totalInserted += count
		}
	}

	log.Println("=" + strings.Repeat("=", 60))
	log.Printf("Total: %d symbols", len(symbols))
	log.Printf("Success: %d", success)
	log.Printf("Failed: %d", failed)
	log.Printf("Total inserted: %d klines", totalInserted)
	log.Printf("Elapsed: %.2f seconds", elapsed.Seconds())
	log.Println("=" + strings.Repeat("=", 60))
}

