# Railway Database Initialization Guide

## Quick Method: Run from Your Local Computer

### Step 1: Get Your Railway Database URL

1. Go to Railway Dashboard: https://railway.app
2. Open your project
3. Click on the **PostgreSQL** database (the database icon, NOT your app)
4. Click the **"Connect"** tab
5. Find **"Postgres Connection URL"**
6. Click to copy it (looks like: `postgresql://postgres:xxx@xxx.railway.app:5432/railway`)

### Step 2: Run the Initialization Script

**Option A: Use the Batch File (Easiest)**

1. Double-click: `init_railway_db_local.bat`
2. Paste your DATABASE_URL when prompted
3. Press Enter
4. Wait for "Done!"

**Option B: Manual Command**

Open Command Prompt in this folder and run:

```cmd
set DATABASE_URL=postgresql://postgres:xxx@xxx.railway.app:5432/railway
python scripts/init_railway_db.py
```

Replace the URL with your actual Railway database URL.

---

## Alternative: Railway CLI Method

If you have Railway CLI installed:

```bash
railway run python scripts/init_railway_db.py
```

---

## How to Find Railway Shell (If Available)

Railway shell location varies by plan:

1. **New UI**: Project → Service → "..." menu → "Shell"
2. **Old UI**: Service → "Deployments" tab → Latest deployment → "View Logs" → "Shell" button
3. **Some plans**: Shell feature may not be available

If you don't see it, use the local method above instead.

---

## Verify Database Initialization

After running the script, you should see:

```
✓ Connected to Railway PostgreSQL
✓ Creating trading_signals table...
✓ Creating pattern_matches table...
✓ Creating scan_history table...
✓ All tables created successfully!
```

---

## Troubleshooting

**Error: "psycopg2 not installed"**
```bash
pip install psycopg2-binary
```

**Error: "Connection refused"**
- Check your DATABASE_URL is correct
- Ensure Railway PostgreSQL is running
- Verify your IP is not blocked

**Error: "Permission denied"**
- Your database user needs CREATE TABLE permissions
- Railway's default user should have this

---

## Next Steps

After database initialization:

1. Go to Railway Dashboard
2. Check your app service logs
3. Look for: "RAILWAY SCANNER SERVICE STARTED"
4. Verify scans are running every 15 minutes

Done! Your scanner is now running 24/7 on Railway.
