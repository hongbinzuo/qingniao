#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""列出ABU数据库中的所有结果"""
import sys
import json
from pathlib import Path
import duckdb
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

DB_FILE = SRC / 'data' / 'qingniao_abu.duckdb'

def format_size(size_bytes):
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def safe_json_parse(text, max_len=200):
    """安全解析JSON并截断"""
    if not text:
        return None
    try:
        data = json.loads(text)
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        if len(json_str) > max_len:
            return json_str[:max_len] + "..."
        return json_str
    except:
        return text[:max_len] + "..." if len(text) > max_len else text

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    
    if not DB_FILE.exists():
        print(f"❌ 数据库文件不存在: {DB_FILE}")
        return
    
    print("=" * 80)
    print("ABU数据库完整结果列表")
    print("=" * 80)
    print(f"数据库文件: {DB_FILE}")
    print(f"文件大小: {format_size(DB_FILE.stat().st_size)}")
    print(f"查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    conn = duckdb.connect(str(DB_FILE))
    
    # 1. 获取所有表
    tables = [t[0] for t in conn.execute('SHOW TABLES').fetchall()]
    print(f"📊 数据库表总数: {len(tables)}")
    print(f"表列表: {', '.join(sorted(tables))}")
    print()
    
    # 2. 每个表的详细统计
    for table in sorted(tables):
        print("=" * 80)
        print(f"📋 表: {table}")
        print("=" * 80)
        
        try:
            # 记录数
            count = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
            print(f"记录数: {count:,}")
            
            # 表结构
            cols = conn.execute(f'PRAGMA table_info({table})').fetchall()
            print(f"字段数: {len(cols)}")
            print("\n字段列表:")
            for col in cols:
                nullable = "NULL" if col[3] == 0 else "NOT NULL"
                default = f" DEFAULT {col[4]}" if col[4] else ""
                print(f"  - {col[1]} ({col[2]}) {nullable}{default}")
            
            # 如果有数据，显示样本
            if count > 0:
                print(f"\n📝 数据样本（前3条）:")
                sample = conn.execute(f'SELECT * FROM {table} LIMIT 3').fetchall()
                col_names = [col[1] for col in cols]
                
                for idx, row in enumerate(sample, 1):
                    print(f"\n  记录 #{idx}:")
                    for col_name, value in zip(col_names, row):
                        if value is None:
                            print(f"    {col_name}: NULL")
                        elif isinstance(value, str) and len(value) > 100:
                            # 长文本截断
                            if value.startswith('{') or value.startswith('['):
                                # JSON字段
                                parsed = safe_json_parse(value, max_len=150)
                                print(f"    {col_name}: {parsed}")
                            else:
                                print(f"    {col_name}: {value[:100]}...")
                        else:
                            print(f"    {col_name}: {value}")
            
            # 特殊表的统计信息
            if table == 'pattern_library':
                print("\n📈 pattern_library 详细统计:")
                
                # 按类型统计
                pattern_types = conn.execute('''
                    SELECT pattern_type, COUNT(*) as cnt 
                    FROM pattern_library 
                    WHERE pattern_type IS NOT NULL 
                    GROUP BY pattern_type 
                    ORDER BY cnt DESC
                ''').fetchall()
                if pattern_types:
                    print("  按类型分布:")
                    for ptype, cnt in pattern_types:
                        print(f"    {ptype or 'NULL'}: {cnt}")
                
                # Gemini标注统计
                gemini_count = conn.execute('''
                    SELECT COUNT(*) FROM pattern_library 
                    WHERE gemini_annotation_json IS NOT NULL 
                      AND gemini_annotation_json != ''
                ''').fetchone()[0]
                print(f"\n  Gemini标注数量: {gemini_count}/{count} ({gemini_count/count*100:.1f}%)")
                
                # 新字段统计
                chart_overview_count = conn.execute('''
                    SELECT COUNT(*) FROM pattern_library 
                    WHERE chart_overview IS NOT NULL AND chart_overview != ''
                ''').fetchone()[0]
                complete_price_path_count = conn.execute('''
                    SELECT COUNT(*) FROM pattern_library 
                    WHERE complete_price_path IS NOT NULL AND complete_price_path != ''
                ''').fetchone()[0]
                complete_narrative_count = conn.execute('''
                    SELECT COUNT(*) FROM pattern_library 
                    WHERE complete_narrative IS NOT NULL AND complete_narrative != ''
                ''').fetchone()[0]
                
                print(f"\n  新字段提取情况:")
                print(f"    chart_overview: {chart_overview_count}/{count} ({chart_overview_count/count*100:.1f}%)")
                print(f"    complete_price_path: {complete_price_path_count}/{count} ({complete_price_path_count/count*100:.1f}%)")
                print(f"    complete_narrative: {complete_narrative_count}/{count} ({complete_narrative_count/count*100:.1f}%)")
                
                # JSON字段大小统计
                json_stats = conn.execute('''
                    SELECT 
                        AVG(LENGTH(key_features)) as avg_key_features,
                        AVG(LENGTH(chart_features_json)) as avg_chart_features,
                        AVG(LENGTH(gemini_annotation_json)) as avg_gemini
                    FROM pattern_library
                    WHERE key_features IS NOT NULL 
                       OR chart_features_json IS NOT NULL 
                       OR gemini_annotation_json IS NOT NULL
                ''').fetchone()
                
                if json_stats[0] or json_stats[1] or json_stats[2]:
                    print(f"\n  JSON字段平均大小:")
                    if json_stats[0]:
                        print(f"    key_features: {json_stats[0]:.0f} bytes")
                    if json_stats[1]:
                        print(f"    chart_features_json: {json_stats[1]:.0f} bytes")
                    if json_stats[2]:
                        print(f"    gemini_annotation_json: {json_stats[2]:.0f} bytes")
            
            elif table == 'trading_signals':
                print("\n📈 trading_signals 详细统计:")
                
                # 按状态统计
                status_stats = conn.execute('''
                    SELECT status, COUNT(*) as cnt 
                    FROM trading_signals 
                    GROUP BY status 
                    ORDER BY cnt DESC
                ''').fetchall()
                if status_stats:
                    print("  按状态分布:")
                    for status, cnt in status_stats:
                        print(f"    {status or 'NULL'}: {cnt}")
                
                # 按时间框架统计
                tf_stats = conn.execute('''
                    SELECT timeframe, COUNT(*) as cnt 
                    FROM trading_signals 
                    WHERE timeframe IS NOT NULL
                    GROUP BY timeframe 
                    ORDER BY cnt DESC
                ''').fetchall()
                if tf_stats:
                    print("\n  按时间框架分布:")
                    for tf, cnt in tf_stats:
                        print(f"    {tf}: {cnt}")
                
                # 按符号统计
                symbol_stats = conn.execute('''
                    SELECT symbol, COUNT(*) as cnt 
                    FROM trading_signals 
                    WHERE symbol IS NOT NULL
                    GROUP BY symbol 
                    ORDER BY cnt DESC
                ''').fetchall()
                if symbol_stats:
                    print("\n  按交易对分布:")
                    for symbol, cnt in symbol_stats:
                        print(f"    {symbol}: {cnt}")
                
                # Score统计
                score_stats = conn.execute('''
                    SELECT 
                        MIN(score) as min_score,
                        MAX(score) as max_score,
                        AVG(score) as avg_score,
                        COUNT(*) as total
                    FROM trading_signals
                    WHERE score IS NOT NULL
                ''').fetchone()
                if score_stats[3] > 0:
                    print(f"\n  Score统计:")
                    print(f"    最小值: {score_stats[0]:.2f}")
                    print(f"    最大值: {score_stats[1]:.2f}")
                    print(f"    平均值: {score_stats[2]:.2f}")
                    print(f"    有Score的记录: {score_stats[3]}/{count}")
            
            elif table == 'conversations':
                print("\n📈 conversations 详细统计:")
                
                # 按来源统计
                source_stats = conn.execute('''
                    SELECT source, COUNT(*) as cnt 
                    FROM conversations 
                    GROUP BY source 
                    ORDER BY cnt DESC
                ''').fetchall()
                if source_stats:
                    print("  按来源分布:")
                    for source, cnt in source_stats:
                        print(f"    {source or 'NULL'}: {cnt}")
            
            elif table == 'trade_records':
                print("\n📈 trade_records 详细统计:")
                
                # 盈亏统计
                profit_stats = conn.execute('''
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN profit_pct > 0 THEN 1 ELSE 0 END) as wins,
                        SUM(CASE WHEN profit_pct < 0 THEN 1 ELSE 0 END) as losses,
                        AVG(profit_pct) as avg_profit
                    FROM trade_records
                    WHERE profit_pct IS NOT NULL
                ''').fetchone()
                if profit_stats[0] > 0:
                    print(f"  盈亏统计:")
                    print(f"    总交易: {profit_stats[0]}")
                    print(f"    盈利: {profit_stats[1]}")
                    print(f"    亏损: {profit_stats[2]}")
                    print(f"    平均盈亏: {profit_stats[3]:.2f}%")
            
            elif table == 'signal_evaluations':
                print("\n📈 signal_evaluations 详细统计:")
                
                # 结果统计
                result_stats = conn.execute('''
                    SELECT result, COUNT(*) as cnt 
                    FROM signal_evaluations 
                    WHERE result IS NOT NULL
                    GROUP BY result 
                    ORDER BY cnt DESC
                ''').fetchall()
                if result_stats:
                    print("  按结果分布:")
                    for result, cnt in result_stats:
                        print(f"    {result}: {cnt}")
        
        except Exception as e:
            print(f"❌ 查询错误: {e}")
        
        print()
    
    # 3. 跨表关联统计
    print("=" * 80)
    print("🔗 跨表关联统计")
    print("=" * 80)
    
    try:
        # pattern_library 与 trading_signals 的关联（通过pattern_matches）
        if 'pattern_matches' in tables:
            match_count = conn.execute('SELECT COUNT(*) FROM pattern_matches').fetchone()[0]
            print(f"pattern_matches 记录数: {match_count}")
            
            # 匹配的模式类型分布
            pattern_match_types = conn.execute('''
                SELECT pattern_type, COUNT(*) as cnt 
                FROM pattern_matches 
                WHERE pattern_type IS NOT NULL
                GROUP BY pattern_type 
                ORDER BY cnt DESC
                LIMIT 10
            ''').fetchall()
            if pattern_match_types:
                print("\n  匹配的模式类型（Top 10）:")
                for ptype, cnt in pattern_match_types:
                    print(f"    {ptype}: {cnt}")
        else:
            print("pattern_matches 表不存在")
        
        # trading_signals 与 signal_evaluations 的关联
        if 'signal_evaluations' in tables:
            eval_count = conn.execute('SELECT COUNT(*) FROM signal_evaluations').fetchone()[0]
            signal_count = conn.execute('SELECT COUNT(*) FROM trading_signals').fetchone()[0]
            if signal_count > 0:
                eval_rate = eval_count / signal_count * 100
                print(f"\n信号评估率: {eval_count}/{signal_count} ({eval_rate:.1f}%)")
    
    except Exception as e:
        print(f"❌ 关联统计错误: {e}")
    
    print()
    print("=" * 80)
    print("✅ 数据库查询完成")
    print("=" * 80)
    
    conn.close()

if __name__ == '__main__':
    main()



