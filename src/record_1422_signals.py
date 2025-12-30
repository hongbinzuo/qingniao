#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接录入14:22信号数据到数据库
"""

import sys
from datetime import datetime
from db_manager_trader import TraderDBManager

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


def main():
    db = TraderDBManager('de')
    
    try:
        signal_time = "2025-12-30 14:22:27"
        
        print("="*80)
        print("录入14:22信号数据")
        print("="*80)
        print("")
        
        # 信号1: 15分钟做空信号
        print("录入信号1: 15分钟做空信号...")
        signal1_id = db.add_trading_signal(
            signal_time=signal_time,
            timeframe='15m',
            signal_type='short',
            entry_price=87824,
            stop_loss=88087,
            take_profit_1=86493,
            take_profit_2=85620,
            entry_model='阻力位回落(量能大)',
            strength='strong',
            risk_reward_ratio=6.71,
            volatility_level='low',
            system_name='de'
        )
        print(f"✅ 信号1 ID: {signal1_id}")
        
        # 直接使用SQL插入评估记录
        conn = db._get_connection()
        try:
            # 检查是否已存在评估记录
            existing = conn.execute('''
                SELECT id FROM signal_evaluations WHERE signal_id = ?
            ''', (signal1_id,)).fetchone()
            
            if existing:
                print(f"⚠️ 评估记录已存在: ID={existing[0]}, 跳过", file=sys.stderr)
                eval1_id = existing[0]
            else:
                # 获取下一个ID
                max_id = conn.execute('SELECT COALESCE(MAX(id), 0) FROM signal_evaluations').fetchone()[0]
                eval1_id = max_id + 1
                
                # 直接插入
                eval_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                conn.execute('''
                    INSERT INTO signal_evaluations 
                    (id, signal_id, evaluation_time, result, actual_entry_price, actual_exit_price,
                     actual_profit_pct, stop_loss_hit, take_profit_1_hit, take_profit_2_hit, 
                     missed, notes, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (eval1_id, signal1_id, eval_time, 'stopped', 87824, 88087, -0.30, 
                      1, 0, 0, 0, "止损距离过小(0.30%); 最大浮盈+0.16%; 被市场噪音触发止损", eval_time))
                conn.commit()
                
                # 更新信号状态（分开执行）
                conn.execute('''
                    UPDATE trading_signals 
                    SET status = ?, updated_at = ?
                    WHERE id = ?
                ''', ('stopped', eval_time, signal1_id))
                conn.commit()
                print(f"✅ 评估1 ID: {eval1_id}")
        except Exception as e:
            print(f"⚠️ 添加评估记录失败: {e}", file=sys.stderr)
            conn.rollback()
        print("")
        
        # 信号2: 1小时做多信号
        print("录入信号2: 1小时做多信号...")
        signal2_id = db.add_trading_signal(
            signal_time=signal_time,
            timeframe='1h',
            signal_type='long',
            entry_price=87018,
            stop_loss=86700,
            take_profit_1=88241,
            take_profit_2=89114,
            entry_model='支撑位反弹(量能大)',
            strength='strong',
            risk_reward_ratio=5.21,
            volatility_level='high',
            system_name='de'
        )
        print(f"✅ 信号2 ID: {signal2_id}")
        
        # 直接使用SQL插入评估记录
        try:
            # 检查是否已存在评估记录
            existing = conn.execute('''
                SELECT id FROM signal_evaluations WHERE signal_id = ?
            ''', (signal2_id,)).fetchone()
            
            if existing:
                print(f"⚠️ 评估记录已存在: ID={existing[0]}, 跳过", file=sys.stderr)
                eval2_id = existing[0]
            else:
                # 获取下一个ID
                max_id = conn.execute('SELECT COALESCE(MAX(id), 0) FROM signal_evaluations').fetchone()[0]
                eval2_id = max_id + 1
                
                # 直接插入
                eval_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                conn.execute('''
                    INSERT INTO signal_evaluations 
                    (id, signal_id, evaluation_time, result, actual_entry_price, actual_exit_price,
                     actual_profit_pct, stop_loss_hit, take_profit_1_hit, take_profit_2_hit, 
                     missed, notes, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (eval2_id, signal2_id, eval_time, 'missed', 87018, None, 0, 
                      0, 0, 0, 1, "入场价无法成交; 入场价$87,018低于实际最低价$87,158.10(偏差0.16%); 入场价是技术位而非当前价格", eval_time))
                conn.commit()
                
                # 更新信号状态（分开执行）
                conn.execute('''
                    UPDATE trading_signals 
                    SET status = ?, updated_at = ?
                    WHERE id = ?
                ''', ('missed', eval_time, signal2_id))
                conn.commit()
                print(f"✅ 评估2 ID: {eval2_id}")
        except Exception as e:
            print(f"⚠️ 添加评估记录失败: {e}", file=sys.stderr)
            conn.rollback()
        print("")
        
        print("="*80)
        print("✅ 数据录入完成")
        print("="*80)
        print("")
        print(f"信号1 (15分钟做空): ID={signal1_id}, 结果=止损")
        print(f"信号2 (1小时做多): ID={signal2_id}, 结果=错过")
        print("")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()

