#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查ABU系统运行状态
"""

import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

try:
    from db_manager_trader import TraderDBManager
    import duckdb
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    sys.exit(1)

def check_processes():
    """检查进程状态"""
    import subprocess
    print("=" * 80)
    print("🔍 进程检查")
    print("=" * 80)
    
    try:
        result = subprocess.run(
            ['wmic', 'process', 'where', "name='python.exe'", 'get', 'processid,commandline'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        pattern_running = 'auto_signal_generator.py' in result.stdout
        vision_running = 'abu_vision_scanner_4h.py' in result.stdout
        
        print(f"模式匹配系统: {'✅ 运行中' if pattern_running else '❌ 未运行'}")
        print(f"视觉匹配系统: {'✅ 运行中' if vision_running else '❌ 未运行'}")
        print()
        
        return pattern_running, vision_running
    except Exception as e:
        print(f"⚠️  进程检查失败: {e}")
        print()
        return None, None

def check_database():
    """检查数据库状态"""
    print("=" * 80)
    print("📊 数据库状态")
    print("=" * 80)
    
    try:
        db = TraderDBManager(trader_id='abu')
        conn = db._get_connection(read_only=True)
        
        # 检查最新信号
        latest_signals = conn.execute('''
            SELECT id, signal_time, symbol, timeframe, signal_type, 
                   entry_price, status, score, created_at
            FROM trading_signals
            WHERE system_name = 'abu'
            ORDER BY created_at DESC
            LIMIT 10
        ''').fetchall()
        
        print(f"\n📈 最新信号 (最近10条):")
        if latest_signals:
            for sig in latest_signals:
                sig_id, sig_time, symbol, tf, sig_type, entry, status, score, created = sig
                print(f"  [{sig_id}] {symbol} {tf} {sig_type.upper()} @ {entry:.2f} | "
                      f"状态: {status} | 评分: {score:.2f} | 时间: {created}")
        else:
            print("  ⚠️  暂无信号记录")
        
        # 统计信息
        stats = conn.execute('''
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
                COUNT(CASE WHEN status = 'active' THEN 1 END) as active,
                COUNT(CASE WHEN status = 'stopped' THEN 1 END) as stopped,
                COUNT(CASE WHEN status = 'full_tp' THEN 1 END) as full_tp,
                MAX(created_at) as latest
            FROM trading_signals
            WHERE system_name = 'abu'
        ''').fetchone()
        
        total, pending, active, stopped, full_tp, latest = stats
        print(f"\n📊 信号统计:")
        print(f"  总计: {total}")
        print(f"  待激活: {pending}")
        print(f"  已激活: {active}")
        print(f"  已止损: {stopped}")
        print(f"  已止盈: {full_tp}")
        if latest:
            print(f"  最新信号时间: {latest}")
        
        # 检查视觉匹配结果
        vision_results = conn.execute('''
            SELECT COUNT(*) as count, MAX(created_at) as latest
            FROM vision_matching_results
            WHERE created_at >= date('now', '-7 days')
        ''').fetchone()
        
        if vision_results:
            count, latest = vision_results
            print(f"\n👁️  视觉匹配 (最近7天):")
            print(f"  匹配次数: {count}")
            if latest:
                print(f"  最新匹配: {latest}")
        
        db.close()
        print()
        
    except Exception as e:
        print(f"❌ 数据库检查失败: {e}")
        import traceback
        traceback.print_exc()
        print()

def check_recent_files():
    """检查最近生成的文件"""
    print("=" * 80)
    print("📁 最近生成的文件")
    print("=" * 80)
    
    trading_plans_dir = ROOT / 'outputs' / 'trading_plans'
    if trading_plans_dir.exists():
        plans = sorted(trading_plans_dir.glob('auto_generated_*.md'), 
                      key=lambda x: x.stat().st_mtime, reverse=True)[:5]
        print(f"\n📋 交易计划 (最近5个):")
        for plan in plans:
            mtime = datetime.fromtimestamp(plan.stat().st_mtime)
            print(f"  {plan.name} - {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
    
    vision_dir = ROOT / 'outputs' / 'vision_matching'
    if vision_dir.exists():
        results = sorted(vision_dir.glob('vision_results_*.json'),
                        key=lambda x: x.stat().st_mtime, reverse=True)[:3]
        print(f"\n👁️  视觉匹配结果 (最近3个):")
        for result in results:
            mtime = datetime.fromtimestamp(result.stat().st_mtime)
            print(f"  {result.name} - {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
    
    print()

def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("🚀 ABU系统状态检查")
    print("=" * 80)
    print()
    
    # 检查进程
    pattern_running, vision_running = check_processes()
    
    # 检查数据库
    check_database()
    
    # 检查文件
    check_recent_files()
    
    # 总结
    print("=" * 80)
    print("📝 总结")
    print("=" * 80)
    if pattern_running and vision_running:
        print("✅ 系统运行正常")
    elif pattern_running or vision_running:
        print("⚠️  部分系统运行中")
    else:
        print("❌ 系统未运行，请运行 'Abu全部启动.bat'")
    print()

if __name__ == '__main__':
    main()
