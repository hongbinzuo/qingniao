# ABU Signal Monitor System - Complete Analysis

**Date**: February 5, 2026  
**Purpose**: Understand what's being monitored in the ABU signal monitoring system

---

## Overview

You have **3 different monitoring systems** working together to track ABU trading signals:

1. **monitor_abu_signals.py** - Automatic TP/SL audit system (database-based)
2. **abu_realtime_monitor.py** - Real-time top signals scanner with live prices
3. **signal_monitor.py** - Pending signal proximity alerts (file-based)

---

## System 1: monitor_abu_signals.py (TP/SL Auto-Audit)

### Purpose
Automatically monitors active signals in the database and checks if they hit TP1, TP2, or Stop Loss.

### What It Monitors

#### 1. **Signal Status Tracking**
- **Active signals** from the last 24 hours (configurable)
- **System filter**: Only "abu" system signals
- **Status types**:
  - `pending` - Signal generated, waiting for entry
  - `partial_tp` - TP1 hit, monitoring for TP2
  - `completed` - TP2 hit (success)
  - `stopped` - Stop loss hit (failure)

#### 2. **Price Level Checks**
For each signal, it monitors:
- **Entry price** - Signal entry point
- **Stop Loss (SL)** - Risk management level
- **Take Profit 1 (TP1)** - First profit target (50% position)
- **Take Profit 2 (TP2)** - Second profit target (50% position)

#### 3. **Kline Data Source**
- **Exchange**: Gate.io API
- **Monitoring timeframe**: Uses lower timeframe for accuracy
  - 15m signals → monitored with 5m klines
  - 1h signals → monitored with 15m klines
  - 4h signals → monitored with 1h klines

#### 4. **Check Logic**

**For LONG signals:**
```
- If low <= stop_loss → Signal STOPPED (loss)
- If high >= tp2 → Signal COMPLETED (TP2 hit)
- If high >= tp1 → Signal PARTIAL_TP (TP1 hit)
```

**For SHORT signals:**
```
- If high >= stop_loss → Signal STOPPED (loss)
- If low <= tp2 → Signal COMPLETED (TP2 hit)
- If low <= tp1 → Signal PARTIAL_TP (TP1 hit)
```

### Key Features

#### Smart Checking
- **Minimum interval**: 20 seconds between checks for same signal
- **Skip completed**: Doesn't re-check stopped/completed signals
- **Incremental**: Only fetches klines since last check

#### PnL Calculation
Automatically calculates profit/loss percentage:
- **Long**: `(exit_price - entry) / entry * 100`
- **Short**: `(entry - exit_price) / entry * 100`

#### Database Updates
When TP/SL is hit:
- Updates signal status
- Records exit time and price
- Calculates PnL percentage
- Adds signal evaluation record
- Increments check counter

### Usage Examples

```bash
# Run once (manual check)
python scripts/abu/monitor_abu_signals.py --once

# Continuous monitoring (60 second interval)
python scripts/abu/monitor_abu_signals.py --interval 60

# Monitor last 48 hours, max 500 signals
python scripts/abu/monitor_abu_signals.py --hours 48 --max-signals 500

# Custom log file
python scripts/abu/monitor_abu_signals.py --log-file logs/my_monitor.log
```

### Output

**Log file** (`logs/abu_signal_monitor.log`):
```json
{"ts": "2026-02-05T10:30:00", "event": "tp1", "signal_id": 123, "symbol": "BTC", "exit_price": 45000, "pnl_pct": 2.5}
{"ts": "2026-02-05T10:31:00", "event": "cycle", "checked": 15, "tp1": 3, "tp2": 1, "stopped": 2, "skipped": 9}
```

---

## System 2: abu_realtime_monitor.py (Real-time Scanner)

### Purpose
Scans top cryptocurrencies for ABU signals and enriches them with live prices to show entry opportunities.

### What It Monitors

#### 1. **Top Coins Selection**
- **Ranking methods**:
  - `marketcap` - Top coins by market capitalization (default)
  - `volume` - Top coins by trading volume
- **Default**: Top 5 coins
- **Timeframes**: 5m, 15m, 1h (configurable)

#### 2. **Signal Generation**
Runs `pa_scan_15m_top10.py` to generate fresh signals:
- Pattern detection (Engulfing, PinBar, etc.)
- Brooks price action analysis
- Pattern scoring
- Entry/SL/TP calculation

#### 3. **Live Price Enrichment**
Fetches real-time prices from Gate.io:
- **Current price** for each coin
- **Triggered status**: Has entry price been reached?
- **Distance %**: How far is current price from entry?

#### 4. **Signal Data Captured**

For each signal:
```
- Rank (1-5)
- Symbol (BTC, ETH, etc.)
- Direction (long/short)
- Entry price
- Stop loss
- Take profit 1
- Take profit 2
- TP1 probability (from ML model)
- TP2 probability (from ML model)
- SL probability (from ML model)
- Score (pattern quality)
- Brooks phase
- Match confidence
- Reason (why signal generated)
```

#### 5. **Trigger Detection**

**For LONG signals:**
- Triggered = YES if `current_price >= entry_price`
- Distance % = `(current_price - entry) / entry * 100`

**For SHORT signals:**
- Triggered = YES if `current_price <= entry_price`
- Distance % = `(entry - current_price) / entry * 100`

### Key Features

#### Context Filtering (Optional)
- `off` - No filtering (default)
- `brooks` - Only signals matching Brooks patterns
- `regime36` - Only signals in favorable market regime
- `both` - Both filters applied

#### Audit Integration
Can enable historical audit to show signal quality:
```bash
--audit-period-hours 24 --audit-since-days 30
```

#### Output Rotation
- Automatically rotates log files when they exceed size limit
- Archives old files to `deleting/` folder

### Usage Examples

```bash
# Run once (manual scan)
python scripts/abu/abu_realtime_monitor.py --once

# Continuous monitoring (60 second interval)
python scripts/abu/abu_realtime_monitor.py --interval 60

# Top 10 coins, 3 timeframes
python scripts/abu/abu_realtime_monitor.py --top 10 --timeframes "5m,15m,1h,4h"

# With Brooks context filter
python scripts/abu/abu_realtime_monitor.py --context-filter brooks

# With audit (show historical performance)
python scripts/abu/abu_realtime_monitor.py --audit-period-hours 24
```

### Output

**Markdown file** (`outputs/trading_signals/ABU_realtime_log.md`):
```markdown
## 生成时间: 2026-02-05 10:30:00 | Top: 5 | Rank: marketcap

### 5m
| 序号 | 币种 | 方向 | 入场价 | 止损 | 目标1 | 目标2 | TP1概率 | TP2概率 | 止损概率 | 当前价 | 是否触发 | 距离% |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|
| 1 | BTC | 多 | 44500 | 44000 | 45000 | 45500 | 55.2% | 48.1% | 42.3% | 44600 | 是 | 0.22 |
| 2 | ETH | 空 | 2350 | 2380 | 2320 | 2290 | 52.8% | 45.6% | 45.1% | 2360 | 否 | -0.43 |
```

---

## System 3: signal_monitor.py (Pending Signal Proximity Alerts)

### Purpose
Monitors pending signals and alerts when current price approaches entry price.

### What It Monitors

#### 1. **Signal Status Filter**
- Only monitors signals with `status = 'pending'`
- Ignores completed, stopped, or active positions
- Checks all systems (not just ABU)

#### 2. **Price Proximity Levels**

Three alert levels based on distance from entry:

**Level 1: Warning (3% away)**
- 📊 Price is approaching entry price
- Distance: 1.5% - 3.0%
- Action: Start paying attention

**Level 2: Alert (1.5% away)**
- ⚠️ Price is close to entry price
- Distance: 1.0% - 1.5%
- Action: Prepare to enter

**Level 3: Ready (1% away)**
- ✅ Price at entry level
- Distance: < 1.0%
- Action: Enter position now

#### 3. **Distance Calculation**

**For LONG signals:**
```python
distance = current_price - entry_price
distance_pct = (distance / entry) * 100

# Positive = price above entry (not triggered yet)
# Negative = price below entry (already triggered)
```

**For SHORT signals:**
```python
distance = entry_price - current_price
distance_pct = (distance / entry) * 100

# Positive = price below entry (not triggered yet)
# Negative = price above entry (already triggered)
```

#### 4. **Data Source**
- Uses `get_btc_current_price()` function
- Falls back to `get_current_price()` if needed
- File-based signal storage (not database)

### Key Features

#### Signal Tracking
- Loads signals from `.signal_history` directory
- Supports multiple trading systems
- Tracks signal metadata (timeframe, pattern, strength)

#### Notification Format
For each signal approaching entry:
```
================================================================================
🚨 信号接近提醒
================================================================================
系统: ABU
时间框架: 15m
信号类型: 做多 (强)
生成时间: 2026-02-05 09:30:00

当前价格: $44,600.00
入场价: $44,500.00
✅ 价格已接近入场价！距离: 0.22%

止损: $44,000.00
止盈1: $45,000.00 (50%)
止盈2: $45,500.00 (50%)
入场模型: engulfing_bullish
理由: Strong bullish engulfing with volume confirmation
================================================================================
```

#### File Output
Saves notifications to:
```
trading_signals/信号提醒_20260205_103000.md
```

### Usage Examples

```bash
# Run once (manual check)
python src/signal_monitor.py --once

# Continuous monitoring (15 minute interval)
python src/signal_monitor.py --interval 900

# Custom interval (5 minutes)
python src/signal_monitor.py --interval 300
```

### Output Example

**Console output:**
```
[2026-02-05 10:30:00] 检查pending信号...
⚠️  发现 2 个信号需要关注！

通知 1/2:
================================================================================
🚨 信号接近提醒
[... signal details ...]
================================================================================

✅ 已保存 2 条通知到: 信号提醒_20260205_103000.md
```

---

## Comparison: Which Monitor to Use?

### Use monitor_abu_signals.py When:
- ✅ You want **automatic TP/SL tracking** for active positions
- ✅ You need **database-based** signal management
- ✅ You want **PnL calculation** and performance tracking
- ✅ You're running **live trading** and need audit trail
- ✅ You want to track signals **after entry**

### Use abu_realtime_monitor.py When:
- ✅ You want to **scan for new opportunities** continuously
- ✅ You need **top coins** ranked by volume/marketcap
- ✅ You want **live price enrichment** for signals
- ✅ You need **multiple timeframes** (5m, 15m, 1h, 4h)
- ✅ You want **ML probability predictions** (TP1/TP2/SL)
- ✅ You're looking for **entry opportunities**

### Use signal_monitor.py When:
- ✅ You have **pending signals** waiting for entry
- ✅ You want **proximity alerts** when price approaches entry
- ✅ You're using **file-based** signal storage
- ✅ You need **manual entry** notifications
- ✅ You want **simple, lightweight** monitoring

---

## Recommended Workflow

### Step 1: Signal Generation (abu_realtime_monitor.py)
```bash
# Scan top 10 coins every 60 seconds
python scripts/abu/abu_realtime_monitor.py --top 10 --interval 60 --timeframes "15m,1h,4h"
```
**Output**: Fresh signals with live prices in `ABU_realtime_log.md`

### Step 2: Entry Monitoring (signal_monitor.py)
```bash
# Check pending signals every 15 minutes
python src/signal_monitor.py --interval 900
```
**Output**: Alerts when price approaches entry

### Step 3: Position Tracking (monitor_abu_signals.py)
```bash
# Monitor active positions every 60 seconds
python scripts/abu/monitor_abu_signals.py --interval 60
```
**Output**: Automatic TP/SL detection and PnL tracking

---

## Key Metrics Being Monitored

### 1. **Signal Quality Metrics**
- Pattern score (0-100)
- Brooks phase match confidence
- ML probability predictions (TP1/TP2/SL)
- Signal strength (strong/medium/weak)

### 2. **Price Action Metrics**
- Current price vs entry price
- Distance to entry (%)
- Triggered status (yes/no)
- Time since signal generation

### 3. **Risk Management Metrics**
- Stop loss distance (%)
- Take profit distances (%)
- Risk/reward ratio
- PnL percentage (after exit)

### 4. **Performance Metrics**
- TP1 hit rate
- TP2 hit rate
- Stop loss hit rate
- Average PnL per signal
- Check count per signal

---

## Database Schema (monitor_abu_signals.py)

### Signals Table
```sql
- id (primary key)
- symbol (BTC, ETH, etc.)
- signal_type (long/short)
- timeframe (5m, 15m, 1h, 4h)
- entry_price
- stop_loss
- take_profit_1
- take_profit_2
- status (pending/partial_tp/completed/stopped)
- signal_time (when generated)
- last_check_time (last monitor check)
- check_count (number of checks)
- exit_time (when TP/SL hit)
- exit_price (actual exit price)
- exit_reason (tp1/tp2/stop_loss)
- pnl_pct (profit/loss percentage)
- system_name (abu)
```

### Signal Evaluations Table
```sql
- signal_id (foreign key)
- evaluation_time
- result (tp1/tp2/stopped)
- actual_exit_price
- actual_profit_pct
- stop_loss_hit (boolean)
- take_profit_1_hit (boolean)
- take_profit_2_hit (boolean)
- missed (boolean)
- notes
```

---

## Log Files

### 1. abu_signal_monitor.log
**Location**: `logs/abu_signal_monitor.log`
**Content**: TP/SL events and cycle statistics
**Format**: JSON lines
```json
{"ts": "2026-02-05T10:30:00", "event": "tp1", "signal_id": 123, ...}
```

### 2. abu_realtime_monitor.log
**Location**: `logs/abu_realtime_monitor.log`
**Content**: Scan execution logs
**Format**: Standard logging
```
2026-02-05 10:30:00 [INFO] Scan start: python scripts/pa_scan_15m_top10.py ...
```

### 3. ABU_realtime_log.md
**Location**: `outputs/trading_signals/ABU_realtime_log.md`
**Content**: Signal tables with live prices
**Format**: Markdown tables

### 4. 信号提醒_*.md
**Location**: `trading_signals/信号提醒_*.md`
**Content**: Proximity alert notifications
**Format**: Markdown formatted alerts

---

## Configuration Options

### monitor_abu_signals.py
```bash
--interval 60           # Check every 60 seconds
--hours 24             # Monitor signals from last 24 hours
--max-signals 200      # Process max 200 signals per cycle
--system abu           # Filter by system name
--min-interval 20      # Min 20 seconds between checks for same signal
--log-file PATH        # Custom log file path
--once                 # Run once and exit
```

### abu_realtime_monitor.py
```bash
--top 5                        # Top 5 coins
--timeframes "5m,15m,1h"      # Multiple timeframes
--interval 60                  # Scan every 60 seconds
--rank-by marketcap           # Rank by marketcap or volume
--exchange-mode gate          # gate/bybit/bitget/split
--context-filter brooks       # off/brooks/regime36/both
--audit-period-hours 24       # Enable audit
--once                        # Run once and exit
```

### signal_monitor.py
```bash
--interval 900         # Check every 15 minutes (900 seconds)
--once                # Run once and exit
```

---

## Performance Considerations

### monitor_abu_signals.py
- **API calls**: 1 per signal per check (Gate.io klines)
- **Database queries**: 1 read + N writes per cycle
- **Recommended interval**: 60 seconds
- **Max signals**: 200 per cycle (to avoid rate limits)

### abu_realtime_monitor.py
- **API calls**: 1 ticker fetch + N kline fetches per scan
- **Subprocess calls**: 1 per timeframe per cycle
- **Recommended interval**: 60-300 seconds
- **File I/O**: Moderate (reads scan files, writes logs)

### signal_monitor.py
- **API calls**: 1 price fetch per cycle
- **File I/O**: Light (reads signal history)
- **Recommended interval**: 300-900 seconds
- **Memory**: Low (file-based, no database)

---

## Summary

Your ABU signal monitoring system is **comprehensive and well-designed**:

### ✅ Strengths
1. **Three-layer monitoring**: Generation → Entry → Exit
2. **Automatic TP/SL tracking** with database persistence
3. **Live price enrichment** for entry timing
4. **ML probability predictions** for signal quality
5. **Flexible configuration** for different use cases
6. **Robust logging** for audit and debugging

### 💡 Use Cases for Monetization

Based on this monitoring system, you can offer:

1. **Signal Service** ($50-200/month)
   - Real-time signals with ML probabilities
   - Automatic TP/SL tracking
   - Performance analytics

2. **Bot Hosting** ($100-500/month)
   - Fully managed monitoring system
   - 24/7 signal generation and tracking
   - Custom alerts via Telegram/Discord

3. **Custom Development** ($2000-10,000)
   - Build similar systems for clients
   - Integrate with their exchanges
   - Add custom indicators and filters

This is a **production-ready system** that demonstrates your expertise in:
- Real-time data processing
- Database design
- API integration
- Risk management
- Performance tracking

**Perfect portfolio piece for freelancing!** 🚀

