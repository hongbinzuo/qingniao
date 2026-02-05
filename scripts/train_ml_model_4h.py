"""Train ML model on 4h labeled signals."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.ml_backtest.config import DATA_DIR
from src.ml_backtest.model_trainer import train_and_evaluate


def main():
    # Load 4h labeled signals
    signals_file = DATA_DIR / "labeled_signals_4h.json"

    if not signals_file.exists():
        print(f"Error: {signals_file} not found")
        print(
            "Run scripts/generate_1h_4h_signals.py and scripts/label_1h_4h_outcomes.py first"
        )
        return

    print(f"Loading 4h signals from {signals_file}...")
    with open(signals_file, "r") as f:
        labeled_signals = json.load(f)

    print(f"Loaded {len(labeled_signals)} labeled 4h signals")

    # Count outcomes
    outcomes = {}
    for sig in labeled_signals:
        outcome = sig.get("outcome", "UNKNOWN")
        outcomes[outcome] = outcomes.get(outcome, 0) + 1

    print("\nOutcome distribution:")
    for outcome, count in sorted(outcomes.items()):
        pct = count / len(labeled_signals) * 100
        print(f"  {outcome}: {count} ({pct:.1f}%)")

    # Train and evaluate with 4h timeframe
    print("\n" + "=" * 60)
    print("TRAINING ML MODEL ON 4H SIGNALS")
    print("=" * 60)
    model, results = train_and_evaluate(labeled_signals, timeframe="4h")

    # Save model
    model_file = DATA_DIR / "signal_quality_model_4h.txt"
    model.save_model(str(model_file))
    print(f"\nModel saved to {model_file}")

    # Save results
    results_file = DATA_DIR / "model_evaluation_4h.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {results_file}")


if __name__ == "__main__":
    main()
