#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证数据库数据
"""

from db_manager_duckdb import DuckDBManager

def main():
    """主函数"""
    print("=" * 80)
    print("验证数据库")
    print("=" * 80)
    print()
    
    db = DuckDBManager()
    
    # 获取统计信息
    stats = db.get_stats()
    
    print("数据库统计:")
    print(f"  De.观点总数: {stats.get('total_viewpoints', 0)}")
    print(f"  手工录入: {stats.get('manual_viewpoints', 0)}")
    print(f"  对话日志总数: {stats.get('total_logs', 0)}")
    print(f"  包含De.的日志: {stats.get('logs_with_de', 0)}")
    print(f"  最近30天日志: {stats.get('logs_last_30_days', 0)}")
    print()
    
    # 查询最近10条观点
    print("最近10条De.观点:")
    print("-" * 80)
    viewpoints = db.get_de_viewpoints(limit=10)
    
    for i, vp in enumerate(viewpoints, 1):
        print(f"{i}. [{vp.get('timestamp', 'N/A')}]")
        print(f"   来源: {vp.get('source', 'N/A')} | 类别: {vp.get('category', 'N/A')}")
        if vp.get('btc_price'):
            print(f"   BTC价格: ${vp['btc_price']:,.2f}")
        print(f"   内容: {vp.get('content', '')[:100]}...")
        print()
    
    db.close()
    
    print("=" * 80)
    print("验证完成！")
    print("=" * 80)

if __name__ == '__main__':
    main()

