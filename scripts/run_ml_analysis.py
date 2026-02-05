"""Run ML analysis on backtest results."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json

from src.ml_backtest.analyzer import analyze_results, print_analysis


def main():
    # Load the labeled signals from full pipeline
    results_file = "data/ml_backtest/labeled_signals.json"

    if not os.path.exists(results_file):
        print(f"Results file not found: {results_file}")
        print("Run run_ml_pipeline.py first to generate results.")
        return

    with open(results_file, "r") as f:
        labeled_signals = json.load(f)

    if not labeled_signals:
        print("No labeled signals found in results.")
        return

    print(f"Loaded {len(labeled_signals)} labeled signals")

    # Run analysis
    results = analyze_results(labeled_signals, {})

    # Print results
    print_analysis(results)

    # Save analysis
    analysis_file = "data/ml_backtest/analysis_results.json"

    # Convert defaultdicts to regular dicts for JSON
    save_results = {
        "total_signals": results["total_signals"],
        "by_outcome": dict(results["by_outcome"]),
        "by_pattern": {k: dict(v) for k, v in results["by_pattern"].items()},
        "by_direction": {k: dict(v) for k, v in results["by_direction"].items()},
        "stop_stats": results.get("stop_stats", {}),
        "issues_found": results["issues_found"],
        "recommendations": results["recommendations"],
    }

    with open(analysis_file, "w") as f:
        json.dump(save_results, f, indent=2)

    print(f"\nAnalysis saved to {analysis_file}")


if __name__ == "__main__":
    main()
