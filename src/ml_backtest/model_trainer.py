"""ML model trainer for signal quality prediction - WITH RICH FEATURES."""

import json
from pathlib import Path
from typing import Dict, List, Tuple

import duckdb
import lightgbm as lgb
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

from .config import DATA_DIR, DB_PATH


def load_klines_for_signal(
    symbol: str, signal_time: int, lookback: int = 100, timeframe: str = "15m"
) -> List[Dict]:
    """Load klines before signal time for feature extraction."""
    conn = duckdb.connect(str(DB_PATH), read_only=True)
    rows = conn.execute(
        "SELECT timestamp, open, high, low, close, volume FROM ml_backtest_klines "
        "WHERE symbol = ? AND timeframe = ? AND timestamp <= ? ORDER BY timestamp DESC LIMIT ?",
        [symbol, timeframe, signal_time, lookback],
    ).fetchall()
    conn.close()

    klines = [
        {
            "timestamp": r[0],
            "open": r[1],
            "high": r[2],
            "low": r[3],
            "close": r[4],
            "volume": r[5],
        }
        for r in reversed(rows)
    ]
    return klines


def calc_atr(klines: List[Dict], period: int = 14) -> float:
    """Calculate ATR."""
    if len(klines) < 2:
        return 0.0
    trs = []
    for i in range(1, len(klines)):
        h, l, pc = klines[i]["high"], klines[i]["low"], klines[i - 1]["close"]
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)
    return sum(trs[-period:]) / min(period, len(trs)) if trs else 0.0


def calc_rsi(klines: List[Dict], period: int = 14) -> float:
    """Calculate RSI."""
    if len(klines) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(klines)):
        delta = klines[i]["close"] - klines[i - 1]["close"]
        gains.append(max(0, delta))
        losses.append(max(0, -delta))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calc_ema(values: List[float], period: int) -> float:
    """Calculate EMA."""
    if not values or len(values) < period:
        return sum(values) / len(values) if values else 0.0
    mult = 2 / (period + 1)
    ema = sum(values[:period]) / period
    for v in values[period:]:
        ema = v * mult + ema * (1 - mult)
    return ema


def prepare_training_data(
    labeled_signals: List[Dict], timeframe: str = "15m"
) -> Tuple[np.ndarray, np.ndarray]:
    """Prepare features and labels - WITH RICH FEATURES."""
    features_list = []
    labels = []
    pattern_types = ["Engulfing", "PinBar", "InsideBar"]

    print(f"Extracting rich features (loading {timeframe} klines)...")
    processed = 0

    for sig in labeled_signals:
        symbol = sig["symbol"]
        signal_time = sig["signal_time"]

        # Load klines
        klines = load_klines_for_signal(
            symbol, signal_time, lookback=100, timeframe=timeframe
        )
        if len(klines) < 50:
            continue

        # Basic features
        pattern = sig.get("pattern", "Unknown")
        direction = sig.get("type", "long")
        entry = sig["entry"]
        sl = sig["stop_loss"]
        tp2 = sig["take_profit_2"]

        # Market context features
        atr = calc_atr(klines)
        rsi = calc_rsi(klines)
        closes = [k["close"] for k in klines]
        ema20 = calc_ema(closes, 20)
        ema50 = calc_ema(closes, 50)

        # Combine all features
        pattern_features = [1 if pattern == p else 0 for p in pattern_types]
        features = pattern_features + [
            1 if direction == "long" else 0,
            abs(sl - entry) / entry,
            abs(tp2 - entry) / entry,
            atr / entry,
            rsi / 100,
            (ema20 - ema50) / ema50 if ema50 > 0 else 0,
        ]

        # Label: TP1_HIT or TP2_HIT = good signal (1), SL_HIT or EXPIRED = bad signal (0)
        outcome = sig.get("outcome", "UNKNOWN")
        label = 1 if outcome in ["TP1_HIT", "TP2_HIT"] else 0

        features_list.append(features)
        labels.append(label)

        processed += 1
        if processed % 1000 == 0:
            print(f"  Processed {processed}/{len(labeled_signals)} signals...")

    X = np.array(features_list)
    y = np.array(labels)
    return X, y


def train_model(X_train, y_train, X_val, y_val) -> lgb.Booster:
    """Train LightGBM model with class weights."""
    train_data = lgb.Dataset(X_train, label=y_train)
    val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

    # Calculate class weights to handle imbalance
    n_samples = len(y_train)
    n_positive = sum(y_train)
    n_negative = n_samples - n_positive
    scale_pos_weight = n_negative / n_positive if n_positive > 0 else 1.0

    params = {
        "objective": "binary",
        "metric": "binary_logloss",
        "scale_pos_weight": scale_pos_weight,
        "num_leaves": 31,
        "learning_rate": 0.05,
        "verbose": -1,
    }

    print(f"Training with scale_pos_weight={scale_pos_weight:.2f}...")
    model = lgb.train(
        params,
        train_data,
        num_boost_round=100,
        valid_sets=[val_data],
        callbacks=[lgb.early_stopping(10)],
    )
    return model


def evaluate_model(model: lgb.Booster, X_test, y_test) -> Dict:
    """Evaluate model performance."""
    y_pred_proba = model.predict(X_test)
    y_pred = (y_pred_proba > 0.5).astype(int)

    print("\n" + "=" * 50)
    print("MODEL EVALUATION")
    print("=" * 50)
    print(classification_report(y_test, y_pred, target_names=["Bad", "Good"]))
    cm = confusion_matrix(y_test, y_pred)
    print(f"\nConfusion Matrix:\n{cm}")

    tn, fp, fn, tp = cm.ravel()
    results = {
        "precision": tp / (tp + fp) if (tp + fp) > 0 else 0,
        "recall": tp / (tp + fn) if (tp + fn) > 0 else 0,
        "confusion_matrix": cm.tolist(),
    }
    return results


def train_and_evaluate(
    labeled_signals: List[Dict], timeframe: str = "15m"
) -> Tuple[lgb.Booster, Dict]:
    """Main function to train and evaluate."""
    print(f"Preparing training data from {len(labeled_signals)} signals...")
    X, y = prepare_training_data(labeled_signals, timeframe=timeframe)

    print(f"Features shape: {X.shape}")
    print(f"Labels: {np.bincount(y)}")

    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp
    )

    print(f"Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")

    model = train_model(X_train, y_train, X_val, y_val)
    results = evaluate_model(model, X_test, y_test)

    return model, results
