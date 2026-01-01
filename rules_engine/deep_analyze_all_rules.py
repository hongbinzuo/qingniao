#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深入分析De.的所有交易规则
提取每条消息中的交易逻辑和规则
结合成熟交易系统理论完善文档
"""

import json
import re
from collections import defaultdict, Counter
from typing import List, Dict, Set

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

def analyze_trading_logic(content: str) -> Dict:
    """分析单条消息中的交易逻辑"""
    rules = {
        'market_analysis': [],      # 市场分析
        'trend_judgment': [],      # 趋势判断
        'scenario_analysis': [],   # 情景分析
        'entry_signals': [],       # 入场信号
        'exit_signals': [],        # 出场信号
        'risk_management': [],     # 风险管理
        'market_structure': []      # 市场结构
    }
    
    # 趋势判断
    if any(kw in content for kw in ['偏多', '偏空', '看多', '看空', '日线', '周线', '大趋势']):
        if '偏多' in content or '看多' in content:
            rules['trend_judgment'].append('偏多/看多')
        if '偏空' in content or '看空' in content:
            rules['trend_judgment'].append('偏空/看空')
        if '日线' in content:
            rules['trend_judgment'].append('日线级别判断')
        if '大趋势' in content:
            rules['trend_judgment'].append('大趋势判断')
    
    # 流动性/扫单分析
    if any(kw in content for kw in ['扫', '扫掉', '流动性', '高点', '低点', '周五', '周一']):
        if '扫' in content or '扫掉' in content:
            rules['market_analysis'].append('流动性被扫')
        if '周五' in content or '周一' in content:
            rules['market_analysis'].append('时间周期分析')
        if '高点' in content or '低点' in content:
            rules['market_analysis'].append('关键点位分析')
    
    # 情景分析（要么...或者...）
    if '要么' in content or '或者' in content or '可能' in content:
        rules['scenario_analysis'].append('多情景分析')
        # 提取具体情景
        if '区间震荡' in content or '震荡' in content:
            rules['scenario_analysis'].append('区间震荡情景')
        if '去找' in content or '去' in content:
            rules['scenario_analysis'].append('趋势延续情景')
    
    # 市场结构
    if any(kw in content for kw in ['供给区', '需求区', '派发', '吸筹', '养', '养空头', '养多头']):
        if '供给区' in content or '派发' in content:
            rules['market_structure'].append('供给区/派发')
        if '需求区' in content or '吸筹' in content:
            rules['market_structure'].append('需求区/吸筹')
        if '养' in content:
            rules['market_structure'].append('养单行为')
    
    # 入场信号
    if any(kw in content for kw in ['挂单', '开', '做多', '做空', '接', '入场']):
        rules['entry_signals'].append('入场信号')
    
    # 出场信号
    if any(kw in content for kw in ['平', '止盈', '止损', '滚仓', '清仓']):
        rules['exit_signals'].append('出场信号')
    
    return rules

def extract_all_trading_rules(de_messages: List[Dict]) -> Dict:
    """提取所有交易规则"""
    print("正在深入分析所有交易规则...")
    
    all_rules = {
        'trend_analysis': [],           # 趋势分析规则
        'liquidity_analysis': [],       # 流动性分析规则
        'scenario_planning': [],        # 情景规划规则
        'market_structure': [],         # 市场结构规则
        'entry_conditions': [],         # 入场条件
        'exit_conditions': [],          # 出场条件
        'risk_management': [],          # 风险管理
        'time_analysis': [],            # 时间分析
        'price_action': [],              # 价格行为
        'market_manipulation': []       # 市场操纵识别
    }
    
    for msg in de_messages:
        content = msg.get('content', '')
        timestamp = msg.get('timestamp', '')
        
        if not content or len(content) < 10:
            continue
        
        # 趋势分析
        if any(kw in content for kw in ['偏多', '偏空', '日线', '周线', '大趋势', '趋势']):
            all_rules['trend_analysis'].append({
                'content': content,
                'timestamp': timestamp
            })
        
        # 流动性分析
        if any(kw in content for kw in ['扫', '扫掉', '流动性', '高点', '低点', '扫单']):
            all_rules['liquidity_analysis'].append({
                'content': content,
                'timestamp': timestamp
            })
        
        # 情景规划
        if any(kw in content for kw in ['要么', '或者', '可能', '如果', '那么']):
            all_rules['scenario_planning'].append({
                'content': content,
                'timestamp': timestamp
            })
        
        # 市场结构
        if any(kw in content for kw in ['供给区', '需求区', '派发', '吸筹', '养', '养空头', '养多头']):
            all_rules['market_structure'].append({
                'content': content,
                'timestamp': timestamp
            })
        
        # 时间分析
        if any(kw in content for kw in ['周五', '周一', '早上', '晚上', '今天', '昨天', '周末', '周六']):
            all_rules['time_analysis'].append({
                'content': content,
                'timestamp': timestamp
            })
        
        # 价格行为
        if any(kw in content for kw in ['回踩', '突破', '假突破', '刺破', '插针', '反弹']):
            all_rules['price_action'].append({
                'content': content,
                'timestamp': timestamp
            })
        
        # 市场操纵识别
        if any(kw in content for kw in ['养', '扫', '骗', '假动作', '诱多', '诱空']):
            all_rules['market_manipulation'].append({
                'content': content,
                'timestamp': timestamp
            })
    
    return all_rules

def generate_comprehensive_system(all_rules: Dict, de_messages: List[Dict]) -> str:
    """生成完整的交易系统文档"""
    print("正在生成完整交易系统文档...")
    
    doc = []
    doc.append("=" * 80)
    doc.append("交易员 De. 的完整交易系统 - 深度分析版")
    doc.append("=" * 80)
    doc.append("")
    doc.append("本系统适用于：5分钟、15分钟、1小时时间框架")
    doc.append("")
    doc.append("**重要说明**：本系统基于De.的所有实际交易记录和规则总结")
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
    doc.append("### 核心特点")
    doc.append("- **多情景分析**: 考虑多种可能的市场走势")
    doc.append("- **流动性分析**: 关注流动性被扫的情况")
    doc.append("- **市场结构识别**: 识别供给区、需求区、养单行为")
    doc.append("- **时间周期分析**: 考虑日线、周线等大周期")
    doc.append("")
    
    # 二、市场分析系统（多维度）
    doc.append("## 二、市场分析系统（多维度分析）")
    doc.append("")
    
    doc.append("### 2.1 趋势分析（多时间框架）")
    doc.append("")
    doc.append("**分析维度**：")
    doc.append("")
    doc.append("1. **日线级别趋势**")
    doc.append("   - 判断：\"今天日线偏多\" 或 \"日线偏空\"")
    doc.append("   - 作用：确定大趋势方向")
    doc.append("   - 应用：大趋势向上，优先考虑多单；大趋势向下，优先考虑空单")
    doc.append("")
    doc.append("2. **周线级别趋势**")
    doc.append("   - 判断：周线级别的整体趋势")
    doc.append("   - 作用：确认长期方向")
    doc.append("")
    doc.append("3. **多时间框架确认**")
    doc.append("   - 日线 + 4小时 + 1小时 + 15分钟")
    doc.append("   - 趋势一致时，交易成功率更高")
    doc.append("")
    doc.append("**实际案例**：")
    if all_rules['trend_analysis']:
        for i, rule in enumerate(all_rules['trend_analysis'][:5], 1):
            doc.append(f"{i}. {rule['content'][:150]}...")
            doc.append(f"   时间: {rule['timestamp']}")
            doc.append("")
    
    doc.append("### 2.2 流动性分析（关键）")
    doc.append("")
    doc.append("**流动性分析的重要性**：")
    doc.append("")
    doc.append("1. **流动性被扫的影响**")
    doc.append("   - \"早上已经扫了，周五的高点\"")
    doc.append("   - 流动性被扫后，价格可能反转")
    doc.append("   - 需要重新评估市场方向")
    doc.append("")
    doc.append("2. **流动性区域识别**")
    doc.append("   - 大量挂单的位置 = 流动性区域")
    doc.append("   - 流动性被扫后，价格可能继续原方向或反转")
    doc.append("   - 需要观察价格在流动性区域附近的行为")
    doc.append("")
    doc.append("3. **流动性陷阱**")
    doc.append("   - 周末的流动性在周一开盘前容易被扫掉")
    doc.append("   - 挂单在流动性区域附近，容易被扫")
    doc.append("")
    doc.append("**实际案例**：")
    if all_rules['liquidity_analysis']:
        for i, rule in enumerate(all_rules['liquidity_analysis'][:5], 1):
            doc.append(f"{i}. {rule['content'][:150]}...")
            doc.append(f"   时间: {rule['timestamp']}")
            doc.append("")
    
    doc.append("### 2.3 情景规划（多情景分析）")
    doc.append("")
    doc.append("**De.的分析方法**：考虑多种可能的情景")
    doc.append("")
    doc.append("**典型分析模式**：")
    doc.append("\"要么...或者...\" / \"可能...也可能...\"")
    doc.append("")
    doc.append("**示例分析**：")
    doc.append("\"今天日线偏多，但考虑到早上已经扫了，周五的高点，那么接下来，要么在1075-1092这个区间震荡，或者去找106低点\"")
    doc.append("")
    doc.append("**分析步骤**：")
    doc.append("1. 确定大趋势（日线偏多）")
    doc.append("2. 考虑关键事件（早上扫了周五高点）")
    doc.append("3. 列出可能情景：")
    doc.append("   - 情景A：区间震荡（1075-1092）")
    doc.append("   - 情景B：趋势延续（去找106低点）")
    doc.append("4. 为每个情景准备交易计划")
    doc.append("")
    doc.append("**实际案例**：")
    if all_rules['scenario_planning']:
        for i, rule in enumerate(all_rules['scenario_planning'][:10], 1):
            doc.append(f"{i}. {rule['content'][:200]}...")
            doc.append(f"   时间: {rule['timestamp']}")
            doc.append("")
    
    doc.append("### 2.4 市场结构分析")
    doc.append("")
    doc.append("**市场结构概念**：")
    doc.append("")
    doc.append("1. **供给区（Supply Zone）**")
    doc.append("   - 定义：大量卖单集中的区域")
    doc.append("   - 特征：价格在此区域容易下跌")
    doc.append("   - 应用：在供给区附近做空")
    doc.append("")
    doc.append("2. **需求区（Demand Zone）**")
    doc.append("   - 定义：大量买单集中的区域")
    doc.append("   - 特征：价格在此区域容易上涨")
    doc.append("   - 应用：在需求区附近做多")
    doc.append("")
    doc.append("3. **派发（Distribution）**")
    doc.append("   - 定义：机构在高位派发筹码")
    doc.append("   - 特征：价格在区间内震荡，但最终会下跌")
    doc.append("   - 应用：识别派发区间，准备做空")
    doc.append("")
    doc.append("4. **吸筹（Accumulation）**")
    doc.append("   - 定义：机构在低位收集筹码")
    doc.append("   - 特征：价格在区间内震荡，但最终会上涨")
    doc.append("   - 应用：识别吸筹区间，准备做多")
    doc.append("")
    doc.append("5. **养单行为（Trapping）**")
    doc.append("   - 定义：\"养空头\" 或 \"养多头\"")
    doc.append("   - 特征：价格在某个方向制造假象，然后反向运行")
    doc.append("   - 应用：识别养单行为，避免被套")
    doc.append("")
    doc.append("**实际案例**：")
    if all_rules['market_structure']:
        for i, rule in enumerate(all_rules['market_structure'][:5], 1):
            doc.append(f"{i}. {rule['content'][:200]}...")
            doc.append(f"   时间: {rule['timestamp']}")
            doc.append("")
    
    doc.append("### 2.5 时间周期分析")
    doc.append("")
    doc.append("**时间因素的重要性**：")
    doc.append("")
    doc.append("1. **周五/周一效应**")
    doc.append("   - 周五的高点/低点可能被周一扫掉")
    doc.append("   - \"早上已经扫了，周五的高点\"")
    doc.append("   - 需要考虑周末流动性变化")
    doc.append("")
    doc.append("2. **周末流动性**")
    doc.append("   - 周末流动性不足")
    doc.append("   - 周末的流动性在周一开盘前容易被扫掉")
    doc.append("   - 周末不适合交易")
    doc.append("")
    doc.append("3. **日内时间分析**")
    doc.append("   - 早上、中午、晚上的市场行为可能不同")
    doc.append("   - 需要考虑不同时段的流动性变化")
    doc.append("")
    doc.append("**实际案例**：")
    if all_rules['time_analysis']:
        for i, rule in enumerate(all_rules['time_analysis'][:5], 1):
            doc.append(f"{i}. {rule['content'][:150]}...")
            doc.append(f"   时间: {rule['timestamp']}")
            doc.append("")
    
    # 三、完整的交易决策流程
    doc.append("## 三、完整的交易决策流程")
    doc.append("")
    doc.append("### 步骤1：多维度市场分析")
    doc.append("")
    doc.append("**必须分析的内容**：")
    doc.append("")
    doc.append("1. **趋势分析**")
    doc.append("   □ 日线级别趋势（偏多/偏空）")
    doc.append("   □ 4小时趋势")
    doc.append("   □ 1小时趋势")
    doc.append("   □ 15分钟趋势")
    doc.append("   □ 多时间框架是否一致")
    doc.append("")
    doc.append("2. **流动性分析**")
    doc.append("   □ 最近是否有流动性被扫（高点/低点）")
    doc.append("   □ 当前流动性区域在哪里")
    doc.append("   □ 流动性被扫后的市场反应")
    doc.append("")
    doc.append("3. **市场结构分析**")
    doc.append("   □ 当前是供给区还是需求区")
    doc.append("   □ 是否有派发或吸筹行为")
    doc.append("   □ 是否有养单行为（养空头/养多头）")
    doc.append("")
    doc.append("4. **时间周期分析**")
    doc.append("   □ 今天是周几（周末不适合交易）")
    doc.append("   □ 是否有周五/周一效应")
    doc.append("   □ 当前是早上/中午/晚上")
    doc.append("")
    doc.append("5. **情景规划**")
    doc.append("   □ 列出所有可能的市场走势")
    doc.append("   □ 为每个情景准备交易计划")
    doc.append("   □ 确定最可能的情景")
    doc.append("")
    
    doc.append("### 步骤2：识别交易区间")
    doc.append("")
    doc.append("**区间识别方法**：")
    doc.append("")
    doc.append("1. **观察价格实际震荡范围**")
    doc.append("   - 在图表上找到明显的价格震荡区间")
    doc.append("   - 确定区间上沿（阻力位）和下沿（支撑位）")
    doc.append("")
    doc.append("2. **使用Vegas通道确认**")
    doc.append("   - 添加EMA144和EMA169")
    doc.append("   - 用Vegas通道确认区间边界")
    doc.append("")
    doc.append("3. **使用VWAP确认**")
    doc.append("   - 添加对应时间框架的VWAP")
    doc.append("   - VWAP在区间内 = 作为动态支撑/阻力")
    doc.append("")
    doc.append("4. **结合市场结构**")
    doc.append("   - 区间是供给区还是需求区？")
    doc.append("   - 是否有派发或吸筹行为？")
    doc.append("")
    
    doc.append("### 步骤3：入场决策")
    doc.append("")
    doc.append("**入场前必须确认**：")
    doc.append("")
    doc.append("1. **趋势确认**")
    doc.append("   - 大趋势方向（日线）")
    doc.append("   - 小趋势方向（15分钟/1小时）")
    doc.append("   - 趋势是否一致")
    doc.append("")
    doc.append("2. **流动性确认**")
    doc.append("   - 流动性是否已被扫")
    doc.append("   - 当前流动性区域位置")
    doc.append("")
    doc.append("3. **市场结构确认**")
    doc.append("   - 是否在供给区/需求区")
    doc.append("   - 是否有养单行为")
    doc.append("")
    doc.append("4. **时间确认**")
    doc.append("   - 不是周末/周六")
    doc.append("   - 流动性充足的时间段")
    doc.append("")
    doc.append("5. **入场位置**")
    doc.append("   - 区间上下沿附近挂单")
    doc.append("   - 不追价，必须挂单等待")
    doc.append("")
    
    doc.append("### 步骤4：风险管理")
    doc.append("")
    doc.append("**止损设置**：")
    doc.append("- 位置：假突破不能打到的位置")
    doc.append("- 距离：通常几百点（根据区间大小调整）")
    doc.append("- 参考：流动性区域外，不破大周期EMA")
    doc.append("")
    doc.append("**止盈设置**：")
    doc.append("- 位置：区间上下沿或中间位置")
    doc.append("- 盈亏比：至少2倍")
    doc.append("- 分批止盈：50%在目标位置，50%看情况")
    doc.append("")
    
    # 四、特殊情况处理
    doc.append("## 四、特殊情况处理规则")
    doc.append("")
    
    doc.append("### 4.1 流动性被扫后的处理")
    doc.append("")
    doc.append("**规则**：")
    doc.append("1. 如果高点/低点被扫，重新评估市场方向")
    doc.append("2. 流动性被扫后，价格可能反转或继续原方向")
    doc.append("3. 需要观察价格在流动性区域附近的行为")
    doc.append("4. 如果流动性被扫后价格反转，考虑反向交易")
    doc.append("")
    doc.append("**示例**：")
    doc.append("\"今天日线偏多，但考虑到早上已经扫了，周五的高点，那么接下来，要么在1075-1092这个区间震荡，或者去找106低点\"")
    doc.append("")
    doc.append("**分析**：")
    doc.append("- 日线偏多（大趋势向上）")
    doc.append("- 但早上扫了周五高点（流动性被扫，可能反转）")
    doc.append("- 可能情景A：区间震荡（1075-1092）")
    doc.append("- 可能情景B：下跌找前低（106）")
    doc.append("")
    
    doc.append("### 4.2 市场结构变化的处理")
    doc.append("")
    doc.append("**规则**：")
    doc.append("1. 识别供给区/需求区")
    doc.append("2. 识别派发/吸筹行为")
    doc.append("3. 识别养单行为（养空头/养多头）")
    doc.append("4. 根据市场结构调整交易策略")
    doc.append("")
    doc.append("**示例**：")
    doc.append("\"目前来看，这段震荡区间跟106-1074那段区间相反，这段区间多头总是能赚，上一段区间空头总是能赚，判断106-1074是在养空头，那么这段到现在为止出现养多头行为！\"")
    doc.append("")
    doc.append("**分析**：")
    doc.append("- 识别出养单行为")
    doc.append("- 养空头 = 价格先上涨，然后下跌")
    doc.append("- 养多头 = 价格先下跌，然后上涨")
    doc.append("- 需要识别并避免被套")
    doc.append("")
    
    doc.append("### 4.3 多情景分析的处理")
    doc.append("")
    doc.append("**规则**：")
    doc.append("1. 列出所有可能的市场走势")
    doc.append("2. 为每个情景准备交易计划")
    doc.append("3. 根据市场发展选择对应的交易计划")
    doc.append("4. 如果市场不符合任何情景，等待或退出")
    doc.append("")
    doc.append("**示例**：")
    doc.append("\"要么在1075-1092这个区间震荡，或者去找106低点\"")
    doc.append("")
    doc.append("**处理**：")
    doc.append("- 情景A：价格在1075-1092震荡 → 区间交易")
    doc.append("- 情景B：价格下跌找106 → 等待或做空")
    doc.append("- 观察市场发展，选择对应的交易计划")
    doc.append("")
    
    # 五、完整的交易检查清单
    doc.append("## 五、完整交易检查清单（必须逐项确认）")
    doc.append("")
    doc.append("### A. 市场分析检查")
    doc.append("")
    doc.append("**趋势分析**：")
    doc.append("□ 1. 日线级别趋势（偏多/偏空）")
    doc.append("□ 2. 4小时趋势")
    doc.append("□ 3. 1小时趋势")
    doc.append("□ 4. 15分钟趋势")
    doc.append("□ 5. 多时间框架是否一致")
    doc.append("")
    doc.append("**流动性分析**：")
    doc.append("□ 6. 最近是否有流动性被扫（高点/低点）")
    doc.append("□ 7. 当前流动性区域在哪里")
    doc.append("□ 8. 流动性被扫后的市场反应如何")
    doc.append("□ 9. 是否有周五/周一效应")
    doc.append("")
    doc.append("**市场结构分析**：")
    doc.append("□ 10. 当前是供给区还是需求区")
    doc.append("□ 11. 是否有派发或吸筹行为")
    doc.append("□ 12. 是否有养单行为（养空头/养多头）")
    doc.append("□ 13. 市场结构是否支持当前交易方向")
    doc.append("")
    doc.append("**时间周期分析**：")
    doc.append("□ 14. 确认不是周末/周六")
    doc.append("□ 15. 确认流动性充足的时间段")
    doc.append("□ 16. 考虑周五/周一效应")
    doc.append("")
    doc.append("**情景规划**：")
    doc.append("□ 17. 列出所有可能的市场走势")
    doc.append("□ 18. 为每个情景准备了交易计划")
    doc.append("□ 19. 确定了最可能的情景")
    doc.append("")
    
    doc.append("### B. 交易区间检查")
    doc.append("")
    doc.append("□ 20. 已识别明确的震荡区间（价格实际震荡范围）")
    doc.append("□ 21. 区间宽度足够（通常100-500点）")
    doc.append("□ 22. 已使用Vegas通道确认区间边界")
    doc.append("□ 23. 已使用VWAP确认支撑阻力位置")
    doc.append("□ 24. 确认区间内价格来回震荡，不是单边趋势")
    doc.append("")
    
    doc.append("### C. 入场条件检查")
    doc.append("")
    doc.append("□ 25. 价格在区间上下沿附近")
    doc.append("□ 26. 大趋势方向确认（与交易方向一致）")
    doc.append("□ 27. 流动性分析完成（未被扫或已处理）")
    doc.append("□ 28. 市场结构支持交易方向")
    doc.append("□ 29. 已挂单（不追价）")
    doc.append("□ 30. 挂单价格合理（区间上下沿±10-20点）")
    doc.append("")
    
    doc.append("### D. 风险管理检查")
    doc.append("")
    doc.append("□ 31. 已设置止损（假突破不能打到）")
    doc.append("□ 32. 止损距离合理（通常几百点）")
    doc.append("□ 33. 止损在流动性区域外")
    doc.append("□ 34. 止损不破大周期EMA")
    doc.append("□ 35. 已设置止盈（2倍以上盈亏比）")
    doc.append("□ 36. 已计算仓位大小（风险不超过5%）")
    doc.append("□ 37. 已使用逐仓模式")
    doc.append("□ 38. 盈亏比≥2倍")
    doc.append("")
    
    doc.append("### E. 特殊情况检查")
    doc.append("")
    doc.append("□ 39. 已考虑流动性被扫的情况")
    doc.append("□ 40. 已识别市场结构（供给区/需求区）")
    doc.append("□ 41. 已识别养单行为（如有）")
    doc.append("□ 42. 已准备多情景交易计划")
    doc.append("□ 43. 确认不是单边行情")
    doc.append("")
    doc.append("")
    doc.append("**只有所有43项都确认后，才能执行交易！**")
    doc.append("")
    
    # 六、结合成熟交易系统理论
    doc.append("## 六、结合成熟交易系统理论")
    doc.append("")
    doc.append("### 6.1 ICT（Inner Circle Trader）概念")
    doc.append("")
    doc.append("De.的系统融合了ICT交易理论：")
    doc.append("")
    doc.append("1. **FVG（Fair Value Gap）**")
    doc.append("   - 价格跳空形成的价值缺口")
    doc.append("   - 价格回填FVG时是交易机会")
    doc.append("")
    doc.append("2. **Order Block（OB）**")
    doc.append("   - 机构订单区域")
    doc.append("   - 价格回到OB时是交易机会")
    doc.append("")
    doc.append("3. **OTE区间（Optimal Trade Entry）**")
    doc.append("   - 618-786斐波那契回撤区间")
    doc.append("   - 突破后回踩到OTE区间是入场机会")
    doc.append("")
    doc.append("4. **流动性（Liquidity）**")
    doc.append("   - 大量挂单的位置")
    doc.append("   - 流动性被扫后，价格可能反转")
    doc.append("")
    
    doc.append("### 6.2 市场微观结构理论")
    doc.append("")
    doc.append("1. **供给与需求**")
    doc.append("   - 供给区 = 大量卖单")
    doc.append("   - 需求区 = 大量买单")
    doc.append("   - 价格在供给区下跌，在需求区上涨")
    doc.append("")
    doc.append("2. **派发与吸筹**")
    doc.append("   - 派发 = 机构在高位卖出")
    doc.append("   - 吸筹 = 机构在低位买入")
    doc.append("   - 识别派发/吸筹区间，预测价格方向")
    doc.append("")
    doc.append("3. **市场操纵**")
    doc.append("   - 养单行为 = 制造假象，然后反向运行")
    doc.append("   - 识别养单行为，避免被套")
    doc.append("")
    
    doc.append("### 6.3 价格行为交易")
    doc.append("")
    doc.append("1. **支撑阻力**")
    doc.append("   - 使用Vegas通道识别")
    doc.append("   - 使用VWAP确认")
    doc.append("   - 结合流动性区域")
    doc.append("")
    doc.append("2. **价格形态**")
    doc.append("   - M顶/W底")
    doc.append("   - 回踩确认")
    doc.append("   - 假突破识别")
    doc.append("")
    
    # 七、实际案例分析
    doc.append("## 七、实际案例分析（深度解析）")
    doc.append("")
    
    doc.append("### 案例1：\"今天日线偏多，但考虑到早上已经扫了，周五的高点，那么接下来，要么在1075-1092这个区间震荡，或者去找106低点\"")
    doc.append("")
    doc.append("**深度分析**：")
    doc.append("")
    doc.append("**步骤1：趋势分析**")
    doc.append("- 日线偏多 = 大趋势向上")
    doc.append("- 这意味着长期方向是上涨")
    doc.append("")
    doc.append("**步骤2：关键事件分析**")
    doc.append("- \"早上已经扫了，周五的高点\"")
    doc.append("- 周五的高点 = 流动性区域")
    doc.append("- 被扫 = 流动性被吃掉")
    doc.append("- 影响：流动性被扫后，价格可能反转或继续原方向")
    doc.append("")
    doc.append("**步骤3：情景规划**")
    doc.append("- 情景A：区间震荡（1075-1092）")
    doc.append("  - 区间：10750-10920，宽度170点")
    doc.append("  - 交易策略：区间挂单交易")
    doc.append("  - 多单：10750附近挂单，止损10720，止盈10900")
    doc.append("  - 空单：10920附近挂单，止损10950，止盈10770")
    doc.append("")
    doc.append("- 情景B：趋势延续（去找106低点）")
    doc.append("  - 目标：10600（前低）")
    doc.append("  - 交易策略：等待下跌，在10600附近做多")
    doc.append("  - 或：如果跌破10600，做空")
    doc.append("")
    doc.append("**步骤4：交易计划**")
    doc.append("1. 观察价格行为，判断是情景A还是情景B")
    doc.append("2. 如果价格在1075-1092震荡 → 执行区间交易")
    doc.append("3. 如果价格下跌 → 等待10600附近的机会")
    doc.append("4. 根据市场发展调整策略")
    doc.append("")
    
    # 八、总结
    doc.append("## 八、系统总结")
    doc.append("")
    doc.append("### 核心原则")
    doc.append("")
    doc.append("1. **多维度分析**：趋势 + 流动性 + 市场结构 + 时间周期")
    doc.append("2. **多情景规划**：考虑所有可能的市场走势")
    doc.append("3. **严格风险管理**：止损 + 止盈 + 仓位管理")
    doc.append("4. **流动性优先**：关注流动性被扫的情况")
    doc.append("5. **市场结构识别**：供给区/需求区/派发/吸筹/养单")
    doc.append("6. **时间周期考虑**：避免周末交易，考虑周五/周一效应")
    doc.append("")
    doc.append("### 交易前必须完成")
    doc.append("")
    doc.append("1. 完整的市场分析（43项检查清单）")
    doc.append("2. 多情景交易计划")
    doc.append("3. 风险控制设置")
    doc.append("4. 特殊情况处理方案")
    doc.append("")
    doc.append("**只有完成所有检查后，才能执行交易！**")
    doc.append("")
    
    return "\n".join(doc)

def main():
    file_path = r"C:\Users\zuoho\Downloads\discord-msg\梦之队 - 梦梦 - 青沐 [1428778462981918951].html"
    
    print("=" * 80)
    print("深度分析De.的所有交易规则")
    print("=" * 80)
    print()
    
    messages = parse_json_file(file_path)
    de_messages = extract_de_messages(messages)
    
    print(f"总消息数: {len(messages)}")
    print(f"De.的消息数: {len(de_messages)}")
    
    all_rules = extract_all_trading_rules(de_messages)
    
    print(f"\n提取的规则分类:")
    print(f"  - 趋势分析: {len(all_rules['trend_analysis'])} 条")
    print(f"  - 流动性分析: {len(all_rules['liquidity_analysis'])} 条")
    print(f"  - 情景规划: {len(all_rules['scenario_planning'])} 条")
    print(f"  - 市场结构: {len(all_rules['market_structure'])} 条")
    print(f"  - 时间分析: {len(all_rules['time_analysis'])} 条")
    print(f"  - 价格行为: {len(all_rules['price_action'])} 条")
    print(f"  - 市场操纵: {len(all_rules['market_manipulation'])} 条")
    
    system_doc = generate_comprehensive_system(all_rules, de_messages)
    
    output_file = "De_trading_system_comprehensive.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(system_doc)
    
    print()
    print("=" * 80)
    print("完成！")
    print("=" * 80)
    print(f"完整交易系统（深度分析版）已保存到: {output_file}")
    print()
    print("主要特点：")
    print("  1. 多维度市场分析（趋势+流动性+市场结构+时间）")
    print("  2. 多情景规划（考虑所有可能的市场走势）")
    print("  3. 完整的43项检查清单")
    print("  4. 结合ICT和市场微观结构理论")
    print("  5. 深度案例分析")

if __name__ == "__main__":
    main()




