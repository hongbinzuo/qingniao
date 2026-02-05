# Easy Way: Add PostgreSQL Using Railway CLI

## Why Use CLI?

The Railway web UI changes frequently and buttons are hard to find. The CLI is simpler and always works.

---

## Step 1: Install Railway CLI

Open Command Prompt and run:

```bash
npm i -g @railway/cli
```

If you don't have npm, install Node.js first from: https://nodejs.org

---

## Step 2: Login to Railway

```bash
railway login
```

This will open your browser to authenticate.

---

## Step 3: Link Your Project

Navigate to your project folder:

```bash
cd C:\Users\zuoho\code\qingniao
railway link
```

Select your Railway project from the list.

---

## Step 4: Add PostgreSQL

```bash
railway add
```

Select "PostgreSQL" from the menu.

Done! Railway will create the database and set DATABASE_URL automatically.

---

## Step 5: Initialize Database

After PostgreSQL is added, run:

```bash
railway run python scripts/init_railway_db.py
```

This runs the init script using Railway's environment (DATABASE_URL).

---

## All Commands in Order

```bash
npm i -g @railway/cli
railway login
cd C:\Users\zuoho\code\qingniao
railway link
railway add
# Select PostgreSQL
railway run python scripts/init_railway_db.py
```

Done! Your scanner is now running with database.

