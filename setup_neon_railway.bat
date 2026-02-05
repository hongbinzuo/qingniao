@echo off
echo ========================================
echo Railway + Neon PostgreSQL Setup
echo ========================================
echo.
echo Step 1: Get your Neon DATABASE_URL
echo.
echo Go to: https://neon.tech
echo 1. Sign in to your Neon account
echo 2. Open your project (abu-scanner or similar)
echo 3. Click "Connection Details"
echo 4. Copy the connection string
echo.
echo It looks like:
echo postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
echo.
set /p NEON_URL="Paste your Neon DATABASE_URL here: "
echo.
echo Step 2: Adding DATABASE_URL to Railway...
railway variables --set DATABASE_URL="%NEON_URL%"
echo.
echo Step 3: Initializing database schema...
railway run python scripts/init_railway_db.py
echo.
echo ========================================
echo Setup Complete!
echo ========================================
pause
