# Railway Complete Setup Guide - From Scratch

## Problem: Cannot See Any Service in Railway

This means you haven't deployed your project to Railway yet.

---

## Complete Setup Steps

### Step 1: Create Railway Project

1. Go to https://railway.app
2. Sign in (or create account)
3. Click **"New Project"**
4. Select **"Deploy from GitHub repo"**
5. Click **"Configure GitHub App"** (if first time)
6. Authorize Railway to access your GitHub
7. Select repository: **hongbinzuo/qingniao**
8. Select branch: **abu_system**
9. Click **"Deploy Now"**

Railway will now:
- Create a new project
- Deploy your code
- Show you the service in the dashboard

### Step 2: Add PostgreSQL Database

After your app service appears:

1. In the same project, click **"+ New"**
2. Select **"Database"**
3. Choose **"Add PostgreSQL"**
4. Wait 1-2 minutes for database to deploy

Now you'll see **2 services**:
- Your app (qingniao)
- PostgreSQL database

### Step 3: Configure Environment Variables

Click on your **app service**, go to **"Variables"** tab, add:

```
SCAN_INTERVAL_MINUTES=15
TOP_COINS=10
TIMEFRAMES=5m,15m,1h
SIGNAL_MODES=aggressive,neutral,conservative
```

Note: `DATABASE_URL` is automatically added when you add PostgreSQL.

