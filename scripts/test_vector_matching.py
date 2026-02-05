#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Vector Matching System
Quick validation of vectorizer and pattern matcher
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from abu.unified_vectorizer import UnifiedVectorizer
from abu.vector_pattern_matcher import VectorPatternMatcher
from db_manager_trader import TraderDBManager


def test_vectorizer():
    """Test unified vectorizer"""
    print("\n" + "=" * 60)
    print("TEST 1: Unified Vectorizer")
    print("=" * 60)

    vectorizer = UnifiedVectorizer()
    vec1 = vectorizer.vectorize_brooks_pattern(
        pattern_features={"primary": "wedge", "direction": "long"},
        market_context={"cycle": "markup", "maturity": "mature"},
    )
    print(f"✓ Brooks pattern → 32-dim vector: shape={vec1.shape}")

    vec2 = vectorizer.vectorize_live_kline(
        trend_features={"direction": "bullish", "strength": 0.8},
        ema_features={"relation": "above", "slope": 0.5},
        pattern_features={"hammer": True, "engulfing": False},
    )
    print(f"✓ Live K-line → 32-dim vector: shape={vec2.shape}")
    return True


def test_end_to_end():
    """Test complete workflow"""
    print("\n" + "=" * 60)
    print("TEST 3: End-to-End Workflow")
    print("=" * 60)
    vectorizer = UnifiedVectorizer()
    db = TraderDBManager("abu")
    index_path = ROOT / "data" / "vectors" / "brooks_patterns_32d.ann"
    id_map_path = ROOT / "data" / "vectors" / "brooks_patterns_id_map.json"
    if not index_path.exists():
        print(f"✗ Index not found")
        return False
    matcher = VectorPatternMatcher(str(index_path), str(id_map_path), db)
    query_vec = vectorizer.vectorize_live_kline(
        trend_features={"direction": "bullish", "strength": 0.7},
        ema_features={"relation": "above", "slope": 0.3},
        pattern_features={"engulfing": True},
    )
    print(f"✓ Created query vector")
    patterns, distances = matcher.find_similar_patterns(query_vec, k=5)
    print(f"✓ Found {len(patterns)} similar patterns")
    outcomes = matcher.aggregate_outcomes(patterns, distances)
    print(
        f"✓ Win prob: {outcomes['win_probability']:.2f}, RR: {outcomes['typical_rr']:.2f}"
    )
    return True


def test_pattern_matcher():
    """Test vector pattern matcher"""
    print("\n" + "=" * 60)
    print("TEST 2: Vector Pattern Matcher")
    print("=" * 60)
    db = TraderDBManager("abu")
    index_path = ROOT / "data" / "vectors" / "brooks_patterns_32d.ann"
    id_map_path = ROOT / "data" / "vectors" / "brooks_patterns_id_map.json"
    if not index_path.exists():
        print(f"✗ Index not found")
        return False
    matcher = VectorPatternMatcher(str(index_path), str(id_map_path), db)
    print(f"✓ Loaded pattern matcher")
    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("VECTOR MATCHING SYSTEM TEST")
    print("=" * 60)
    tests = [
        ("Vectorizer", test_vectorizer),
        ("Pattern Matcher", test_pattern_matcher),
        ("End-to-End", test_end_to_end),
    ]
    passed = 0
    failed = 0
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ {name} failed: {e}")
            failed += 1
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
