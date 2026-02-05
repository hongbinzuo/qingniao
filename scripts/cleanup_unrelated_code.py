#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理与青鸟系统不相关的遗留代码
"""

import os
import shutil
from pathlib import Path

# 设置UTF-8编码
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 项目根目录
ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"

# 要删除的文件列表（与青鸟系统无关）

# 1. 死叉分析相关
DEATH_CROSS_FILES = [
    "crypto_top200_death_cross_analysis.py",
    "crypto_top200_simple.py",
    "others_death_cross_analysis.py",
    "others_death_cross_complete.py",
    "others_death_cross_simple.py",
    "weekly_death_cross_analysis.py",
    "weekly_death_cross_detailed.py",
    "crypto_kline_analysis.py",
    "quick_kline_test.py",
    "OTHERS死叉分析报告.md",
    "加密货币前200市值死叉分析报告.md",
    "weekly_underwater_death_cross_detailed_report.md",
    "weekly_underwater_death_cross_report.md",
    "运行K线分析.bat",
    "运行K线分析V2.bat",
    "运行OTHERS死叉分析.bat",
    "运行前200市值死叉分析.bat",
    "运行周线死叉分析.bat",
    "运行最终分析.bat",
]

# 2. 特定币种分析（与青鸟系统无关）
SPECIFIC_COIN_FILES = [
    "analyze_fartcoin_leading_indicator.py",
    "analyze_folks_altcoin.py",
    "generate_luna2_trading_signals.py",
    "generate_rave_trading_plan.py",
    "generate_rave_new_listing_short_plan.py",
    "generate_lumia_long_plan.py",
    "generate_bnb_multi_tf_plan.py",
    "generate_bch_15m_auction_plan.py",
    "generate_bch_15m_auction_plan_fixed.py",
    "generate_bch_1h_auction_plan.py",
    "generate_beat_trading_plan.py",
    "analyze_beat_trend.py",
    "analyze_beat_trend_fixed.py",
    "test_beat_data.py",
]

# 3. 工具类文件（可能不相关）
TOOL_FILES = [
    "organize_project_files.py",
    "json_to_word.py",
    "convert_to_pdf.py",
    "convert_to_pdf_v2.py",
    "convert_to_pdf_v3.py",
    "convert_to_pdf_final.py",
    "create_pdf_report.py",
]

# 4. 测试文件（除了test_stop_loss.py，这个可能相关）
TEST_FILES = [
    "simple_crypto_test.py",
    "simple_print_test.py",
    "single_crypto_test.py",
    "test_tensortrade.py",
]

# 5. 临时/输出文件
TEMP_FILES = [
    "analysis_log.txt",
    "scan_output.txt",
    "scenarios_output.txt",
    "运行筑底扫描.bat",
]

# 合并所有要删除的文件
ALL_FILES_TO_DELETE = (
    DEATH_CROSS_FILES +
    SPECIFIC_COIN_FILES +
    TOOL_FILES +
    TEST_FILES +
    TEMP_FILES
)


def delete_files():
    """删除不相关的文件"""
    deleted = []
    not_found = []
    
    print("=" * 70)
    print("清理与青鸟系统不相关的遗留代码")
    print("=" * 70)
    print(f"\n要删除的文件数量: {len(ALL_FILES_TO_DELETE)}")
    print()
    
    # 确认
    response = input("确认删除这些文件? (y/n): ")
    if response.lower() != 'y':
        print("❌ 取消删除")
        return
    
    print("\n开始删除...\n")
    
    for filename in ALL_FILES_TO_DELETE:
        file_path = SRC_DIR / filename
        
        if file_path.exists():
            try:
                file_path.unlink()
                print(f"✅ 删除: {filename}")
                deleted.append(filename)
            except Exception as e:
                print(f"❌ 删除失败 {filename}: {e}")
        else:
            not_found.append(filename)
    
    print("\n" + "=" * 70)
    print("清理完成！")
    print("=" * 70)
    print(f"\n✅ 成功删除: {len(deleted)} 个文件")
    if not_found:
        print(f"⚠️  未找到: {len(not_found)} 个文件")
    
    print("\n建议下一步:")
    print("1. 检查删除的文件是否正确")
    print("2. 运行 git status 查看更改")
    print("3. 提交更改: git add -A && git commit -m 'chore: 清理遗留代码'")


if __name__ == "__main__":
    delete_files()


