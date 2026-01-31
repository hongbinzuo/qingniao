# Quick Start Guide - Windows Environment

## Python Command
Use `py -3` instead of `python` on Windows:

```bash
# Check Python version
py -3 --version

# Run scripts
py -3 scripts/pa_scan_main.py
```

---

## Usage Examples

### 1. Run Scanner (Default: 15m timeframe)
```bash
py -3 scripts/pa_scan_main.py
```

### 2. Specify Timeframe
```bash
# 1 hour timeframe
py -3 scripts/pa_scan_main.py --timeframe 1h

# 5 minute timeframe
py -3 scripts/pa_scan_main.py --timeframe 5m
```

### 3. Specify Top N Coins
```bash
py -3 scripts/pa_scan_main.py --top 20
```

### 4. Combine Options
```bash
py -3 scripts/pa_scan_main.py --timeframe 1h --top 15
```

---

## Maintenance Commands

### Rebuild Vector Index
```bash
py -3 scripts/rebuild_vector_index.py --trees 20
```

### Re-solidify Vectors
```bash
# Audit only
py -3 scripts/solidify_vectors_v2.py --audit-only

# Fix and commit
py -3 scripts/solidify_vectors_v2.py --fix --commit
```

### Verify Solidification
```bash
py -3 scripts/verify_solidification.py
```

---

## Check Vector Matching Status

When running the scanner, look for this message:
```
[INFO] Vector matching enabled
```

If you see:
```
[WARN] Vector index not found, vector matching disabled
```

Then rebuild the index:
```bash
py -3 scripts/rebuild_vector_index.py --trees 20
```

---

## Output Fields

The scanner adds these vector-related fields to each candidate:

- `_vector_score` - Contribution to final score
- `_vector_win_prob` - Aggregated win probability (0.0-1.0)
- `_vector_rr` - Aggregated risk/reward ratio
- `_vector_confidence` - Similarity confidence (0.0-1.0)
- `_vector_matches` - Number of similar patterns found
- `_vector_direction` - Consensus direction (bullish/bearish/neutral)

---

## Troubleshooting

### Vector matching not enabled?
1. Check if index files exist:
   ```bash
   ls data/vectors/
   ```
   Should see: `brooks_patterns_32d.ann` and `brooks_patterns_id_map.json`

2. If missing, rebuild:
   ```bash
   py -3 scripts/rebuild_vector_index.py --trees 20
   ```

### Import errors?
Install dependencies:
```bash
py -3 -m pip install annoy numpy
```

### Database connection errors?
Check `.env` file has PostgreSQL credentials:
```
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=qingniao_abu
PG_USER=abu_user
PG_PASSWORD=Abu2026!Secure
```
