#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新De.的完整交易系统文档
纠正区间宽度的理解，加入周末交易说明
"""

import json
import re
from collections import defaultdict

def parse_json_file(file_path: str) -> list:
    """解析JSON文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data.get('messages', [])

def extract_de_messages(messages: list) -> list:
    """提取De.的消息"""
    de_messages = []
    for msg in messages:
        author = msg.get('author', {})
        if author.get('nickname') == 'De.':
            de_messages.append(msg)
    return de_messages

def analyze_interval_concept(de_messages: list) -> dict:
    """分析De.关于区间的概念"""
    intervals = []
    stop_loss_distances = []
    weekend_mentions = []
    
    for msg in de_messages:
        content = msg.get('content', '')
        
        # 提取价格区间（如106-1074，实际是10600-10740）
        # 匹配模式：106-1074, 1075-1103等
        interval_patterns = [
            r'(\d{3,4})-(\d{3,4})\s*这个区间',
            r'区间.*(\d{3,4})-(\d{3,4})',
            r'在(\d{3,4})-(\d{3,4})\s*区间',
            r'(\d{3,4})-(\d{3,4})\s*区间'
        ]
        
        for pattern in interval_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                try:
                    if match[0] and match[1]:
                        lower = float(match[0])
                        upper = float(match[1])
                        
                        # 判断是否需要乘以100（如106可能是10600的简写）
                        # 如果数字小于1000，可能是简写（如106 = 10600）
                        if lower < 1000:
                            lower = lower * 100
                        if upper < 1000:
                            upper = upper * 100
                        
                        if 1000 <= lower < upper <= 200000:
                            width = upper - lower
                            intervals.append({
                                'lower': lower,
                                'upper': upper,
                                'width': width,
                                'content': content,
                                'timestamp': msg.get('timestamp', '')
                            })
                            break  # 找到一个就跳出
                except:
                    pass
        
        # 提取止损距离
        if '止损' in content and '几百点' in content:
            stop_loss_distances.append({
                'content': content,
                'timestamp': msg.get('timestamp', '')
            })
        
        # 提取周末相关内容
        if any(kw in content for kw in ['周末', '周六', '流动性', '扫掉']):
            if '流动性' in content or '扫掉' in content:
                weekend_mentions.append({
                    'content': content,
                    'timestamp': msg.get('timestamp', '')
                })
    
    return {
        'intervals': intervals,
        'stop_loss_distances': stop_loss_distances,
        'weekend_mentions': weekend_mentions
    }

def generate_final_system(analysis: dict, de_messages: list) -> str:
    """生成最终完整交易系统文档"""
    
    doc = []
    doc.append("=" * 80)
    doc.append("交易员 De. 的完整交易系统 - 最终版（含周末说明）")
    doc.append("=" * 80)
    doc.append("")
    doc.append("本系统适用于：5分钟、15分钟、1小时时间框架")
    doc.append("")
    
    # 一、重要概念澄清
    doc.append("## 一、重要概念澄清")
    doc.append("")
    doc.append("### 区间 vs Vegas通道")
    doc.append("")
    doc.append("**关键理解**：区间 ≠ Vegas通道宽度")
    doc.append("")
    doc.append("**区间（Price Range）**：")
    doc.append("- 定义：价格实际震荡的范围（上沿价格 - 下沿价格）")
    doc.append("- 示例：\"106-1074这个区间\" = 10600-10740，区间宽度 = 140点")
    doc.append("- 确定方法：观察价格在图表上的实际震荡范围")
    doc.append("- 区间宽度：通常几百点（如140点、280点等）")
    doc.append("")
    doc.append("**Vegas通道（EMA144 + EMA169）**：")
    doc.append("- 定义：EMA144和EMA169形成的技术指标通道")
    doc.append("- 作用：用来**识别和确认**区间边界，不是区间本身")
    doc.append("- 关系：区间可能在Vegas通道内，也可能包含Vegas通道")
    doc.append("")
    doc.append("**\"几百点\"的含义**：")
    doc.append("- 通常指**止损距离**：\"找好流动性区域挂单止损一般就几百点\"")
    doc.append("- 不是指Vegas通道宽度")
    doc.append("- 不是指区间宽度（区间宽度可能只有100-300点）")
    doc.append("")
    
    # 二、实际区间案例
    doc.append("## 二、实际区间案例（来自De.的消息）")
    doc.append("")
    if analysis['intervals']:
        for i, interval in enumerate(analysis['intervals'][:10], 1):
            doc.append(f"### 案例 {i}")
            doc.append(f"**区间**: ${interval['lower']:,.0f} - ${interval['upper']:,.0f}")
            doc.append(f"**区间宽度**: {interval['width']:,.0f} 点")
            doc.append(f"**内容**: {interval['content'][:100]}...")
            doc.append(f"**时间**: {interval['timestamp']}")
            doc.append("")
    
    # 三、交易系统概述
    doc.append("## 三、交易系统概述")
    doc.append("")
    doc.append("### 系统类型")
    doc.append("- **交易风格**: 区间震荡剥头皮交易")
    doc.append("- **主要标的**: BTC/USDT")
    doc.append("- **持仓时间**: 短线（几分钟到几小时）")
    doc.append("- **风险等级**: 中等（窄止损，快速进出）")
    doc.append("")
    
    # 四、核心交易规则
    doc.append("## 四、核心交易规则（按步骤执行）")
    doc.append("")
    
    doc.append("### 第一步：市场分析 - 识别震荡区间")
    doc.append("")
    doc.append("**目标**: 识别价格实际震荡区间")
    doc.append("")
    doc.append("**操作步骤**:")
    doc.append("1. 在图表上观察价格的实际震荡范围")
    doc.append("2. 确定区间的上沿（阻力位）和下沿（支撑位）")
    doc.append("3. **区间宽度**：通常是100-500点（BTC价格）")
    doc.append("   - 示例：10600-10740区间，宽度140点")
    doc.append("   - 示例：10750-11030区间，宽度280点")
    doc.append("4. 使用Vegas通道（EMA144/169）**确认**区间边界")
    doc.append("   - Vegas通道用来识别区间，但区间本身是价格的实际震荡范围")
    doc.append("   - 区间可能在Vegas通道内，也可能包含Vegas通道")
    doc.append("5. 使用VWAP进一步确认支撑阻力位置")
    doc.append("6. 确认区间内价格来回震荡，不是单边趋势")
    doc.append("")
    doc.append("**重要**：区间是价格的实际震荡范围，不是Vegas通道的宽度！")
    doc.append("")
    
    doc.append("### 第二步：入场规则")
    doc.append("")
    doc.append("**规则1: 区间挂单法（推荐）**")
    doc.append("")
    doc.append("**多单入场**:")
    doc.append("- 在区间下沿附近挂买单（例如：下沿+10-20点）")
    doc.append("- 等待价格回落到挂单价位自动成交")
    doc.append("- 不要追涨，必须挂单等待")
    doc.append("")
    doc.append("**空单入场**:")
    doc.append("- 在区间上沿附近挂卖单（例如：上沿-10-20点）")
    doc.append("- 等待价格反弹到挂单价位自动成交")
    doc.append("- 不要追跌，必须挂单等待")
    doc.append("")
    doc.append("**规则2: 回踩入场法**")
    doc.append("")
    doc.append("**适用场景**: 价格突破区间后回踩")
    doc.append("- 突破后回踩到618-786斐波那契区间（OTE区间）")
    doc.append("- 回踩时出现假动作（刺破618但未破786）")
    doc.append("- 在回踩位置入场，方向与突破方向一致")
    doc.append("")
    doc.append("**规则3: M顶/W底入场法**")
    doc.append("")
    doc.append("**M顶做空**:")
    doc.append("- 价格形成M顶形态")
    doc.append("- 回踩到M顶的腰线位置")
    doc.append("- 实体K线收在腰线下方，做空")
    doc.append("")
    doc.append("**W底做多**:")
    doc.append("- 价格形成W底形态")
    doc.append("- 反弹到W底的腰线位置")
    doc.append("- 实体K线收在腰线上方，做多")
    doc.append("")
    
    doc.append("### 第三步：止损规则（严格执行）")
    doc.append("")
    doc.append("**止损距离**：")
    doc.append("- **通常几百点**（BTC价格）")
    doc.append("- 示例：\"找好流动性区域挂单止损一般就几百点\"")
    doc.append("- 具体距离：根据区间大小和流动性区域调整")
    doc.append("")
    doc.append("**止损位置设置原则**:")
    doc.append("")
    doc.append("1. **假突破保护原则**")
    doc.append("   - 止损必须设置在假突破不能打到的位置")
    doc.append("   - 例如：区间下沿是10600，止损设在10570（假突破通常不会超过30点）")
    doc.append("")
    doc.append("2. **流动性区域外原则**")
    doc.append("   - 找到流动性区域（大量挂单的位置）")
    doc.append("   - 止损设置在流动性区域之外")
    doc.append("   - 避免被流动性扫止损")
    doc.append("")
    doc.append("3. **止损距离**")
    doc.append("   - 通常为几百点（BTC价格）")
    doc.append("   - 例如：入场价10600，止损10570，止损距离30点")
    doc.append("   - 根据区间大小调整，但不超过区间宽度的10-20%")
    doc.append("")
    doc.append("4. **逐仓模式 + 杠杆计算**")
    doc.append("   - 使用逐仓模式（隔离风险）")
    doc.append("   - 计算杠杆：确保止损线刚好拉到止损位置")
    doc.append("   - 公式：杠杆 = 入场价 / (入场价 - 止损价)")
    doc.append("   - 例如：入场10600，止损10570，杠杆 = 10600/(10600-10570) ≈ 353倍")
    doc.append("   - 但实际使用建议：10-50倍杠杆（更安全）")
    doc.append("")
    
    doc.append("### 第四步：止盈规则")
    doc.append("")
    doc.append("**止盈位置设置**:")
    doc.append("")
    doc.append("1. **区间上下沿止盈（推荐）**")
    doc.append("   - 多单：在区间上沿差一点点的位置止盈（例如：上沿-10点）")
    doc.append("   - 空单：在区间下沿差一点点的位置止盈（例如：下沿+10点）")
    doc.append("   - 不要贪心，接近上下沿就止盈")
    doc.append("")
    doc.append("2. **区间中间止盈**")
    doc.append("   - 如果区间较大，可以在区间中间位置止盈")
    doc.append("   - 例如：区间10600-10740，中间是10670，可以在此止盈")
    doc.append("")
    doc.append("3. **打掉低点/高点止盈**")
    doc.append("   - 剥头皮交易：打掉上一个低点（多单）或高点（空单）就止盈")
    doc.append("   - 快速获利了结，不持仓过久")
    doc.append("")
    doc.append("4. **分批止盈**")
    doc.append("   - 可以分批平仓：50%在目标位置平仓，50%保留")
    doc.append("   - 例如：1052的多单，1074平一半，剩余部分看情况")
    doc.append("")
    
    doc.append("### 第五步：仓位管理")
    doc.append("")
    doc.append("**仓位大小**:")
    doc.append("- 100油账户：每次10-20油")
    doc.append("- 根据账户大小按比例调整")
    doc.append("- 单次交易风险不超过账户的2-5%")
    doc.append("")
    doc.append("**盈亏比要求**:")
    doc.append("- 固定2倍以上盈亏比")
    doc.append("- 例如：止损30点，止盈至少60点")
    doc.append("- 如果盈亏比不足2倍，放弃交易")
    doc.append("")
    
    # 五、指标系统
    doc.append("## 五、指标系统（用于识别和确认区间）")
    doc.append("")
    doc.append("### Vegas通道（EMA144 + EMA169）")
    doc.append("")
    doc.append("**作用**：用来识别和确认区间边界，不是区间本身")
    doc.append("")
    doc.append("**使用方法**：")
    doc.append("1. 在图表上添加EMA144和EMA169")
    doc.append("2. 观察价格在两条均线之间的震荡")
    doc.append("3. **区间**是价格的实际震荡范围，可能在Vegas通道内，也可能包含Vegas通道")
    doc.append("4. 用Vegas通道**确认**区间的上下沿")
    doc.append("")
    doc.append("**重要**：区间宽度 ≠ Vegas通道宽度")
    doc.append("- 区间宽度：价格实际震荡范围（如10600-10740，宽度140点）")
    doc.append("- Vegas通道：EMA144/169形成的技术指标通道（用来识别区间）")
    doc.append("")
    
    doc.append("### VWAP（成交量加权平均价格）")
    doc.append("")
    doc.append("**作用**：确认支撑阻力位置")
    doc.append("")
    doc.append("**使用方法**：")
    doc.append("1. 添加对应时间框架的VWAP")
    doc.append("2. VWAP在区间内 = 作为动态支撑/阻力")
    doc.append("3. VWAP在区间外 = 作为突破确认")
    doc.append("4. 与Vegas通道结合使用，提高准确性")
    doc.append("")
    
    # 六、不同时间框架
    doc.append("## 六、不同时间框架的交易计划")
    doc.append("")
    
    doc.append("### 5分钟时间框架")
    doc.append("")
    doc.append("**适用场景**: 超短线剥头皮")
    doc.append("")
    doc.append("**交易计划**:")
    doc.append("1. 识别5分钟图上的小区间（50-200点）")
    doc.append("2. 使用5分钟Vegas通道确认区间边界")
    doc.append("3. 在区间上下沿挂单")
    doc.append("4. 止损：20-50点（几百点中的较小值）")
    doc.append("5. 止盈：40-100点（2倍盈亏比）")
    doc.append("6. 持仓时间：5-30分钟")
    doc.append("7. 需要看盘，快速进出")
    doc.append("")
    
    doc.append("### 15分钟时间框架（推荐新手）")
    doc.append("")
    doc.append("**适用场景**: 短线区间交易")
    doc.append("")
    doc.append("**交易计划**:")
    doc.append("1. 识别15分钟图上的区间（100-500点）")
    doc.append("2. 使用15分钟Vegas通道确认区间边界")
    doc.append("3. 使用15分钟VWAP确认支撑阻力")
    doc.append("4. 在区间上下沿挂单")
    doc.append("5. 止损：50-100点（几百点）")
    doc.append("6. 止盈：100-200点（2倍盈亏比）")
    doc.append("7. 持仓时间：30分钟-2小时")
    doc.append("8. 可以挂单后不看盘，等待成交")
    doc.append("")
    
    doc.append("### 1小时时间框架")
    doc.append("")
    doc.append("**适用场景**: 中短线区间交易")
    doc.append("")
    doc.append("**交易计划**:")
    doc.append("1. 识别1小时图上的大区间（200-1000点）")
    doc.append("2. 使用1小时Vegas通道确认区间边界")
    doc.append("3. 使用1小时VWAP确认支撑阻力")
    doc.append("4. 在区间上下沿挂单")
    doc.append("5. 止损：100-200点（几百点）")
    doc.append("6. 止盈：200-400点（2倍盈亏比）")
    doc.append("7. 持仓时间：2-8小时")
    doc.append("8. 适合挂单后长时间等待")
    doc.append("")
    
    # 七、周末交易说明
    doc.append("## 七、周末/周六不适合交易的原因")
    doc.append("")
    doc.append("### De.的观点（基于实际消息记录）")
    doc.append("")
    doc.append("**核心原因：流动性不足**")
    doc.append("")
    doc.append("**De.的原话**：")
    if analysis['weekend_mentions']:
        for mention in analysis['weekend_mentions'][:5]:
            doc.append(f"- **{mention['timestamp']}**: \"{mention['content']}\"")
    doc.append("")
    doc.append("### 为什么周末不适合交易？")
    doc.append("")
    doc.append("1. **流动性不足**")
    doc.append("   - 周末全球主要市场（股市、传统金融市场）休市")
    doc.append("   - 机构交易者减少交易活动")
    doc.append("   - 散户交易者也相对减少")
    doc.append("   - 交易量大幅下降")
    doc.append("")
    doc.append("2. **流动性陷阱**")
    doc.append("   - 周末的流动性在周一开盘前容易被\"扫掉\"")
    doc.append("   - 即：周末积累的挂单，在周一开盘时容易被大资金一次性吃掉")
    doc.append("   - 这导致周末挂单的风险增加")
    doc.append("")
    doc.append("3. **系统失效**")
    doc.append("   - De.的区间震荡系统依赖流动性")
    doc.append("   - 周末流动性不足，系统可能失效")
    doc.append("   - 容易出现假突破或假信号")
    doc.append("")
    doc.append("4. **波动异常**")
    doc.append("   - 流动性不足时，价格波动可能异常")
    doc.append("   - 不适合区间震荡交易")
    doc.append("   - 剥头皮交易困难")
    doc.append("")
    doc.append("### 周末交易的风险")
    doc.append("")
    doc.append("- ❌ 挂单难以成交")
    doc.append("- ❌ 容易被大资金扫单")
    doc.append("- ❌ 价格波动异常")
    doc.append("- ❌ 止损可能滑点")
    doc.append("- ❌ 价格跳空风险增加")
    doc.append("")
    doc.append("### 交易时间建议")
    doc.append("")
    doc.append("**适合交易的时间**：")
    doc.append("- ✅ **周一至周五**：流动性充足，适合交易")
    doc.append("- ✅ **工作日交易时段**：机构活跃，流动性好")
    doc.append("")
    doc.append("**不适合交易的时间**：")
    doc.append("- ❌ **周六**：流动性不足")
    doc.append("- ❌ **周末**：流动性不足，开局前都要扫掉")
    doc.append("")
    doc.append("**如果必须在周末交易**：")
    doc.append("- 需要更大的止损")
    doc.append("- 更谨慎的仓位管理")
    doc.append("- 但De.的系统在周末可能失效，**不建议交易**")
    doc.append("")
    
    # 八、实际交易案例
    doc.append("## 八、实际交易案例")
    doc.append("")
    doc.append("### 案例1：106-1074区间")
    doc.append("")
    doc.append("**De.的原话**：\"比如现在在106-1074这个区间，剥头皮就在这个区间上下沿附近挂单，下面止损1057附近，上面1077上面\"")
    doc.append("")
    doc.append("**分析**：")
    doc.append("- 区间：10600-10740（宽度140点）")
    doc.append("- 多单挂单：区间下沿附近（10600+10-20点）")
    doc.append("- 多单止损：10570附近（假突破不能打到）")
    doc.append("- 空单挂单：区间上沿附近（10740-10-20点）")
    doc.append("- 空单止损：10770上面（假突破不能打到）")
    doc.append("")
    doc.append("**注意**：区间宽度是140点，不是Vegas通道宽度")
    doc.append("")
    
    doc.append("### 案例2：1075-1103区间")
    doc.append("")
    doc.append("**De.的原话**：\"下一个区间在1075-1103中线1088，fvg1092-1098\"")
    doc.append("")
    doc.append("**分析**：")
    doc.append("- 区间：10750-11030（宽度280点）")
    doc.append("- 中线：10880（区间中间位置）")
    doc.append("- FVG：10920-10980（Fair Value Gap）")
    doc.append("")
    
    # 九、交易前检查清单
    doc.append("## 九、交易前检查清单")
    doc.append("")
    doc.append("在每次交易前，确认以下所有项目：")
    doc.append("")
    doc.append("□ 1. 已识别明确的震荡区间（价格实际震荡范围）")
    doc.append("□ 2. 区间宽度足够（通常100-500点，根据时间框架调整）")
    doc.append("□ 3. 已使用Vegas通道确认区间边界")
    doc.append("□ 4. 已使用VWAP确认支撑阻力位置")
    doc.append("□ 5. 已确定入场位置（区间上下沿）")
    doc.append("□ 6. 已设置止损（假突破不能打到，通常几百点）")
    doc.append("□ 7. 已设置止盈（2倍以上盈亏比）")
    doc.append("□ 8. 已计算仓位大小（风险不超过5%）")
    doc.append("□ 9. 已使用逐仓模式")
    doc.append("□ 10. 已挂单（不追价）")
    doc.append("□ 11. 确认不是单边行情")
    doc.append("□ 12. 盈亏比≥2倍")
    doc.append("□ 13. **确认不是周末/周六**（流动性充足）")
    doc.append("")
    doc.append("**只有所有项目都确认后，才能执行交易！**")
    doc.append("")
    
    # 十、重要提示
    doc.append("## 十、重要提示与注意事项")
    doc.append("")
    doc.append("### 必须遵守的规则")
    doc.append("")
    doc.append("1. **严格止损**")
    doc.append("   - 止损是生命线，必须严格执行")
    doc.append("   - 不要移动止损，不要心存侥幸")
    doc.append("   - 爆单即止损，使用逐仓模式")
    doc.append("")
    doc.append("2. **单边行情回避**")
    doc.append("   - 遇到单边行情立即止损")
    doc.append("   - 震荡能赚，单边死亏")
    doc.append("   - 如果价格突破区间并站稳，放弃反向交易")
    doc.append("")
    doc.append("3. **区间失效处理**")
    doc.append("   - 震荡区间挂单，越到后面越不灵")
    doc.append("   - 如果区间被突破，撤销挂单")
    doc.append("   - 突破后重新识别新区间")
    doc.append("")
    doc.append("4. **不要追涨杀跌**")
    doc.append("   - 必须挂单等待，不要追价")
    doc.append("   - 挂单价格要合理，不要偏离区间太远")
    doc.append("")
    doc.append("5. **盈亏比不足不交易**")
    doc.append("   - 如果止损和止盈的盈亏比不足2倍，放弃交易")
    doc.append("   - 宁可错过，不要做错")
    doc.append("")
    doc.append("6. **周末不交易**")
    doc.append("   - 周末流动性不足，系统可能失效")
    doc.append("   - 周末的流动性在周一开盘前容易被扫掉")
    doc.append("   - 建议周末休息，等待周一开盘后再交易")
    doc.append("")
    
    return "\n".join(doc)

def main():
    file_path = r"C:\Users\zuoho\Downloads\discord-msg\梦之队 - 梦梦 - 青沐 [1428778462981918951].html"
    
    print("=" * 80)
    print("更新完整交易系统文档")
    print("=" * 80)
    print()
    
    messages = parse_json_file(file_path)
    de_messages = extract_de_messages(messages)
    
    print(f"总消息数: {len(messages)}")
    print(f"De.的消息数: {len(de_messages)}")
    
    analysis = analyze_interval_concept(de_messages)
    print(f"提取的区间案例: {len(analysis['intervals'])}")
    print(f"止损距离提及: {len(analysis['stop_loss_distances'])}")
    print(f"周末相关内容: {len(analysis['weekend_mentions'])}")
    
    system_doc = generate_final_system(analysis, de_messages)
    
    output_file = "De_trading_system_final_complete.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(system_doc)
    
    print()
    print("=" * 80)
    print("完成！")
    print("=" * 80)
    print(f"完整交易系统（最终版）已保存到: {output_file}")
    print()
    print("主要更新：")
    print("  1. 纠正了区间宽度的理解（区间 ≠ Vegas通道宽度）")
    print("  2. 明确了\"几百点\"指的是止损距离")
    print("  3. 加入了周末不适合交易的详细说明")
    print("  4. 加入了实际区间案例")

if __name__ == "__main__":
    main()

