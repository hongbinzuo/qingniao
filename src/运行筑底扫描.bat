@echo off
chcp 65001
echo 启动Gate.io币种筑底扫描程序...
echo 扫描前1000个币种，寻找筑底概率^>70%且指标背离的币种
echo.
python gate_scanner_bottom_formation.py
echo.
echo 扫描完成！
pause


