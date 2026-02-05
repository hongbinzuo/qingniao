# Railway - Where to Add Database

## Different Railway UI Versions

Railway has updated their UI several times. Here are all the ways to add a database:

---

## Method 1: Canvas View (New UI)

If you see a **canvas/graph view** with your service:

1. Look for a **"+ New"** button (usually top-right)
2. OR right-click on empty space in the canvas
3. OR look for **"Add Service"** button
4. Select **"Database"** → **"PostgreSQL"**

---

## Method 2: List View (Alternative UI)

If you see a **list of services**:

1. Look for **"+ Add Service"** button
2. OR **"New"** dropdown menu
3. Select **"Database"** → **"PostgreSQL"**

---

## Method 3: Project Settings

1. Click on your project name (top-left)
2. Look for **"Settings"** or **"Configure"**
3. Find **"Add Service"** or **"Resources"**
4. Add PostgreSQL

---

## Method 4: Use Railway CLI (Easiest Alternative)

If you can't find the button, use Railway CLI:

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link to your project
railway link

# Add PostgreSQL
railway add --database postgres
```

---

## What to Look For

You should see one of these:
- **"+ New"** button
- **"Add Service"** button  
- **"+"** icon
- Right-click menu with "Add"

---

## Can You Tell Me What You See?

Please describe what you see on your Railway dashboard:
- Do you see your app/service?
- What buttons do you see?
- Is it a canvas view or list view?

This will help me guide you better.

