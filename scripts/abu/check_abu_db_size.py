#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查ABU数据库容量和结构"""
import sys
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[2]
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

def estimate_table_size(conn, table_name):
    """估算表大小"""
    try:
        # 获取表结构
        cols = conn.execute(f'PRAGMA table_info({table_name})').fetchall()
        count = conn.execute(f'SELECT COUNT(*) FROM {table_name}').fetchone()[0]
        
        # 估算每行大小（粗略）
        row_size = 0
        for col in cols:
            col_type = col[1].upper()
            if 'INTEGER' in col_type or 'INT' in col_type:
                row_size += 8  # 8 bytes
            elif 'REAL' in col_type or 'FLOAT' in col_type or 'DOUBLE' in col_type:
                row_size += 8  # 8 bytes
            elif 'VARCHAR' in col_type or 'TEXT' in col_type or 'JSON' in col_type:
                row_size += 200  # 平均200字节（包含VARCHAR开销）
            elif 'BOOLEAN' in col_type:
                row_size += 1  # 1 byte
            else:
                row_size += 100  # 默认100字节
        
        total_size = count * row_size
        return {
            'table': table_name,
            'count': count,
            'columns': len(cols),
            'estimated_row_size': row_size,
            'estimated_total_size': total_size
        }
    except Exception as e:
        return {'table': table_name, 'error': str(e)}

def main():
    if not DB_FILE.exists():
        print(f"数据库文件不存在: {DB_FILE}")
        return
    
    # 文件大小
    file_size = DB_FILE.stat().st_size
    print(f"=== ABU数据库容量分析 ===\n")
    print(f"数据库文件: {DB_FILE}")
    print(f"当前文件大小: {format_size(file_size)}\n")
    
    conn = duckdb.connect(str(DB_FILE))
    
    # 获取所有表
    tables = [t[0] for t in conn.execute('SHOW TABLES').fetchall()]
    print(f"表数量: {len(tables)}\n")
    
    # 分析每个表
    print("=== 表详细分析 ===\n")
    total_estimated_size = 0
    
    for table in sorted(tables):
        info = estimate_table_size(conn, table)
        if 'error' in info:
            print(f"{table}: 错误 - {info['error']}")
        else:
            print(f"{info['table']}:")
            print(f"  记录数: {info['count']:,}")
            print(f"  列数: {info['columns']}")
            print(f"  估算行大小: {info['estimated_row_size']} bytes")
            print(f"  估算总大小: {format_size(info['estimated_total_size'])}")
            total_estimated_size += info['estimated_total_size']
            print()
    
    print(f"=== 总估算大小 ===")
    print(f"所有表估算总大小: {format_size(total_estimated_size)}")
    print(f"数据库文件实际大小: {format_size(file_size)}")
    print()
    
    # 检查pattern_library详情
    print("=== pattern_library表详情 ===")
    try:
        pattern_count = conn.execute('SELECT COUNT(*) FROM pattern_library').fetchone()[0]
        pattern_types = conn.execute('''
            SELECT pattern_type, COUNT(*) as cnt 
            FROM pattern_library 
            WHERE pattern_type IS NOT NULL 
            GROUP BY pattern_type 
            ORDER BY cnt DESC
        ''').fetchall()
        
        print(f"总模式数: {pattern_count}")
        print("\n按类型分布:")
        for ptype, cnt in pattern_types:
            print(f"  {ptype or 'NULL'}: {cnt}")
        
        # 检查JSON字段大小
        sample = conn.execute('''
            SELECT 
                AVG(LENGTH(key_features)) as avg_key_features,
                AVG(LENGTH(chart_features_json)) as avg_chart_features,
                AVG(LENGTH(gemini_annotation_json)) as avg_gemini
            FROM pattern_library
            WHERE key_features IS NOT NULL OR chart_features_json IS NOT NULL OR gemini_annotation_json IS NOT NULL
        ''').fetchone()
        
        print(f"\nJSON字段平均大小:")
        print(f"  key_features: {sample[0] or 0:.0f} bytes")
        print(f"  chart_features_json: {sample[1] or 0:.0f} bytes")
        print(f"  gemini_annotation_json: {sample[2] or 0:.0f} bytes")
        
    except Exception as e:
        print(f"错误: {e}")
    
    # 检查pattern_matches表（如果存在）
    print("\n=== pattern_matches表 ===")
    if 'pattern_matches' in tables:
        try:
            matches_count = conn.execute('SELECT COUNT(*) FROM pattern_matches').fetchone()[0]
            cols = conn.execute('PRAGMA table_info(pattern_matches)').fetchall()
            print(f"记录数: {matches_count}")
            print("字段:")
            for col in cols:
                print(f"  {col[1]} ({col[2]})")
        except Exception as e:
            print(f"错误: {e}")
    else:
        print("表不存在（需要创建）")
    
    # DuckDB容量评估
    print("\n=== DuckDB容量评估 ===")
    print("DuckDB理论限制:")
    print("  - 最大数据库大小: 无硬性限制（取决于磁盘空间）")
    print("  - 单表最大行数: ~2^63 (9.2 quintillion)")
    print("  - 单行最大大小: 无硬性限制（但建议<1MB）")
    print("  - 推荐单表行数: < 10亿行（性能最佳）")
    print()
    print("容量建议:")
    
    # 估算未来数据量
    # 假设每天生成10个信号，每个信号可能匹配多个模式
    daily_signals = 10
    avg_patterns_per_signal = 3  # 每个信号平均匹配3个模式
    daily_matches = daily_signals * avg_patterns_per_signal
    yearly_matches = daily_matches * 365
    
    # pattern_match_history表估算（每条记录约2KB）
    match_record_size = 2000  # bytes
    one_year_matches_size = yearly_matches * match_record_size
    
    print(f"  假设每天生成 {daily_signals} 个信号")
    print(f"  每个信号平均匹配 {avg_patterns_per_signal} 个模式")
    print(f"  每年模式匹配记录: {yearly_matches:,} 条")
    print(f"  每年pattern_match_history表大小: {format_size(one_year_matches_size)}")
    print()
    
    # 估算5年数据量
    five_years_size = one_year_matches_size * 5
    current_db_size = file_size
    projected_size = current_db_size + five_years_size
    
    print(f"  5年后的估算数据库大小: {format_size(projected_size)}")
    
    if projected_size < 1_000_000_000:  # < 1GB
        print(f"  ✅ 容量充足（< 1GB）")
    elif projected_size < 10_000_000_000:  # < 10GB
        print(f"  ✅ 容量充足（< 10GB，建议定期归档）")
    else:
        print(f"  ⚠️  容量较大（> 10GB，建议实施归档策略）")
    
    conn.close()

if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    main()

