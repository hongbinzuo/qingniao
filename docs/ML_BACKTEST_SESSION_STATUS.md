# ML Backtest Session Status

**Last Updated**: 2026-02-02 20:45 UTC
**Session**: ML Backtest Pipeline Implementation

---

## Current Progress

### Completed Tasks

1. **Data Collector Rebuilt** - Using Bitget API (primary) with Bybit fallback
   - File: `src/ml_backtest/data_collector.py`
   - Fixed timeframe mapping: `{"15m": "15min", "1h": "1h", "4h": "4h"}`

2. **DuckDB Storage Setup**
   - File: `data/ml_backtest/backtest.duckdb`
   - Table: `ml_backtest_klines` (symbol, timeframe, timestamp, OHLCV, source)
   - **RULE**: DuckDB is ONLY for klines, not for signals/features/models

3. **Kline Data Imported** - 86,400 klines total
   - Source: Cached file `data/ml_backtest/klines_15m_50coins.json`
   - Period: 2025-10-13 to 2026-01-11 (~3 months)
   - Coins: BTC, ETH, XRP, BNB, SOL, DOGE, ADA, TRX, AVAX, LINK
   - Each coin: 8,640 klines (15m timeframe)

### In Progress

4. **Signal Generation** - Pipeline was running when session ended
   - Script: `scripts/run_ml_pipeline.py`
   - Progress: 8/10 coins completed signal generation
   - Signals generated so far:
     - BTC: 647 signals
     - ETH: 643 signals
     - XRP: 671 signals
     - BNB: 611 signals
     - SOL: 587 signals
     - DOGE: 587 signals
     - ADA: 531 signals
     - TRX: 647 signals
     - AVAX: (pending)
     - LINK: (pending)
   - Expected total: ~6,000 signals

### Pending Tasks

5. **Label Signal Outcomes** - Phase 3
   - Labels: TP2_HIT, TP1_HIT, SL_HIT, EXPIRED
   - Output: `data/ml_backtest/labeled_signals.json`

6. **Feature Engineering** - Phase 4
   - File: `src/ml_backtest/feature_engineer.py` (already implemented)
   - Features: ATR, RSI, volatility, trend, volume ratio, etc.

7. **ML Training** - Phase 5
   - Need to implement: `src/ml_backtest/model_trainer.py`
   - Model: LightGBM classifier

8. **Analysis & ABU Evolution** - Phase 6
   - Analyzer: `src/ml_backtest/analyzer.py` (already implemented)

---

## Key Files

### ML Backtest Module
- `src/ml_backtest/__init__.py`
- `src/ml_backtest/config.py` - Configuration
- `src/ml_backtest/data_collector.py` - Bitget/Bybit API
- `src/ml_backtest/signal_generator.py` - Uses ABU detectors
- `src/ml_backtest/outcome_labeler.py` - Labels signals
- `src/ml_backtest/feature_engineer.py` - Feature extraction
- `src/ml_backtest/analyzer.py` - Results analysis

### Scripts
- `scripts/run_ml_pipeline.py` - Main pipeline runner
- `scripts/run_ml_analysis.py` - Analysis runner
- `scripts/run_iteration1.py` - Data collection

### Data Files
- `data/ml_backtest/backtest.duckdb` - Klines storage (86,400 rows)
- `data/ml_backtest/klines_15m_50coins.json` - Cached klines (74MB)
- `data/ml_backtest/labeled_signals.json` - (to be created)

---

## ABU System Fixes Applied (Earlier in Session)

Based on mini backtest analysis (68% SL hit rate):

1. **Widened Stop Losses** - All patterns now use wider of pattern SL or 1.5x ATR
   - `src/abu/detectors.py`: Engulfing, PinBar updated

2. **Disabled KeyLevel Pattern** - 100% SL hit rate
   - `src/abu/detectors.py:351,379` - Commented out in detect_all_15m/1h

3. **Added Trend Filter** - Reduces counter-trend signals
   - `src/abu/detectors.py:55-86` - Added `_calc_ema()` and `_get_trend()`
   - Longs only in uptrend/neutral, shorts only in downtrend/neutral

---

## To Continue Next Session

1. **Check if pipeline completed**:
   ```bash
   ls data/ml_backtest/labeled_signals.json
   ```

2. **If not completed, re-run pipeline**:
   ```bash
   python scripts/run_ml_pipeline.py
   ```

3. **After signals labeled, run analysis**:
   ```bash
   python scripts/run_ml_analysis.py
   ```

4. **Implement ML training** (if not done):
   - Create `src/ml_backtest/model_trainer.py`
   - Train LightGBM on labeled signals

5. **Commit changes**:
   ```bash
   git add data/ml_backtest/backtest.duckdb
   git add src/ml_backtest/
   git add scripts/run_ml_pipeline.py
   git commit -m "feat: ML backtest pipeline with 86k klines"
   ```

---

## Important Rules (from AGENTS.md)

- **DuckDB**: ONLY for historical klines, not for signals/features/models
- **Other data**: Use JSON files or PostgreSQL
- **Scripts**: Must be in `scripts/` folder
- **ABU scripts**: Must be in `scripts/abu/` folder
