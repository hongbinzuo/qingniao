# Railway Setup Guide - Step by Step

## Problem: Cannot See Database Page

This means you haven't added a PostgreSQL database to your Railway project yet.

---

## Solution: Add PostgreSQL Database to Railway

### Step 1: Add Database Service

1. Go to https://railway.app
2. Open your `qingniao` project
3. Look for a **"+ New"** button or **"Add Service"** button
4. Click it
5. Select **"Database"**
6. Choose **"Add PostgreSQL"**

Railway will automatically:
- Create a PostgreSQL database
- Generate a `DATABASE_URL` environment variable
- Connect it to your app service

### Step 2: Wait for Database to Deploy

- It takes 1-2 minutes to provision
- You'll see a new PostgreSQL card/service in your project
- Status will change from "Deploying" to "Active"

### Step 3: Verify DATABASE_URL is Set

1. Click on your **app service** (not the database)
2. Go to **"Variables"** tab
3. You should now see `DATABASE_URL` automatically added
4. It looks like: `postgresql://postgres:xxx@xxx.railway.app:5432/railway`

---

## After Database is Added

Once you see the PostgreSQL service in your project, you can:

### Option A: Get DATABASE_URL from Variables

1. Click your **app service**
2. Go to **"Variables"** tab
3. Find and copy `DATABASE_URL`
4. Run: `init_railway_db_local.bat` (paste the URL when prompted)

### Option B: Get DATABASE_URL from Database Service

1. Click the **PostgreSQL** service (database icon)
2. Go to **"Connect"** tab
3. Copy **"Postgres Connection URL"**
4. Run: `init_railway_db_local.bat` (paste the URL when prompted)

---

## Important Notes

- **Free Tier**: Railway Hobby plan ($5/month) includes PostgreSQL
- **Trial**: You may have trial credits to test
- **DATABASE_URL**: Automatically injected into your app when database is added

---

## What to Look For in Railway Dashboard

Your project should have **2 services**:

1. **Your App** (qingniao scanner service)
   - Shows your code deployments
   - Has "Variables", "Deployments", "Logs" tabs

2. **PostgreSQL** (database service)
   - Shows database status
   - Has "Connect", "Metrics", "Settings" tabs

If you only see 1 service, you need to add the database!

---

## Next Steps

1. Add PostgreSQL database to Railway (see Step 1 above)
2. Wait for it to deploy
3. Run `init_railway_db_local.bat` to create tables
4. Check logs to verify scanner is running

