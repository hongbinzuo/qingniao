"""Run ML backtest pipeline - Iteration 1."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ml_backtest.data_collector import collect_iteration1

if __name__ == "__main__":
    print("=" * 50)
    print("ML BACKTEST PIPELINE - ITERATION 1")
    print("=" * 50)
    collect_iteration1("15m")
