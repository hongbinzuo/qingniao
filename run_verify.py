#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
import sys

result = subprocess.run([sys.executable, 'auto_verify.py'], 
                       capture_output=True, text=True, encoding='utf-8')

# 保存到文件
with open('verification_report.txt', 'w', encoding='utf-8') as f:
    f.write(result.stdout)
    if result.stderr:
        f.write('\n\nErrors:\n')
        f.write(result.stderr)

print('Report saved to verification_report.txt')

# 提取关键指标
lines = result.stdout.split('\n')
for line in lines:
    if any(keyword in line for keyword in ['样本数', '组内', '组间', '分离度', '准确率', '综合得分', '结论']):
        print(line)
