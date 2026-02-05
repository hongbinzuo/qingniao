# Vector Search Integration Plan

## Current Status
✅ **Phase 1 Complete**: Vector infrastructure ready
- 938 Brooks patterns solidified with outcome labels
- Unified 32-dim vectorizer implemented
- Annoy index built and tested

🔄 **Phase 2 Next**: Integrate into pa_scan_15m_top10.py

---

## Integration Architecture

```
Live K-line Data
      ↓
Extract Features (trend, EMA, patterns)
      ↓
UnifiedVectorizer.vectorize_live_kline()
      ↓
32-dim Query Vector
      ↓
Annoy Index Search (top-K neighbors)
      ↓
Retrieve Brooks Patterns + Outcomes
      ↓
Aggregate: avg(win_prob), avg(RR), consensus_direction
      ↓
Generate Signal with Confidence Score
```

---

## Implementation Steps

### Step 1: Create Vector Search Module
**File**: `src/abu/vector_pattern_matcher.py`

**Class**: `VectorPatternMatcher`
- Load Annoy index at init
- Load ID mapping
- Method: `find_similar_patterns(query_vec, k=10)`
- Method: `aggregate_outcomes(matches)`

### Step 2: Modify pa_scan_15m_top10.py
**Changes needed**:
1. Import VectorPatternMatcher and UnifiedVectorizer
2. Initialize at startup (load index once)
3. In candidate processing:
   - Extract features from K-line
   - Vectorize features
   - Query similar patterns
   - Add vector_score to candidate
4. Use vector outcomes for signal generation

### Step 3: A/B Testing
- Run both categorical and vector matching
- Compare results side-by-side
- Log performance metrics

---

## Code Snippets

### VectorPatternMatcher (skeleton)
```python
class VectorPatternMatcher:
    def __init__(self, index_path, id_map_path, db_manager):
        self.index = AnnoyIndex(32, 'angular')
        self.index.load(index_path)
        self.id_map = json.load(open(id_map_path))
        self.db = db_manager
    
    def find_similar(self, query_vec, k=10):
        # Query Annoy index
        indices, distances = self.index.get_nns_by_vector(
            query_vec, k, include_distances=True
        )
        
        # Retrieve pattern metadata from DB
        pattern_ids = [self.id_map[str(i)] for i in indices]
        patterns = self.db.get_patterns_by_ids(pattern_ids)
        
        return patterns, distances
    
    def aggregate_outcomes(self, patterns, distances):
        # Weight by similarity (1 - distance)
        weights = [1 - d for d in distances]
        
        # Aggregate win_prob, RR, direction
        avg_win_prob = weighted_avg([p.win_probability for p in patterns], weights)
        avg_rr = weighted_avg([p.typical_rr for p in patterns], weights)
        
        return {
            'win_probability': avg_win_prob,
            'typical_rr': avg_rr,
            'confidence': min(weights),  # similarity of closest match
            'num_matches': len(patterns)
        }
```

### Integration into pa_scan_15m_top10.py
```python
# At startup
vector_matcher = VectorPatternMatcher(
    index_path='data/vectors/brooks_patterns_32d.ann',
    id_map_path='data/vectors/brooks_patterns_id_map.json',
    db_manager=db
)
vectorizer = UnifiedVectorizer()

# In candidate processing
def process_candidate(candidate, klines):
    # Extract features
    trend = extract_trend_features(klines)
    ema = extract_ema_features(klines)
    patterns = detect_kline_patterns(klines)
    
    # Vectorize
    query_vec = vectorizer.vectorize_live_kline(
        trend_features=trend,
        ema_features=ema,
        pattern_features=patterns
    )
    
    # Find similar patterns
    matches, distances = vector_matcher.find_similar(query_vec, k=10)
    outcomes = vector_matcher.aggregate_outcomes(matches, distances)
    
    # Add to candidate
    candidate['vector_outcomes'] = outcomes
    candidate['vector_confidence'] = outcomes['confidence']
    
    return candidate
```

---

## Testing Strategy

### Unit Tests
- Test vectorizer with known inputs
- Test Annoy index queries
- Test outcome aggregation

### Integration Tests
- Run scanner with vector matching enabled
- Compare signals with/without vector matching
- Verify performance (latency, memory)

### A/B Test Metrics
- Signal count (vector vs categorical)
- Win rate comparison
- Average RR comparison
- Latency impact

---

## Rollout Plan

1. **Development**: Implement VectorPatternMatcher
2. **Testing**: Unit tests + integration tests
3. **Staging**: Run in parallel with current system
4. **Analysis**: Compare results over 1 week
5. **Decision**: Keep, tune, or rollback

---

## Risk Mitigation

**Risk**: Vector matching produces worse signals
- **Mitigation**: A/B test, keep categorical as fallback

**Risk**: Performance degradation
- **Mitigation**: Load index once at startup, cache queries

**Risk**: Index becomes stale
- **Mitigation**: Rebuild index weekly, version control

---

## Success Criteria

✅ Vector matching integrated without breaking existing system
✅ Latency increase <50ms per candidate
✅ Win rate improvement >5% OR RR improvement >10%
✅ System stable over 1 week of live trading

---

## Next Actions

1. Create `src/abu/vector_pattern_matcher.py`
2. Add unit tests
3. Integrate into pa_scan_15m_top10.py
4. Run A/B test
5. Analyze results and iterate
