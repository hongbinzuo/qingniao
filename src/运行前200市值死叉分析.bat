@echo off
chcp 65001
echo 开始运行加密货币前200市值总和（排除BTC和ETH）周线死叉分析程序...
echo.

python crypto_top200_death_cross_analysis.py

echo.
echo 程序执行完毕！
pause




