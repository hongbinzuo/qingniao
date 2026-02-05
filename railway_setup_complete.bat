@echo off
echo Waiting for Railway PostgreSQL to be added...
echo.
echo Please add PostgreSQL in Railway web dashboard:
echo 1. Go to: https://railway.app/project/bc8eaba3-858a-44ff-b5b5-d81b76ff4d26
echo 2. Click "+ New" or "+" button
echo 3. Select "Database" -^> "PostgreSQL"
echo.
echo Press any key after you've added PostgreSQL...
pause >nul

echo.
echo Checking for DATABASE_URL...
railway variables | findstr DATABASE_URL >nul
if errorlevel 1 (
    echo ERROR: DATABASE_URL not found. Please make sure PostgreSQL is added.
    pause
    exit /b 1
)

echo.
echo DATABASE_URL found! Initializing database...
railway run python scripts/init_railway_db.py

echo.
echo Done! Your scanner should now be running.
pause
