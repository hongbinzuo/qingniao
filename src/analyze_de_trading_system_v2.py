#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析交易员 De. 的交易系统 - 优化版
从Discord消息中提取交易信息，并查询GATE交易所API获取实际BTC价格
"""

import json
import re
from datetime import datetime, timezone
import requests
from typing import List, Dict, Optional
import time

def parse_json_file(file_path: str) -> List[Dict]:
    """解析JSON文件，提取消息数据"""
    print("正在读取文件...")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data.get('messages', [])

def extract_de_messages(messages: List[Dict]) -> List[Dict]:
    """提取De.的所有消息"""
    print("正在提取De.的消息...")
    de_messages = []
    for msg in messages:
        author = msg.get('author', {})
        if author.get('nickname') == 'De.':
            de_messages.append(msg)
    return de_messages

def get_gateio_price_at_timestamp(timestamp_str: str, retry=2) -> Optional[float]:
    """根据时间戳查询GATE交易所的BTC价格"""
    try:
        # 解析时间戳
        dt = datetime.fromisoformat(timestamp_str.replace('+08:00', ''))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        
        # 转换为Unix时间戳
        unix_ts = int(dt.timestamp())
        
        # 查询GATE.io API - 获取该时间点附近的K线数据
        url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        
        # 先尝试1分钟K线
        for interval in ['1m', '5m', '15m']:
            params = {
                'currency_pair': 'BTC_USDT',
                'interval': interval,
                'from': unix_ts - 300 if interval == '1m' else unix_ts - 900,
                'to': unix_ts + 300 if interval == '1m' else unix_ts + 900,
                'limit': 5
            }
            
            try:
                response = requests.get(url, params=params, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        # K线格式: [timestamp, volume, close, high, low, open]
                        closest_candle = min(data, key=lambda x: abs(int(x[0]) - unix_ts))
                        return float(closest_candle[2])  # close price
            except:
                continue
        
        return None
    except Exception as e:
        return None

def extract_price_from_content(content: str) -> List[float]:
    """从消息内容中提取价格数字"""
    # 匹配价格模式，如 1052, 1064, 1074, 1057, 1077等
    prices = re.findall(r'\b(\d{4,5})\b', content)
    # 过滤掉明显不是价格的值（如年份、ID等）
    filtered_prices = []
    for price in prices:
        try:
            p = float(price)
            # BTC价格通常在几千到十几万之间，这里假设是1000-200000范围
            if 1000 <= p <= 200000:
                filtered_prices.append(p)
        except:
            continue
    return filtered_prices

def analyze_trading_system(de_messages: List[Dict]) -> Dict:
    """分析交易系统"""
    print("正在分析交易系统...")
    system_info = {
        'trading_style': [],
        'stop_loss': [],
        'take_profit': [],
        'position_sizing': [],
        'risk_management': [],
        'trading_rules': [],
        'price_levels': [],
        'trades': []
    }
    
    for msg in de_messages:
        content = msg.get('content', '')
        timestamp = msg.get('timestamp', '')
        
        # 提取价格信息
        prices = extract_price_from_content(content)
        if prices:
            system_info['price_levels'].append({
                'timestamp': timestamp,
                'content': content,
                'prices': prices
            })
        
        # 识别交易系统特征
        if '剥头皮' in content:
            system_info['trading_style'].append({
                'timestamp': timestamp,
                'content': content
            })
        
        if '止损' in content:
            system_info['stop_loss'].append({
                'timestamp': timestamp,
                'content': content
            })
        
        if '止盈' in content:
            system_info['take_profit'].append({
                'timestamp': timestamp,
                'content': content
            })
        
        if '多单' in content or '空单' in content:
            # 提取交易记录
            trade_info = {
                'timestamp': timestamp,
                'content': content,
                'prices': prices
            }
            system_info['trades'].append(trade_info)
        
        if '区间' in content:
            system_info['trading_rules'].append({
                'timestamp': timestamp,
                'content': content
            })
        
        if '盈亏比' in content or '杠杆' in content or '逐仓' in content:
            system_info['risk_management'].append({
                'timestamp': timestamp,
                'content': content
            })
    
    return system_info

def generate_report(system_info: Dict, de_messages: List[Dict]) -> str:
    """生成分析报告"""
    report = []
    report.append("=" * 80)
    report.append("交易员 De. 的交易系统分析报告")
    report.append("=" * 80)
    report.append("")
    
    # 简要说明
    report.append("## 一、交易系统简要说明")
    report.append("")
    report.append("**交易风格**: 短线剥头皮交易（Scalping）")
    report.append("**主要标的**: BTC/USDT")
    report.append("**止损特点**: 窄止损，通常几百点")
    report.append("**交易方式**: 区间震荡挂单交易")
    report.append("**风险控制**: 逐仓模式，固定2倍以上盈亏比")
    report.append("")
    
    # 详细说明
    report.append("## 二、交易系统详细说明")
    report.append("")
    
    # 交易风格
    report.append("### 1. 交易风格")
    report.append("")
    report.append("- **剥头皮交易（Scalping）**: 在震荡区间内进行快速进出场交易")
    report.append("- **区间交易**: 识别价格震荡区间，在区间上下沿附近挂单")
    report.append("- **挂单交易**: 不追涨杀跌，提前在关键位置挂单等待成交")
    report.append("- **短线持仓**: 持仓时间短，通常在区间内快速获利了结")
    report.append("")
    
    # 止损策略
    report.append("### 2. 止损策略")
    report.append("")
    report.append("- **止损位置**: 设置在假突破不能打到的位置")
    report.append("- **止损距离**: 通常几百点（BTC价格）")
    report.append("- **止损逻辑**: 找好流动性区域，止损设置在流动性区域之外")
    report.append("- **爆单即止损**: 使用逐仓模式，爆单即止损，算好止损线杠杆刚好拉到止损线")
    report.append("")
    
    # 止盈策略
    report.append("### 3. 止盈策略")
    report.append("")
    report.append("- **止盈位置**: 在区间上下沿差一点点的位置，或者中间位置")
    report.append("- **止盈逻辑**: 打掉上一个低点就走（剥头皮止盈理由）")
    report.append("- **分批平仓**: 部分仓位在目标位置平仓，保留部分仓位")
    report.append("")
    
    # 风险控制
    report.append("### 4. 风险控制")
    report.append("")
    report.append("- **仓位管理**: 100油账户，一次10-20油")
    report.append("- **盈亏比**: 固定2倍以上盈亏比")
    report.append("- **杠杆使用**: 逐仓模式，根据止损距离调整杠杆")
    report.append("- **单边行情**: 遇到单边行情及时止损，避免死扛")
    report.append("")
    
    # 交易规则
    report.append("### 5. 核心交易规则")
    report.append("")
    key_rules = [
        "识别震荡区间，在区间上下沿附近挂单",
        "止损设置在假突破不能打到的位置",
        "止盈在区间上下沿差一点点的位置或中间位置",
        "突破回踩有假动作，刺破618但在786以内（ICT OTE区间）",
        "M顶回踩腰线做空好点位",
        "震荡区间挂单，越到后面越不灵，需要及时调整",
        "突破区间后，止损重开，直接做下一个区间"
    ]
    for i, rule in enumerate(key_rules, 1):
        report.append(f"{i}. {rule}")
    report.append("")
    
    # 交易记录
    report.append("## 三、交易记录（含GATE交易所价格验证）")
    report.append("")
    
    # 提取所有交易记录
    print("正在提取交易记录...")
    trades = []
    for i, msg in enumerate(de_messages):
        if i % 100 == 0:
            print(f"  处理进度: {i}/{len(de_messages)}")
        
        content = msg.get('content', '')
        timestamp = msg.get('timestamp', '')
        
        # 识别交易相关消息
        if any(keyword in content for keyword in ['多单', '空单', '平', '挂单', '开', '加仓']):
            prices = extract_price_from_content(content)
            if prices or any(keyword in content for keyword in ['多单', '空单']):
                # 查询实际价格（限制查询数量以避免API限制）
                actual_price = None
                if len(trades) < 30:  # 只查询前30条的价格
                    actual_price = get_gateio_price_at_timestamp(timestamp)
                    time.sleep(0.2)  # 避免请求过快
                
                trades.append({
                    'timestamp': timestamp,
                    'content': content,
                    'mentioned_prices': prices,
                    'actual_price': actual_price
                })
    
    # 输出交易记录
    print(f"找到 {len(trades)} 条交易记录")
    for i, trade in enumerate(trades[:30], 1):  # 限制前30条
        report.append(f"### 交易记录 {i}")
        report.append(f"**时间**: {trade['timestamp']}")
        report.append(f"**消息内容**: {trade['content']}")
        if trade['mentioned_prices']:
            report.append(f"**提及价格**: {', '.join([f'${p:,.0f}' for p in trade['mentioned_prices']])}")
        if trade['actual_price']:
            report.append(f"**GATE交易所实际价格**: ${trade['actual_price']:,.2f}")
        else:
            report.append(f"**GATE交易所实际价格**: 未查询（避免API限制）")
        report.append("")
    
    # 关键价格水平
    report.append("## 四、关键价格水平分析")
    report.append("")
    
    # 提取关键价格区间
    print("正在提取关键价格水平...")
    key_levels = []
    for msg in de_messages:
        content = msg.get('content', '')
        if '区间' in content or any(p in content for p in ['106', '107', '105', '110', '112']):
            prices = extract_price_from_content(content)
            if prices:
                key_levels.append({
                    'timestamp': msg.get('timestamp', ''),
                    'content': content,
                    'prices': prices
                })
    
    # 去重并排序
    seen = set()
    unique_levels = []
    for level in key_levels:
        key = tuple(sorted(level['prices']))
        if key not in seen and len(key) > 0:
            seen.add(key)
            unique_levels.append(level)
    
    for i, level in enumerate(unique_levels[:15], 1):  # 前15个
        report.append(f"### 价格水平 {i}")
        report.append(f"**时间**: {level['timestamp']}")
        report.append(f"**内容**: {level['content']}")
        report.append(f"**价格水平**: {', '.join([f'${p:,.0f}' for p in level['prices']])}")
        report.append("")
    
    return "\n".join(report)

def main():
    file_path = r"C:\Users\zuoho\Downloads\discord-msg\梦之队 - 梦梦 - 青沐 [1428778462981918951].html"
    
    print("=" * 80)
    print("开始分析交易员 De. 的交易系统")
    print("=" * 80)
    print()
    
    messages = parse_json_file(file_path)
    print(f"[OK] 共找到 {len(messages)} 条消息")
    
    de_messages = extract_de_messages(messages)
    print(f"[OK] 共找到 {len(de_messages)} 条De.的消息")
    
    system_info = analyze_trading_system(de_messages)
    print(f"[OK] 分析完成")
    print(f"  - 交易风格相关: {len(system_info['trading_style'])} 条")
    print(f"  - 止损相关: {len(system_info['stop_loss'])} 条")
    print(f"  - 止盈相关: {len(system_info['take_profit'])} 条")
    print(f"  - 交易记录: {len(system_info['trades'])} 条")
    print(f"  - 价格水平: {len(system_info['price_levels'])} 条")
    print()
    
    print("正在生成报告（查询GATE交易所价格可能需要一些时间）...")
    report = generate_report(system_info, de_messages)
    
    # 保存报告
    output_file = "De_trading_system_analysis.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n[OK] 报告已保存到: {output_file}")
    print("\n" + "=" * 80)
    print("分析完成！")
    print("=" * 80)

if __name__ == "__main__":
    main()

