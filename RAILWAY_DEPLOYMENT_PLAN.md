# Railway Deployment Plan for Qingniao Abu Scanner

## Executive Summary

This document outlines the complete Railway deployment strategy for the Abu trading signal scanner system. The scanner analyzes cryptocurrency patterns using Price Action analysis, Brooks patterns, and vector-based pattern matching.

## Current System Analysis

### Core Components
- **Main Scanner**: `scripts/pa_scan_main.py` - Multi-exchange crypto scanner (Gate.io, Bybit, Bitget)
- **Database**: PostgreSQL (via `db_manager_trader.py`)
- **Vector Index**: `data/vectors/brooks_patterns_32d.ann` (361KB)
- **Pattern Library**: Unified pattern matching with Gemini Pro 3 integration
- **Timeframes**: 5m, 15m, 1h (default: 15m)

### Dependencies
- Python 3.x
- PostgreSQL with psycopg2
- Annoy (vector similarity search)
- External APIs: Gemini, Moonshot, OpenRouter
- Exchange APIs: Gate.io, Bybit, Bitget

### Current Execution Profile
- **15m timeframe**: ~96 potential runs/day, ~30-60s per scan
- **1h timeframe**: ~24 runs/day, ~45-90s per scan
- **5m timeframe**: ~288 runs/day, ~20-40s per scan

---

## Deployment Questions & Recommendations

### 1. Database Preference

**Question**: Do you already have a PostgreSQL database set up on Railway, or should we add a new PostgreSQL service? Or would you prefer to use an external provider like Supabase or Neon?

**Recommendations**:

#### Option A: Railway PostgreSQL (Recommended for Simplicity)
- **Pros**: 
  - Integrated with Railway platform
  - Automatic backups
  - Easy connection via internal networking
  - No external dependencies
- **Cons**: 
  - Costs $5/month minimum (Hobby plan)
  - Limited to Railway ecosystem
- **Best for**: Quick setup, all-in-one solution

#### Option B: Supabase (Recommended for Features)
- **Pros**: 
  - Free tier available (500MB database)
  - Built-in connection pooling
  - Dashboard and monitoring tools
  - Can be used outside Railway
- **Cons**: 
  - External dependency
  - Connection via public internet
  - May need connection pooling for concurrent scans
- **Best for**: Cost optimization, multi-environment usage

#### Option C: Neon (Recommended for Scalability)
- **Pros**: 
  - Serverless PostgreSQL with autoscaling
  - Free tier available (0.5GB storage)
  - Excellent for intermittent workloads
  - Branch-based development
- **Cons**: 
  - External dependency
  - Cold start delays possible
- **Best for**: Variable workload patterns

**My Recommendation**: Start with **Railway PostgreSQL** for simplicity, migrate to Neon later if cost becomes an issue.

---

### 2. Cron Schedule

**Question**: What scanning frequency do you want?

**Analysis by Timeframe**:

#### 15m Timeframe (Recommended Default)
- **Every 15 minutes**: 96 runs/day
  - Cron: `*/15 * * * *`
  - Execution time: ~30-60s
  - Railway cost: ~$2-4/month (Hobby plan)
  - **Best for**: Active trading, timely signals

- **Every 30 minutes**: 48 runs/day
  - Cron: `*/30 * * * *`
  - Execution time: ~30-60s
  - Railway cost: ~$1-2/month
  - **Best for**: Moderate trading frequency

- **Every hour**: 24 runs/day
  - Cron: `0 * * * *`
  - Execution time: ~30-60s
  - Railway cost: ~$0.50-1/month
  - **Best for**: Conservative approach

#### 1h Timeframe
- **Every hour**: 24 runs/day
  - Cron: `0 * * * *`
  - Execution time: ~45-90s
  - Railway cost: ~$1-2/month
  - **Best for**: Swing trading, longer-term signals

#### 5m Timeframe (High Frequency)
- **Every 5 minutes**: 288 runs/day
  - Cron: `*/5 * * * *`
  - Execution time: ~20-40s
  - Railway cost: ~$5-10/month
  - **Best for**: Scalping, very active trading
  - **Warning**: High execution cost

**My Recommendation**: 
- **Primary**: 15m every 15 minutes (`*/15 * * * *`)
- **Secondary**: 1h every hour (`0 * * * *`)
- **Skip 5m** unless you need scalping signals (too expensive)

---

### 3. Symbol Count

**Question**: How many symbols should the scanner analyze?

**Current Default**: 10 symbols (via `--top 10`)

**Analysis**:
- **10 symbols**: ~30-45s execution time
- **20 symbols**: ~60-90s execution time
- **30 symbols**: ~90-120s execution time
- **50+ symbols**: 2-3+ minutes execution time

**Recommendations by Timeframe**:

#### 15m Timeframe
- **10 symbols**: Fast, focused on top movers
- **20 symbols**: Good balance (recommended)
- **30 symbols**: Comprehensive coverage

#### 1h Timeframe
- **20 symbols**: Minimum recommended
- **30 symbols**: Good balance
- **50 symbols**: Comprehensive (still under 3 min)

**My Recommendation**: 
- **15m**: 20 symbols (`--top 20`)
- **1h**: 30 symbols (`--top 30`)

---

### 4. Vector Files Deployment

**Question**: The vector index files need to be deployed. Which approach?

**File Details**:
- `data/vectors/brooks_patterns_32d.ann` (361KB)
- `data/vectors/brooks_patterns_id_map.json` (~10KB)
- Total: ~371KB

#### Option A: Commit to Git (Recommended)
- **Pros**: 
  - Simple deployment
  - Version controlled
  - No runtime download needed
  - Fast startup
- **Cons**: 
  - Increases repo size by ~371KB (negligible)
  - Must rebuild if patterns change
- **Implementation**: Add to git, remove from .gitignore
- **Best for**: Static pattern library

#### Option B: Railway Volumes
- **Pros**: 
  - Persistent storage
  - Can update without redeployment
  - Separate from code
- **Cons**: 
  - Costs $0.25/GB/month (~$0.01/month for 371KB)
  - More complex setup
  - Slower first access
- **Implementation**: Mount volume, copy files on first run
- **Best for**: Frequently updated patterns

#### Option C: Cloud Storage (S3/R2)
- **Pros**: 
  - External storage
  - Can share across deployments
  - CDN-backed downloads
- **Cons**: 
  - External dependency
  - Download time on startup (~1-2s)
  - Additional service to manage
- **Implementation**: Download from S3 on startup
- **Best for**: Multi-region deployments

**My Recommendation**: **Option A (Commit to Git)** - 371KB is tiny, and the files are relatively static.

---

### 5. Output Files

**Question**: The scanner generates markdown reports in `outputs/trading_signals/`. Do you need these files, or is database storage sufficient?

**Current Behavior**:
- Generates markdown reports: `ABU_top{N}_{timeframe}_{timestamp}.md`
- Writes signals to PostgreSQL database
- Reports include detailed analysis, skip reasons, statistics

**Options**:

#### Option A: Database Only (Recommended)
- **Pros**: 
  - No file storage needed
  - Queryable data
  - No cleanup required
  - Lower costs
- **Cons**: 
  - No human-readable reports
  - Harder to debug
- **Implementation**: Set `--write-db 1`, ignore markdown output
- **Best for**: Production deployment

#### Option B: Database + Ephemeral Reports
- **Pros**: 
  - Reports available for debugging
  - Automatic cleanup on restart
  - No persistent storage cost
- **Cons**: 
  - Reports lost on restart
  - Not accessible after deployment
- **Implementation**: Write to `/tmp`, don't persist
- **Best for**: Development/debugging

#### Option C: Database + Persistent Reports (Railway Volumes)
- **Pros**: 
  - Full report history
  - Debugging capability
  - Audit trail
- **Cons**: 
  - Storage costs (~$0.25/GB/month)
  - Cleanup required (grows over time)
  - ~1-2MB per report × 96 runs/day = ~200MB/day
- **Implementation**: Mount volume for `outputs/`
- **Best for**: Compliance/audit requirements

**My Recommendation**: **Option A (Database Only)** - Reports are nice for debugging but not essential for production.

---

### 6. Railway Plan

**Question**: Do you have Railway Hobby ($5/month) or Pro plan? This affects execution limits.

**Plan Comparison**:

#### Hobby Plan ($5/month)
- **Execution time**: $0.000231/minute
- **Memory**: 512MB-8GB
- **Included**: $5 credit/month (~21,645 minutes)
- **Limits**: 
  - 500 hours/month execution time
  - Shared resources
- **Cost estimate for our use**:
  - 15m every 15min: ~96 runs × 1min = 96min/day = 2,880min/month = **$0.67/month**
  - 1h every hour: ~24 runs × 1.5min = 36min/day = 1,080min/month = **$0.25/month**
  - **Total**: ~$1/month (well within $5 credit)

#### Pro Plan ($20/month)
- **Execution time**: $0.000231/minute (same)
- **Memory**: Up to 32GB
- **Included**: $20 credit/month
- **Limits**: Higher priority, more resources
- **Best for**: High-frequency trading, multiple scanners

**My Recommendation**: **Hobby Plan** is more than sufficient for your use case.

---

## Recommended Configuration

Based on the analysis above, here's my recommended setup:

### Configuration Summary
1. **Database**: Railway PostgreSQL ($5/month)
2. **Cron Schedules**: 
   - 15m scanner: Every 15 minutes (`*/15 * * * *`)
   - 1h scanner: Every hour (`0 * * * *`)
3. **Symbol Count**: 
   - 15m: 20 symbols
   - 1h: 30 symbols
4. **Vector Files**: Commit to Git
5. **Output**: Database only (no persistent reports)
6. **Railway Plan**: Hobby ($5/month)

### Estimated Monthly Cost
- Railway Hobby Plan: $5/month (includes $5 credit)
- Execution time: ~$1/month (covered by credit)
- PostgreSQL: Included in Hobby plan
- **Total**: $5/month

### Expected Performance
- 15m scanner: 96 runs/day, ~30-60s each
- 1h scanner: 24 runs/day, ~45-90s each
- Total execution time: ~120 minutes/day
- Signals generated: 10-30 per day (estimated)

---

## Next Steps

Once you confirm your preferences, I will:

1. Create Railway configuration files (`railway.json`, `railway.toml`)
2. Create Dockerfile optimized for Railway
3. Set up cron job configuration
4. Create environment variable template
5. Write deployment instructions
6. Create monitoring/alerting setup

Please answer the 6 questions above, or let me know if you'd like to proceed with my recommended configuration.
