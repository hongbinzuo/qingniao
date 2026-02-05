"""Analyze backtest results to find ABU system issues."""

import json
from collections import defaultdict
from typing import Dict, List, Tuple

from .feature_engineer import calc_atr, extract_features


def analyze_results(labeled_signals: List[Dict], klines_cache: Dict) -> Dict:
    """Analyze labeled signals to find patterns and issues."""
    results = {
        "total_signals": len(labeled_signals),
        "by_outcome": defaultdict(int),
        "by_pattern": defaultdict(lambda: defaultdict(int)),
        "by_direction": defaultdict(lambda: defaultdict(int)),
        "stop_analysis": [],
        "issues_found": [],
        "recommendations": [],
    }

    for sig in labeled_signals:
        outcome = sig.get("outcome", "UNKNOWN")
        pattern = sig.get("pattern", "unknown")
        direction = sig.get("direction", "unknown")

        results["by_outcome"][outcome] += 1
        results["by_pattern"][pattern][outcome] += 1
        results["by_direction"][direction][outcome] += 1

        # Analyze stop loss distance
        entry = sig.get("entry", 0)
        sl = sig.get("stop_loss", 0)
        if entry > 0 and sl > 0:
            sl_pct = abs(entry - sl) / entry * 100
            results["stop_analysis"].append(
                {
                    "pattern": pattern,
                    "direction": direction,
                    "sl_pct": sl_pct,
                    "outcome": outcome,
                }
            )

    # Calculate statistics
    _analyze_stop_losses(results)
    _analyze_patterns(results)
    _analyze_directions(results)
    _generate_recommendations(results)

    return results


def _analyze_stop_losses(results: Dict) -> None:
    """Analyze stop loss effectiveness."""
    stops = results["stop_analysis"]
    if not stops:
        return

    sl_pcts = [s["sl_pct"] for s in stops]
    avg_sl = sum(sl_pcts) / len(sl_pcts)

    # SL hit rate by stop distance
    tight_stops = [s for s in stops if s["sl_pct"] < 0.3]
    medium_stops = [s for s in stops if 0.3 <= s["sl_pct"] < 1.0]
    wide_stops = [s for s in stops if s["sl_pct"] >= 1.0]

    def sl_hit_rate(group):
        if not group:
            return 0
        return sum(1 for s in group if s["outcome"] == "SL_HIT") / len(group) * 100

    results["stop_stats"] = {
        "avg_sl_pct": avg_sl,
        "tight_sl_hit_rate": sl_hit_rate(tight_stops),
        "medium_sl_hit_rate": sl_hit_rate(medium_stops),
        "wide_sl_hit_rate": sl_hit_rate(wide_stops),
        "tight_count": len(tight_stops),
        "medium_count": len(medium_stops),
        "wide_count": len(wide_stops),
    }

    if avg_sl < 0.5 and sl_hit_rate(tight_stops) > 60:
        results["issues_found"].append(
            {
                "type": "STOP_TOO_TIGHT",
                "severity": "HIGH",
                "detail": f"Avg SL is {avg_sl:.2f}%, tight stops have {sl_hit_rate(tight_stops):.0f}% hit rate",
            }
        )


def _analyze_patterns(results: Dict) -> None:
    """Analyze pattern performance."""
    for pattern, outcomes in results["by_pattern"].items():
        total = sum(outcomes.values())
        if total < 5:
            continue
        sl_rate = outcomes.get("SL_HIT", 0) / total * 100
        tp2_rate = outcomes.get("TP2_HIT", 0) / total * 100

        if sl_rate > 70:
            results["issues_found"].append(
                {
                    "type": "PATTERN_POOR_PERFORMANCE",
                    "severity": "HIGH",
                    "pattern": pattern,
                    "detail": f"{pattern} has {sl_rate:.0f}% SL rate ({total} signals)",
                }
            )
        elif sl_rate > 60:
            results["issues_found"].append(
                {
                    "type": "PATTERN_WEAK_PERFORMANCE",
                    "severity": "MEDIUM",
                    "pattern": pattern,
                    "detail": f"{pattern} has {sl_rate:.0f}% SL rate ({total} signals)",
                }
            )


def _analyze_directions(results: Dict) -> None:
    """Analyze long vs short performance."""
    for direction, outcomes in results["by_direction"].items():
        total = sum(outcomes.values())
        if total < 5:
            continue
        sl_rate = outcomes.get("SL_HIT", 0) / total * 100

        if sl_rate > 70:
            results["issues_found"].append(
                {
                    "type": "DIRECTION_BIAS",
                    "severity": "MEDIUM",
                    "direction": direction,
                    "detail": f"{direction} signals have {sl_rate:.0f}% SL rate",
                }
            )


def _generate_recommendations(results: Dict) -> None:
    """Generate recommendations based on issues found."""
    for issue in results["issues_found"]:
        if issue["type"] == "STOP_TOO_TIGHT":
            results["recommendations"].append(
                {
                    "action": "WIDEN_STOP_LOSS",
                    "detail": "Use ATR-based stops (1.5-2x ATR) instead of pattern-based stops",
                    "priority": "HIGH",
                }
            )
        elif issue["type"] == "PATTERN_POOR_PERFORMANCE":
            results["recommendations"].append(
                {
                    "action": "DISABLE_OR_FIX_PATTERN",
                    "pattern": issue.get("pattern"),
                    "detail": f"Consider disabling {issue.get('pattern')} or adding filters",
                    "priority": "HIGH",
                }
            )
        elif issue["type"] == "DIRECTION_BIAS":
            results["recommendations"].append(
                {
                    "action": "ADD_TREND_FILTER",
                    "direction": issue.get("direction"),
                    "detail": f"Add trend confirmation for {issue.get('direction')} signals",
                    "priority": "MEDIUM",
                }
            )


def print_analysis(results: Dict) -> None:
    """Print analysis results."""
    print("\n" + "=" * 60)
    print("ML BACKTEST ANALYSIS RESULTS")
    print("=" * 60)

    print(f"\nTotal signals: {results['total_signals']}")
    print("\nOutcome distribution:")
    for outcome, count in sorted(results["by_outcome"].items()):
        pct = count / results["total_signals"] * 100
        print(f"  {outcome}: {count} ({pct:.1f}%)")

    print("\nBy pattern:")
    for pattern, outcomes in sorted(results["by_pattern"].items()):
        total = sum(outcomes.values())
        sl_rate = outcomes.get("SL_HIT", 0) / total * 100 if total > 0 else 0
        print(f"  {pattern}: {total} signals, {sl_rate:.0f}% SL rate")

    if "stop_stats" in results:
        stats = results["stop_stats"]
        print(f"\nStop loss analysis:")
        print(f"  Avg SL distance: {stats['avg_sl_pct']:.2f}%")
        print(
            f"  Tight (<0.3%): {stats['tight_count']} signals, {stats['tight_sl_hit_rate']:.0f}% SL rate"
        )
        print(
            f"  Medium (0.3-1%): {stats['medium_count']} signals, {stats['medium_sl_hit_rate']:.0f}% SL rate"
        )
        print(
            f"  Wide (>1%): {stats['wide_count']} signals, {stats['wide_sl_hit_rate']:.0f}% SL rate"
        )

    if results["issues_found"]:
        print("\n" + "-" * 40)
        print("ISSUES FOUND:")
        for i, issue in enumerate(results["issues_found"], 1):
            print(f"\n{i}. [{issue['severity']}] {issue['type']}")
            print(f"   {issue['detail']}")

    if results["recommendations"]:
        print("\n" + "-" * 40)
        print("RECOMMENDATIONS:")
        for i, rec in enumerate(results["recommendations"], 1):
            print(f"\n{i}. [{rec['priority']}] {rec['action']}")
            print(f"   {rec['detail']}")

    print("\n" + "=" * 60)
