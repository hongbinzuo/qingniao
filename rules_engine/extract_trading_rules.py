#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深入提取De.的交易系统规则
生成可执行的交易计划指南
"""

import json
import re
from collections import defaultdict, Counter
from typing import List, Dict

def parse_json_file(file_path: str) -> List[Dict]:
    """解析JSON文件"""
    print("正在读取文件...")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data.get('messages', [])

def extract_de_messages(messages: List[Dict]) -> List[Dict]:
    """提取De.的消息"""
    de_messages = []
    for msg in messages:
        author = msg.get('author', {})
        if author.get('nickname') == 'De.':
            de_messages.append(msg)
    return de_messages

def extract_trading_rules(de_messages: List[Dict]) -> Dict:
    """提取交易规则"""
    print("正在提取交易规则...")
    
    rules = {
        'entry_rules': [],      # 入场规则
        'stop_loss_rules': [],  # 止损规则
        'take_profit_rules': [], # 止盈规则
        'position_sizing': [],   # 仓位管理
        'risk_management': [],   # 风险管理
        'timeframe_rules': [],   # 时间框架规则
        'price_levels': [],      # 价格水平
        'examples': []           # 实际案例
    }
    
    for msg in de_messages:
        content = msg.get('content', '')
        timestamp = msg.get('timestamp', '')
        
        if not content or len(content) < 10:
            continue
        
        # 提取入场规则
        if any(kw in content for kw in ['挂单', '开', '做多', '做空', '多单', '空单', '入场', '进场']):
            if '区间' in content or '回踩' in content or '突破' in content:
                rules['entry_rules'].append({
                    'content': content,
                    'timestamp': timestamp
                })
        
        # 提取止损规则
        if '止损' in content:
            rules['stop_loss_rules'].append({
                'content': content,
                'timestamp': timestamp
            })
        
        # 提取止盈规则
        if '止盈' in content:
            rules['take_profit_rules'].append({
                'content': content,
                'timestamp': timestamp
            })
        
        # 提取仓位管理
        if any(kw in content for kw in ['仓位', '杠杆', '盈亏比', '逐仓', '10-20', '100油']):
            rules['position_sizing'].append({
                'content': content,
                'timestamp': timestamp
            })
        
        # 提取风险管理
        if any(kw in content for kw in ['风险', '爆单', '止损', '保护']):
            rules['risk_management'].append({
                'content': content,
                'timestamp': timestamp
            })
        
        # 提取时间框架相关
        if any(kw in content for kw in ['5分钟', '15分钟', '1小时', '1h', '15m', '5m', '小时', '分钟']):
            rules['timeframe_rules'].append({
                'content': content,
                'timestamp': timestamp
            })
        
        # 提取价格水平
        prices = re.findall(r'\b(\d{4,5})\b', content)
        if prices and any(kw in content for kw in ['区间', '挂单', '止损', '止盈']):
            valid_prices = [float(p) for p in prices if 1000 <= float(p) <= 200000]
            if valid_prices:
                rules['price_levels'].append({
                    'content': content,
                    'timestamp': timestamp,
                    'prices': valid_prices
                })
        
        # 提取实际交易案例
        if any(kw in content for kw in ['我', '1052', '1074', '1064', '1060', '1057']):
            if any(kw in content for kw in ['多单', '空单', '平', '开']):
                rules['examples'].append({
                    'content': content,
                    'timestamp': timestamp
                })
    
    return rules

def analyze_rules(rules: Dict) -> Dict:
    """分析并总结规则"""
    print("正在分析规则...")
    
    # 分析入场规则
    entry_patterns = []
    for rule in rules['entry_rules']:
        content = rule['content']
        if '区间' in content and '挂单' in content:
            entry_patterns.append('区间挂单')
        if '回踩' in content:
            entry_patterns.append('回踩入场')
        if '突破' in content:
            entry_patterns.append('突破入场')
        if '618' in content or '786' in content:
            entry_patterns.append('斐波那契回撤')
    
    # 分析止损规则
    stop_loss_patterns = []
    for rule in rules['stop_loss_rules']:
        content = rule['content']
        if '假突破' in content:
            stop_loss_patterns.append('假突破之外')
        if '流动性' in content:
            stop_loss_patterns.append('流动性区域外')
        if '几百点' in content:
            stop_loss_patterns.append('几百点止损')
        if '爆单' in content:
            stop_loss_patterns.append('爆单即止损')
    
    # 分析止盈规则
    take_profit_patterns = []
    for rule in rules['take_profit_rules']:
        content = rule['content']
        if '上下沿' in content:
            take_profit_patterns.append('区间上下沿')
        if '中间' in content:
            take_profit_patterns.append('区间中间')
        if '低点' in content:
            take_profit_patterns.append('打掉低点')
    
    return {
        'entry_patterns': Counter(entry_patterns),
        'stop_loss_patterns': Counter(stop_loss_patterns),
        'take_profit_patterns': Counter(take_profit_patterns),
        'total_rules': {
            'entry': len(rules['entry_rules']),
            'stop_loss': len(rules['stop_loss_rules']),
            'take_profit': len(rules['take_profit_rules']),
            'position': len(rules['position_sizing']),
            'risk': len(rules['risk_management']),
            'examples': len(rules['examples'])
        }
    }

def generate_trading_system(rules: Dict, analysis: Dict) -> str:
    """生成交易系统文档"""
    print("正在生成交易系统文档...")
    
    doc = []
    doc.append("=" * 80)
    doc.append("交易员 De. 的交易系统 - 完整规则指南")
    doc.append("=" * 80)
    doc.append("")
    doc.append("本系统适用于：5分钟、15分钟、1小时时间框架")
    doc.append("")
    
    # 一、系统概述
    doc.append("## 一、交易系统概述")
    doc.append("")
    doc.append("### 系统类型")
    doc.append("- **交易风格**: 区间震荡剥头皮交易")
    doc.append("- **主要标的**: BTC/USDT")
    doc.append("- **持仓时间**: 短线（几分钟到几小时）")
    doc.append("- **风险等级**: 中等（窄止损，快速进出）")
    doc.append("")
    
    # 二、核心交易规则
    doc.append("## 二、核心交易规则（按步骤执行）")
    doc.append("")
    
    # 2.1 市场分析
    doc.append("### 第一步：市场分析")
    doc.append("")
    doc.append("**目标**: 识别震荡区间")
    doc.append("")
    doc.append("**操作步骤**:")
    doc.append("1. 在图表上找到明显的价格震荡区间")
    doc.append("2. 确定区间的上沿（阻力位）和下沿（支撑位）")
    doc.append("3. 区间宽度建议：至少200-500点（BTC价格）")
    doc.append("4. 确认区间内价格来回震荡，不是单边趋势")
    doc.append("")
    doc.append("**示例**:")
    doc.append("- 如果BTC在10600-10740之间震荡，这就是一个交易区间")
    doc.append("- 上沿：10740，下沿：10600")
    doc.append("")
    
    # 2.2 入场规则
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
    
    # 2.3 止损规则
    doc.append("### 第三步：止损规则（严格执行）")
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
    doc.append("   - 根据区间大小调整，但不超过区间宽度的10%")
    doc.append("")
    doc.append("4. **逐仓模式 + 杠杆计算**")
    doc.append("   - 使用逐仓模式（隔离风险）")
    doc.append("   - 计算杠杆：确保止损线刚好拉到止损位置")
    doc.append("   - 公式：杠杆 = 入场价 / (入场价 - 止损价)")
    doc.append("   - 例如：入场10600，止损10570，杠杆 = 10600/(10600-10570) ≈ 353倍")
    doc.append("   - 但实际使用建议：10-50倍杠杆（更安全）")
    doc.append("")
    
    # 2.4 止盈规则
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
    
    # 2.5 仓位管理
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
    
    # 三、不同时间框架的适用性
    doc.append("## 三、不同时间框架的交易计划")
    doc.append("")
    
    doc.append("### 5分钟时间框架")
    doc.append("")
    doc.append("**适用场景**: 超短线剥头皮")
    doc.append("")
    doc.append("**交易计划**:")
    doc.append("1. 识别5分钟图上的小区间（50-200点）")
    doc.append("2. 在区间上下沿挂单")
    doc.append("3. 止损：20-50点")
    doc.append("4. 止盈：40-100点（2倍盈亏比）")
    doc.append("5. 持仓时间：5-30分钟")
    doc.append("6. 需要看盘，快速进出")
    doc.append("")
    doc.append("**注意事项**:")
    doc.append("- 5分钟波动大，需要快速反应")
    doc.append("- 不适合不看盘的时候挂单")
    doc.append("- 建议在活跃交易时段使用")
    doc.append("")
    
    doc.append("### 15分钟时间框架")
    doc.append("")
    doc.append("**适用场景**: 短线区间交易（推荐）")
    doc.append("")
    doc.append("**交易计划**:")
    doc.append("1. 识别15分钟图上的区间（200-500点）")
    doc.append("2. 在区间上下沿挂单")
    doc.append("3. 止损：50-100点")
    doc.append("4. 止盈：100-200点（2倍盈亏比）")
    doc.append("5. 持仓时间：30分钟-2小时")
    doc.append("6. 可以挂单后不看盘，等待成交")
    doc.append("")
    doc.append("**注意事项**:")
    doc.append("- 15分钟是最平衡的时间框架")
    doc.append("- 区间相对稳定，适合挂单交易")
    doc.append("- 建议新手从这个时间框架开始")
    doc.append("")
    
    doc.append("### 1小时时间框架")
    doc.append("")
    doc.append("**适用场景**: 中短线区间交易")
    doc.append("")
    doc.append("**交易计划**:")
    doc.append("1. 识别1小时图上的大区间（500-1000点）")
    doc.append("2. 在区间上下沿挂单")
    doc.append("3. 止损：100-200点")
    doc.append("4. 止盈：200-400点（2倍盈亏比）")
    doc.append("5. 持仓时间：2-8小时")
    doc.append("6. 适合挂单后长时间等待")
    doc.append("")
    doc.append("**注意事项**:")
    doc.append("- 1小时区间更稳定，但持仓时间更长")
    doc.append("- 适合不能经常看盘的交易者")
    doc.append("- 需要更大的资金来承受波动")
    doc.append("")
    
    # 四、实际交易案例
    doc.append("## 四、实际交易案例")
    doc.append("")
    
    # 提取实际案例
    examples = rules['examples'][:10]
    for i, example in enumerate(examples, 1):
        doc.append(f"### 案例 {i}")
        doc.append(f"**时间**: {example['timestamp']}")
        doc.append(f"**内容**: {example['content']}")
        doc.append("")
    
    # 五、风险提示
    doc.append("## 五、风险提示与注意事项")
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
    
    # 六、交易检查清单
    doc.append("## 六、交易前检查清单")
    doc.append("")
    doc.append("在每次交易前，确认以下所有项目：")
    doc.append("")
    doc.append("□ 1. 已识别明确的震荡区间")
    doc.append("□ 2. 区间宽度足够（至少200点）")
    doc.append("□ 3. 已确定入场位置（区间上下沿）")
    doc.append("□ 4. 已设置止损（假突破不能打到）")
    doc.append("□ 5. 已设置止盈（2倍以上盈亏比）")
    doc.append("□ 6. 已计算仓位大小（风险不超过5%）")
    doc.append("□ 7. 已使用逐仓模式")
    doc.append("□ 8. 已挂单（不追价）")
    doc.append("□ 9. 确认不是单边行情")
    doc.append("□ 10. 盈亏比≥2倍")
    doc.append("")
    doc.append("**只有所有项目都确认后，才能执行交易！**")
    doc.append("")
    
    return "\n".join(doc)

def main():
    file_path = r"C:\Users\zuoho\Downloads\discord-msg\梦之队 - 梦梦 - 青沐 [1428778462981918951].html"
    
    print("=" * 80)
    print("提取交易系统规则")
    print("=" * 80)
    print()
    
    # 解析文件
    messages = parse_json_file(file_path)
    print(f"总消息数: {len(messages)}")
    
    # 提取De.的消息
    de_messages = extract_de_messages(messages)
    print(f"De.的消息数: {len(de_messages)}")
    
    # 提取规则
    rules = extract_trading_rules(de_messages)
    print(f"提取的规则数:")
    print(f"  - 入场规则: {len(rules['entry_rules'])}")
    print(f"  - 止损规则: {len(rules['stop_loss_rules'])}")
    print(f"  - 止盈规则: {len(rules['take_profit_rules'])}")
    print(f"  - 仓位管理: {len(rules['position_sizing'])}")
    print(f"  - 风险管理: {len(rules['risk_management'])}")
    print(f"  - 实际案例: {len(rules['examples'])}")
    
    # 分析规则
    analysis = analyze_rules(rules)
    
    # 生成交易系统文档
    system_doc = generate_trading_system(rules, analysis)
    
    # 保存文档
    output_file = "De_trading_system_complete_guide.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(system_doc)
    
    print()
    print("=" * 80)
    print("完成！")
    print("=" * 80)
    print(f"交易系统指南已保存到: {output_file}")
    print()
    print("文档包含:")
    print("  - 完整的交易规则（按步骤）")
    print("  - 5分钟、15分钟、1小时交易计划")
    print("  - 实际交易案例")
    print("  - 风险提示")
    print("  - 交易检查清单")

if __name__ == "__main__":
    main()




