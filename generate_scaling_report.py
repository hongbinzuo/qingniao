# -*- coding: utf-8 -*-
"""
生成De.滚仓策略详细报告
"""
import sys
sys.path.insert(0, 'src')
from db_manager_trader import TraderDBManager
from datetime import datetime
from pathlib import Path
import duckdb
import re

def generate_scaling_report():
    """生成滚仓策略报告"""
    db = TraderDBManager('de')
    conn = db._get_connection()
    
    # 查询相关对话
    conversations = conn.execute('''
        SELECT id, timestamp, trader_message, user_evaluation, btc_price
        FROM conversations
        WHERE (trader_message LIKE '%876%' OR trader_message LIKE '%818%' 
               OR trader_message LIKE '%888%' OR trader_message LIKE '%883%'
               OR trader_message LIKE '%893%' OR trader_message LIKE '%886%'
               OR trader_message LIKE '%加仓%' OR trader_message LIKE '%减仓%')
        AND timestamp >= '2025-12-31 00:00:00'
        ORDER BY timestamp ASC
    ''').fetchall()
    
    report = []
    report.append("# De.滚仓策略分析报告")
    report.append("")
    report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # 一、对话记录
    report.append("## 一、相关对话记录")
    report.append("")
    
    for conv in conversations:
        msg = conv[2] if len(conv) > 2 else ''
        timestamp = conv[1] if len(conv) > 1 else ''
        btc_price = conv[4] if len(conv) > 4 else None
        evaluation = conv[3] if len(conv) > 3 else None
        
        report.append(f"### {timestamp}")
        report.append("")
        report.append(f"**对话内容**: {msg}")
        report.append("")
        if btc_price:
            report.append(f"**BTC价格**: ${btc_price:,.2f}")
            report.append("")
        if evaluation:
            report.append(f"**用户评价**: {evaluation}")
            report.append("")
    
    # 二、滚仓操作提取
    report.append("## 二、滚仓操作提取")
    report.append("")
    
    # 查找包含具体操作的对话
    main_msg = None
    for conv in conversations:
        msg = conv[2] if len(conv) > 2 else ''
        if '876' in msg and '818' in msg:
            main_msg = msg
            break
    
    if main_msg:
        report.append("### 核心操作序列")
        report.append("")
        
        # 提取价格
        prices = re.findall(r'(\d{3})', main_msg)
        prices = [int(p) for p in prices if 800 <= int(p) <= 1000]
        
        report.append("根据对话内容，De.的滚仓操作序列如下：")
        report.append("")
        
        if 876 in prices:
            report.append("1. **初始入场**: $876")
        if 818 in prices:
            report.append("2. **向下加仓**: 价格跌到 $818 时加仓（降低成本）")
        if 888 in prices and '减仓' in main_msg:
            report.append("3. **止盈减仓**: 价格涨到 $888 时减仓一半（锁定利润）")
        if 883 in prices and '加回' in main_msg:
            report.append("4. **回调加仓**: 价格回调到 $883 时加回1/4（重新入场）")
        
        report.append("")
    
    # 三、滚仓策略分析
    report.append("## 三、滚仓策略分析")
    report.append("")
    
    report.append("### 3.1 策略特点")
    report.append("")
    report.append("#### 1. 向下加仓（降低成本）")
    report.append("")
    report.append("- **操作**: 从 $876 加仓到 $818")
    report.append("- **目的**: 通过向下加仓降低平均持仓成本")
    report.append("- **适用场景**: 趋势向上，但价格出现回调时")
    report.append("")
    
    report.append("#### 2. 分批止盈（锁定利润）")
    report.append("")
    report.append("- **操作**: 价格涨到 $888 时减仓一半")
    report.append("- **目的**: 锁定部分利润，保留部分仓位继续持有")
    report.append("- **仓位管理**: 减仓50%，保留50%")
    report.append("")
    
    report.append("#### 3. 回调加仓（重新入场）")
    report.append("")
    report.append("- **操作**: 价格回调到 $883 时加回1/4")
    report.append("- **目的**: 利用回调机会重新建立仓位")
    report.append("- **仓位管理**: 加回25%，总仓位约75%")
    report.append("")
    
    report.append("#### 4. 灵活操作（手动档）")
    report.append("")
    report.append("- **操作方式**: 看盘手动操作")
    report.append("- **止损策略**: 不固定止损，先突破再看")
    report.append("- **决策依据**: 根据市场实时情况灵活调整")
    report.append("")
    
    report.append("### 3.2 价格区间分析")
    report.append("")
    report.append("| 价格 | 操作 | 目的 |")
    report.append("|------|------|------|")
    report.append("| $876 | 初始入场 | 建立多单仓位 |")
    report.append("| $818 | 向下加仓 | 降低成本 |")
    report.append("| $888 | 减仓一半 | 锁定利润 |")
    report.append("| $883 | 加回1/4 | 重新入场 |")
    report.append("| $893 | 考虑加仓 | 突破加仓 |")
    report.append("| $886 | 止损位 | 风险控制 |")
    report.append("")
    
    report.append("### 3.3 仓位管理")
    report.append("")
    report.append("假设初始仓位为100%：")
    report.append("")
    report.append("1. **初始**: 100% @ $876")
    report.append("2. **加仓后**: 约200% @ 平均成本 $847 (876和818的平均)")
    report.append("3. **减仓后**: 约100% @ 平均成本 $847")
    report.append("4. **加回后**: 约125% @ 平均成本约 $850")
    report.append("")
    
    report.append("### 3.4 盈亏比分析")
    report.append("")
    report.append("- **入场成本**: 约 $850 (加权平均)")
    report.append("- **止盈位**: $888 (已部分止盈)")
    report.append("- **潜在止盈**: $893+ (考虑加仓)")
    report.append("- **止损位**: $886 (如果跌破)")
    report.append("- **盈亏比**: 约 4:1 (从$850到$893 vs 从$850到$886)")
    report.append("")
    
    # 四、结合BTC价格
    report.append("## 四、结合BTC价格分析")
    report.append("")
    
    try:
        ts_file = Path(__file__).parent / "data" / "btc_price_timeseries.duckdb"
        if ts_file.exists():
            price_conn = duckdb.connect(str(ts_file))
            
            # 查询价格数据
            price_data = price_conn.execute('''
                SELECT datetime, open, high, low, close, volume
                FROM btc_price_5m
                WHERE datetime >= '2025-12-31 00:00:00' 
                  AND datetime < '2025-12-31 01:00:00'
                ORDER BY datetime
            ''').fetchall()
            
            if price_data:
                report.append("### 4.1 BTC价格走势（5分钟K线）")
                report.append("")
                report.append("| 时间 | 开盘 | 最高 | 最低 | 收盘 | 成交量 |")
                report.append("|------|------|------|------|------|--------|")
                for row in price_data[:20]:  # 显示前20条
                    dt = row[0] if len(row) > 0 else ''
                    open_p = row[1] if len(row) > 1 else 0
                    high = row[2] if len(row) > 2 else 0
                    low = row[3] if len(row) > 3 else 0
                    close = row[4] if len(row) > 4 else 0
                    vol = row[5] if len(row) > 5 else 0
                    report.append(f"| {dt} | ${open_p:,.0f} | ${high:,.0f} | ${low:,.0f} | ${close:,.0f} | {vol:,.0f} |")
                report.append("")
                
                # 价格区间分析
                prices_only = [row[4] for row in price_data if len(row) > 4]
                if prices_only:
                    min_price = min(prices_only)
                    max_price = max(prices_only)
                    avg_price = sum(prices_only) / len(prices_only)
                    
                    report.append("### 4.2 价格区间统计")
                    report.append("")
                    report.append(f"- **最低价**: ${min_price:,.2f}")
                    report.append(f"- **最高价**: ${max_price:,.2f}")
                    report.append(f"- **平均价**: ${avg_price:,.2f}")
                    report.append(f"- **价格区间**: ${max_price - min_price:,.2f}")
                    report.append("")
            
            price_conn.close()
    except Exception as e:
        report.append(f"⚠️ 无法获取BTC价格数据: {e}")
        report.append("")
    
    # 五、策略总结
    report.append("## 五、策略总结")
    report.append("")
    
    report.append("### 5.1 核心策略")
    report.append("")
    report.append("De.的滚仓策略是一种**动态仓位管理**方法，特点包括：")
    report.append("")
    report.append("1. **趋势跟踪**: 在上升趋势中通过加仓放大收益")
    report.append("2. **成本优化**: 通过向下加仓降低平均成本")
    report.append("3. **利润锁定**: 通过分批止盈锁定部分利润")
    report.append("4. **灵活调整**: 根据市场情况手动调整仓位和止损")
    report.append("")
    
    report.append("### 5.2 适用场景")
    report.append("")
    report.append("- ✅ 明确的上升趋势")
    report.append("- ✅ 价格有回调机会")
    report.append("- ✅ 有足够的时间和精力看盘")
    report.append("- ✅ 能够承受较大的仓位波动")
    report.append("")
    
    report.append("### 5.3 风险提示")
    report.append("")
    report.append("- ⚠️ 需要准确判断趋势方向")
    report.append("- ⚠️ 向下加仓会增加风险，如果趋势反转损失更大")
    report.append("- ⚠️ 需要密切监控市场，及时调整")
    report.append("- ⚠️ 不适合没有时间看盘的交易者")
    report.append("")
    
    report.append("---")
    report.append("")
    report.append(f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    
    # 保存报告
    report_text = '\n'.join(report)
    output_file = Path(__file__).parent / "outputs" / "De滚仓策略分析报告.md"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report_text)
    
    print("=" * 80)
    print("滚仓策略报告已生成")
    print("=" * 80)
    print()
    print(f"报告已保存到: {output_file}")
    print()
    print("报告摘要:")
    print("- 已提取De.的滚仓操作序列")
    print("- 分析了价格区间和仓位管理")
    print("- 结合BTC价格数据")
    print("- 总结了策略特点和风险提示")
    print("=" * 80)
    
    db.close()

if __name__ == '__main__':
    generate_scaling_report()

