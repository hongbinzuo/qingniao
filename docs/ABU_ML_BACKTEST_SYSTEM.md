# ABU ML Backtest Training System

## Overview

This system generates labeled training data for machine learning by backtesting ABU signals on historical price data across diverse coins and time periods.

## Goals

1. **Primary**: Rank signals by expected profitability (regression)
2. **Secondary**: Filter signals - predict which to take vs skip (classification)
3. **Tertiary**: Optimize parameters - learn best SL/TP for each pattern

---

## Data Sampling Strategy

### Coin Batches (by Market Cap Rank)

| Batch | Rank Range | Count | Purpose |
|-------|------------|-------|---------|
| 1 | Top 10 | 10 | High liquidity, stable patterns |
| 2 | 100-120 | 20 | Mid-cap, moderate volatility |
| 3 | 200-210 | 10 | Lower liquidity |
| 4 | 500-510 | 10 | Small cap |
| 5 | 990-1000 | 10 | Micro cap |
| 6 | 1500-1520 | 20 | Ultra small cap |
| **Total** | | **80** | |

### Survivorship Bias Mitigation

**Approach**: Fixed coin list per period

For each historical period, we lock a coin list based on what existed at that time:
- 2019-2020: Only coins that existed then (BTC, ETH, XRP, LTC, etc.)
- 2021-2022: Add coins launched by then (SOL, AVAX, etc.)
- 2023+: Full current list

**Metadata stored**: `period_coin_list.json` with exact coins per period.

**Known limitation**: This is simpler than true historical snapshots but avoids the worst survivorship bias.

### Time Periods (Fixed Date Ranges)

| Period | Exact Dates | Duration | Purpose |
|--------|-------------|----------|---------|
| Recent | 2025-11-01 to 2026-01-31 | 3 months | Current market |
| Summer 2025 | 2025-07-01 to 2025-07-31 | 1 month | Seasonal |
| 2023 | 2023-03-01 to 2023-04-30 | 2 months | Bear/recovery |
| 2022 | 2022-05-01 to 2022-08-31 | 4 months | Bear market |
| 2021 | 2021-04-01 to 2021-05-31 | 2 months | Bull peak |
| 2020 | 2020-03-01 to 2020-05-31 | 3 months | COVID crash |
| 2019 | 2019-06-01 to 2019-07-31 | 2 months | Pre-bull |
| **Total** | | **17 months** | |

**RNG Seed**: 42 (for any randomization, documented for reproducibility)

### Timeframes

| Timeframe | Signal Interval | Expiration | Candles to Check |
|-----------|-----------------|------------|------------------|
| 15m | Every 2 hours | 24 hours | 96 candles |
| 1h | Every 4 hours | 48 hours | 48 candles |
| 4h | Every 8 hours | 1 week | 42 candles |

---

## Data Volume

### Calculation Formula

```
Coins: 80 (across all batches)
Months: 17 (total across all periods)
Days per month: 30 (average)

Candles per timeframe:
  - 15m: 80 coins × 17 months × 30 days × 24h × 4 = 3,916,800
  - 1h:  80 coins × 17 months × 30 days × 24h × 1 = 979,200
  - 4h:  80 coins × 17 months × 30 days × 6 = 244,800

Signals per timeframe (signal_interval):
  - 15m: 80 × 17 × 30 × 12 (every 2h) = 489,600
  - 1h:  80 × 17 × 30 × 6 (every 4h) = 244,800
  - 4h:  80 × 17 × 30 × 3 (every 8h) = 122,400
```

### Summary

| Metric | 15m | 1h | 4h | Total |
|--------|-----|----|----|-------|
| Candles | 3.9M | 1.0M | 0.2M | 5.1M |
| Signal Points | 489K | 245K | 122K | 856K |

---

## Signal Outcome Labels

### Multi-class Classification

| Label | Definition |
|-------|------------|
| `TP2_HIT` | Price reached TP2 before SL or expiration |
| `TP1_HIT` | Price reached TP1 before SL or expiration (may or may not hit TP2 later) |
| `SL_HIT` | Price hit stop loss before any TP |
| `EXPIRED` | Signal expired without hitting TP or SL |

### Sequential Outcome Rules

**Key rule**: First trigger wins, checked candle-by-candle.

| Scenario | Outcome | Reason |
|----------|---------|--------|
| TP1 hit, then SL later | `TP1_HIT` | TP1 triggered first |
| TP1 hit, then TP2 | `TP2_HIT` | Best outcome achieved |
| SL and TP1 same candle | `SL_HIT` | Conservative (SL wins ties) |
| No trigger within expiration | `EXPIRED` | Time ran out |

### Partial Outcome Metadata

For `TP1_HIT` outcomes, we also record:
- `partial_sl_hit`: Boolean - did SL hit after TP1?
- `max_favorable_excursion`: How far price went in favorable direction
- `actual_rr`: Realized risk-reward ratio

### Conflict Resolution

If price hits both TP and SL in same candle: **SL wins** (conservative)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ABU ML Backtest System                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │    Phase 1   │───▶│    Phase 2   │───▶│    Phase 3   │  │
│  │    Data      │    │    Signal    │    │   Outcome    │  │
│  │  Collection  │    │  Generation  │    │   Labeling   │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                                       │           │
│         ▼                                       ▼           │
│  ┌──────────────┐                       ┌──────────────┐   │
│  │   DuckDB     │                       │   Labeled    │   │
│  │   Storage    │                       │   Dataset    │   │
│  └──────────────┘                       └──────────────┘   │
│                                                │            │
│                    ┌──────────────┐            │            │
│                    │    Phase 4   │◀───────────┘            │
│                    │   Feature    │                         │
│                    │ Engineering  │                         │
│                    └──────────────┘                         │
│                           │                                 │
│                           ▼                                 │
│                    ┌──────────────┐    ┌──────────────┐    │
│                    │    Phase 5   │───▶│   Trained    │    │
│                    │  ML Training │    │    Model     │    │
│                    └──────────────┘    └──────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase Details

### Phase 1: Data Collection

**Input**: Coin list + time periods
**Output**: Historical OHLCV data in DuckDB

**Process**:
1. Fetch coin rankings from CoinGecko/CoinMarketCap
2. For each coin + period + timeframe:
   - Fetch klines from Gate.io (primary)
   - Fallback to Bitget/Bybit if unavailable
3. Store in `ml_backtest_klines` table

**Exchange Consistency Rule**:
- Once a coin uses a specific exchange for a period, ALL data for that coin+period must come from same exchange
- Store `source` column and filter by it during signal generation and labeling
- Never mix Gate.io signals with Bitget outcome data

**Rate Limiting**:
- Gate.io: 5 req/sec
- Implement exponential backoff
- Cache to avoid re-fetching

### Phase 2: Signal Generation

**Input**: Historical klines
**Output**: Raw signals with entry/SL/TP

**Process**:
1. For each coin + timeframe:
   - Slide through klines at signal interval
   - Run all detectors (InsideBar, Engulfing, PinBar, KeyLevel)
   - Record signal with timestamp, entry, SL, TP1, TP2
2. Store in `ml_backtest_signals` table

**Detectors**:
- InsideBar (with Brooks + ATR stop loss)
- Engulfing
- PinBar
- KeyLevel

### Phase 3: Outcome Labeling

**Input**: Signals + future klines
**Output**: Labeled signals

**Process**:
1. For each signal:
   - Get future klines up to expiration
   - Check candle by candle:
     - If low <= SL (long) or high >= SL (short): `SL_HIT`
     - If high >= TP2 (long) or low <= TP2 (short): `TP2_HIT`
     - If high >= TP1 (long) or low <= TP1 (short): `TP1_HIT`
   - If no trigger: `EXPIRED`
2. Update `ml_backtest_signals` with outcome

**Priority**: SL > TP2 > TP1 > EXPIRED

### Phase 4: Feature Engineering

**Input**: Labeled signals + klines
**Output**: Feature matrix

**CRITICAL: No Future Data Leakage**

All features must be computed using ONLY data available at `signal_time`:
- Lookback window: klines[signal_time - N : signal_time] (inclusive)
- Never use klines after signal_time
- Default lookback: 100 candles for most features

**Features** (~50 total):

```
Pattern Features:
  - pattern_type (one-hot)
  - signal_direction (long/short)
  - brooks_score
  - atr_ratio (risk / ATR)

Price Action Features (lookback=50):
  - trend_direction (EMA20 vs EMA50)
  - trend_strength
  - distance_to_support (from past 50 candles)
  - distance_to_resistance (from past 50 candles)
  - recent_volatility (ATR% over past 14 candles)

Market Context Features (lookback=100):
  - regime_36 components
  - overlap_ratio
  - pullback_depth

Volume Features (lookback=20):
  - volume_ratio (current / avg of past 20)
  - volume_trend (past 20 candles)

Time Features:
  - hour_of_day
  - day_of_week
  - is_weekend
```

### Phase 5: ML Training

**Input**: Feature matrix + labels
**Output**: Trained model

**Train/Test Split: Time-Based (No Leakage)**

```
Training: 2019, 2020, 2021, 2022 periods
Testing:  2023, 2025 (summer), Recent periods

Rationale: Never train on future data
```

**Models**:

1. **Ranking Model** (Primary): LightGBM Ranker
   - Predict expected R:R or profit probability
   - **Query Group**: All signals in same 2-hour window compete
   - Group key: `floor(signal_time / 7200)` (2h buckets)
   - Target: `actual_rr` (continuous) or `outcome_score` (TP2=3, TP1=2, EXPIRED=1, SL=0)
   
2. **Classification Model** (Secondary): XGBoost Classifier
   - Predict outcome class (TP2/TP1/SL/EXPIRED)

3. **Parameter Optimizer** (Tertiary): Bayesian Optimization
   - Find optimal SL/TP multipliers per pattern

**Evaluation Metrics**:
- NDCG@10 (ranking quality within each time window)
- Precision/Recall per class
- Profit factor on test set

---

## Evolution Strategy

### Iteration 1: Minimum Viable (10% data)

```
Goal: Validate approach works
Data: Top 10 coins, recent 3 months only
Time: ~30 minutes

Success Criteria:
  - Model trains without errors
  - Better than random baseline
  - Feature importance makes sense
```

### Iteration 2: Scale Up (50% data)

```
Goal: Improve model quality
Data: All coin batches, 50% of time periods
Time: ~2 hours

Actions:
  - Add more features based on Iteration 1 insights
  - Tune hyperparameters
  - Handle class imbalance
```

### Iteration 3: Full Dataset (100% data)

```
Goal: Production-ready model
Data: All coins, all periods
Time: ~4 hours

Actions:
  - Final feature selection
  - Cross-validation
  - Model ensembling
```

### Iteration 4+: Continuous Improvement

```
Frequency: Monthly
Actions:
  - Add new month's data
  - Retrain model
  - Monitor for drift
  - A/B test in production
```

---

## Database Schema

### Table: ml_backtest_klines

```sql
CREATE TABLE ml_backtest_klines (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL,
    source TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, timeframe, timestamp)
);

CREATE INDEX idx_klines_symbol_tf ON ml_backtest_klines(symbol, timeframe, timestamp);
```

### Table: ml_backtest_signals

```sql
CREATE TABLE ml_backtest_signals (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    signal_time INTEGER NOT NULL,
    pattern TEXT NOT NULL,
    direction TEXT NOT NULL,
    entry REAL NOT NULL,
    stop_loss REAL NOT NULL,
    stop_loss_atr REAL,
    take_profit_1 REAL NOT NULL,
    take_profit_2 REAL NOT NULL,
    
    -- Outcome (filled in Phase 3)
    outcome TEXT,  -- TP2_HIT, TP1_HIT, SL_HIT, EXPIRED
    outcome_time INTEGER,
    outcome_price REAL,
    actual_rr REAL,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, timeframe, signal_time, pattern, direction)
);

CREATE INDEX idx_signals_outcome ON ml_backtest_signals(outcome);
```

### Table: ml_backtest_features

```sql
CREATE TABLE ml_backtest_features (
    signal_id INTEGER PRIMARY KEY REFERENCES ml_backtest_signals(id),
    features_json TEXT NOT NULL,  -- JSON blob of all features
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## File Structure

```
qingniao/
├── src/
│   └── ml_backtest/
│       ├── __init__.py
│       ├── config.py           # Configuration constants
│       ├── data_collector.py   # Phase 1
│       ├── signal_generator.py # Phase 2
│       ├── outcome_labeler.py  # Phase 3
│       ├── feature_engineer.py # Phase 4
│       ├── model_trainer.py    # Phase 5
│       └── utils.py            # Shared utilities
├── tests/
│   └── ml_backtest/
│       ├── test_data_collector.py
│       ├── test_signal_generator.py
│       ├── test_outcome_labeler.py
│       ├── test_feature_engineer.py
│       └── test_model_trainer.py
├── models/
│   └── ml_backtest/
│       ├── ranking_model.pkl
│       └── classifier_model.pkl
└── data/
    └── ml_backtest/
        └── backtest.duckdb
```

---

## Usage

### Full Pipeline

```bash
# Run complete pipeline
python -m src.ml_backtest.run_pipeline --iteration 1

# Or run phases individually
python -m src.ml_backtest.data_collector --batch top10 --period recent
python -m src.ml_backtest.signal_generator --symbol BTC --timeframe 15m
python -m src.ml_backtest.outcome_labeler
python -m src.ml_backtest.feature_engineer
python -m src.ml_backtest.model_trainer --model ranking
```

### Configuration

```python
# src/ml_backtest/config.py

COIN_BATCHES = {
    'top10': {'start': 1, 'end': 10},
    'mid100': {'start': 100, 'end': 120},
    'rank200': {'start': 200, 'end': 210},
    'rank500': {'start': 500, 'end': 510},
    'rank1000': {'start': 990, 'end': 1000},
    'rank1500': {'start': 1500, 'end': 1520},
}

TIME_PERIODS = [
    {'name': 'recent', 'months': 3, 'year': 2026},
    {'name': 'summer', 'months': 1, 'year': 2025, 'start_month': 7},
    # ... etc
]

TIMEFRAME_CONFIG = {
    '15m': {'signal_interval_hours': 2, 'expiration_hours': 24},
    '1h': {'signal_interval_hours': 4, 'expiration_hours': 48},
    '4h': {'signal_interval_hours': 8, 'expiration_hours': 168},
}
```

---

## Next Steps

1. [ ] Review this documentation
2. [ ] Write unit tests for each phase
3. [ ] Implement Phase 1 (Data Collection)
4. [ ] Implement Phase 2 (Signal Generation)
5. [ ] Implement Phase 3 (Outcome Labeling)
6. [ ] Implement Phase 4 (Feature Engineering)
7. [ ] Implement Phase 5 (ML Training)
8. [ ] Run Iteration 1 (10% data)
9. [ ] Evaluate and iterate

---

## Appendix: Time Estimates

| Phase | First Run | Iteration |
|-------|-----------|-----------|
| Data Collection | 1-2 hours | 30 min (new data only) |
| Signal Generation | 15-30 min | 10 min |
| Outcome Labeling | 30-60 min | 15 min |
| Feature Engineering | 20-30 min | 10 min |
| ML Training | 10-30 min | 10-20 min |
| **Total** | **3-5 hours** | **1-2 hours** |
