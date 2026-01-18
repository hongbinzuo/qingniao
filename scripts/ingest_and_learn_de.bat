@echo off
setlocal
cd /d %~dp0\..

rem Optional: scan C:\Users\zuoho\Pictures for IMG_190*.{jpg,jpeg,png,webp} placeholders
py -3 scripts\ingest_screenshots_190x.py

py -3 scripts\flush_pending_conversations.py
py -3 scripts\flush_pending_trades.py
py -3 scripts\run_incremental_learner.py
