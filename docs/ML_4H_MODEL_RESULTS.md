# 4H ML Model Training Results

**Date**: February 4, 2026  
**Objective**: Train ML model to filter 4h ABU signals and reduce SL hit rate

---

## Dataset Summary

**Total Signals**: 872 labeled 4h signals

**Outcome Distribution**:
- SL_HIT: 410 (47.0%) - Stop loss hit
- TP1_HIT: 351 (40.3%) - First take profit hit
- TP2_HIT: 100 (11.5%) - Second take profit hit
- EXPIRED: 11 (1.3%) - Neither TP nor SL hit

**Labeling Strategy**:
- **Good signals (label=1)**: TP1_HIT or TP2_HIT = 451 signals (51.7%)
- **Bad signals (label=0)**: SL_HIT or EXPIRED = 421 signals (48.3%)

---

## Model Architecture

**Algorithm**: LightGBM (Gradient Boosting)

**Features** (9 total):
1. Pattern type (one-hot): Engulfing, PinBar, InsideBar
2. Direction: Long vs Short
3. Stop-loss distance (% from entry)
4. Take-profit-2 distance (% from entry)
5. ATR (% of entry price)
6. RSI (normalized 0-1)
7. EMA trend (EMA20 vs EMA50)

**Training Split**:
- Train: 70%
- Validation: 15%
- Test: 15%

---

## Performance Results

### Test Set Metrics (131 signals)

**Confusion Matrix**:
```
                Predicted Bad  Predicted Good
Actual Bad            26            37
Actual Good           28            40
```

**Key Metrics**:
- **Precision**: 51.9% (40/77 predicted good signals were actually good)
- **Recall**: 58.8% (40/68 actual good signals were caught)
- **Accuracy**: 50.4% (66/131 correct predictions)
- **F1-Score**: 55.1%

---

## Comparison to Baseline

### Without ML Filtering (All 4h Signals)
- Success rate: 51.7% (TP1 or TP2 hit)
- SL hit rate: 47.0%
- Total signals: 872

### With ML Filtering (Predicted "Good" Only)
- Success rate: 51.9% (40 good / 77 predicted)
- SL hit rate: 48.1% (37 bad / 77 predicted)
- Signal reduction: ~88% fewer signals (77 vs 872)

**Conclusion**: Model performs at baseline level with no significant improvement.

---

## Issues Identified

### 1. Class Imbalance (FIXED)
- **Initial problem**: Only TP2_HIT (11.5%) labeled as good
- **Solution**: Changed to TP1_HIT OR TP2_HIT (51.7%) as good
- **Result**: Balanced dataset, model now makes predictions

### 2. Limited Feature Set
Current features are basic technical indicators. Missing:
- Volume patterns and anomalies
- Market structure (higher timeframe context)
- Volatility regime indicators
- Time-of-day / day-of-week patterns
- Multi-timeframe confirmation

### 3. Small Dataset
- Only 872 signals total
- Test set only 131 signals
- May not capture full market regime diversity

---

## Recommendations for Improvement

### Phase 1: Feature Engineering (HIGH PRIORITY)

Add more sophisticated features to capture market context:

**Volume Features**:
- Volume spike detection (current vs average)
- Volume trend (increasing/decreasing)
- Volume-price divergence

**Market Structure**:
- Recent swing highs/lows
- Support/resistance proximity
- Trend strength indicators (ADX)

**Volatility Features**:
- ATR percentile (current vs historical)
- Bollinger Band width
- Recent volatility regime changes

**Multi-Timeframe Context**:
- Daily trend alignment
- Weekly support/resistance levels
- Higher timeframe momentum

### Phase 2: Model Tuning

**Hyperparameter Optimization**:
- Grid search for optimal learning rate, num_leaves, max_depth
- Adjust scale_pos_weight for better precision/recall balance
- Experiment with different threshold values (currently 0.5)

**Alternative Algorithms**:
- Try XGBoost, CatBoost for comparison
- Ensemble multiple models
- Neural network approaches

### Phase 3: Data Expansion

**Collect More Historical Data**:
- Extend lookback period to capture more market regimes
- Include bear market, bull market, and sideways periods
- Target 2000+ signals for more robust training

### Phase 4: Alternative Approaches

**Consider Different Success Criteria**:
- Instead of binary classification, predict probability of success
- Predict expected return or risk/reward ratio
- Multi-class classification (TP2, TP1, SL, EXPIRED)

**Feature Importance Analysis**:
- Identify which features contribute most to predictions
- Remove low-importance features to reduce overfitting
- Focus data collection on high-value features

---

## Next Steps

1. **Immediate**: Implement Phase 1 feature engineering
2. **Short-term**: Tune model hyperparameters and threshold
3. **Medium-term**: Collect more historical data
4. **Long-term**: Explore alternative ML approaches

---

## Files Generated

- `data/ml_backtest/signal_quality_model_4h.txt` - Trained LightGBM model
- `data/ml_backtest/model_evaluation_4h.json` - Performance metrics
- `scripts/train_ml_model_4h.py` - Training script for 4h signals
- `src/ml_backtest/model_trainer.py` - Updated with timeframe support

---

## Conclusion

The 4h ML model has been successfully trained but currently performs at baseline level (51.9% success rate). The model needs enhanced features and tuning to achieve the goal of reducing SL hit rate below 50%. The infrastructure is in place for iterative improvement through feature engineering and hyperparameter optimization.
