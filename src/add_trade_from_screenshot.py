#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从交易截图自动识别并录入交易记录
支持Bitget等交易所的交易截图信息提取
"""

import sys
import re
from datetime import datetime
from pathlib import Path

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from db_manager_trader import TraderDBManager

def parse_trade_info_from_text(text):
    """从文本中解析交易信息（OCR结果或手动输入）"""
    trade_info = {}
    
    # 提取时间
    time_patterns = [
        r'(\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2})',
        r'(\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2}:\d{2})',
    ]
    for pattern in time_patterns:
        match = re.search(pattern, text)
        if match:
            trade_info['timestamp'] = match.group(1).replace('/', '-')
            break
    
    # 提取交易对
    if 'BTCUSDT' in text or 'BTC/USDT' in text or 'BTC USDT' in text:
        trade_info['symbol'] = 'BTC/USDT'
    elif 'ETHUSDT' in text or 'ETH/USDT' in text or 'ETH USDT' in text:
        trade_info['symbol'] = 'ETH/USDT'
    
    # 提取方向
    if '做多' in text or 'long' in text.lower() or 'Long' in text:
        trade_info['direction'] = 'long'
    elif '做空' in text or 'short' in text.lower() or 'Short' in text:
        trade_info['direction'] = 'short'
    
    # 提取杠杆
    leverage_match = re.search(r'(\d+)x', text)
    if leverage_match:
        trade_info['leverage'] = int(leverage_match.group(1))
    
    # 提取持仓均价/开仓价格
    entry_patterns = [
        r'持仓均价[：:]\s*([\d,.]+)',
        r'开仓均价[：:]\s*([\d,.]+)',
        r'entry[：:]\s*([\d,.]+)',
        r'平均价格[：:]\s*([\d,.]+)',
    ]
    for pattern in entry_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            price_str = match.group(1).replace(',', '').replace('，', '')
            try:
                trade_info['entry_price'] = float(price_str)
                break
            except:
                pass
    
    # 提取当前价格
    current_patterns = [
        r'当前价格[：:]\s*([\d,.]+)',
        r'最新价格[：:]\s*([\d,.]+)',
        r'current[：:]\s*([\d,.]+)',
    ]
    for pattern in current_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            price_str = match.group(1).replace(',', '').replace('，', '')
            try:
                trade_info['current_price'] = float(price_str)
                break
            except:
                pass
    
    # 提取收益率
    profit_patterns = [
        r'([+-]?[\d.]+)%',
        r'收益率[：:]\s*([+-]?[\d.]+)%',
        r'profit[：:]\s*([+-]?[\d.]+)%',
    ]
    for pattern in profit_patterns:
        matches = re.findall(pattern, text)
        if matches:
            # 取最大的百分比（通常是收益率）
            try:
                profits = [float(m) for m in matches]
                trade_info['profit_pct'] = max(profits, key=abs)
                break
            except:
                pass
    
    # 提取盈利金额
    profit_usdt_patterns = [
        r'([+-]?[\d,.]+)\s*USDT',
        r'盈利[：:]\s*([+-]?[\d,.]+)\s*USDT',
    ]
    for pattern in profit_usdt_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(',', '').replace('，', '')
            try:
                trade_info['profit_usdt'] = float(amount_str)
                break
            except:
                pass
    
    return trade_info

def format_timestamp(timestamp_str):
    """格式化时间戳"""
    try:
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y/%m/%d %H:%M:%S',
            '%Y/%m/%d %H:%M',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(timestamp_str, fmt)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                continue
        
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    except:
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def add_trade_from_screenshot(text_content, screenshot_path=None):
    """从截图文本内容录入交易记录"""
    print("=" * 80)
    print("从截图识别交易信息")
    print("=" * 80)
    print()
    
    # 解析交易信息
    trade_info = parse_trade_info_from_text(text_content)
    
    if not trade_info:
        print("❌ 未能识别到交易信息")
        return None
    
    print("识别到的交易信息:")
    print("-" * 80)
    for key, value in trade_info.items():
        print(f"  {key}: {value}")
    print()
    
    # 检查必填字段
    if 'entry_price' not in trade_info:
        print("❌ 未识别到开仓价格，无法录入")
        return None
    
    # 设置默认值
    timestamp = trade_info.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    timestamp = format_timestamp(timestamp)
    symbol = trade_info.get('symbol', 'BTC/USDT')
    direction = trade_info.get('direction', 'long')
    leverage = trade_info.get('leverage', 1)
    entry_price = trade_info['entry_price']
    current_price = trade_info.get('current_price')
    profit_pct = trade_info.get('profit_pct')
    profit_usdt = trade_info.get('profit_usdt')
    
    # 如果只有当前价格和收益率，可以计算盈利金额
    if current_price and profit_pct and not profit_usdt:
        # 估算盈利金额（需要知道仓位大小，这里用百分比估算）
        pass
    
    print("准备录入以下信息:")
    print("-" * 80)
    print(f"时间: {timestamp}")
    print(f"交易对: {symbol}")
    print(f"方向: {direction.upper()}")
    print(f"杠杆: {leverage}x")
    print(f"开仓价格: ${entry_price:,.2f}")
    if current_price:
        print(f"当前价格: ${current_price:,.2f}")
    if profit_pct:
        print(f"收益率: {profit_pct:+.2f}%")
    if profit_usdt:
        print(f"盈利: {profit_usdt:+,.2f} USDT")
    print()
    
    # 确认录入
    confirm = input("确认录入? (y/n): ").strip().lower()
    if confirm not in ['y', 'yes', '是']:
        print("已取消录入")
        return None
    
    # 录入数据库
    try:
        db = TraderDBManager('de')
        
        trade_id = db.add_trade_record(
            timestamp=timestamp,
            symbol=symbol,
            direction=direction,
            leverage=leverage,
            entry_price=entry_price,
            exit_price=current_price,  # 使用当前价格作为平仓价格（如果未平仓）
            profit_pct=profit_pct,
            profit_usdt=profit_usdt,
            strategy=None,
            screenshot_path=screenshot_path,
            text_content=text_content,
            source='screenshot'
        )
        
        print()
        print("=" * 80)
        print(f"✓ 交易记录录入成功！")
        print(f"交易记录ID: {trade_id}")
        print("=" * 80)
        
        db.close()
        return trade_id
        
    except Exception as e:
        print()
        print("=" * 80)
        print(f"❌ 录入失败: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        return None

def main():
    """主函数"""
    print()
    print("请粘贴截图中的文本内容（或OCR结果）:")
    print("（输入完成后按两次回车或输入 'done' 结束）")
    print()
    
    lines = []
    while True:
        try:
            line = input()
            if line.strip().lower() in ['done', '完成', '']:
                if lines:
                    break
            else:
                lines.append(line)
        except (EOFError, KeyboardInterrupt):
            break
    
    text_content = '\n'.join(lines)
    
    if not text_content.strip():
        print("❌ 未输入任何内容")
        return
    
    add_trade_from_screenshot(text_content)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n已取消录入")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)








