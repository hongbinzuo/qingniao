package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"
)

// Kline 单个K线数据
type Kline struct {
	OpenTime  int64   `json:"open_time"`
	Open      float64 `json:"open"`
	High      float64 `json:"high"`
	Low       float64 `json:"low"`
	Close     float64 `json:"close"`
	Volume    float64 `json:"volume"`
	CloseTime int64   `json:"close_time"`
}

// KlineResult 单个币种的K线结果
type KlineResult struct {
	Symbol    string  `json:"symbol"`
	Timeframe string  `json:"timeframe"`
	Klines    []Kline `json:"klines"`
	Error     string  `json:"error,omitempty"`
}

// BatchResult 批量获取结果
type BatchResult struct {
	Results []KlineResult `json:"results"`
	Total   int           `json:"total"`
	Success int           `json:"success"`
	Failed  int           `json:"failed"`
	Elapsed float64       `json:"elapsed_seconds"`
}

func main() {
	var symbolsStr = flag.String("symbols", "", "Comma-separated list of symbols (e.g., BTC,ETH,SOL)")
	var timeframe = flag.String("timeframe", "15m", "Timeframe (5m,15m,1h,4h)")
	var exchange = flag.String("exchange", "binance", "Exchange (binance,gate)")
	var limit = flag.Int("limit", 200, "Number of klines to fetch")
	var concurrency = flag.Int("concurrency", 20, "Max concurrent requests")
	flag.Parse()

	if *symbolsStr == "" {
		fmt.Fprintf(os.Stderr, "Error: --symbols is required\n")
		os.Exit(1)
	}

	symbols := strings.Split(*symbolsStr, ",")
	for i := range symbols {
		symbols[i] = strings.TrimSpace(strings.ToUpper(symbols[i]))
	}

	startTime := time.Now()

	// 使用 channel 控制并发数
	semaphore := make(chan struct{}, *concurrency)
	var wg sync.WaitGroup
	results := make([]KlineResult, len(symbols))
	var mu sync.Mutex

	// 并发获取每个币种的K线数据
	for i, symbol := range symbols {
		wg.Add(1)
		go func(idx int, sym string) {
			defer wg.Done()

			// 获取信号量
			semaphore <- struct{}{}
			defer func() { <-semaphore }()

			result := KlineResult{
				Symbol:    sym,
				Timeframe: *timeframe,
			}

			// 获取K线数据
			klines, err := fetchKlines(sym, *timeframe, *exchange, *limit)
			if err != nil {
				result.Error = err.Error()
			} else {
				result.Klines = klines
			}

			mu.Lock()
			results[idx] = result
			mu.Unlock()
		}(i, symbol)
	}

	wg.Wait()

	elapsed := time.Since(startTime).Seconds()

	// 统计结果
	success := 0
	failed := 0
	for _, r := range results {
		if r.Error == "" {
			success++
		} else {
			failed++
		}
	}

	batchResult := BatchResult{
		Results: results,
		Total:   len(symbols),
		Success: success,
		Failed:  failed,
		Elapsed: elapsed,
	}

	// 输出 JSON
	jsonData, err := json.MarshalIndent(batchResult, "", "  ")
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error marshaling JSON: %v\n", err)
		os.Exit(1)
	}

	fmt.Println(string(jsonData))
}

func fetchKlines(symbol, timeframe, exchange string, limit int) ([]Kline, error) {
	var url string
	var interval string

	// 映射时间框架
	switch timeframe {
	case "5m":
		interval = "5m"
	case "15m":
		interval = "15m"
	case "1h":
		interval = "1h"
	case "4h":
		interval = "4h"
	default:
		return nil, fmt.Errorf("unsupported timeframe: %s", timeframe)
	}

	// 构建请求URL
	if exchange == "binance" {
		// Binance API: GET /api/v3/klines
		url = fmt.Sprintf("https://api.binance.com/api/v3/klines?symbol=%sUSDT&interval=%s&limit=%d",
			symbol, interval, limit)
	} else if exchange == "gate" {
		// Gate.io API: GET /api/v4/spot/candlesticks
		url = fmt.Sprintf("https://api.gateio.ws/api/v4/spot/candlesticks?currency_pair=%s_USDT&interval=%s&limit=%d",
			symbol, interval, limit)
	} else {
		return nil, fmt.Errorf("unsupported exchange: %s", exchange)
	}

	// 发送HTTP请求
	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Get(url)
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

	var klines []Kline
	if exchange == "binance" {
		// Binance格式: [[openTime, open, high, low, close, volume, ...], ...]
		var rawData [][]interface{}
		if err := json.Unmarshal(body, &rawData); err != nil {
			return nil, fmt.Errorf("failed to parse Binance response: %w", err)
		}

		klines = make([]Kline, len(rawData))
		for i, row := range rawData {
			if len(row) < 6 {
				continue
			}
			openTime, _ := strconv.ParseInt(fmt.Sprintf("%.0f", row[0]), 10, 64)
			open, _ := strconv.ParseFloat(fmt.Sprintf("%v", row[1]), 64)
			high, _ := strconv.ParseFloat(fmt.Sprintf("%v", row[2]), 64)
			low, _ := strconv.ParseFloat(fmt.Sprintf("%v", row[3]), 64)
			close, _ := strconv.ParseFloat(fmt.Sprintf("%v", row[4]), 64)
			volume, _ := strconv.ParseFloat(fmt.Sprintf("%v", row[5]), 64)
			closeTime, _ := strconv.ParseInt(fmt.Sprintf("%.0f", row[6]), 10, 64)

			klines[i] = Kline{
				OpenTime:  openTime / 1000, // 转换为秒
				Open:      open,
				High:      high,
				Low:       low,
				Close:     close,
				Volume:    volume,
				CloseTime: closeTime / 1000,
			}
		}
	} else if exchange == "gate" {
		// Gate.io格式: [["timestamp", "volume", "close", "high", "low", "open"], ...]
		// 注意：Gate.io返回的时间戳已经是秒级，不是毫秒
		var rawData [][]string
		if err := json.Unmarshal(body, &rawData); err != nil {
			return nil, fmt.Errorf("failed to parse Gate.io response: %w", err)
		}

		klines = make([]Kline, 0, len(rawData))
		for _, row := range rawData {
			if len(row) < 6 {
				continue
			}
			timestamp, err := strconv.ParseInt(row[0], 10, 64)
			if err != nil {
				continue
			}
			volume, _ := strconv.ParseFloat(row[1], 64)
			close, _ := strconv.ParseFloat(row[2], 64)
			high, _ := strconv.ParseFloat(row[3], 64)
			low, _ := strconv.ParseFloat(row[4], 64)
			open, _ := strconv.ParseFloat(row[5], 64)

			// Gate.io时间戳：如果小于1e10则是秒，否则是毫秒
			openTime := timestamp
			if timestamp > 1e10 {
				openTime = timestamp / 1000
			}

			klines = append(klines, Kline{
				OpenTime:  openTime,
				Open:      open,
				High:      high,
				Low:       low,
				Close:     close,
				Volume:    volume,
				CloseTime: openTime + 900, // 15分钟 = 900秒
			})
		}
	}

	return klines, nil
}
