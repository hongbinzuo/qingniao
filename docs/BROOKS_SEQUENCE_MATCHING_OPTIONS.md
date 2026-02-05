# Brooks Sequence Matching: Three Options for Improvement

## Current Status

We built a hybrid sequence matcher (`src/abu/brooks_sequence_matcher.py`) that:
- Extracts 62 consecutive page clusters from Brooks' 1000 teaching images
- Matches live candle phases against these clusters
- Predicts next phase based on cluster consensus

### The Gap We Discovered

Brooks' clusters use rich, multi-dimensional phases:
- `wedge_double_top_bottom_trading_range`
- `channel_triangle_broad_channel`
- `trend_gap_tight_channel`

Our live candle encoder produces simple phases:
- `trend`, `reversal`, `range`, `breakout`, `channel`

This means matching only works on the primary component, losing pattern specificity.

---

## Option 1: Use Vector Embeddings for Similarity Matching

### What We Have

When Brooks' 1000 teaching images were processed with Gemini, it created vector embeddings stored in `pattern_vectors.trend_vector` in PostgreSQL. Each vector is a long list of numbers (768 or 1024 numbers) representing the "essence" of what Gemini saw.

### How It Would Work

1. Take live candle data (last 20 candles)
2. Calculate numerical features (price changes, volatility, pattern shapes)
3. Convert features into a vector of the same size as Brooks' vectors
4. Use cosine similarity to find most similar Brooks vectors

### Advantages

- Vectors capture subtle visual patterns that text labels miss
- A vector might encode "price made 3 pushes up with decreasing momentum" without naming it
- More nuanced matching with similarity scores (0.85, 0.72, etc.)

### Challenges

- Need to convert live candles into vectors comparable to Gemini's image vectors
- Gemini's vectors came from images, not raw price data
- Requires training a model or finding a mapping between candle features and image features

### Effort Required

- Research how Gemini encodes images
- Build feature extractor for candles
- Train or calibrate mapping layer
- Estimated: High effort

---

## Option 2: Generate Chart Images and Match Directly

### The Concept

Since Brooks' patterns are stored as image embeddings, match them with images directly. This is the most straightforward "apples to apples" comparison.

### How It Would Work

1. Take live candle data (last 20 candles)
2. Render a candlestick chart image (using existing `chart_renderer.py`)
3. Send image to Gemini to create a vector embedding
4. Compare embedding against all 1000 Brooks embeddings
5. Find closest matches

### Advantages

- Apples to apples comparison - both sides are image embeddings from Gemini
- Captures exactly what a human would see on the chart
- No translation layer needed - matching happens in "visual space"
- Highest potential accuracy

### Challenges

- API costs - calling Gemini for every signal check costs money
- Latency - generating image + API call takes 2-5 seconds
- Rate limits - checking many coins frequently may hit limits

### When This Makes Sense

- For high-value signals only (not every candle)
- When maximum accuracy is worth the cost
- As a "confirmation" step after cheaper filters pass

### Effort Required

- Integrate chart renderer with Gemini API
- Build embedding comparison logic
- Add caching to reduce API calls
- Estimated: Medium effort

---

## Option 3: Enhance the Candle Encoder

### What We Have Now

The current `extract_phase_from_candle()` function outputs one of 5 labels:
- `trend`, `reversal`, `range`, `breakout`, `channel`

### What Enhancement Means

Make the encoder detect secondary patterns and market cycles.

#### Secondary Patterns to Detect

- **Wedge**: 3 pushes with converging trendlines
- **Double top/bottom**: Two peaks/valleys at similar price
- **Triangle**: Converging highs and lows
- **Measured move**: Equal-length price swings
- **Gap**: Price jump between candles
- **Spike**: Extreme single-candle move

#### Market Cycles to Detect

- **Trading range**: Price bouncing between support/resistance
- **Trend**: Consistent higher highs or lower lows
- **Climactic**: Extreme volume/volatility at end of move
- **Tight channel**: Narrow, controlled pullback
- **Broad channel**: Wide, volatile pullback

### How It Would Work

Instead of outputting `trend`, the encoder would output `trend_wedge_tight_channel` - matching Brooks' data format exactly.

### Advantages

- No API costs - runs locally
- Fast - pure computation
- Leverages the text-based cluster matching already built

### Challenges

- Significant coding effort to detect wedges, triangles, etc.
- May not match Gemini's interpretation
- After all that work, might still be less accurate than image matching

### Effort Required

- Implement secondary pattern detection algorithms
- Implement cycle detection algorithms
- Test and calibrate against Brooks' labels
- Estimated: High effort

---

## Comparison Table

| Aspect | Option 1: Vectors | Option 2: Images | Option 3: Encoder |
|--------|------------------|------------------|-------------------|
| Accuracy | Medium-High | Highest | Medium |
| Cost per signal | Free (local) | ~$0.01-0.05 (API) | Free (local) |
| Speed | Fast (<100ms) | Slow (2-5s) | Fast (<100ms) |
| Development effort | High | Medium | High |
| Uses existing data | Yes (vectors) | Yes (embeddings) | Partially |
| Maintenance | Low | Medium (API changes) | High |

---

## Recommendation

### If accuracy is priority: Option 2 (Image Matching)
- Most direct use of existing Brooks embeddings
- Gemini compares like with like
- Use as confirmation for high-value signals

### If cost/speed is priority: Option 1 (Vector Matching)
- Requires upfront work to build mapping
- Once built, runs fast and free
- Good for screening many coins

### If you want incremental progress: Option 3 (Encoder)
- Can improve gradually
- Each pattern added improves matching
- But may never reach image matching accuracy

---

## Files Reference

- Sequence matcher: `src/abu/brooks_sequence_matcher.py`
- Chart renderer: `src/abu/chart_renderer.py`
- Pattern vectors table: PostgreSQL `pattern_vectors`
- Pattern library table: PostgreSQL `pattern_library`

---

## Next Steps (When Ready)

1. Decide which option to pursue
2. For Option 2: Test with a few manual image comparisons first
3. For Option 1: Analyze vector dimensions and feature requirements
4. For Option 3: List all secondary patterns in Brooks' data to prioritize

---

## Integration Options: How to Use the Matcher

The sequence matcher functions are ready. Here are three ways to integrate into the trading system:

### Integration A: Filter ABU Signals

**Concept**: When ABU generates a signal, check if Brooks matcher agrees before taking the trade.

**How It Works**:
1. ABU detects pattern (Engulfing, PinBar, etc.) and generates signal
2. Encode recent candles into phases
3. Match against Brooks clusters
4. Check if predicted next phase aligns with signal direction
   - Long signal + predicted "trend" or "breakout" = TAKE
   - Long signal + predicted "reversal" = SKIP
5. Only execute signals that pass Brooks filter

**Pros**:
- Simple to implement
- Reduces false signals
- Keeps existing ABU logic intact

**Cons**:
- May filter out too many signals if matcher is noisy
- Binary decision (take/skip) loses nuance

### Integration B: Standalone Signal Generator

**Concept**: Use Brooks matcher independently to generate its own signals.

**How It Works**:
1. Every N minutes, encode recent candles for each coin
2. Match against Brooks clusters
3. If high-confidence prediction of "breakout" or "trend" continuation, generate signal
4. Set entry/SL/TP based on cluster's historical outcomes

**Pros**:
- Pure Brooks-based trading
- Not dependent on ABU pattern detection
- Can capture patterns ABU misses

**Cons**:
- Needs more development (entry/exit logic)
- Less tested than ABU approach
- May generate conflicting signals with ABU

### Integration C: Confidence Multiplier

**Concept**: Use Brooks match as a confidence score to adjust position sizing.

**How It Works**:
1. ABU generates signal with base position size
2. Encode candles and match against Brooks clusters
3. Calculate confidence score (0.0 - 1.0) based on:
   - Match similarity
   - Number of supporting patterns
   - Position in pattern story
4. Adjust position size: `final_size = base_size * (0.5 + confidence * 0.5)`
   - Low confidence (0.3): 65% of base size
   - High confidence (0.8): 90% of base size

**Pros**:
- Nuanced approach (not binary)
- Still takes all ABU signals
- Higher conviction = larger position

**Cons**:
- More complex position management
- Needs careful calibration of multiplier formula

---

## Recommended Path Forward

### Phase 1: Quick Win (Integration A)
1. Add Brooks filter to ABU signal generation
2. Log filtered vs unfiltered signals for 1 week
3. Compare outcomes to validate filter effectiveness

### Phase 2: Improve Encoder (Option 2 or 3)
1. If filter shows promise, invest in better matching
2. Option 2 (Image) for highest accuracy on filtered signals
3. Option 3 (Encoder) for free, fast screening

### Phase 3: Full Integration (Integration C)
1. Once matching is reliable, use confidence multiplier
2. Backtest position sizing strategy
3. Deploy to production

---

## Decision Required

**Encoder Improvement**: Which option?
- [ ] Option 1: Vector matching (high effort, free)
- [ ] Option 2: Image matching (medium effort, API cost)
- [ ] Option 3: Enhanced encoder (high effort, free)

**Integration Approach**: Which method?
- [ ] Integration A: Filter ABU signals (simplest)
- [ ] Integration B: Standalone generator (most independent)
- [ ] Integration C: Confidence multiplier (most nuanced)

---

Take your time to rest. This document will be here when you return.
