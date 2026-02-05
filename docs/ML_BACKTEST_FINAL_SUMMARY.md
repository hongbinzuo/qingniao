# ML Backtest Analysis Summary

**Date**: 2026-02-02
**Session**: ML Backtest Pipeline Implementation & Analysis

---

## Executive Summary

Completed full ML backtest pipeline with 6,029 signals across 10 coins over 3 months. Analysis reveals **68.4% stop-loss hit rate** with no predictive factors found. Current ABU patterns show no edge in crypto markets.

---

## Data Overview

### Signals Generated
- **Total**: 6,029 signals
- **File**: `data/ml_backtest/labeled_signals.json` (3.0 MB)
- **Timeframe**: 15m only
- **Period**: October 14, 2025 → January 11, 2026 (~3 months)
- **Signal Interval**: Every 6 hours

### Data Sources
- **Primary Exchange**: Bitget API
- **Fallback Exchange**: Bybit API
- **Klines Storage**: `data/ml_backtest/backtest.duckdb` (86,400 klines)

### Coins Analyzed (10 total)
```
BTC:  647 signals
ETH:  643 signals
XRP:  671 signals
BNB:  611 signals
SOL:  587 signals
DOGE: 587 signals
ADA:  531 signals
TRX:  647 signals
AVAX: 580 signals
LINK: 525 signals
```

---

## Signal Outcomes

### Overall Results
- **SL_HIT**: 4,121 (68.4%) ❌ FAILED
- **TP2_HIT**: 1,862 (30.9%) ✅ SUCCESS
- **TP1_HIT**: 26 (0.4%)
- **EXPIRED**: 20 (0.3%)

### Pattern Performance
All patterns show similar poor performance:
- **InsideBar**: 2,476 signals, 69% SL rate
- **PinBar**: 2,486 signals, 67% SL rate
- **Engulfing**: 1,067 signals, 68% SL rate

---

## Analysis Findings

### What We Tested
✗ **Pattern type**: No difference (all ~31% success)
✗ **Direction** (long/short): Both ~31% success
✗ **Risk/Reward ratio**: 2.00 vs 1.98 (identical)
✗ **Time of day**: 30-32% success (minimal difference)
✗ **Stop loss width**: 67-69% fail rate across all ranges
✗ **Coin selection**: 29-34% range (small variance)
✗ **Market features** (ATR, RSI, EMA): No predictive power

### Critical Finding
**The 31% success rate appears RANDOM, not skill-based.**

None of the analyzed factors can predict which signals will succeed.

---

## ML Model Results

### Baseline Model (Simple Features)
- Accuracy: 69% (predicts all signals as "bad")
- Precision: 0% for good signals
- Recall: 0% for good signals
- **Conclusion**: Useless - just predicts majority class

### Enhanced Model (Rich Features)
Added: ATR, RSI, EMA trend, volume
- Accuracy: 69% (same as baseline)
- Precision: 0% for good signals
- Recall: 0% for good signals
- **Conclusion**: Rich features didn't help

---

## Performance Optimizations Applied

### Signal Generator
- **Before**: O(n²) linear search
- **After**: O(n log n) binary search with `bisect`
- **Impact**: Dramatically faster

### Outcome Labeler
- **Before**: O(n×m) filtering
- **After**: O(n log m) with grouping + binary search
- **Impact**: Much faster labeling

### Pipeline Concurrency
- **Added**: ProcessPoolExecutor with 4 workers
- **DuckDB Fix**: `read_only=True` for concurrent access
- **Impact**: 4x speedup potential

---

## Key Insights

### 1. Stop Loss Width Doesn't Matter
- Tight (<0.5%): 67.9% SL hit
- Medium (0.5-1%): 69.6% SL hit
- Wide (>1%): 67.3% SL hit

**Conclusion**: Widening stops won't help - same failure rate.

### 2. Patterns Have No Edge
All patterns fail at similar rates regardless of:
- Market conditions (volatility, trend)
- Time of day
- Coin selection
- Direction (long/short)

### 3. Success is Random
The 31% success rate shows no correlation with any measurable factor, suggesting it's random market noise, not skill.

---

## Profitability Analysis

**Math**: (0.31 × 2 R:R) - (0.69 × 1 risk) = **-0.07**

**Result**: LOSING SYSTEM (-7% expected value per trade)

---

## Recommendations

### Option 1: Fundamental Redesign ⭐ RECOMMENDED
- Current patterns are broken
- Research what actually works in crypto
- Rebuild from scratch with proven concepts

### Option 2: Accept & Document
- Document 31% success rate
- Do NOT trade this live
- Use as learning experience

### Option 3: Different Approach
- Abandon pattern-based trading
- Try momentum/trend following
- Use ML to generate new signals (not filter)

---

## Next Steps (In Progress)

Currently collecting 1h and 4h klines to test if higher timeframes perform better:
- Higher timeframes typically have less noise
- Could show different success rates
- Worth testing before final decision

---

## Files & Locations

### Data Files
- `data/ml_backtest/labeled_signals.json` - 6,029 labeled signals (3.0 MB)
- `data/ml_backtest/backtest.duckdb` - 86,400 klines (15m only)
- `data/ml_backtest/analysis_results.json` - Analysis results
- `data/ml_backtest/signal_quality_model.txt` - Trained ML model
- `data/ml_backtest/model_evaluation.json` - Model metrics

### Code Files
- `src/ml_backtest/` - ML backtest module
- `scripts/run_ml_pipeline.py` - Main pipeline (optimized)
- `scripts/train_ml_model.py` - ML training script
- `scripts/run_ml_analysis.py` - Analysis script
- `CLAUDE.md` - Session memory file

---

## Session Memory

This analysis is documented in `CLAUDE.md` for future sessions. All progress, findings, and optimizations are preserved for continuation.
