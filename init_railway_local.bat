@echo off
echo Railway Database Initialization
echo ================================
echo.
echo Please get your DATABASE_URL from Railway:
echo 1. Go to Railway Dashboard
echo 2. Click on PostgreSQL database
echo 3. Click "Connect" tab
echo 4. Copy "Postgres Connection URL"
echo.
set /p DATABASE_URL="Paste DATABASE_URL here: "
echo.
echo Initializing database...
python scripts/init_railway_db.py
pause
