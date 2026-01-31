package main

import (
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

// KlineResult 单个币种的K线结果
type KlineResult struct {
	Symbol    string  `json:"symbol"`
	Timeframe string  `json:"timeframe"`
	Klines    []Kline `json:"klines"`
	Error     string  `json:"error,omitempty"`
	Inserted  int     `json:"inserted,omitempty"`
}

// BatchResult 批量获取结果
type BatchResult struct {
	Results  []KlineResult `json:"results"`
	Total    int           `json:"total"`
	Success  int           `json:"success"`
	Failed   int           `json:"failed"`
	Elapsed  float64       `json:"elapsed_seconds"`
	FromTime int64         `json:"from_time,omitempty"`
	ToTime   int64         `json:"to_time,omitempty"`
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
	// 如果limit超过1000，需要分批获取
	maxPerRequest := 1000
	if limit <= maxPerRequest && from == 0 && to == 0 {
		return c.fetchKlinesSingle(symbol, timeframe, from, to, limit)
	}
	
	// 分批获取
	return c.fetchKlinesBatch(symbol, timeframe, from, to, limit)
}

// fetchKlinesSingle 单次获取K线数据
func (c *GateIOClient) fetchKlinesSingle(symbol, timeframe string, from, to int64, limit int) ([]Kline, error) {
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

// fetchKlinesBatch 分批获取K线数据（支持超过1000条限制）
func (c *GateIOClient) fetchKlinesBatch(symbol, timeframe string, from, to int64, totalLimit int) ([]Kline, error) {
	maxPerRequest := 1000
	allKlines := []Kline{}

	// 第一次请求：获取最新的数据
	klines, err := c.fetchKlinesSingle(symbol, timeframe, 0, 0, maxPerRequest)
	if err != nil {
		return nil, err
	}
	if len(klines) == 0 {
		return allKlines, nil
	}

	allKlines = klines
	log.Printf("[%s] 进度: %d/%d (%.1f%%)", symbol, len(allKlines), totalLimit, float64(len(allKlines))/float64(totalLimit)*100)

	// 如果需要更多数据，继续获取更早的数据
	for len(allKlines) < totalLimit {
		// 获取当前最旧的时间戳
		oldestTS := allKlines[0].Timestamp

		// 计算还需要的数据量
		remaining := totalLimit - len(allKlines)
		if remaining <= 0 {
			break
		}

		// 请求更早的数据
		limit := remaining
		if limit > maxPerRequest {
			limit = maxPerRequest
		}

		// 使用from/to参数获取更早的数据（Gate.io使用to参数获取更早的数据）
		newKlines, err := c.fetchKlinesSingle(symbol, timeframe, 0, oldestTS-1, limit)
		if err != nil {
			log.Printf("[%s] Warning: failed to fetch more klines: %v", symbol, err)
			break
		}

		if len(newKlines) == 0 {
			break // 没有更多数据了
		}

		// 合并数据（从早到晚）
		allKlines = append(newKlines, allKlines...)
		log.Printf("[%s] 进度: %d/%d (%.1f%%)", symbol, len(allKlines), totalLimit, float64(len(allKlines))/float64(totalLimit)*100)

		// 避免请求过快
		time.Sleep(100 * time.Millisecond)
	}

	// 去重（按timestamp）
	seen := make(map[int64]bool)
	uniqueKlines := []Kline{}
	for _, k := range allKlines {
		if !seen[k.Timestamp] {
			seen[k.Timestamp] = true
			uniqueKlines = append(uniqueKlines, k)
		}
	}

	return uniqueKlines, nil
}

func main() {
	var (
		symbolsStr  = flag.String("symbols", "BTC,ETH,SOL", "Comma-separated list of symbols")
		timeframe   = flag.String("timeframe", "15m", "Timeframe (5m,15m,1h,4h)")
		days        = flag.Int("days", 90, "Number of days to fetch")
		concurrency = flag.Int("concurrency", 20, "Max concurrent requests")
		output      = flag.String("output", "", "Output JSON file (default: stdout)")
		from        = flag.Int64("from", 0, "Start timestamp (Unix seconds, 0 for auto)")
		to          = flag.Int64("to", 0, "End timestamp (Unix seconds, 0 for now)")
	)
	flag.Parse()

	// 解析币种列表
	symbols := strings.Split(*symbolsStr, ",")
	for i := range symbols {
		symbols[i] = strings.TrimSpace(strings.ToUpper(symbols[i]))
	}

	// 初始化Gate.io客户端
	client := NewGateIOClient()

	// 计算时间范围
	now := time.Now().Unix()
	var fromTS, toTS int64
	if *from > 0 {
		fromTS = *from
	} else {
		fromTS = now - int64(*days*24*3600)
	}
	if *to > 0 {
		toTS = *to
	} else {
		toTS = now
	}

	// 并发控制
	semaphore := make(chan struct{}, *concurrency)
	var wg sync.WaitGroup
	results := make([]KlineResult, len(symbols))
	var mu sync.Mutex

	startTime := time.Now()

	// 计算每个币种需要的K线数量（根据days）
	klinesPerDayMap := map[string]int{
		"5m":  288, // 24 * 60 / 5
		"15m": 96,  // 24 * 60 / 15
		"1h":  24,
		"4h":  6,
		"1d":  1,
	}
	klinesPerDay := klinesPerDayMap[*timeframe]
	if klinesPerDay == 0 {
		klinesPerDay = 96
	}
	totalKlinesNeeded := *days * klinesPerDay

	// 并发获取每个币种的K线数据
	for i, symbol := range symbols {
		wg.Add(1)
		go func(idx int, sym string) {
			defer wg.Done()

			// 获取信号量
			semaphore <- struct{}{}
			defer func() { <-semaphore }()

			mu.Lock()
			log.Printf("[%d/%d] 处理 %s...", idx+1, len(symbols), sym)
			mu.Unlock()

			result := KlineResult{
				Symbol:    sym,
				Timeframe: *timeframe,
			}

			// 获取K线数据（使用计算出的limit）
			limit := totalKlinesNeeded
			if limit > 10000 {
				limit = 10000 // 最大限制，防止过多
			}
			klines, err := client.FetchKlines(sym, *timeframe, fromTS, toTS, limit)
			if err != nil {
				result.Error = err.Error()
				mu.Lock()
				results[idx] = result
				mu.Unlock()
				log.Printf("❌ %s: %v", sym, err)
				return
			}

			result.Klines = klines
			result.Inserted = len(klines)
			mu.Lock()
			results[idx] = result
			mu.Unlock()
			log.Printf("✅ %s: fetched %d klines", sym, len(klines))
		}(i, symbol)
	}

	wg.Wait()

	elapsed := time.Since(startTime)

	// 统计结果
	success := 0
	failed := 0
	totalKlines := 0

	for _, r := range results {
		if r.Error != "" {
			failed++
		} else {
			success++
			totalKlines += len(r.Klines)
		}
	}

	batchResult := BatchResult{
		Results: results,
		Total:   len(symbols),
		Success: success,
		Failed:  failed,
		Elapsed: elapsed.Seconds(),
		FromTime: fromTS,
		ToTime:   toTS,
	}

	// 输出结果
	var outputWriter io.Writer
	if *output != "" {
		// 确保目录存在
		dir := filepath.Dir(*output)
		if err := os.MkdirAll(dir, 0755); err != nil {
			log.Fatalf("Failed to create output directory: %v", err)
		}

		file, err := os.Create(*output)
		if err != nil {
			log.Fatalf("Failed to create output file: %v", err)
		}
		defer file.Close()
		outputWriter = file
	} else {
		outputWriter = os.Stdout
	}

	// 输出JSON
	jsonData, err := json.MarshalIndent(batchResult, "", "  ")
	if err != nil {
		log.Fatalf("Failed to marshal JSON: %v", err)
	}

	if _, err := outputWriter.Write(jsonData); err != nil {
		log.Fatalf("Failed to write output: %v", err)
	}

	// 输出统计信息到stderr
	log.SetOutput(os.Stderr)
	log.Println("=" + strings.Repeat("=", 60))
	log.Printf("Total: %d symbols", len(symbols))
	log.Printf("Success: %d", success)
	log.Printf("Failed: %d", failed)
	log.Printf("Total klines: %d", totalKlines)
	log.Printf("Elapsed: %.2f seconds", elapsed.Seconds())
	if *output != "" {
		log.Printf("Output file: %s", *output)
	}
	log.Println("=" + strings.Repeat("=", 60))
}

