#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""运行Dream流水线处理所有Discord导出文件（直接调用，避免命令行编码问题）"""
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 添加src目录到路径
SRC = Path(__file__).resolve().parent.parent / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager
from dream_run_pipeline import (
    load_json_any, norm_ts, contextual_extract_trades, 
    build_events, fetch_klines, first_hit, _find_symbols_lean
)
import json
import hashlib

def main():
    # 查找所有Discord导出文件
    discord_dir = Path(r'C:\Users\zuoho\Downloads\discord-msg')
    json_files = [
        discord_dir / 'Direct Messages - 知更 [1361229030715687024].json',
        discord_dir / '梦之队 - 梦梦 - 梦梦-个人交易 [1417055357426991134].json',
        discord_dir / '梦之队 - 梦梦 - 青沐 [1428778462981918951].json',
    ]
    
    # 过滤存在的文件
    existing_files = [f for f in json_files if f.exists()]
    
    if not existing_files:
        print("❌ 未找到文件")
        return
    
    print(f"📁 找到 {len(existing_files)} 个文件:")
    for f in existing_files:
        print(f"   - {f.name} ({f.stat().st_size / 1024 / 1024:.2f} MB)")
    
    # 加载所有消息
    print(f"\n📥 加载消息...")
    all_msgs = []
    for f in existing_files:
        try:
            msgs = load_json_any(f)
            all_msgs.extend(msgs)
            print(f"   ✓ {f.name}: {len(msgs)} 条消息")
        except Exception as e:
            print(f"   ✗ {f.name}: 加载失败 - {e}")
    
    print(f"\n📊 总计: {len(all_msgs)} 条消息")
    
    if not all_msgs:
        print("❌ 没有消息可处理")
        return
    
    # 1) 导入对话（去重）
    print(f"\n💾 导入对话到数据库...")
    db = TraderDBManager('dream')
    conn = db._get_connection()
    
    # 检查已存在的对话
    existing_conv_hashes = set()
    try:
        existing = conn.execute('SELECT timestamp, trader_message FROM conversations WHERE source = ?', ('dream',)).fetchall()
        for row in existing:
            ts, msg = row[0] if len(row) > 0 else '', row[1] if len(row) > 1 else ''
            if ts and msg:
                hash_val = hashlib.md5(f"{ts}|{msg}".encode('utf-8')).hexdigest()
                existing_conv_hashes.add(hash_val)
    except Exception as e:
        print(f"⚠️ 检查已存在对话时出错: {e}")
    
    new_conv_count = 0
    for m in all_msgs:
        ts = norm_ts(m.get('timestamp',''))
        txt = m.get('text','')
        if not txt:
            continue
        # 检查是否已存在
        hash_val = hashlib.md5(f"{ts}|{txt}".encode('utf-8')).hexdigest()
        if hash_val in existing_conv_hashes:
            continue
        db.add_conversation(timestamp=ts, user_message=None, trader_message=txt, source='dream', btc_price=None, extracted_content=None)
        new_conv_count += 1
        existing_conv_hashes.add(hash_val)
    
    print(f"   ✓ 新增 {new_conv_count} 条，跳过 {len(all_msgs) - new_conv_count} 条重复")
    
    # 2) 抽取交易
    print(f"\n🔍 抽取交易信息...")
    trade_rows = contextual_extract_trades(all_msgs)
    print(f"   ✓ 抽取到 {len(trade_rows)} 条交易记录")
    
    # 写入交易记录（去重）
    existing_trade_keys = set()
    try:
        existing_trades = conn.execute('''
            SELECT timestamp, symbol, direction, entry_price FROM trade_records 
            WHERE source = ? AND timestamp IS NOT NULL
        ''', ('dream',)).fetchall()
        for row in existing_trades:
            ts, sym, dir, entry = row[0] if len(row) > 0 else '', row[1] if len(row) > 1 else None, row[2] if len(row) > 2 else None, row[3] if len(row) > 3 else None
            key = f"{ts}|{sym}|{dir}|{entry}"
            existing_trade_keys.add(key)
    except Exception as e:
        print(f"⚠️ 检查已存在交易时出错: {e}")
    
    inserted = []
    new_trade_count = 0
    for tr in trade_rows:
        key = f"{tr['timestamp']}|{tr.get('symbol')}|{tr.get('side')}|{tr.get('entry')}"
        if key in existing_trade_keys:
            continue
        rid = db.add_trade_record(
            timestamp=tr['timestamp'], symbol=tr['symbol'], direction=tr.get('side'),
            entry_price=tr.get('entry'), exit_price=None, profit_pct=None, profit_usdt=None,
            strategy='dream_extract', screenshot_path=None, text_content=tr.get('raw'), source='dream')
        tr2 = dict(tr)
        tr2['id'] = rid
        inserted.append(tr2)
        existing_trade_keys.add(key)
        new_trade_count += 1
    
    print(f"   ✓ 新增 {new_trade_count} 条，跳过 {len(trade_rows) - new_trade_count} 条重复")
    
    # 3) 评估（简化版，只评估新插入的交易）
    if inserted:
        print(f"\n📈 评估交易结果...")
        print(f"   ⚠️ 评估功能需要K线数据，可能需要较长时间...")
        print(f"   💡 建议使用完整流水线脚本进行详细评估")
    
    print(f"\n✅ 处理完成！")
    print(f"   - 对话: 新增 {new_conv_count} 条")
    print(f"   - 交易: 新增 {new_trade_count} 条")
    
    db.close()

if __name__ == '__main__':
    main()
