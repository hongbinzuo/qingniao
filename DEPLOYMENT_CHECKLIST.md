# Railway Deployment Checklist

## ✓ Files Verified for Deployment

### Core Application Files
- ✓ `scripts/railway_scanner_service.py` - Main scanner service
- ✓ `scripts/pa_scan_main.py` - Pattern scanner
- ✓ `scripts/init_railway_db.py` - Database initialization
- ✓ `Procfile` - Railway process configuration
- ✓ `requirements.txt` - Python dependencies
- ✓ `railway.toml` - Railway build configuration
- ✓ `nixpacks.toml` - TA-Lib system dependency

### Source Code (45 files)
- ✓ `src/abu/*.py` - All 45 Abu modules tracked in git
- ✓ `src/db_manager_trader.py` - Database manager
- ✓ `src/__init__.py` - Package initialization

### Configuration Files (13 files)
- ✓ `config/brooks_pattern_constraints.yaml` - Pattern rules
- ✓ `config/abu_best_practices.yaml` - Trading rules
- ✓ `config/abu_pattern_weights.yaml` - Pattern weights
- ✓ `config/logging_config.json` - Logging configuration
- ✓ All other config files

### Vector Files (CRITICAL - Now Included!)
- ✓ `data/vectors/brooks_patterns_32d.ann` (369KB) - Pattern vectors
- ✓ `data/vectors/brooks_patterns_id_map.json` (14KB) - Pattern IDs

### Documentation
- ✓ `RAILWAY_NEON_DEPLOYMENT.md` - Deployment guide
- ✓ `RAILWAY_DEPLOYMENT_GUIDE.md` - Alternative guide
- ✓ `.env.railway.example` - Environment template

---

## Dependencies Verification

### Python Packages (requirements.txt)
- ✓ `psycopg2-binary` - PostgreSQL driver
- ✓ `annoy` - Vector similarity search
- ✓ `numpy`, `pandas` - Data processing
- ✓ `requests` - HTTP client
- ✓ `python-dotenv` - Environment variables
- ✓ `scikit-learn`, `xgboost` - ML models
- ✓ `TA-Lib` - Technical analysis

### System Dependencies (nixpacks.toml)
- ✓ `ta-lib` - TA-Lib C library

---

## What Gets Deployed to Railway

When you deploy from GitHub, Railway will include:

1. **All tracked files in git** (use `git ls-files` to see)
2. **Installed dependencies** from requirements.txt
3. **System packages** from nixpacks.toml

### Files NOT Deployed (Excluded by .gitignore)
- ❌ Local database files (*.db, *.duckdb)
- ❌ Output files (outputs/, logs/)
- ❌ Python cache (__pycache__/)
- ❌ Environment files (.env)
- ❌ Temporary files

---

## Pre-Deployment Verification

Run these commands to verify everything is ready:

```bash
# 1. Check vector files are in git
git ls-files | grep "data/vectors"
# Should show:
#   data/vectors/brooks_patterns_32d.ann
#   data/vectors/brooks_patterns_id_map.json

# 2. Check abu modules are in git
git ls-files | grep "src/abu" | wc -l
# Should show: 45

# 3. Check config files are in git
git ls-files | grep "config/" | wc -l
# Should show: 13

# 4. Verify requirements.txt exists
cat requirements.txt | grep -E "psycopg2|annoy|TA-Lib"
# Should show all three packages
```

---

## Deployment Size

Total deployment size: ~5-10 MB
- Source code: ~2 MB
- Vector files: ~370 KB
- Config files: ~10 KB
- Dependencies installed by Railway: ~100-200 MB

---

## Post-Deployment Verification

After deploying to Railway, verify in logs:

```
✓ RAILWAY SCANNER SERVICE STARTED
✓ Signal Thresholds displayed
✓ Scan cycles starting
✓ No "ModuleNotFoundError" errors
✓ No "FileNotFoundError" for vector files
```

---

## Summary

✅ **All required files are now in git and will be deployed**
✅ **Vector files added (critical fix)**
✅ **All dependencies specified**
✅ **Configuration files tracked**
✅ **Ready for Railway deployment**


