@echo off
REM Sherlock 强势币筛选（Windows）
REM 初始化数据库（若未创建）
py -3 scripts\init_sherlock_db.py
REM 运行扫描（不写库）：
py -3 scripts\sherlock_scan_strong_coins.py --limit 50 --topn 20
REM 如需写库加上 --write-db
REM py -3 scripts\sherlock_scan_strong_coins.py --limit 50 --topn 20 --write-db
echo Done.
