#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
De.交易员交易记录录入工具
交互式录入交易记录到数据库
"""

import sys
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

def get_input(prompt, default=None, input_type=str):
    """获取用户输入"""
    if default is not None:
        prompt = f"{prompt} (默认: {default}): "
    else:
        prompt = f"{prompt}: "
    
    try:
        value = input(prompt).strip()
        if not value and default is not None:
            return default
        if not value:
            return None
        
        if input_type == int:
            return int(value)
        elif input_type == float:
            return float(value)
        elif input_type == bool:
            return value.lower() in ['y', 'yes', '是', '1', 'true']
        else:
            return value
    except (ValueError, KeyboardInterrupt):
        return None

def format_timestamp(timestamp_str):
    """格式化时间戳"""
    try:
        # 尝试多种格式
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y/%m/%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y/%m/%d %H:%M',
            '%Y-%m-%d',
            '%Y/%m/%d'
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(timestamp_str, fmt)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                continue
        
        # 如果都失败，返回当前时间
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    except:
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def add_trade_record_interactive():
    """交互式添加交易记录"""
    print("=" * 80)
    print("De.交易员交易记录录入")
    print("=" * 80)
    print()
    
    # 初始化数据库
    try:
        db = TraderDBManager('de')
        print("✓ 数据库连接成功")
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return
    
    print()
    print("请填写交易信息（直接回车使用默认值或跳过）")
    print("-" * 80)
    
    # 基本信息
    timestamp_str = get_input("交易时间", default=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    if not timestamp_str:
        timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    timestamp = format_timestamp(timestamp_str)
    
    symbol = get_input("交易对", default='BTC/USDT')
    if not symbol:
        symbol = 'BTC/USDT'
    
    # 方向
    direction_input = get_input("方向 (long/short)", default='long')
    if direction_input:
        direction = 'long' if direction_input.lower() in ['long', 'l', '多', '做多'] else 'short'
    else:
        direction = 'long'
    
    # 杠杆
    leverage = get_input("杠杆倍数", default=1, input_type=int)
    if leverage is None:
        leverage = 1
    
    # 价格信息
    entry_price = get_input("开仓价格 (USD)", input_type=float)
    if entry_price is None:
        print("❌ 开仓价格是必填项")
        return
    
    exit_price = get_input("平仓价格 (USD，未平仓可留空)", input_type=float)
    
    # 盈亏信息
    profit_pct = get_input("收益率 (%)", input_type=float)
    profit_usdt = get_input("盈利金额 (USDT)", input_type=float)
    
    # 策略信息
    strategy = get_input("策略名称（可选）")
    
    # 其他信息
    screenshot_path = get_input("截图路径（可选）")
    text_content = get_input("备注信息（可选）")
    
    source = get_input("数据来源", default='manual')
    if not source:
        source = 'manual'
    
    print()
    print("-" * 80)
    print("交易信息确认:")
    print("-" * 80)
    print(f"时间: {timestamp}")
    print(f"交易对: {symbol}")
    print(f"方向: {direction.upper()}")
    print(f"杠杆: {leverage}x")
    print(f"开仓价格: ${entry_price:,.2f}")
    if exit_price:
        print(f"平仓价格: ${exit_price:,.2f}")
    if profit_pct is not None:
        print(f"收益率: {profit_pct:+.2f}%")
    if profit_usdt is not None:
        print(f"盈利: {profit_usdt:+,.2f} USDT")
    if strategy:
        print(f"策略: {strategy}")
    if screenshot_path:
        print(f"截图: {screenshot_path}")
    if text_content:
        print(f"备注: {text_content}")
    print()
    
    # 确认
    confirm = get_input("确认录入? (y/n)", default='y', input_type=bool)
    if not confirm:
        print("已取消录入")
        return
    
    # 录入数据库
    try:
        trade_id = db.add_trade_record(
            timestamp=timestamp,
            symbol=symbol,
            direction=direction,
            leverage=leverage,
            entry_price=entry_price,
            exit_price=exit_price,
            profit_pct=profit_pct,
            profit_usdt=profit_usdt,
            strategy=strategy,
            screenshot_path=screenshot_path,
            text_content=text_content,
            source=source
        )
        
        print()
        print("=" * 80)
        print(f"✓ 交易记录录入成功！")
        print(f"交易记录ID: {trade_id}")
        print("=" * 80)
        
        # 关闭数据库连接
        db.close()
        
    except Exception as e:
        print()
        print("=" * 80)
        print(f"❌ 录入失败: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()

def batch_add_from_text():
    """从文本批量录入"""
    print("=" * 80)
    print("批量录入交易记录（从文本）")
    print("=" * 80)
    print()
    print("请输入交易记录文本（每行一条，格式：时间|交易对|方向|杠杆|开仓价|平仓价|收益率|盈利）")
    print("示例: 2025-12-30 10:00:00|BTC/USDT|long|10|87000|87500|5.75|575")
    print("输入 'done' 或 '完成' 结束录入")
    print()
    
    try:
        db = TraderDBManager('de')
        print("✓ 数据库连接成功")
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return
    
    count = 0
    while True:
        line = input("> ").strip()
        if not line or line.lower() in ['done', '完成', 'exit', '退出']:
            break
        
        try:
            parts = line.split('|')
            if len(parts) < 5:
                print("⚠️  格式错误，跳过")
                continue
            
            timestamp = format_timestamp(parts[0].strip())
            symbol = parts[1].strip() if len(parts) > 1 else 'BTC/USDT'
            direction = 'long' if parts[2].strip().lower() in ['long', 'l', '多'] else 'short'
            leverage = int(parts[3].strip()) if len(parts) > 3 else 1
            entry_price = float(parts[4].strip()) if len(parts) > 4 else None
            exit_price = float(parts[5].strip()) if len(parts) > 5 else None
            profit_pct = float(parts[6].strip()) if len(parts) > 6 else None
            profit_usdt = float(parts[7].strip()) if len(parts) > 7 else None
            
            if entry_price is None:
                print("⚠️  开仓价格缺失，跳过")
                continue
            
            trade_id = db.add_trade_record(
                timestamp=timestamp,
                symbol=symbol,
                direction=direction,
                leverage=leverage,
                entry_price=entry_price,
                exit_price=exit_price,
                profit_pct=profit_pct,
                profit_usdt=profit_usdt,
                source='batch'
            )
            
            count += 1
            print(f"✓ 已录入 (ID: {trade_id})")
            
        except Exception as e:
            print(f"⚠️  录入失败: {e}")
            continue
    
    print()
    print("=" * 80)
    print(f"✓ 批量录入完成，共录入 {count} 条记录")
    print("=" * 80)
    
    db.close()

def main():
    """主函数"""
    print()
    print("请选择录入方式:")
    print("1. 交互式录入（单条）")
    print("2. 批量录入（从文本）")
    print()
    
    choice = input("请选择 (1/2): ").strip()
    
    if choice == '2':
        batch_add_from_text()
    else:
        add_trade_record_interactive()

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




