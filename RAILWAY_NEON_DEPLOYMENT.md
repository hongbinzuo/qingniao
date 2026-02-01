# Railway + Neon Free PostgreSQL Deployment Guide

Deploy the Abu scanner to Railway with Neon's free PostgreSQL database for 24/7 operation.

## Cost Breakdown

- **Railway Hobby Plan**: $5/month (runs the scanner)
- **Neon PostgreSQL**: FREE (0.5GB storage, 3GB transfer/month)
- **Total: $5/month**

---

## Part 1: Set Up Neon PostgreSQL (Free)

### Step 1: Create Neon Account

1. Go to https://neon.tech
2. Sign up with GitHub (recommended) or email
3. Verify your email

### Step 2: Create Database

1. Click "Create a project"
2. Project name: `abu-scanner`
3. Region: Choose closest to you (US East, EU, Asia)
4. PostgreSQL version: 16 (latest)
5. Click "Create project"

### Step 3: Get Connection String

1. In your Neon dashboard, click on your project
2. Go to "Connection Details"
3. Copy the connection string (looks like):
   ```
   postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
4. Save this - you'll need it for Railway

### Step 4: Initialize Database Schema

On your local machine:

```bash
# Set the Neon database URL
export DATABASE_URL="postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require"

# Run initialization script
python scripts/init_railway_db.py
```

You should see:
```
✓ Connected successfully
✓ trading_signals table created
✓ Indexes created
✓ Database initialization complete!
```

---

## Part 2: Deploy Scanner to Railway

### Step 1: Create Railway Project

1. Go to https://railway.app
2. Sign up/login with GitHub
3. Click "New Project"
4. Select "Deploy from GitHub repo"
5. Choose `hongbinzuo/qingniao` repository
6. Select branch: `abu_system`
7. Railway will start building

### Step 2: Configure Environment Variables

1. In Railway dashboard, click on your service
2. Go to "Variables" tab
3. Click "New Variable"
4. Add these variables:

#### Required Variables

```
DATABASE_URL=postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
SCAN_INTERVAL_MINUTES=15
TOP_COINS=10
TIMEFRAMES=5m,15m,1h
SIGNAL_MODES=aggressive,neutral,conservative
```

**Important**: Use your Neon connection string for `DATABASE_URL`

#### Optional Threshold Variables

```
AGGRESSIVE_MIN_SCORE=0.1
AGGRESSIVE_MIN_VECTOR=0.6
NEUTRAL_MIN_SCORE=0.2
NEUTRAL_MIN_VECTOR=0.7
CONSERVATIVE_MIN_SCORE=0.4
CONSERVATIVE_MIN_VECTOR=0.8
```

### Step 3: Deploy

1. Railway will automatically deploy after variables are set
2. Check "Deployments" tab for build progress
3. Wait for "Success" status

### Step 4: Verify Scanner is Running

1. Go to "Logs" tab in Railway
2. You should see:
   ```
   RAILWAY SCANNER SERVICE STARTED
   Signal Thresholds:
     AGGRESSIVE: min_score: 0.1, min_vector_match: 0.6
   Scan interval: 15 minutes
   ```
3. Watch for scan cycles to start

---

## Part 3: Monitor and View Signals

### View Signals from Local Machine

```bash
export DATABASE_URL="your-neon-connection-string"
python scripts/view_recent_signals.py
```

### Query Database Directly

In Neon dashboard → SQL Editor:

```sql
SELECT symbol, timeframe, direction, entry_price, 
       created_at, signal_mode, confidence
FROM trading_signals 
ORDER BY created_at DESC 
LIMIT 20;
```

---

## Configuration Tips

### Scan Frequency

- `15` minutes = 96 scans/day (recommended)
- `30` minutes = 48 scans/day (moderate)
- `60` minutes = 24 scans/day (conservative)

### Coin Count

- `10` coins = ~30-45s per scan (recommended)
- `20` coins = ~60-90s per scan
- `5` coins = ~20-30s per scan (faster)

---

## Troubleshooting

**Issue: "Connection refused" to database**
- Check DATABASE_URL is correct
- Ensure Neon project is active
- Verify connection string includes `?sslmode=require`

**Issue: "No signals generated"**
- Normal if market is ranging/sideways
- Scanner is working, waiting for clear patterns
- Check logs to confirm scans are completing

**Issue: Build fails on Railway**
- Check build logs for errors
- Ensure all dependencies in requirements.txt
- Verify Python version compatibility

---

## Cost Summary

- **Railway Hobby**: $5/month (includes $5 execution credit)
- **Neon PostgreSQL**: FREE (0.5GB storage)
- **Actual execution cost**: ~$0.67/month (covered by credit)
- **Total out-of-pocket: $5/month**

---

## Next Steps

1. ✓ Set up Neon database
2. ✓ Initialize schema
3. ✓ Deploy to Railway
4. ✓ Configure environment variables
5. Monitor logs for first signals
6. Adjust thresholds if needed

**You're now running 24/7 and won't miss any more moves!**


