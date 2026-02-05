# ABU ML Backtest System - Test Specifications

## Overview

This document defines the test cases for each phase of the ML backtest system.

---

## Test Structure

```
tests/ml_backtest/
├── conftest.py              # Shared fixtures
├── test_data_collector.py   # Phase 1 tests
├── test_signal_generator.py # Phase 2 tests
├── test_outcome_labeler.py  # Phase 3 tests
├── test_feature_engineer.py # Phase 4 tests
├── test_model_trainer.py    # Phase 5 tests
└── test_integration.py      # End-to-end tests
```

---

## Phase 1: Data Collector Tests

### test_data_collector.py

```python
class TestCoinRankingFetcher:
    """Test coin ranking retrieval"""
    
    def test_fetch_top10_coins(self):
        """Should return exactly 10 coins for top10 batch"""
        # Expected: ['BTC', 'ETH', 'XRP', ...]
        
    def test_fetch_mid_cap_coins(self):
        """Should return coins in rank 100-120"""
        
    def test_excludes_stablecoins(self):
        """Should exclude USDT, USDC, DAI, etc."""
        
    def test_handles_api_error(self):
        """Should retry on API failure"""


class TestKlineFetcher:
    """Test historical kline fetching"""
    
    def test_fetch_15m_klines(self):
        """Should fetch 15m klines with correct format"""
        # Verify: timestamp, open, high, low, close, volume
        
    def test_fetch_1h_klines(self):
        """Should fetch 1h klines"""
        
    def test_fetch_4h_klines(self):
        """Should fetch 4h klines"""
        
    def test_klines_sorted_by_timestamp(self):
        """Klines should be sorted oldest to newest"""
        
    def test_fallback_to_bitget(self):
        """Should fallback to Bitget if Gate.io fails"""
        
    def test_handles_missing_historical_data(self):
        """Should handle coins without 2019 data gracefully"""


class TestDataStorage:
    """Test DuckDB storage"""
    
    def test_insert_klines(self):
        """Should insert klines without duplicates"""
        
    def test_upsert_existing_klines(self):
        """Should update existing klines on conflict"""
        
    def test_query_klines_by_range(self):
        """Should query klines by time range efficiently"""
```

---

## Phase 2: Signal Generator Tests

### test_signal_generator.py

```python
class TestSignalGeneration:
    """Test signal generation from klines"""
    
    def test_generate_inside_bar_signal(self):
        """Should detect InsideBar pattern correctly"""
        # Given: klines with valid inside bar
        # Expected: long + short signals with correct entry/SL/TP
        
    def test_inside_bar_dual_stop_loss(self):
        """InsideBar should have both Brooks and ATR stop loss"""
        
    def test_generate_engulfing_signal(self):
        """Should detect Engulfing pattern"""
        
    def test_generate_pinbar_signal(self):
        """Should detect PinBar pattern"""
        
    def test_no_signal_when_no_pattern(self):
        """Should return empty when no pattern detected"""


class TestSignalInterval:
    """Test signal generation intervals"""
    
    def test_15m_signal_every_2h(self):
        """15m signals should be generated every 2 hours"""
        
    def test_1h_signal_every_4h(self):
        """1h signals should be generated every 4 hours"""
        
    def test_4h_signal_every_8h(self):
        """4h signals should be generated every 8 hours"""


class TestSignalStorage:
    """Test signal storage"""
    
    def test_store_signal(self):
        """Should store signal with all fields"""
        
    def test_no_duplicate_signals(self):
        """Should not create duplicate signals"""
```

---

## Phase 3: Outcome Labeler Tests

### test_outcome_labeler.py

```python
class TestOutcomeLabeling:
    """Test signal outcome determination"""
    
    def test_label_tp2_hit(self):
        """Should label TP2_HIT when price reaches TP2"""
        # Given: long signal, future candle high >= TP2
        # Expected: outcome = 'TP2_HIT'
        
    def test_label_tp1_hit(self):
        """Should label TP1_HIT when price reaches TP1 but not TP2"""
        
    def test_label_sl_hit(self):
        """Should label SL_HIT when price hits stop loss"""
        
    def test_label_expired(self):
        """Should label EXPIRED when no trigger within expiration"""
        
    def test_sl_wins_on_same_candle(self):
        """SL should win when both SL and TP hit in same candle"""
        # Given: candle where low <= SL and high >= TP1
        # Expected: outcome = 'SL_HIT'


class TestExpirationRules:
    """Test expiration time rules"""
    
    def test_15m_expires_in_24h(self):
        """15m signals should expire after 24 hours"""
        
    def test_1h_expires_in_48h(self):
        """1h signals should expire after 48 hours"""
        
    def test_4h_expires_in_1week(self):
        """4h signals should expire after 1 week"""


class TestShortSignals:
    """Test short signal outcome logic"""
    
    def test_short_tp_hit(self):
        """Short TP hit when price goes DOWN to target"""
        # Given: short signal, future candle low <= TP1
        # Expected: outcome = 'TP1_HIT'
        
    def test_short_sl_hit(self):
        """Short SL hit when price goes UP to stop"""
        # Given: short signal, future candle high >= SL
        # Expected: outcome = 'SL_HIT'
```

---

## Phase 4: Feature Engineer Tests

### test_feature_engineer.py

```python
class TestPatternFeatures:
    """Test pattern-related features"""
    
    def test_pattern_type_encoding(self):
        """Should one-hot encode pattern types"""
        
    def test_direction_encoding(self):
        """Should encode long=1, short=0"""
        
    def test_atr_ratio_calculation(self):
        """Should calculate risk / ATR correctly"""


class TestPriceActionFeatures:
    """Test price action features"""
    
    def test_trend_direction(self):
        """Should calculate trend from EMA20 vs EMA50"""
        
    def test_trend_strength(self):
        """Should calculate trend strength"""
        
    def test_support_resistance_distance(self):
        """Should calculate distance to S/R levels"""


class TestMarketContextFeatures:
    """Test market context features"""
    
    def test_regime_36_components(self):
        """Should extract regime_36 components"""
        
    def test_overlap_ratio(self):
        """Should calculate overlap ratio"""


class TestTimeFeatures:
    """Test time-based features"""
    
    def test_hour_of_day(self):
        """Should extract hour (0-23)"""
        
    def test_day_of_week(self):
        """Should extract day (0-6)"""
        
    def test_is_weekend(self):
        """Should flag weekend correctly"""
```

---

## Phase 5: Model Trainer Tests

### test_model_trainer.py

```python
class TestDataPreparation:
    """Test training data preparation"""
    
    def test_time_based_split(self):
        """Should split by time period, not random"""
        # Train: 2019-2022 periods
        # Test: 2023, 2025 periods
        # Verify: No overlap in timestamps
        
    def test_no_future_leakage_in_split(self):
        """Test set should only contain later dates than train set"""
        
    def test_handle_class_imbalance(self):
        """Should handle imbalanced classes"""
        
    def test_feature_scaling(self):
        """Should scale features appropriately"""


class TestRankingModel:
    """Test ranking model training"""
    
    def test_train_ranking_model(self):
        """Should train LightGBM ranker"""
        
    def test_query_groups_defined(self):
        """Should have query groups for ranking (2h windows)"""
        
    def test_ranking_model_prediction(self):
        """Should output ranking scores"""
        
    def test_ranking_better_than_random(self):
        """Ranking should beat random baseline"""


class TestClassificationModel:
    """Test classification model training"""
    
    def test_train_classifier(self):
        """Should train XGBoost classifier"""
        
    def test_predict_outcome_class(self):
        """Should predict TP2/TP1/SL/EXPIRED"""
        
    def test_classification_metrics(self):
        """Should report precision/recall per class"""


class TestModelPersistence:
    """Test model save/load"""
    
    def test_save_model(self):
        """Should save model to disk"""
        
    def test_load_model(self):
        """Should load model from disk"""
        
    def test_model_versioning(self):
        """Should version models with timestamp"""
```

---

## Integration Tests

### test_integration.py

```python
class TestEndToEnd:
    """End-to-end pipeline tests"""
    
    def test_mini_pipeline(self):
        """Run pipeline on 1 coin, 1 week data"""
        # Steps:
        # 1. Fetch BTC 15m klines for 1 week
        # 2. Generate signals
        # 3. Label outcomes
        # 4. Extract features
        # 5. Train model
        # Verify: No errors, model produces predictions
        
    def test_iteration_1_subset(self):
        """Run Iteration 1 on 10% data"""


class TestDataConsistency:
    """Test data consistency across phases"""
    
    def test_signal_count_matches_labels(self):
        """All signals should have outcome labels"""
        
    def test_features_match_signals(self):
        """All signals should have features"""
    
    def test_exchange_consistency(self):
        """Signal and outcome data must use same exchange source"""
        # Verify: signal.source == klines.source for outcome check


class TestLeakagePrevention:
    """Test for data leakage issues"""
    
    def test_no_future_features(self):
        """Features must only use data before signal_time"""
        # Given: signal at time T
        # Verify: all feature klines have timestamp <= T
        
    def test_time_split_no_overlap(self):
        """Train and test sets must not overlap in time"""
        
    def test_feature_lookback_respected(self):
        """Features use correct lookback windows"""


class TestSequentialOutcomes:
    """Test TP1 followed by SL scenarios"""
    
    def test_tp1_then_sl_is_tp1_hit(self):
        """TP1 hit first, then SL later = TP1_HIT"""
        # Given: candle 1 hits TP1, candle 5 hits SL
        # Expected: outcome = TP1_HIT
        
    def test_tp1_then_tp2_is_tp2_hit(self):
        """TP1 hit, then TP2 = TP2_HIT"""
```

---

## Test Fixtures (conftest.py)

```python
import pytest

@pytest.fixture
def sample_klines():
    """Generate sample klines for testing"""
    return [
        {'timestamp': 1700000000, 'open': 100, 'high': 105, 'low': 98, 'close': 103, 'volume': 1000},
        {'timestamp': 1700000900, 'open': 103, 'high': 104, 'low': 101, 'close': 102, 'volume': 800},
        # ... more candles
    ]

@pytest.fixture
def inside_bar_klines():
    """Klines with valid inside bar pattern"""
    return [
        {'timestamp': 1700000000, 'open': 100, 'high': 110, 'low': 95, 'close': 105, 'volume': 1000},
        {'timestamp': 1700000900, 'open': 105, 'high': 108, 'low': 97, 'close': 103, 'volume': 800},
    ]

@pytest.fixture
def sample_signal():
    """Sample signal for testing"""
    return {
        'symbol': 'BTC',
        'timeframe': '15m',
        'signal_time': 1700000900,
        'pattern': 'InsideBar',
        'direction': 'long',
        'entry': 103,
        'stop_loss': 95,
        'take_profit_1': 111,
        'take_profit_2': 119,
    }

@pytest.fixture
def test_db(tmp_path):
    """Create temporary test database"""
    db_path = tmp_path / "test_backtest.duckdb"
    # Initialize schema
    return db_path
```

---

## Running Tests

```bash
# Run all tests
pytest tests/ml_backtest/ -v

# Run specific phase
pytest tests/ml_backtest/test_data_collector.py -v

# Run with coverage
pytest tests/ml_backtest/ --cov=src/ml_backtest --cov-report=html

# Run integration tests only
pytest tests/ml_backtest/test_integration.py -v
```
