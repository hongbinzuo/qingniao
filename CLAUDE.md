# Qingniao Trading Bot - Project Context

## Project Overview
Cryptocurrency trading bot with ABU (Automated Buy/Sell) system using pattern detection and ML-enhanced signal filtering.

## Current Focus: ML Backtest System
**Goal**: Train ML model to filter ABU signals and reduce stop-loss hit rate from 68% to <50%.

### ML Backtest Progress (COMPLETED Phase 1-4)
- **Phase 1-3**: 15m timeframe baseline completed
- **Phase 4**: ✅ Timeframe comparison completed (15m vs 1h vs 4h)
- **Status**: Ready for ML model training with optimal timeframe

### Timeframe Comparison Results (Feb 2026)
**Data Collected:**
- **15m**: 86,400 klines → 6,029 signals
- **1h**: 10,000 klines → 1,291 signals
- **4h**: 4,132 klines → 872 signals

**Success Rates (TP1 or TP2 Hit):**
- **15m**: 31.3% success, 68.4% SL hit (baseline)
- **1h**: 47.3% success, 52.0% SL hit (+15.9% improvement)
- **4h**: 51.7% success, 47.0% SL hit (+20.4% improvement) ⭐ BEST

**Key Finding**: 4h timeframe produces significantly better signals with 51.7% success rate vs 31.3% for 15m.

**Recommendation**: Use 4h timeframe for production signal generation.

### Key Files
- `src/ml_backtest/` - ML backtest module
- `scripts/run_ml_pipeline.py` - Main pipeline (optimized with concurrency)
- `scripts/collect_1h_4h_klines.py` - Collect 1h and 4h klines
- `scripts/generate_1h_4h_signals.py` - Generate signals for 1h/4h timeframes
- `scripts/label_1h_4h_outcomes.py` - Label outcomes for 1h/4h signals
- `scripts/compare_timeframes.py` - Compare 15m vs 1h vs 4h results
- `data/ml_backtest/backtest.duckdb` - Klines storage (15m, 1h, 4h)
- `data/ml_backtest/labeled_signals.json` - 6,029 labeled 15m signals (3.0 MB)
- `data/ml_backtest/labeled_signals_1h.json` - 1,291 labeled 1h signals
- `data/ml_backtest/labeled_signals_4h.json` - 872 labeled 4h signals
- `docs/ML_BACKTEST_SESSION_STATUS.md` - Detailed progress tracker

## Performance Optimizations Applied

### Signal Generator (src/ml_backtest/signal_generator.py)
- **Before**: O(n²) linear search for each timestamp
- **After**: O(n log n) binary search with `bisect` module
- **Impact**: Dramatically faster signal generation

### Outcome Labeler (src/ml_backtest/outcome_labeler.py)
- **Before**: O(n×m) filtering all klines for each signal
- **After**: O(n log m) group by symbol + binary search
- **Impact**: Much faster outcome labeling

### Pipeline Concurrency (scripts/run_ml_pipeline.py)
- **Added**: ProcessPoolExecutor with 4 workers
- **Benefit**: Process multiple coins in parallel
- **DuckDB Fix**: Added `read_only=True` for concurrent access
- **Impact**: 4x speedup potential

## Architecture Rules

### Data Storage
- **DuckDB**: ONLY for historical klines (OHLCV data)
- **PostgreSQL**: Live trading data, signals, positions
- **JSON files**: ML backtest signals, features, analysis results
- **Never**: Store signals/features/models in DuckDB

### Code Organization
- Scripts in `scripts/` folder
- ABU-specific scripts in `scripts/abu/`
- ML backtest module in `src/ml_backtest/`
- Core ABU detectors in `src/abu/detectors.py`

### ABU System
- Patterns: Engulfing, PinBar, KeyLevel (disabled), HighVolume
- Stop-loss: Wider of pattern SL or 1.5x ATR
- Trend filter: EMA-based (longs in uptrend, shorts in downtrend)
- Timeframes: 15m (primary), 1h, 4h

## Recent Changes
1. Widened stop-losses to 1.5x ATR minimum
2. Disabled KeyLevel pattern (100% SL hit rate)
3. Added EMA trend filter to reduce counter-trend signals
4. Built ML backtest pipeline with Bitget/Bybit data sources

## Development Workflow
1. Always check `docs/ML_BACKTEST_SESSION_STATUS.md` for current state
2. Use `scripts/run_ml_pipeline.py` for full ML workflow
3. Commit DuckDB and JSON files to track progress
4. Test changes with mini backtest before full runs

## External Services
- **Bitget API**: Primary data source (15m, 1h, 4h klines)
- **Bybit API**: Fallback data source
- **Railway**: Deployment platform with PostgreSQL
- **Neon**: Alternative PostgreSQL provider

## Brooks Sequence Matching (Feb 2026)

### What Was Built
- `src/abu/brooks_sequence_matcher.py` - Hybrid sequence matcher
- Extracts 62 consecutive page clusters from Brooks' 1000 teaching images
- Matches live candle phases against multi-page pattern progressions
- Predicts next phase based on cluster consensus

### Key Functions
- `load_brooks_clusters()` - Extract consecutive page sequences
- `match_against_clusters()` - Match live phases against clusters
- `predict_next_phase()` - Predict what comes next

### The Gap Discovered
Brooks' clusters use rich phases like `wedge_double_top_bottom_trading_range`
Our encoder produces simple phases like `trend`, `reversal`, `range`
Matching only works on primary component, losing specificity.

### Three Options to Improve (see docs/BROOKS_SEQUENCE_MATCHING_OPTIONS.md)
1. **Vector Matching**: Use existing `pattern_vectors.trend_vector` embeddings
2. **Image Matching**: Render charts, send to Gemini, compare embeddings (highest accuracy)
3. **Enhanced Encoder**: Detect secondary patterns and cycles locally

### Decision Pending
User needs to decide which option to pursue. Document saved for review.
