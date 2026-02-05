"""
Brooks Sequence Matcher - Prototype
Match live candle sequences against Brooks' multi-page teaching progressions
"""

from collections import defaultdict
from typing import Dict, List, Tuple

import psycopg2


def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="qingniao_abu",
        user="abu_user",
        password="Abu2026!Secure",
    )


def load_brooks_clusters(min_cluster_size: int = 3, max_gap: int = 2) -> List[Dict]:
    """
    Load consecutive page clusters from Brooks patterns.

    Args:
        min_cluster_size: Minimum pages to form a cluster
        max_gap: Maximum gap between pages to be consecutive

    Returns:
        List of cluster dicts with pattern_name, pages, phases
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT pv.source_page, pl.pattern_name,
               pv.pattern_features->>'primary' as pri,
               pv.pattern_features->>'secondary' as sec,
               pv.market_context->>'cycle' as cycle
        FROM pattern_vectors pv
        JOIN pattern_library pl ON pv.pattern_library_id = pl.id
        WHERE pv.source_page IS NOT NULL
        AND pl.pattern_name IS NOT NULL
        AND pl.pattern_name != ''
        ORDER BY pv.source_page
    """)

    rows = cur.fetchall()
    conn.close()

    # Group by pattern name first
    by_pattern = defaultdict(list)
    for page, name, pri, sec, cycle in rows:
        phase = f"{pri}_{sec}_{cycle}"
        by_pattern[name].append({"page": page, "phase": phase})

    # Extract consecutive clusters
    clusters = []
    for pattern_name, pages in by_pattern.items():
        pages.sort(key=lambda x: x["page"])

        current = [pages[0]]
        for i in range(1, len(pages)):
            gap = pages[i]["page"] - pages[i - 1]["page"]
            if gap <= max_gap:
                current.append(pages[i])
            else:
                if len(current) >= min_cluster_size:
                    clusters.append(
                        {
                            "pattern": pattern_name,
                            "pages": [p["page"] for p in current],
                            "phases": [p["phase"] for p in current],
                            "length": len(current),
                        }
                    )
                current = [pages[i]]

        if len(current) >= min_cluster_size:
            clusters.append(
                {
                    "pattern": pattern_name,
                    "pages": [p["page"] for p in current],
                    "phases": [p["phase"] for p in current],
                    "length": len(current),
                }
            )

    clusters.sort(key=lambda x: x["length"], reverse=True)
    return clusters


def load_brooks_sequences() -> Dict[str, List[Tuple[int, str]]]:
    """Load all Brooks pattern sequences from database."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT pv.source_page, pl.pattern_name,
               pv.pattern_features, pv.market_context
        FROM pattern_vectors pv
        JOIN pattern_library pl ON pv.pattern_library_id = pl.id
        WHERE pv.source_page IS NOT NULL
        AND pl.pattern_name IS NOT NULL
        ORDER BY pv.source_page
    """)

    sequences = defaultdict(list)
    for page, name, features, context in cur.fetchall():
        if features:
            # Use primary pattern instead of secondary
            phase = features.get("primary", "none")
            cycle = context.get("cycle", "unknown") if context else "unknown"
            sequences[name].append({"page": page, "phase": phase, "cycle": cycle})

    conn.close()
    return dict(sequences)


def extract_phase_from_candle(candle: Dict, prev_candles: List[Dict]) -> str:
    """Classify a candle into Brooks primary pattern type."""
    o, h, l, c = candle["open"], candle["high"], candle["low"], candle["close"]

    body = abs(c - o)
    is_green = c > o
    body_pct = (body / o * 100) if o > 0 else 0

    # Wick analysis
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l

    # Check recent trend (5 candles)
    if len(prev_candles) >= 5:
        recent = prev_candles[-5:]
        closes = [k["close"] for k in recent]
        trend_up = closes[-1] > closes[0] * 1.01
        trend_down = closes[-1] < closes[0] * 0.99
        # Check if in channel (higher lows for up, lower highs for down)
        lows = [k["low"] for k in recent]
        highs = [k["high"] for k in recent]
        channel_up = all(lows[i] <= lows[i + 1] for i in range(len(lows) - 1))
        channel_down = all(highs[i] >= highs[i + 1] for i in range(len(highs) - 1))
    else:
        trend_up = trend_down = channel_up = channel_down = False

    # Classify into Brooks primary patterns
    if body_pct > 2.0:
        return "breakout"
    elif body_pct < 0.2:
        return "range"
    elif (trend_down and is_green) or (trend_up and not is_green):
        if lower_wick > body * 2 or upper_wick > body * 2:
            return "reversal"
        return "reversal"
    elif channel_up or channel_down:
        return "channel"
    elif trend_up or trend_down:
        return "trend"
    else:
        return "range"


def encode_candle_sequence(klines: List[Dict], window: int = 5) -> List[str]:
    """Encode last N candles into phase sequence."""
    if len(klines) < window:
        return []

    recent = klines[-window:]
    phases = []

    for i, candle in enumerate(recent):
        prev = klines[: len(klines) - window + i]
        phase = extract_phase_from_candle(candle, prev)
        phases.append(phase)

    return phases


def match_against_clusters(
    live_phases: List[str],
    clusters: List[Dict],
    min_match_ratio: float = 0.5,
) -> List[Dict]:
    """
    Match live candle phases against consecutive Brooks clusters.

    This is the core of the hybrid approach - matching against real
    multi-page progressions where Brooks shows the same pattern evolving.

    Args:
        live_phases: List of phase strings from live candles
        clusters: Output from load_brooks_clusters()
        min_match_ratio: Minimum similarity to consider a match

    Returns:
        List of matches with pattern, similarity, position info
    """
    matches = []
    live_len = len(live_phases)

    if live_len < 3:
        return []

    for cluster in clusters:
        cluster_phases = cluster["phases"]
        cluster_len = cluster["length"]

        # Try matching live sequence at different positions in cluster
        best_match = None

        # Slide live window through cluster
        for start in range(max(1, cluster_len - live_len + 1)):
            end = min(start + live_len, cluster_len)
            window_size = end - start

            if window_size < 3:
                continue

            cluster_window = cluster_phases[start:end]
            live_window = live_phases[:window_size]

            # Count matching phases
            match_count = sum(
                1
                for a, b in zip(live_window, cluster_window)
                if a == b or _phases_similar(a, b)
            )
            similarity = match_count / window_size

            if similarity >= min_match_ratio:
                # Calculate position in the story
                position_in_story = start + window_size
                remaining = cluster_len - position_in_story

                if best_match is None or similarity > best_match["similarity"]:
                    best_match = {
                        "pattern": cluster["pattern"],
                        "similarity": similarity,
                        "cluster_pages": cluster["pages"],
                        "matched_window": window_size,
                        "position": position_in_story,
                        "total_pages": cluster_len,
                        "remaining_pages": remaining,
                        "next_phases": cluster_phases[
                            position_in_story : position_in_story + 3
                        ],
                        "progress_pct": position_in_story / cluster_len * 100,
                    }

        if best_match:
            matches.append(best_match)

    # Sort by similarity, then by cluster length (prefer longer stories)
    matches.sort(key=lambda x: (x["similarity"], x["total_pages"]), reverse=True)
    return matches[:10]


def _phases_similar(a: str, b: str) -> bool:
    """Check if two phase strings are similar (fuzzy match)."""
    if a == b:
        return True

    # Extract primary component from combined phases
    a_primary = a.split("_")[0] if "_" in a else a
    b_primary = b.split("_")[0] if "_" in b else b

    if a_primary == b_primary:
        return True

    # Handle None values in phase components
    if "None" in a or "None" in b:
        a_parts = [p for p in a.split("_") if p != "None"]
        b_parts = [p for p in b.split("_") if p != "None"]
        return len(set(a_parts) & set(b_parts)) > 0

    return False


def predict_next_phase(
    live_phases: List[str],
    clusters: List[Dict],
    min_match_ratio: float = 0.5,
) -> Dict:
    """
    Predict what comes next based on cluster matches.

    Returns prediction with confidence based on:
    - How many clusters agree on the next phase
    - Quality of the matches (similarity scores)
    - Position in the pattern story
    """
    matches = match_against_clusters(live_phases, clusters, min_match_ratio)

    if not matches:
        return {"prediction": None, "confidence": 0, "reason": "No matches found"}

    # Collect next phases from all matches
    next_phase_votes = {}
    total_weight = 0

    for m in matches:
        if m["next_phases"]:
            next_phase = m["next_phases"][0]  # Immediate next
            weight = m["similarity"] * (1 + m["total_pages"] / 20)  # Weight by quality

            if next_phase not in next_phase_votes:
                next_phase_votes[next_phase] = {"weight": 0, "patterns": []}
            next_phase_votes[next_phase]["weight"] += weight
            next_phase_votes[next_phase]["patterns"].append(m["pattern"])
            total_weight += weight

    if not next_phase_votes:
        return {
            "prediction": None,
            "confidence": 0,
            "reason": "All matches at end of story",
        }

    # Find consensus
    best_phase = max(
        next_phase_votes.keys(), key=lambda x: next_phase_votes[x]["weight"]
    )
    confidence = (
        next_phase_votes[best_phase]["weight"] / total_weight if total_weight > 0 else 0
    )

    return {
        "prediction": best_phase,
        "confidence": confidence,
        "supporting_patterns": next_phase_votes[best_phase]["patterns"],
        "all_votes": {k: v["weight"] for k, v in next_phase_votes.items()},
    }


def match_sequence(
    live_phases: List[str],
    brooks_sequences: Dict,
    min_window: int = 5,
    max_window: int = 50,
) -> List[Dict]:
    """
    Find Brooks patterns that match the live phase sequence.
    Uses sliding window to find best match at any position.
    """
    matches = []

    for pattern_name, pages in brooks_sequences.items():
        brooks_phases = [p["phase"] for p in pages]

        if len(brooks_phases) < min_window:
            continue

        best_match = None

        # Try different window sizes
        for window in range(min_window, min(max_window, len(live_phases)) + 1):
            if window > len(live_phases):
                break

            live_window = live_phases[-window:]

            # Slide through Brooks sequence
            for start_pos in range(len(brooks_phases) - window + 1):
                brooks_window = brooks_phases[start_pos : start_pos + window]

                match_count = sum(
                    1 for a, b in zip(live_window, brooks_window) if a == b
                )
                similarity = match_count / window

                if similarity >= 0.6:
                    if best_match is None or similarity > best_match["similarity"]:
                        best_match = {
                            "pattern": pattern_name,
                            "similarity": similarity,
                            "window": window,
                            "position": start_pos,
                            "total": len(brooks_phases),
                            "progress": f"{start_pos + window}/{len(brooks_phases)}",
                        }

        if best_match:
            matches.append(best_match)

    matches.sort(key=lambda x: (x["similarity"], x["window"]), reverse=True)
    return matches[:10]


if __name__ == "__main__":
    # Test the hybrid approach
    print("=" * 60)
    print("HYBRID APPROACH: Cluster-based Sequence Matching")
    print("=" * 60)

    # 1. Load consecutive clusters
    print("\n1. Loading consecutive Brooks clusters...")
    clusters = load_brooks_clusters(min_cluster_size=3, max_gap=2)
    print(f"   Found {len(clusters)} clusters")

    # Show top clusters
    print("\n   Top 5 longest clusters:")
    for c in clusters[:5]:
        print(
            f"     {c['length']:2d} pages: {c['pattern']} (pages {c['pages'][0]}-{c['pages'][-1]})"
        )

    # 2. Simulate live candle phases
    test_phases = [
        "breakout_None_None",
        "trend_None_None",
        "channel_None_None",
        "range_None_None",
        "reversal_None_None",
    ]
    print(f"\n2. Test live phases: {len(test_phases)} candles")
    for i, p in enumerate(test_phases):
        print(f"     [{i + 1}] {p}")

    # 3. Match against clusters
    print("\n3. Matching against clusters...")
    matches = match_against_clusters(test_phases, clusters, min_match_ratio=0.4)

    if matches:
        print(f"\n   Found {len(matches)} matches:")
        for m in matches[:5]:
            print(f"\n   {m['pattern']}")
            print(f"     Similarity: {m['similarity']:.0%}")
            print(f"     Position: page {m['position']} of {m['total_pages']}")
            print(f"     Progress: {m['progress_pct']:.0f}%")
            if m["next_phases"]:
                print(f"     Next phases: {m['next_phases']}")
    else:
        print("   No matches found with current threshold")

    # 4. Also test single-page matching
    print("\n" + "=" * 60)
    print("SINGLE-PAGE MATCHING (for validation)")
    print("=" * 60)
    sequences = load_brooks_sequences()
    print(f"\nLoaded {len(sequences)} pattern types")

    simple_phases = ["trend", "trend", "range", "reversal", "breakout"]
    print(f"Test phases: {simple_phases}")

    single_matches = match_sequence(simple_phases, sequences)
    print(f"\nTop single-page matches:")
    for m in single_matches[:3]:
        print(f"  {m['pattern']}: {m['similarity']:.0%} (window={m['window']})")

    # 5. Test prediction
    print("\n" + "=" * 60)
    print("PREDICTION TEST")
    print("=" * 60)
    prediction = predict_next_phase(test_phases, clusters, min_match_ratio=0.4)
    print(f"\nPredicted next phase: {prediction.get('prediction')}")
    print(f"Confidence: {prediction.get('confidence', 0):.0%}")
    if prediction.get("supporting_patterns"):
        print(f"Supporting patterns: {prediction['supporting_patterns'][:3]}")

    # 6. Test with real candle data
    print("\n" + "=" * 60)
    print("REAL CANDLE DATA TEST")
    print("=" * 60)
    try:
        from src.abu.market_cache import MarketDataCache

        cache = MarketDataCache()
        klines, stats = cache.get_klines("BTC", "4h", 20)

        if klines:
            print(f"\nFetched {len(klines)} BTC 4h candles")

            # Encode real candles into phases
            real_phases = encode_candle_sequence(klines, window=len(klines))
            print(f"Encoded phases: {real_phases[-5:]}")

            # Match against clusters
            real_matches = match_against_clusters(
                real_phases, clusters, min_match_ratio=0.3
            )
            if real_matches:
                print(f"\nReal data matches:")
                for m in real_matches[:3]:
                    print(f"  {m['pattern']}: {m['similarity']:.0%}")
                    print(f"    Position: {m['position']}/{m['total_pages']}")

            # Predict next
            real_pred = predict_next_phase(real_phases, clusters, min_match_ratio=0.3)
            print(f"\nPrediction for BTC: {real_pred.get('prediction')}")
            print(f"Confidence: {real_pred.get('confidence', 0):.0%}")
        else:
            print("No klines fetched")
    except Exception as e:
        print(f"Real data test skipped: {e}")
