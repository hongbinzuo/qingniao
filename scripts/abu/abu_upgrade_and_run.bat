@echo off
setlocal ENABLEDELAYEDEXPANSION
set SCRIPT_DIR=%~dp0
pushd "%SCRIPT_DIR%\..\.."
set "PY=py -3"
set "ROOT=%SCRIPT_DIR%\..\.."
cd /d "%ROOT%"

echo [1/6] Check Abu DB...
if not exist "src\data\qingniao_abu.duckdb" (
  echo  - Not found. Initializing Abu DB...
  %PY% scripts\abu\init_abu_db.py
  if errorlevel 1 (
    echo  ERROR: init_abu_db failed.
    exit /b 1
  )
)

echo [2/6] Migrate columns (score, symbol, notes)...
%PY% scripts\abu\migrate_abu_add_score.py
if errorlevel 1 (
  echo  WARN: migration returned non-zero code, continue if DB was just created.
)

echo [3/6] Install PDF deps if needed (PyMuPDF)...
%PY% -m pip show pymupdf >NUL 2>&1
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo  - Installing PyMuPDF (this may take a while)...
  %PY% -m pip install pymupdf
) else (
  echo  - PyMuPDF already installed
)
rem Import check (fitz)
%PY% -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('fitz') else 1)"
if errorlevel 1 (
  echo  WARN: PyMuPDF import failed. PDF ingestion may be skipped.
) else (
  echo  - PyMuPDF import OK
)
if errorlevel 1 (
  echo  WARN: install PyMuPDF failed, skip PDF ingestion. You can install later.
)

echo [4/6] Optional: Ingest PDF sampled pages (env PDF_IN and PDF_PAGES)
if not "%PDF_IN%"=="" (
  set PAGES=%PDF_PAGES%
  if "%PAGES%"=="" set PAGES=500
  echo  - Ingesting !PAGES! pages from: %PDF_IN%
  if not exist "%PDF_IN%" (
    echo  ERROR: PDF_IN does not exist: %PDF_IN%
    exit /b 3
  )
  %PY% scripts\pa_ingest_pdf.py --pdf "%PDF_IN%" --max-pages !PAGES!
  if errorlevel 1 (
    echo  WARN: PDF ingestion failed, continue.
  )
  echo  - Building Abu library...
  %PY% scripts\abu\abu_build_library.py
)
if "%PDF_IN%"=="" (
  echo  - PDF_IN not set, skip PDF ingestion.
)

echo [5/6] Run Abu 15m scan (binance -> gate fallback)...
%PY% scripts\pa_scan_15m_top10.py --top 10 --exchange binance --write-db 1
if errorlevel 1 (
  echo  ERROR: Abu scan failed.
  exit /b 2
)

echo [6/6] Start Qingniao BE API on :8090 ...
REM Start in current window; use 'start' to spawn a new one if you prefer
%PY% -m uvicorn scripts.qingniao_be_api:app --host 0.0.0.0 --port 8090

endlocal
