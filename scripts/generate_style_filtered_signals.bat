@echo off
chcp 65001 >nul
python scripts\generate_style_filtered_signals.py %*

