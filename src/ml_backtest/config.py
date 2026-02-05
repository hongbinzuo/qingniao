# Configuration for ML Backtest System

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data" / "ml_backtest"
MODELS_DIR = ROOT / "models" / "ml_backtest"

DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "backtest.duckdb"

RNG_SEED = 42

# Coin batches by market cap rank
COIN_BATCHES = {
    "top10": (1, 10),
    "mid100": (100, 120),
    "rank200": (200, 210),
    "rank500": (500, 510),
    "rank1000": (990, 1000),
    "rank1500": (1500, 1520),
}

# Fixed date ranges for each period
TIME_PERIODS = [
    {"name": "recent", "start": "2025-11-01", "end": "2026-01-31"},
    {"name": "summer2025", "start": "2025-07-01", "end": "2025-07-31"},
    {"name": "2023", "start": "2023-03-01", "end": "2023-04-30"},
    {"name": "2022", "start": "2022-05-01", "end": "2022-08-31"},
    {"name": "2021", "start": "2021-04-01", "end": "2021-05-31"},
    {"name": "2020", "start": "2020-03-01", "end": "2020-05-31"},
    {"name": "2019", "start": "2019-06-01", "end": "2019-07-31"},
]

# Timeframe settings
TIMEFRAME_CONFIG = {
    "15m": {"signal_interval_hours": 2, "expiration_hours": 24},
    "1h": {"signal_interval_hours": 4, "expiration_hours": 48},
    "4h": {"signal_interval_hours": 8, "expiration_hours": 168},
}
