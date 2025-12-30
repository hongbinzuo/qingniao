#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提取De.的完整指标系统和技术分析方法
包括Vegas通道、VWAP、EMA、RSI等所有指标的使用方法
"""

import json
import re
from collections import defaultdict
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

def extract_indicator_system(de_messages: List[Dict]) -> Dict:
    """提取指标系统相关内容"""
    print("正在提取指标系统...")
    
    indicators = {
        'vegas_channel': [],      # Vegas通道
        'vwap': [],                # VWAP
        'ema': [],                 # EMA均线
        'ma': [],                  # MA均线
        'rsi': [],                 # RSI指标
        'support_resistance': [],  # 支撑阻力
        'fibonacci': [],           # 斐波那契
        'bollinger': [],           # 布林带
        'ict': [],                 # ICT概念
        'liquidity': [],           # 流动性
        'fvg': [],                 # FVG (Fair Value Gap)
        'ob': [],                  # Order Block
        'timeframe_indicators': [] # 不同时间框架的指标使用
    }
    
    for msg in de_messages:
        content = msg.get('content', '')
        timestamp = msg.get('timestamp', '')
        
        if not content or len(content) < 5:
            continue
        
        # Vegas通道
        if 'vegas' in content.lower():
            indicators['vegas_channel'].append({
                'content': content,
                'timestamp': timestamp
            })
        elif ('ema144' in content.lower() and 'ema169' in content.lower()) or ('144' in content and '169' in content and 'ema' in content.lower()):
            indicators['vegas_channel'].append({
                'content': content,
                'timestamp': timestamp
            })
        
        # VWAP
        if 'vwap' in content.lower():
            indicators['vwap'].append({
                'content': content,
                'timestamp': timestamp
            })
        
        # EMA
        if 'ema' in content.lower() and any(x in content for x in ['144', '169', '233', '89', '55', '34', '21']):
            indicators['ema'].append({
                'content': content,
                'timestamp': timestamp
            })
        
        # MA
        if 'ma' in content.lower() and ('144' in content or '169' in content or '89' in content):
            indicators['ma'].append({
                'content': content,
                'timestamp': timestamp
            })
        
        # RSI
        if 'rsi' in content.lower():
            indicators['rsi'].append({
                'content': content,
                'timestamp': timestamp
            })
        
        # 支撑阻力
        if any(kw in content for kw in ['支撑', '阻力', '压制', '压力']):
            indicators['support_resistance'].append({
                'content': content,
                'timestamp': timestamp
            })
        
        # 斐波那契
        if any(kw in content for kw in ['618', '786', '382', '500', '斐波', 'fibonacci']):
            indicators['fibonacci'].append({
                'content': content,
                'timestamp': timestamp
            })
        
        # ICT相关
        if any(kw in content for kw in ['ict', 'ote', 'fvg', 'ob', 'order block', 'fair value gap']):
            indicators['ict'].append({
                'content': content,
                'timestamp': timestamp
            })
        
        # FVG
        if 'fvg' in content.lower():
            indicators['fvg'].append({
                'content': content,
                'timestamp': timestamp
            })
        
        # Order Block
        if 'ob' in content.lower() or 'order block' in content.lower():
            indicators['ob'].append({
                'content': content,
                'timestamp': timestamp
            })
        
        # 流动性
        if '流动性' in content:
            indicators['liquidity'].append({
                'content': content,
                'timestamp': timestamp
            })
        
        # 时间框架 + 指标
        if any(tf in content for tf in ['5分', '15分', '1h', '1小时', '4h', '4小时']) and any(ind in content for ind in ['vegas', 'vwap', 'ema', 'ma']):
            indicators['timeframe_indicators'].append({
                'content': content,
                'timestamp': timestamp
            })
    
    return indicators

def generate_complete_system(indicators: Dict, de_messages: List[Dict]) -> str:
    """生成完整的交易系统文档（包含所有指标）"""
    print("正在生成完整交易系统文档...")
    
    doc = []
    doc.append("=" * 80)
    doc.append("交易员 De. 的完整交易系统 - 包含所有指标系统")
    doc.append("=" * 80)
    doc.append("")
    doc.append("本系统适用于：5分钟、15分钟、1小时时间框架")
    doc.append("")
    
    # 一、指标系统概述
    doc.append("## 一、指标系统概述")
    doc.append("")
    doc.append("De.使用的核心指标组合：")
    doc.append("")
    doc.append("1. **Vegas通道**: EMA144 + EMA169（主要用于识别区间）")
    doc.append("2. **VWAP**: 成交量加权平均价格（用于确认支撑阻力）")
    doc.append("3. **EMA均线组**: EMA144, EMA169, EMA233等（不同时间框架）")
    doc.append("4. **RSI**: 相对强弱指标（用于判断趋势和超买超卖）")
    doc.append("5. **斐波那契回撤**: 618-786区间（OTE区间）")
    doc.append("6. **ICT概念**: FVG、Order Block、流动性等")
    doc.append("")
    
    # 二、Vegas通道系统
    doc.append("## 二、Vegas通道系统（核心指标）")
    doc.append("")
    doc.append("### 什么是Vegas通道")
    doc.append("")
    doc.append("Vegas通道 = EMA144 + EMA169")
    doc.append("")
    doc.append("- **EMA144**: 144周期指数移动平均线")
    doc.append("- **EMA169**: 169周期指数移动平均线")
    doc.append("- 这两条均线形成的通道就是Vegas通道")
    doc.append("")
    doc.append("### Vegas通道的作用")
    doc.append("")
    doc.append("1. **识别区间边界**")
    doc.append("   - 价格在Vegas通道内 = 震荡区间")
    doc.append("   - 价格突破Vegas通道 = 趋势开始")
    doc.append("")
    doc.append("2. **判断支撑阻力**")
    doc.append("   - 价格在通道上方 = 通道作为支撑")
    doc.append("   - 价格在通道下方 = 通道作为阻力")
    doc.append("")
    doc.append("3. **确认交易区间**")
    doc.append("   - 区间上下沿需要Vegas通道确认")
    doc.append("   - 结合VWAP进一步确认")
    doc.append("")
    doc.append("### 实际应用示例")
    doc.append("")
    if indicators['vegas_channel']:
        for i, item in enumerate(indicators['vegas_channel'][:5], 1):
            doc.append(f"**示例{i}**: {item['content']}")
            doc.append(f"时间: {item['timestamp']}")
            doc.append("")
    
    # 三、VWAP系统
    doc.append("## 三、VWAP（成交量加权平均价格）系统")
    doc.append("")
    doc.append("### VWAP的作用")
    doc.append("")
    doc.append("1. **确认支撑阻力**")
    doc.append("   - VWAP作为动态支撑/阻力位")
    doc.append("   - 价格在VWAP上方 = VWAP是支撑")
    doc.append("   - 价格在VWAP下方 = VWAP是阻力")
    doc.append("")
    doc.append("2. **与Vegas通道结合**")
    doc.append("   - Vegas通道确定区间边界")
    doc.append("   - VWAP确认支撑阻力位置")
    doc.append("   - 两者结合使用，提高准确性")
    doc.append("")
    doc.append("3. **不同时间框架的VWAP**")
    doc.append("   - 5分钟VWAP: 短期支撑阻力")
    doc.append("   - 15分钟VWAP: 中期支撑阻力（推荐）")
    doc.append("   - 1小时VWAP: 长期支撑阻力")
    doc.append("")
    doc.append("### 实际应用示例")
    doc.append("")
    if indicators['vwap']:
        for i, item in enumerate(indicators['vwap'][:5], 1):
            doc.append(f"**示例{i}**: {item['content']}")
            doc.append(f"时间: {item['timestamp']}")
            doc.append("")
    
    # 四、EMA均线系统
    doc.append("## 四、EMA均线系统")
    doc.append("")
    doc.append("### 常用EMA参数")
    doc.append("")
    doc.append("- **EMA144**: 144周期（Vegas通道组成部分）")
    doc.append("- **EMA169**: 169周期（Vegas通道组成部分）")
    doc.append("- **EMA233**: 233周期（长期趋势）")
    doc.append("- **EMA89**: 89周期（中期趋势）")
    doc.append("- **EMA55**: 55周期（短期趋势）")
    doc.append("")
    doc.append("### EMA的使用方法")
    doc.append("")
    doc.append("1. **趋势判断**")
    doc.append("   - 价格在EMA上方 = 上升趋势")
    doc.append("   - 价格在EMA下方 = 下降趋势")
    doc.append("   - EMA144/169是重要的趋势分界线")
    doc.append("")
    doc.append("2. **支撑阻力**")
    doc.append("   - 大周期EMA（如4小时EMA144）作为重要支撑阻力")
    doc.append("   - 价格回踩EMA144/169是入场机会")
    doc.append("")
    doc.append("3. **多时间框架确认**")
    doc.append("   - 1小时EMA144/169确认短期趋势")
    doc.append("   - 4小时EMA144/169确认中期趋势")
    doc.append("   - 日线EMA144/169确认长期趋势")
    doc.append("")
    
    # 五、RSI指标系统
    doc.append("## 五、RSI指标系统")
    doc.append("")
    doc.append("### RSI的使用方法（基于De.的实际经验）")
    doc.append("")
    doc.append("**重要发现**（De.的总结）：")
    doc.append("")
    doc.append("1. **RSI > 50 与下跌趋势的关系**")
    doc.append("   - RSI大于50，对应的下跌趋势，一般跌不动")
    doc.append("   - 表现为横盘或者跌的少涨的多")
    doc.append("   - 这是震荡行情的特征")
    doc.append("")
    doc.append("2. **RSI < 50 与上涨趋势的关系**")
    doc.append("   - RSI小于50，对应的上涨趋势，一般涨不动")
    doc.append("   - 表现为横盘或者涨的少跌的多")
    doc.append("   - 这也是震荡行情的特征")
    doc.append("")
    doc.append("3. **单边行情的RSI特征**")
    doc.append("   - 单边行情都是顶着RSI的顶在跑的")
    doc.append("   - RSI在顶格（接近100）或底格（接近0）")
    doc.append("   - 这时指标钝化，等待开口反手交易")
    doc.append("   - 但RSI在顶格时，反手都是动能最强或最弱的时候，根本没用")
    doc.append("")
    doc.append("4. **RSI的局限性**")
    doc.append("   - 震荡能赚，单边死亏")
    doc.append("   - RSI在震荡行情中有效，在单边行情中失效")
    doc.append("   - 最后还是看趋势，不能单纯依赖RSI")
    doc.append("")
    
    # 六、支撑阻力判断方法
    doc.append("## 六、支撑阻力判断方法")
    doc.append("")
    doc.append("### 综合判断方法")
    doc.append("")
    doc.append("**步骤1: 使用Vegas通道识别区间**")
    doc.append("- 在图表上添加EMA144和EMA169")
    doc.append("- 观察价格在两条均线之间的震荡区间")
    doc.append("- 区间上沿 = EMA169（或更高点）")
    doc.append("- 区间下沿 = EMA144（或更低点）")
    doc.append("")
    doc.append("**步骤2: 使用VWAP确认支撑阻力**")
    doc.append("- 添加对应时间框架的VWAP")
    doc.append("- VWAP在区间内 = 作为动态支撑/阻力")
    doc.append("- VWAP在区间外 = 作为突破确认")
    doc.append("")
    doc.append("**步骤3: 多时间框架确认**")
    doc.append("- 15分钟Vegas通道确定交易区间")
    doc.append("- 15分钟VWAP确认支撑阻力")
    doc.append("- 1小时Vegas通道确认大趋势")
    doc.append("- 4小时Vegas通道确认长期方向")
    doc.append("")
    doc.append("### 实际案例")
    doc.append("")
    doc.append("**案例**: \"目前价格在864-882区间，15分vegas压制（87127-87400），15分vwap支撑862\"")
    doc.append("")
    doc.append("分析：")
    doc.append("- 交易区间：864-882")
    doc.append("- 15分钟Vegas通道：87127-87400（作为阻力/压制）")
    doc.append("- 15分钟VWAP：862（作为支撑）")
    doc.append("- 价格在区间内，VWAP作为支撑，Vegas作为阻力")
    doc.append("")
    
    # 七、ICT概念系统
    doc.append("## 七、ICT概念系统")
    doc.append("")
    doc.append("### FVG (Fair Value Gap)")
    doc.append("")
    doc.append("**定义**: 价格跳空形成的价值缺口")
    doc.append("")
    doc.append("**使用方法**:")
    doc.append("- 识别FVG位置")
    doc.append("- 价格回填FVG时是交易机会")
    doc.append("- 例如：\"1092-96有个fvg，可以挂点空单，有概率扫进去\"")
    doc.append("")
    doc.append("### Order Block (OB)")
    doc.append("")
    doc.append("**定义**: 机构订单区域")
    doc.append("")
    doc.append("**使用方法**:")
    doc.append("- 识别OB位置（通常是大幅波动的起点）")
    doc.append("- 价格回到OB时是交易机会")
    doc.append("- 例如：\"1100-1103这个区间的ob挂单\"")
    doc.append("")
    doc.append("### OTE区间（Optimal Trade Entry）")
    doc.append("")
    doc.append("**定义**: 618-786斐波那契回撤区间")
    doc.append("")
    doc.append("**使用方法**:")
    doc.append("- 突破后回踩到618-786区间")
    doc.append("- 出现假动作（刺破618但未破786）")
    doc.append("- 这是最佳入场位置")
    doc.append("- 例如：\"106-1068（ote区间618-786）这个区间，有很大的反弹概率\"")
    doc.append("")
    
    # 八、完整的交易流程（包含指标）
    doc.append("## 八、完整的交易流程（包含所有指标）")
    doc.append("")
    doc.append("### 第一步：设置图表指标")
    doc.append("")
    doc.append("**必须添加的指标**:")
    doc.append("1. EMA144（Vegas通道）")
    doc.append("2. EMA169（Vegas通道）")
    doc.append("3. VWAP（对应时间框架）")
    doc.append("4. RSI（可选，用于辅助判断）")
    doc.append("5. 斐波那契回撤工具（618-786）")
    doc.append("")
    doc.append("**多时间框架设置**:")
    doc.append("- 5分钟图：5分钟VWAP + 5分钟EMA144/169")
    doc.append("- 15分钟图：15分钟VWAP + 15分钟EMA144/169（主要交易图表）")
    doc.append("- 1小时图：1小时VWAP + 1小时EMA144/169（趋势确认）")
    doc.append("- 4小时图：4小时EMA144/169（大趋势确认）")
    doc.append("")
    
    doc.append("### 第二步：识别交易区间")
    doc.append("")
    doc.append("**方法**:")
    doc.append("1. 在15分钟图上，观察价格在EMA144和EMA169之间的震荡")
    doc.append("2. 确定区间上沿（通常是EMA169或更高点）")
    doc.append("3. 确定区间下沿（通常是EMA144或更低点）")
    doc.append("4. 用VWAP确认：VWAP应该在区间内或接近区间边界")
    doc.append("5. 区间宽度至少200-500点")
    doc.append("")
    
    doc.append("### 第三步：判断支撑阻力")
    doc.append("")
    doc.append("**支撑位判断**:")
    doc.append("- 区间下沿（EMA144附近）")
    doc.append("- VWAP位置（如果VWAP在区间下沿附近）")
    doc.append("- 大周期EMA144/169（如4小时EMA144）")
    doc.append("- 流动性区域（大量挂单的位置）")
    doc.append("")
    doc.append("**阻力位判断**:")
    doc.append("- 区间上沿（EMA169附近）")
    doc.append("- VWAP位置（如果VWAP在区间上沿附近）")
    doc.append("- 大周期EMA144/169（如4小时EMA169）")
    doc.append("- 流动性区域（大量挂单的位置）")
    doc.append("")
    
    doc.append("### 第四步：入场规则（结合指标）")
    doc.append("")
    doc.append("**多单入场条件（全部满足）**:")
    doc.append("1. 价格回落到区间下沿（EMA144附近）")
    doc.append("2. VWAP在下方作为支撑")
    doc.append("3. RSI < 50（如果使用RSI）")
    doc.append("4. 大周期趋势向上（4小时EMA144/169向上）")
    doc.append("5. 在区间下沿+10-20点挂买单")
    doc.append("")
    doc.append("**空单入场条件（全部满足）**:")
    doc.append("1. 价格反弹到区间上沿（EMA169附近）")
    doc.append("2. VWAP在上方作为阻力")
    doc.append("3. RSI > 50（如果使用RSI）")
    doc.append("4. 大周期趋势向下（4小时EMA144/169向下）")
    doc.append("5. 在区间上沿-10-20点挂卖单")
    doc.append("")
    
    doc.append("### 第五步：止损止盈（结合指标）")
    doc.append("")
    doc.append("**止损设置**:")
    doc.append("- 多单止损：区间下沿下方，假突破不能打到的位置")
    doc.append("- 空单止损：区间上沿上方，假突破不能打到的位置")
    doc.append("- 参考VWAP：如果VWAP在止损位置附近，可以调整")
    doc.append("- 参考大周期EMA：止损不要破大周期EMA144/169")
    doc.append("")
    doc.append("**止盈设置**:")
    doc.append("- 多单止盈：区间上沿附近（EMA169附近）")
    doc.append("- 空单止盈：区间下沿附近（EMA144附近）")
    doc.append("- 参考VWAP：如果VWAP在止盈位置，可以在此止盈")
    doc.append("- 分批止盈：50%在目标位置，50%看情况")
    doc.append("")
    
    # 九、不同时间框架的具体应用
    doc.append("## 九、不同时间框架的具体应用")
    doc.append("")
    doc.append("### 5分钟时间框架")
    doc.append("")
    doc.append("**指标设置**:")
    doc.append("- 5分钟EMA144/169（Vegas通道）")
    doc.append("- 5分钟VWAP")
    doc.append("")
    doc.append("**使用方法**:")
    doc.append("- 识别5分钟图上的小区间（50-200点）")
    doc.append("- 5分钟VWAP作为动态支撑/阻力")
    doc.append("- 5分钟Vegas通道确认区间边界")
    doc.append("- 需要看盘，快速进出")
    doc.append("")
    
    doc.append("### 15分钟时间框架（推荐）")
    doc.append("")
    doc.append("**指标设置**:")
    doc.append("- 15分钟EMA144/169（Vegas通道）")
    doc.append("- 15分钟VWAP")
    doc.append("- 1小时EMA144/169（趋势确认）")
    doc.append("")
    doc.append("**使用方法**:")
    doc.append("- 识别15分钟图上的区间（200-500点）")
    doc.append("- 15分钟VWAP作为主要支撑/阻力")
    doc.append("- 15分钟Vegas通道确定交易区间")
    doc.append("- 1小时Vegas通道确认大趋势方向")
    doc.append("- 可以挂单后不看盘")
    doc.append("")
    
    doc.append("### 1小时时间框架")
    doc.append("")
    doc.append("**指标设置**:")
    doc.append("- 1小时EMA144/169（Vegas通道）")
    doc.append("- 1小时VWAP")
    doc.append("- 4小时EMA144/169（大趋势确认）")
    doc.append("")
    doc.append("**使用方法**:")
    doc.append("- 识别1小时图上的大区间（500-1000点）")
    doc.append("- 1小时VWAP作为主要支撑/阻力")
    doc.append("- 1小时Vegas通道确定交易区间")
    doc.append("- 4小时Vegas通道确认长期趋势")
    doc.append("- 适合挂单后长时间等待")
    doc.append("")
    
    # 十、实际案例（包含指标）
    doc.append("## 十、实际案例（包含指标分析）")
    doc.append("")
    if indicators['timeframe_indicators']:
        for i, item in enumerate(indicators['timeframe_indicators'][:10], 1):
            doc.append(f"### 案例 {i}")
            doc.append(f"**时间**: {item['timestamp']}")
            doc.append(f"**内容**: {item['content']}")
            doc.append("")
    
    # 十一、指标使用注意事项
    doc.append("## 十一、指标使用注意事项")
    doc.append("")
    doc.append("### 重要原则")
    doc.append("")
    doc.append("1. **指标组合使用**")
    doc.append("   - 不要单独依赖一个指标")
    doc.append("   - Vegas通道 + VWAP + 趋势确认")
    doc.append("   - 多个指标共振时，信号更可靠")
    doc.append("")
    doc.append("2. **多时间框架确认**")
    doc.append("   - 小周期找入场点")
    doc.append("   - 大周期确认趋势")
    doc.append("   - 趋势一致时，交易成功率更高")
    doc.append("")
    doc.append("3. **指标失效的情况**")
    doc.append("   - 单边行情时，震荡指标失效（如RSI）")
    doc.append("   - 突破Vegas通道后，区间交易失效")
    doc.append("   - 遇到单边行情，立即止损")
    doc.append("")
    doc.append("4. **指标参数的调整**")
    doc.append("   - EMA144/169是标准参数，不要随意修改")
    doc.append("   - VWAP使用对应时间框架的VWAP")
    doc.append("   - 不同时间框架使用对应周期的指标")
    doc.append("")
    
    return "\n".join(doc)

def main():
    file_path = r"C:\Users\zuoho\Downloads\discord-msg\梦之队 - 梦梦 - 青沐 [1428778462981918951].html"
    
    print("=" * 80)
    print("提取完整指标系统")
    print("=" * 80)
    print()
    
    # 解析文件
    messages = parse_json_file(file_path)
    print(f"总消息数: {len(messages)}")
    
    # 提取De.的消息
    de_messages = extract_de_messages(messages)
    print(f"De.的消息数: {len(de_messages)}")
    
    # 提取指标系统
    indicators = extract_indicator_system(de_messages)
    print(f"提取的指标内容:")
    print(f"  - Vegas通道: {len(indicators['vegas_channel'])}")
    print(f"  - VWAP: {len(indicators['vwap'])}")
    print(f"  - EMA: {len(indicators['ema'])}")
    print(f"  - RSI: {len(indicators['rsi'])}")
    print(f"  - 支撑阻力: {len(indicators['support_resistance'])}")
    print(f"  - 时间框架+指标: {len(indicators['timeframe_indicators'])}")
    
    # 生成完整系统文档
    system_doc = generate_complete_system(indicators, de_messages)
    
    # 保存文档
    output_file = "De_trading_system_with_indicators.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(system_doc)
    
    print()
    print("=" * 80)
    print("完成！")
    print("=" * 80)
    print(f"完整交易系统（含指标）已保存到: {output_file}")

if __name__ == "__main__":
    main()

