#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析De.在12月21-23日的交易策略
结合BTC价格和全网相似策略
"""

import requests
from datetime import datetime, timedelta

def get_btc_price_at_time(target_time_str):
    """获取BTC在特定时间的价格（使用Gate.io API）"""
    try:
        # 获取当前价格作为参考
        url = "https://api.gateio.ws/api/v4/spot/tickers"
        params = {'currency_pair': 'BTC_USDT'}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                current_price = float(data[0]['last'])
                return current_price
    except Exception as e:
        print(f"获取价格失败: {e}")
    return None

# De.的策略分析
de_strategy_analysis = {
    "时间": "2025年12月21-23日",
    "关键概念": {
        "垃圾时间": {
            "定义": "价格在特定区间（885-877）内震荡，没有明确方向",
            "De.的原话": "价格在885-877都是垃圾时间",
            "策略": "等待突破或关键位确认后再入场",
            "相似策略": "Trading Range / Consolidation Zone - 在震荡区间内避免交易，等待突破"
        },
        "FVG (Fair Value Gap)": {
            "定义": "价格快速移动留下的价格缺口，通常是支撑或阻力位",
            "De.的原话": "858-866是个fvg，做多止损放在858下面",
            "策略": "在FVG下方做多，止损放在FVG下方",
            "相似策略": "ICT Fair Value Gap - 价格快速移动后留下的不平衡区域，通常会被回填"
        },
        "Vegas Channel 5分钟": {
            "定义": "5分钟时间框架的EMA144/169通道",
            "De.的原话": "5分钟的vegas了，894，顶不住，我也加入空军队伍",
            "策略": "价格在5分钟Vegas通道上方受阻，做空信号",
            "相似策略": "Vegas Tunnel Strategy - 使用EMA144/169作为动态支撑阻力"
        },
        "多推模式 (Multiple Push)": {
            "定义": "价格多次测试同一位置但无法突破",
            "De.的原话": "一分钟五推，3推5推的逼空，很很难涨",
            "策略": "多次推高但无法突破，是反转信号",
            "相似策略": "Multiple Push Pattern / Exhaustion Pattern - 多次测试阻力位失败，通常是反转信号"
        },
        "双顶/双底": {
            "定义": "价格在同一水平形成两个高点或低点",
            "De.的原话": "8755显然还有一个底做双顶",
            "策略": "双顶确认后做空，双底确认后做多",
            "相似策略": "Double Top/Bottom Pattern - 经典反转形态"
        },
        "M形态": {
            "定义": "价格形成M字形的顶部形态",
            "De.的原话": "左边有M形态且878跌破了上一段8805-896的起涨",
            "策略": "M形态确认后，跌破起涨点，做空信号",
            "相似策略": "M-Top Pattern / Double Top - 顶部反转形态"
        },
        "插针 vs 实体": {
            "定义": "K线的影线（插针）和实体部分",
            "De.的原话": "15分插针跌破，实体收线没破",
            "策略": "插针跌破不算有效突破，实体收线跌破才是",
            "相似策略": "Wick Rejection vs Body Break - 影线测试不算有效突破，实体突破才是"
        },
        "中线DCA策略": {
            "定义": "分批建仓，降低成本",
            "De.的原话": "中线：进头寸866补一单85补一单837补一单，拿到96-99，止损8万以下，或者dca",
            "策略": "在关键支撑位分批建仓，设置止损，目标位96-99",
            "相似策略": "Dollar Cost Averaging (DCA) - 分批建仓策略，降低平均成本"
        },
        "剧本思维": {
            "定义": "提前规划多种可能的走势",
            "De.的原话": "看法1：如果按12.6那个周末的走法...看法2：如果先扫866...",
            "策略": "准备多个剧本，根据实际走势选择",
            "相似策略": "Scenario Planning / Multiple Timeframe Analysis - 多时间框架分析，准备多种可能"
        },
        "保本单": {
            "定义": "将止损移动到入场价，锁定利润",
            "De.的原话": "我单881挂了保本",
            "策略": "盈利后移动止损到入场价，锁定利润",
            "相似策略": "Break-Even Stop Loss - 移动止损到入场价，锁定利润"
        }
    },
    "关键价格位": {
        "支撑位": [866, 858, 837, 8755, 878, 884],
        "阻力位": [892, 894, 896, 906, 913, 926, 940, 960, 990],
        "关键区间": ["885-877", "892-878", "858-866", "894-883-878-886"]
    },
    "交易策略总结": {
        "短线策略": {
            "做多": "在关键支撑位（866, 858, 837）做多，止损放在支撑下方",
            "做空": "在关键阻力位（894, 906）做空，止损放在阻力上方",
            "时间框架": "5分钟、15分钟",
            "止盈": "500-800点"
        },
        "中线策略": {
            "做多": "866/850/837分批建仓，目标96-99，止损8万以下或DCA",
            "时间框架": "日线、4小时",
            "止盈": "96-99（约1000-2000点）"
        },
        "风险管理": {
            "止损": "窄止损，放在关键位下方/上方2-3%",
            "保本": "盈利后移动止损到入场价",
            "仓位": "中线多单持有，短线空单偷偷撸"
        }
    }
}

def generate_strategy_document():
    """生成策略分析文档"""
    doc = []
    doc.append("# De. 交易系统更新（2025年12月21-23日策略分析）")
    doc.append("")
    doc.append(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    doc.append("")
    doc.append("## 一、关键概念解析")
    doc.append("")
    
    for concept, details in de_strategy_analysis["关键概念"].items():
        doc.append(f"### {concept}")
        doc.append("")
        doc.append(f"**定义**: {details['定义']}")
        doc.append("")
        doc.append(f"**De.的原话**: \"{details['De.的原话']}\"")
        doc.append("")
        doc.append(f"**策略**: {details['策略']}")
        doc.append("")
        doc.append(f"**相似策略**: {details['相似策略']}")
        doc.append("")
        doc.append("---")
        doc.append("")
    
    doc.append("## 二、关键价格位分析")
    doc.append("")
    doc.append("### 支撑位（做多关注）")
    for level in sorted(de_strategy_analysis["关键价格位"]["支撑位"], reverse=True):
        doc.append(f"- **${level}**: 关键支撑位")
    doc.append("")
    doc.append("### 阻力位（做空关注）")
    for level in sorted(de_strategy_analysis["关键价格位"]["阻力位"]):
        doc.append(f"- **${level}**: 关键阻力位")
    doc.append("")
    doc.append("### 关键区间")
    for interval in de_strategy_analysis["关键价格位"]["关键区间"]:
        doc.append(f"- **{interval}**: 震荡区间或关键区域")
    doc.append("")
    
    doc.append("## 三、交易策略总结")
    doc.append("")
    doc.append("### 1. 短线策略")
    doc.append("")
    for key, value in de_strategy_analysis["交易策略总结"]["短线策略"].items():
        doc.append(f"**{key}**: {value}")
    doc.append("")
    doc.append("### 2. 中线策略")
    doc.append("")
    for key, value in de_strategy_analysis["交易策略总结"]["中线策略"].items():
        doc.append(f"**{key}**: {value}")
    doc.append("")
    doc.append("### 3. 风险管理")
    doc.append("")
    for key, value in de_strategy_analysis["交易策略总结"]["风险管理"].items():
        doc.append(f"**{key}**: {value}")
    doc.append("")
    
    doc.append("## 四、实战案例分析")
    doc.append("")
    doc.append("### 案例1：12月21日 - 垃圾时间识别")
    doc.append("")
    doc.append("**情况**: 价格在885-877区间震荡")
    doc.append("")
    doc.append("**De.的策略**:")
    doc.append("- 识别为垃圾时间，等待突破")
    doc.append("- 准备两个剧本：突破896做空，或先扫866后上涨")
    doc.append("- 不提前下单，等待确认")
    doc.append("")
    doc.append("**交易指导**:")
    doc.append("- ✅ 在震荡区间内避免交易")
    doc.append("- ✅ 等待价格突破区间边界")
    doc.append("- ✅ 准备多个剧本，根据实际走势选择")
    doc.append("")
    
    doc.append("### 案例2：12月22日 - FVG做多")
    doc.append("")
    doc.append("**情况**: 858-866是FVG，价格在FVG下方")
    doc.append("")
    doc.append("**De.的策略**:")
    doc.append("- 在FVG下方做多")
    doc.append("- 止损放在858下面")
    doc.append("- 目标：500-800点")
    doc.append("")
    doc.append("**交易指导**:")
    doc.append("- ✅ 识别FVG（价格快速移动留下的缺口）")
    doc.append("- ✅ 在FVG下方做多，止损放在FVG下方")
    doc.append("- ✅ 如果FVG被回填，可能继续下跌")
    doc.append("")
    
    doc.append("### 案例3：12月22日 - 5分钟Vegas做空")
    doc.append("")
    doc.append("**情况**: 5分钟Vegas通道在894，价格在通道上方受阻")
    doc.append("")
    doc.append("**De.的策略**:")
    doc.append("- 价格在5分钟Vegas通道上方受阻")
    doc.append("- 加入空军，做空")
    doc.append("- 目标：894-883-878-886")
    doc.append("")
    doc.append("**交易指导**:")
    doc.append("- ✅ 多时间框架确认：5分钟Vegas通道作为短期信号")
    doc.append("- ✅ 价格在通道上方受阻，做空信号")
    doc.append("- ✅ 结合其他技术指标确认")
    doc.append("")
    
    doc.append("### 案例4：12月21-23日 - 中线DCA策略")
    doc.append("")
    doc.append("**情况**: 中线看多，分批建仓")
    doc.append("")
    doc.append("**De.的策略**:")
    doc.append("- 866补一单，850补一单，837补一单")
    doc.append("- 目标：96-99")
    doc.append("- 止损：8万以下，或DCA")
    doc.append("")
    doc.append("**交易指导**:")
    doc.append("- ✅ 在关键支撑位分批建仓")
    doc.append("- ✅ 降低平均成本")
    doc.append("- ✅ 设置止损或使用DCA策略")
    doc.append("- ✅ 目标位要足够远，保证盈亏比")
    doc.append("")
    
    doc.append("## 五、新增交易规则")
    doc.append("")
    doc.append("### 1. 垃圾时间规则")
    doc.append("")
    doc.append("- **识别**: 价格在特定区间内反复震荡，没有明确方向")
    doc.append("- **策略**: 避免在垃圾时间内交易，等待突破")
    doc.append("- **确认**: 价格突破区间边界，或出现明确的趋势信号")
    doc.append("")
    
    doc.append("### 2. FVG交易规则")
    doc.append("")
    doc.append("- **识别**: 价格快速移动留下的价格缺口（通常3根K线）")
    doc.append("- **做多**: 在FVG下方做多，止损放在FVG下方")
    doc.append("- **做空**: 在FVG上方做空，止损放在FVG上方")
    doc.append("- **确认**: FVG通常会被回填，如果回填失败，可能继续原趋势")
    doc.append("")
    
    doc.append("### 3. 多推模式规则")
    doc.append("")
    doc.append("- **识别**: 价格多次（3-5次）测试同一位置但无法突破")
    doc.append("- **策略**: 多次推高但无法突破，是反转信号")
    doc.append("- **确认**: 出现看跌/看涨K线信号，成交量萎缩")
    doc.append("")
    
    doc.append("### 4. 插针 vs 实体规则")
    doc.append("")
    doc.append("- **插针**: K线的影线部分，不算有效突破")
    doc.append("- **实体**: K线的实体部分，有效突破需要实体收线")
    doc.append("- **策略**: 插针跌破不算有效突破，实体收线跌破才是")
    doc.append("")
    
    doc.append("### 5. 多时间框架Vegas规则")
    doc.append("")
    doc.append("- **5分钟Vegas**: 短期信号，快速反应")
    doc.append("- **15分钟Vegas**: 中期信号，主要参考")
    doc.append("- **1小时Vegas**: 长期信号，确认方向")
    doc.append("- **策略**: 多时间框架确认，提高胜率")
    doc.append("")
    
    doc.append("### 6. 中线DCA规则")
    doc.append("")
    doc.append("- **分批建仓**: 在关键支撑位分批建仓（3-5个位置）")
    doc.append("- **止损**: 设置止损或使用DCA策略")
    doc.append("- **目标**: 目标位要足够远，保证盈亏比≥3:1")
    doc.append("- **时间**: 中线持仓，不频繁交易")
    doc.append("")
    
    doc.append("### 7. 保本单规则")
    doc.append("")
    doc.append("- **时机**: 盈利后（通常500点以上）")
    doc.append("- **策略**: 移动止损到入场价，锁定利润")
    doc.append("- **优势**: 即使价格反转，也能保本退出")
    doc.append("")
    
    doc.append("### 8. 剧本思维规则")
    doc.append("")
    doc.append("- **准备**: 提前规划多种可能的走势（2-3个剧本）")
    doc.append("- **执行**: 根据实际走势选择对应的剧本")
    doc.append("- **调整**: 如果实际走势不符合任何剧本，等待或退出")
    doc.append("")
    
    doc.append("## 六、交易检查清单（更新）")
    doc.append("")
    doc.append("**入场前检查**:")
    doc.append("□ 1. 是否在垃圾时间内？（如果是，等待突破）")
    doc.append("□ 2. 是否有FVG机会？（识别价格缺口）")
    doc.append("□ 3. 是否出现多推模式？（3-5次测试同一位置）")
    doc.append("□ 4. 插针还是实体突破？（实体收线才算有效）")
    doc.append("□ 5. 多时间框架Vegas是否确认？（5分钟、15分钟、1小时）")
    doc.append("□ 6. 是否有明确的支撑/阻力位？")
    doc.append("□ 7. 是否准备了多个剧本？")
    doc.append("")
    doc.append("**风险管理检查**:")
    doc.append("□ 8. 已设置止损（窄止损，关键位下方/上方2-3%）")
    doc.append("□ 9. 是否使用DCA策略？（中线交易）")
    doc.append("□ 10. 盈利后是否移动止损到保本？")
    doc.append("□ 11. 仓位大小已计算（风险2-3%）")
    doc.append("□ 12. 盈亏比≥2:1（短线）或≥3:1（中线）")
    doc.append("")
    
    doc.append("## 七、重要提醒")
    doc.append("")
    doc.append("1. **垃圾时间避免交易**: 在震荡区间内避免交易，等待突破")
    doc.append("2. **FVG是强信号**: 价格快速移动留下的缺口，通常是支撑/阻力")
    doc.append("3. **多推模式是反转信号**: 多次测试同一位置但无法突破，通常是反转")
    doc.append("4. **实体突破才有效**: 插针测试不算有效突破，实体收线才算")
    doc.append("5. **多时间框架确认**: 使用5分钟、15分钟、1小时Vegas通道确认")
    doc.append("6. **中线DCA策略**: 在关键支撑位分批建仓，降低平均成本")
    doc.append("7. **保本单锁定利润**: 盈利后移动止损到入场价，锁定利润")
    doc.append("8. **剧本思维**: 提前规划多种可能的走势，根据实际走势选择")
    doc.append("")
    doc.append("---")
    doc.append("")
    doc.append("**免责声明**: 本分析基于De.的实际交易记录，仅供参考。交易有风险，入市需谨慎。")
    
    return "\n".join(doc)

if __name__ == '__main__':
    doc = generate_strategy_document()
    
    # 保存文档
    filename = "De_trading_system_update_20251221_23.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(doc)
    
    print("=" * 80)
    print("De. 交易系统更新分析")
    print("=" * 80)
    print()
    print(f"文档已保存到: {filename}")
    print()
    try:
        print(doc)
    except UnicodeEncodeError:
        print("文档已生成，请查看文件内容")

