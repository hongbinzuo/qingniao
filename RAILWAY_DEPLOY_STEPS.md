# Railway Deployment - Complete Step-by-Step Guide

## You Need to Deploy Your Project First

Since you cannot see any services, you haven't deployed to Railway yet.

---

## Step-by-Step Instructions

### Step 1: Go to Railway and Create Project

1. Open browser and go to: **https://railway.app**
2. Sign in (or create a free account)
3. Click the **"New Project"** button (big purple button)

### Step 2: Connect Your GitHub Repository

4. Select **"Deploy from GitHub repo"**
5. If first time: Click **"Configure GitHub App"**
   - Authorize Railway to access your GitHub
   - Select which repositories Railway can access
   - Choose: **hongbinzuo/qingniao** (or "All repositories")
6. After authorization, you'll see your repositories
7. Click on **"hongbinzuo/qingniao"**
8. Select branch: **abu_system**

### Step 3: Railway Starts Deploying

Railway will now:
- Create a new project
- Start building your code
- Show build logs
- Deploy the service

**Wait 2-5 minutes** for the first deployment to complete.

You should now see **1 service** in your Railway dashboard (your app).

---

## Next: Add Database (After App Deploys)

Once you see your app service:

1. Click **"+ New"** button in the same project
2. Select **"Database"**  
3. Choose **"Add PostgreSQL"**
4. Wait 1-2 minutes

Now you'll have **2 services**:
- qingniao (your app)
- PostgreSQL (database)

---

## Then: Initialize Database

After both services are running:

1. Click on your **app service**
2. Go to **"Variables"** tab
3. Copy the `DATABASE_URL` value
4. On your computer, run: `init_railway_db_local.bat`
5. Paste the DATABASE_URL when prompted

Done! Your scanner will be running 24/7.

---

## Important Notes

- **First deployment takes 3-5 minutes** (installing dependencies)
- **Subsequent deployments are faster** (1-2 minutes)
- **Railway auto-deploys** when you push to GitHub
- **Free trial available** - then $5/month Hobby plan

---

## What You Should See

After Step 3, your Railway dashboard should show:
```
Project: qingniao
├── Service: qingniao (your app) ✓ Running
└── (Add database next)
```

After adding database:
```
Project: qingniao
├── Service: qingniao (your app) ✓ Running
└── Service: PostgreSQL ✓ Running
```

---

## Troubleshooting

**Q: I don't see "Deploy from GitHub repo" option**
A: Make sure you're signed in to Railway first.

**Q: I don't see my repository**
A: Click "Configure GitHub App" and authorize Railway.

**Q: Build failed**
A: Check the build logs - the fixes we pushed should resolve this.

**Q: Where is the "+ New" button?**
A: It's in your project view, usually top-right or in the project canvas.

