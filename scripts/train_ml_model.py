"""Train ML model on labeled signals."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.ml_backtest.config import DATA_DIR
from src.ml_backtest.model_trainer import train_and_evaluate


def main():
    # Load labeled signals
    signals_file = DATA_DIR / "labeled_signals.json"

    if not signals_file.exists():
        print(f"Error: {signals_file} not found")
        print("Run scripts/run_ml_pipeline.py first")
        return

    print(f"Loading signals from {signals_file}...")
    with open(signals_file, "r") as f:
        labeled_signals = json.load(f)

    print(f"Loaded {len(labeled_signals)} labeled signals")

    # Train and evaluate
    model, results = train_and_evaluate(labeled_signals)

    # Save model
    model_file = DATA_DIR / "signal_quality_model.txt"
    model.save_model(str(model_file))
    print(f"\nModel saved to {model_file}")

    # Save results
    results_file = DATA_DIR / "model_evaluation.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {results_file}")


if __name__ == "__main__":
    main()
