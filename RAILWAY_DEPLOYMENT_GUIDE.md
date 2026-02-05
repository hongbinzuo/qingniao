# Railway Deployment Guide - Abu Scanner 24/7

This guide will help you deploy the Abu trading signal scanner to Railway with free PostgreSQL database for continuous 24/7 operation.

## Overview

**What this does:**
- Runs the Abu scanner continuously on Railway
- Scans crypto markets every 15 minutes (configurable)
- Stores signals in Railway PostgreSQL database
- Catches trading signals in real-time (no more missed moves!)

**Cost:**
- Railway Hobby Plan: $5/month
- Includes $5 execution credit (enough for our usage)
- PostgreSQL database included
- **Estimated actual cost: ~$1/month** (well within credit)

## Prerequisites

1. Railway account (sign up at https://railway.app)
2. GitHub account (to connect your repo)
3. This repository pushed to GitHub

---

## Step 1: Push Code to GitHub

If you haven't already, push your code to GitHub:

```bash
git add .
git commit -m "feat: add Railway deployment configuration"
git push origin abu_system
```

---

## Step 2: Create Railway Project

1. Go to https://railway.app
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Authorize Railway to access your GitHub
5. Select your `qingniao` repository
6. Select branch: `abu_system`

Railway will automatically detect the configuration from `railway.toml` and `Procfile`.

---

## Step 3: Add PostgreSQL Database

1. In your Railway project dashboard, click "+ New"
2. Select "Database"
3. Choose "PostgreSQL"
4. Railway will automatically:
   - Create a PostgreSQL instance
   - Generate `DATABASE_URL` environment variable
   - Connect it to your service

**Note:** Railway's PostgreSQL is NOT free, but it's included in the $5/month Hobby plan.

---

## Step 4: Configure Environment Variables

In your Railway project:

1. Click on your service (not the database)
2. Go to "Variables" tab
3. Add the following variables:

### Required Variables

```
SCAN_INTERVAL_MINUTES=15
TOP_COINS=10
TIMEFRAMES=5m,15m,1h
SIGNAL_MODES=aggressive,neutral,conservative
```

### Signal Thresholds (Optional - defaults shown)

```
AGGRESSIVE_MIN_SCORE=0.1
AGGRESSIVE_MIN_VECTOR=0.6
NEUTRAL_MIN_SCORE=0.2
NEUTRAL_MIN_VECTOR=0.7
CONSERVATIVE_MIN_SCORE=0.4
CONSERVATIVE_MIN_VECTOR=0.8
```

**Note:** `DATABASE_URL` is automatically set by Railway when you add PostgreSQL.

---

## Step 5: Initialize Database Schema

Before the scanner can run, you need to create the database tables.

1. In Railway, click on your PostgreSQL database
2. Go to "Connect" tab
3. Copy the "Postgres Connection URL"
4. On your local machine, run:

```bash
# Set the Railway database URL
export DATABASE_URL="your-railway-postgres-url"

# Run the database initialization script
python scripts/init_railway_db.py
```

This will create all necessary tables for storing trading signals.

---

## Step 6: Deploy and Monitor

1. Railway will automatically deploy after you push to GitHub
2. Check the "Deployments" tab to see build progress
3. Once deployed, check "Logs" tab to see scanner output
4. You should see:
   - "RAILWAY SCANNER SERVICE STARTED"
   - Signal thresholds displayed
   - Scan cycles running every 15 minutes

---

## Step 7: View Signals

To view generated signals, you have two options:

### Option A: Query Database Directly

In Railway PostgreSQL dashboard:

```sql
SELECT symbol, timeframe, direction, entry_price, created_at, signal_mode
FROM trading_signals 
ORDER BY created_at DESC 
LIMIT 20;
```

### Option B: Use Local Script (Connected to Railway DB)

```bash
export DATABASE_URL="your-railway-postgres-url"
python scripts/view_recent_signals.py
```

---

## Configuration Options

### Scan Frequency

Adjust `SCAN_INTERVAL_MINUTES` based on your needs:

- `5` = Every 5 minutes (very active, higher cost)
- `15` = Every 15 minutes (recommended, balanced)
- `30` = Every 30 minutes (moderate)
- `60` = Every hour (conservative, lower cost)

### Coin Count

Adjust `TOP_COINS` based on scan time tolerance:

- `5` = Fast scans (~20-30s)
- `10` = Balanced (recommended, ~30-45s)
- `20` = Comprehensive (~60-90s)
- `30+` = Very comprehensive (2+ minutes)

---

## Monitoring and Troubleshooting

### Check Scanner Status

In Railway logs, look for:
- ✓ Successful scans
- ✗ Failed scans
- Signal generation messages

### Common Issues

**Issue: "No module named 'abu'"**
- Solution: Railway should install dependencies automatically. Check build logs.

**Issue: "Connection refused" to PostgreSQL**
- Solution: Ensure PostgreSQL service is running and `DATABASE_URL` is set.

**Issue: "No signals generated"**
- This is normal if market is ranging/sideways
- Scanner is working correctly, just waiting for clear patterns

---

## Cost Estimation

Based on recommended configuration:

- Scan interval: 15 minutes
- Scans per day: 96
- Scan duration: ~1 minute average
- Monthly execution: ~2,880 minutes
- Cost: ~$0.67/month (covered by $5 credit)

**Total monthly cost: $5 (Hobby plan)**

---

## Next Steps

1. Monitor logs for first few cycles
2. Verify signals are being stored in database
3. Adjust thresholds if too many/few signals
4. Set up alerts (optional - see below)

---

## Optional: Set Up Alerts

To get notified when signals are generated, you can:

1. Add a webhook endpoint to your service
2. Configure Telegram/Discord bot
3. Use Railway's built-in notifications

(Contact me if you need help setting this up)

---

## Support

If you encounter issues:

1. Check Railway logs first
2. Verify DATABASE_URL is set correctly
3. Ensure PostgreSQL service is running
4. Check that all environment variables are configured

---

## Summary

✓ Scanner runs 24/7 on Railway
✓ Catches signals in real-time
✓ Stores in PostgreSQL database
✓ Costs ~$5/month
✓ No more missed trading opportunities!


