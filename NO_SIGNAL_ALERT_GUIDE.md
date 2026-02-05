# Abu Scanner - No Signal Alert System

## Problem: What if no signals for 2 days?

If your scanner produces **no signals for 48+ hours**, it indicates a problem:

### Why This is Bad:
- Scanner should find 5-10+ signals daily (10 coins × 3 timeframes)
- Market always has patterns, even in ranging conditions
- 48 hours of silence = Scanner is broken

### Possible Causes:
1. ❌ Scanner crashed and didn't restart
2. ❌ Database connection lost
3. ❌ Code error causing silent failure
4. ❌ Railway service stopped (billing/credits)

---

## Solution Implemented

### 1. Visual Alert on Dashboard ⚠️

**Red banner appears when:**
- No signals in last 48 hours
- Or no signals in database at all

**What you'll see:**
```
⚠️ WARNING: No signals detected in last 48 hours! Scanner may be down.
```

The alert banner:
- Shows automatically on dashboard
- Updates every 30 seconds
- Bright red background (impossible to miss)

### 2. Health Check Script

**Location:** `scripts/health_check.py`

**What it checks:**
- Last signal timestamp
- Signals in last 24 hours
- Database connectivity

**Run manually:**
```bash
python scripts/health_check.py
```

**Output example:**
```
✓ Scanner is HEALTHY
```

Or if problems:
```
✗ Scanner has ISSUES

ERRORS:
  ✗ CRITICAL: No signals for 52.3 hours (2+ days)

WARNINGS:
  ⚠ WARNING: Only 3 signals in last 24h (expected ~10-20)
```

---

## How to Monitor

### Option 1: Check Dashboard Daily
- Visit: https://qingniao-production.up.railway.app
- Look for red alert banner
- Check "Signals (24h)" count

### Option 2: Run Health Check
```bash
# Locally (with Railway DATABASE_URL)
export DATABASE_URL="your-neon-url"
python scripts/health_check.py

# Or via Railway CLI
railway run python scripts/health_check.py
```

### Option 3: Set Up External Monitoring (Optional)
Use services like:
- UptimeRobot (free) - Ping your dashboard URL
- Cronitor - Monitor health check endpoint
- Railway's built-in health checks

---

## What to Do if Alert Shows

### Step 1: Check Railway Logs
```bash
railway logs
```

Look for:
- Error messages
- "Scanner stopped" messages
- Database connection errors

### Step 2: Check Railway Dashboard
- Go to: https://railway.app
- Check if service is running
- Look at deployment status

### Step 3: Restart Service
```bash
railway restart
```

Or redeploy:
```bash
railway up
```

### Step 4: Check Database
```bash
railway run python scripts/health_check.py
```

---

## Prevention

### Auto-Restart Policy (Already Configured)
Railway is configured to auto-restart on failure:
```toml
[deploy]
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

### What This Means:
- If scanner crashes, Railway restarts it automatically
- Up to 3 restart attempts
- Should recover from temporary issues

---

## Expected Signal Frequency

**Normal operation:**
- **5-20 signals per day** (varies with market conditions)
- **At least 1 signal every 6-12 hours**
- **Never more than 24 hours without signals**

**If you see:**
- 0 signals in 48h → **CRITICAL** - Scanner broken
- 0-2 signals in 24h → **WARNING** - Check scanner
- 5+ signals in 24h → **NORMAL** - All good

---

## Dashboard Features

### Status Indicators:
- 🟢 **Running** - Last signal < 30 min ago
- 🔴 **Stopped** - Last signal > 30 min ago
- ⚠️ **Alert Banner** - No signals in 48h

### Metrics Shown:
- Scanner status (Running/Stopped)
- Signals in last 24 hours
- Recent 20 signals table
- Signal outcomes (TP/SL) for last 7 days

---

## Summary

✅ **Alert system active** - Red banner shows if no signals for 2 days
✅ **Health check script** - Manual monitoring tool
✅ **Auto-restart enabled** - Railway restarts on crashes
✅ **Dashboard monitoring** - Visual status at a glance

**Your scanner is now protected against silent failures!**
