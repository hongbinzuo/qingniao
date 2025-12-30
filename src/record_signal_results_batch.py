#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量录入信号结果到系统学习
"""

import sys
from pathlib import Path
from datetime import datetime

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

try:
    from record_missed_signal import record_missed_signal
    from record_completed_signal import record_completed_signal
except ImportError as e:
    print(f"导入失败: {e}", file=sys.stderr)
    print("请确保在src目录下运行此脚本", file=sys.stderr)
    sys.exit(1)


def main():
    """主函数 - 录入3个信号的结果"""
    print("=" * 80)
    print("批量录入信号结果到系统学习")
    print("=" * 80)
    print()
    
    # 信号1：5分钟做多 - 没有入场，止盈先到（信号无效）
    print("📝 录入信号1：5分钟做多（未接到）...")
    signal1_id = record_missed_signal(
        system_name='de',
        timeframe='5分钟',
        signal_type='long',
        entry=88093,
        stop_loss=87800,
        take_profit_1=89531,
        take_profit_2=90250,
        entry_model='反转形态-三重底',
        strength='strong',
        reason='识别到三重底形态',
        generated_time='2025-12-29 10:55:44',
        current_price_at_generation=89245.90,
        actual_price_movement='价格直接上涨，未回调到入场价$88,093，止盈位$89,531和$90,250先到达',
        why_missed='入场价设置过低，价格未回调到入场价，止盈先到，信号无效'
    )
    print()
    
    # 信号2：15分钟做多 - 顺利入场，2个止盈都到达
    print("📝 录入信号2：15分钟做多（成功）...")
    signal2_id = record_completed_signal(
        system_name='de',
        timeframe='15分钟',
        signal_type='long',
        entry=89335,
        stop_loss=89067,
        take_profit_1=89465,
        take_profit_2=89600,
        entry_model='区间突破',
        strength='strong',
        reason='价格突破区间上沿，顺利入场，2个止盈都到达，但止盈可以宽一点',
        generated_time='2025-12-29 10:55:44',
        entry_time='2025-12-29 10:55:44',
        completion_time='2025-12-29 12:00:00',
        max_profit_pct=0.30  # (89600 - 89335) / 89335 * 100
    )
    print()
    
    # 信号3：1小时做空 - 顺利入场，2个止盈都到达
    print("📝 录入信号3：1小时做空（成功）...")
    signal3_id = record_completed_signal(
        system_name='de',
        timeframe='1小时',
        signal_type='short',
        entry=89090,
        stop_loss=91054,
        take_profit_1=88353,
        take_profit_2=87461,
        entry_model='阻力位回落',
        strength='medium',
        reason='价格接近阻力位，可能回落，顺利入场，2个止盈都到达',
        generated_time='2025-12-29 10:55:44',
        entry_time='2025-12-29 10:55:44',
        completion_time='2025-12-29 14:00:00',
        max_profit_pct=1.84  # (89090 - 87461) / 89090 * 100
    )
    print()
    
    print("=" * 80)
    print("✅ 所有信号已成功录入！")
    print("=" * 80)
    print()
    print("📊 录入统计:")
    print(f"   - 信号1（5分钟做多）: 错过（方向正确但未接到）")
    print(f"   - 信号2（15分钟做多）: 成功（全部止盈）")
    print(f"   - 信号3（1小时做空）: 成功（全部止盈）")
    print()
    print("💡 提示: 可以运行以下命令训练/更新机器学习模型:")
    print("   python src/train_ml_model.py")
    print("=" * 80)


if __name__ == "__main__":
    main()

