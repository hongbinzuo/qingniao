# ABU System Vector Matching Enhancement Design

## Document Info
- Version: 1.0
- Date: 2026-01-29
- Author: Claude Agent

---

## 1. Executive Summary

### Current State
The ABU system uses **categorical pattern matching** - detecting patterns by name (InsideBar, Engulfing, etc.) and matching against the 1000 Brooks patterns library.

### Proposed Enhancement
Migrate to **vector-based similarity matching** - converting live K-line features into vectors and finding the most similar historical patterns using approximate nearest neighbor (ANN) search.

### Key Benefits
| Aspect | Current (Categorical) | Enhanced (Vector) |
|--------|----------------------|-------------------|
| Matching | Exact name match | Continuous similarity 0.0-1.0 |
| Discovery | Limited to known patterns | Cross-pattern discovery |
| Speed | O(n) linear search | O(log n) ANN search |
| Nuance | Binary match/no-match | Partial similarity capture |

---

## 2. Current 1000 Brooks Vectors Analysis

### 2.1 Data Quality Assessment

**Strengths:**
- Rich structured features (market_cycle, trend_maturity, direction_bias)
- EMA-20 relationship captured (above/below/crossing, slope)
- Pattern hierarchy (family → type → name)
- Confidence scores included
- Text logic (bull_logic, bear_logic) preserved

**Weaknesses:**
- Vectors are **isolated** - no cross-references between related patterns
- No **outcome data** - missing historical win/loss rates
- No **sequence context** - patterns don't know what comes before/after
- **Sparse embedding** - current vectors don't fully utilize the 768-dim space

### 2.2 Recommendation: Solidify First, Then Cross-Relate

| Phase | Priority | Description |
|-------|----------|-------------|
| Phase 1: Solidify | HIGH | Make each vector complete and consistent |
| Phase 2: Cross-Relate | MEDIUM | Build relationships between patterns |

---

## 3. Vector Matching Architecture

### 3.1 High-Level Flow

```
Live K-line Data
      │
      ▼
┌─────────────────┐
│ Feature Extract │  extract_basic_kline_features()
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Vectorization  │  FeatureVectorizer.vectorize()
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────────┐
│  Vector Search  │────▶│  Annoy/FAISS Index   │
└────────┬────────┘     │  (1000 Brooks vecs)  │
         │              └──────────────────────┘
         ▼
┌─────────────────┐
│  Top-K Similar  │  Returns: [(pattern_id, similarity), ...]
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Aggregate Stats │  Win rate, RR, direction from matches
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Generate Signal │  Entry, SL, TP with confidence
└─────────────────┘
```

### 3.2 Component Responsibilities

| Component | File | Responsibility |
|-----------|------|----------------|
| Feature Extractor | `kline_feature_extractor.py` | Extract numeric features from OHLCV |
| Feature Vectorizer | `feature_vectorizer.py` | Convert features to fixed-dim vector |
| Vector Index | `vector_index_manager.py` | Build/search Annoy index |
| Pattern Library | `unified_pattern_library.py` | Load patterns, manage metadata |
| Signal Generator | `pa_scan_15m_top10.py` | Orchestrate the flow |

---

## 4. Feature Vector Schema

### 4.1 Live K-line Feature Vector (Input)

Extracted from real-time OHLCV data:

| Category | Fields | Dimensions |
|----------|--------|------------|
| Trend | direction, strength, delta | 5 |
| Volatility | volatility, range_pct, range_mode | 3 |
| EMA | relation, slope, distance | 4 |
| Breakout | up, down | 2 |
| Structure | pullback, swings, double patterns | 4 |
| K-line Patterns | engulfing, inside_bar, etc. | 7 |
| **Total** | | **~25-30** |

### 4.2 Brooks Pattern Vector (Stored in DB)

| Category | Fields | Dimensions |
|----------|--------|------------|
| Market Context | cycle, maturity, bias | 4 |
| EMA-20 | relation, slope, confidence | 3 |
| Pattern Identity | family, type, name | variable |
| Bar-by-Bar | overlap, follow_through, gap | 4 |
| K-line Features | multi-hot encoding | 7 |

### 4.3 Vector Alignment Solution

Create a **unified 32-dim vector** that maps both sources:

| Dims | Description | Live Source | Brooks Source |
|------|-------------|-------------|---------------|
| 0-2 | Direction | trend_direction | direction_bias |
| 3 | Strength | trend_strength | derived from maturity |
| 4-6 | EMA relation | price vs ema | ema_20.relation |
| 7 | EMA slope | derived | ema_20.slope |
| 8-12 | Market cycle | derived from features | market_cycle |
| 13-19 | K-line patterns | kline_features | kline_features |
| 20-31 | Pattern type | detected pattern | pattern_family |

---

## 5. Solidify vs Cross-Relate Analysis

### 5.1 What "Solidify" Means

**Goal:** Make each of the 1000 vectors self-contained and complete.

**Actions:**
1. Fill missing fields with proper defaults
2. Add outcome labels (expected_outcome, win_probability)
3. Normalize confidence scores to 0.0-1.0
4. Validate vector dimension consistency

**Example - Before vs After:**

```
BEFORE:
{
  "pattern_name": "Tight Bear Channel",
  "direction_bias": "short"
}

AFTER:
{
  "pattern_name": "Tight Bear Channel",
  "direction_bias": "short",
  "expected_outcome": "bearish_continuation",
  "win_probability": 0.65,
  "typical_rr": 2.0,
  "invalidation_condition": "break_above_channel"
}
```

### 5.2 What "Cross-Relate" Means

**Goal:** Build relationships between patterns.

**Relationship Types:**

| Type | Example | Use Case |
|------|---------|----------|
| is_variant_of | Truncated Wedge → Wedge | Pattern family grouping |
| often_follows | Breakout → Pullback | Sequence prediction |
| often_precedes | Tight Channel → Breakout | Setup detection |
| same_family | Double Top ↔ Double Bottom | Mirror patterns |
| opposite_of | Bull Flag ↔ Bear Flag | Direction flip |

### 5.3 Recommendation: Solidify First

**Why Solidify First:**
1. Cross-relating requires consistent base data
2. Outcome labels enable win rate calculation
3. Normalized vectors enable accurate similarity
4. Easier to validate and debug

**Solidification Checklist:**
- [ ] All 1000 patterns have direction_bias
- [ ] All patterns have expected_outcome label
- [ ] All patterns have win_probability estimate
- [ ] All patterns have typical_rr (risk/reward)
- [ ] Vector dimensions are consistent (32-dim)
- [ ] Confidence scores normalized to 0.0-1.0

---

## 6. Implementation Plan

### 6.1 Phase 1: Solidify Vectors (Week 1-2)

**Task 1.1: Audit Current Vectors**
- Count patterns with missing fields
- Identify inconsistent encodings
- List patterns without outcome labels

**Task 1.2: Add Outcome Labels**
- Map pattern_name → expected_outcome
- Estimate win_probability from Brooks theory
- Add typical_rr based on pattern type

**Task 1.3: Normalize Vectors**
- Standardize all vectors to 32 dimensions
- Apply L2 normalization
- Rebuild Annoy index

### 6.2 Phase 2: Integrate Vector Search (Week 2-3)

**Task 2.1: Modify pa_scan_15m_top10.py**
- Add vector search alongside pattern matching
- Weight results by similarity score
- Aggregate outcomes from top-K matches

**Task 2.2: Build Unified Vectorizer**
- Create live_to_unified_vector() function
- Create brooks_to_unified_vector() function
- Ensure both produce same 32-dim output

**Task 2.3: Performance Testing**
- Benchmark search speed
- Validate similarity accuracy
- Compare signal quality vs current system

### 6.3 Phase 3: Cross-Relate (Week 3-4)

**Task 3.1: Build Relationship Graph**
- Create pattern_relationships table
- Populate is_variant_of links
- Populate often_follows links

**Task 3.2: Enhance Signal Generation**
- Use relationships for sequence prediction
- Boost confidence when related patterns align
- Warn when conflicting patterns detected

---

## 7. Database Schema Changes

### 7.1 pattern_library Table Updates

```sql
ALTER TABLE pattern_library ADD COLUMN IF NOT EXISTS
  expected_outcome VARCHAR(50),
  win_probability FLOAT,
  typical_rr FLOAT,
  invalidation_condition TEXT;
```

### 7.2 New pattern_relationships Table

```sql
CREATE TABLE IF NOT EXISTS pattern_relationships (
  id SERIAL PRIMARY KEY,
  pattern_id_from VARCHAR(100) NOT NULL,
  pattern_id_to VARCHAR(100) NOT NULL,
  relationship_type VARCHAR(50) NOT NULL,
  confidence FLOAT DEFAULT 0.5,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(pattern_id_from, pattern_id_to, relationship_type)
);
```

---

## 8. Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Search Speed | ~50ms | <10ms |
| Pattern Coverage | Name-based only | Similarity-based |
| Win Rate Accuracy | Unknown | Track actual vs predicted |
| Signal Confidence | Heuristic | Data-driven |

---

## 9. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Vector dimension mismatch | Search fails | Strict schema validation |
| Poor similarity quality | Bad signals | A/B test vs current system |
| Performance regression | Slow scans | Benchmark before deploy |
| Data loss during migration | Lost patterns | Backup before changes |

---

## 10. Next Steps

1. **Immediate:** Run audit script to assess current vector quality
2. **This Week:** Add outcome labels to top 100 most common patterns
3. **Next Week:** Build unified vectorizer and test on sample data
4. **Week 3:** Integrate into pa_scan_15m_top10.py with feature flag
5. **Week 4:** A/B test and measure signal quality improvement

---

*Document End*
