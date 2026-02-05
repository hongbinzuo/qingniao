#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
向量相似度验证工具
用法: python verify_similarity.py --query_id 24 --top_k 5
"""
import psycopg2
import math
import argparse
from typing import List, Tuple

def cosine_similarity(vec1: dict, vec2: dict) -> float:
    """计算两个趋势向量的余弦相似度"""
    keys = ['direction', 'ema_distance', 'volatility', 'slope_strength']
    
    v1 = [vec1.get(k, 0) for k in keys]
    v2 = [vec2.get(k, 0) for k in keys]
    
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(a * a for a in v2))
    
    if norm1 == 0 or norm2 == 0:
        return 0
    return dot / (norm1 * norm2)

def pattern_match_score(p1: dict, p2: dict) -> float:
    """计算模式匹配分数"""
    score = 0
    if p1.get('primary') == p2.get('primary'):
        score += 0.5
    if p1.get('secondary') == p2.get('secondary'):
        score += 0.3
    if p1.get('direction') == p2.get('direction'):
        score += 0.2
    return score

def find_similar(conn, query_id: int, top_k: int = 5) -> List[Tuple]:
    """查找最相似的向量"""
    cursor = conn.cursor()
    
    # 获取查询向量
    cursor.execute('''
        SELECT v.*, p.pattern_name 
        FROM pattern_vectors v
        JOIN pattern_library p ON v.pattern_library_id = p.id
        WHERE v.pattern_library_id = %s
    ''', (query_id,))
    
    query = cursor.fetchone()
    if not query:
        return []
    
    query_trend = query[4]  # trend_vector (already dict)
    query_pattern = query[5]  # pattern_features (already dict)
    query_summary = query[8]
    query_image = query[2]

    
    print(f"\n{'='*60}")
    print(f"查询图: {query_image}")
    print(f"原模式: {query[8]}")
    print(f"向量摘要: {query_summary}")
    print(f"趋势向量: {query_trend}")
    print(f"{'='*60}")
    
    # 获取所有其他向量
    cursor.execute('''
        SELECT v.*, p.pattern_name 
        FROM pattern_vectors v
        JOIN pattern_library p ON v.pattern_library_id = p.id
        WHERE v.pattern_library_id != %s
    ''', (query_id,))
    
    similarities = []
    for row in cursor.fetchall():
        target_trend = row[4]
        target_pattern = row[5]
        
        # 计算综合相似度
        trend_sim = cosine_similarity(query_trend, target_trend)
        pattern_sim = pattern_match_score(query_pattern, target_pattern)
        
        # 加权 (趋势60% + 模式40%)
        total_sim = trend_sim * 0.6 + pattern_sim * 0.4
        
        similarities.append((
            row[1],  # id
            row[2],  # image_path
            row[10], # pattern_name (joined from p)
            row[8],   # vector_summary
            row[4],   # trend dict
            total_sim,
            trend_sim,
            pattern_sim
        ))
    
    # 排序取TopK
    similarities.sort(key=lambda x: x[5], reverse=True)
    return similarities[:top_k]

def main():
    parser = argparse.ArgumentParser(description='向量相似度验证')
    parser.add_argument('--query_id', type=int, required=True, help='查询图片的ID (pattern_library.id)')
    parser.add_argument('--top_k', type=int, default=5, help='返回最相似的K个结果')
    args = parser.parse_args()
    
    conn = psycopg2.connect(
        host='localhost', port=5432, database='qingniao_abu',
        user='abu_user', password='Abu2026!Secure'
    )
    
    results = find_similar(conn, args.query_id, args.top_k)
    
    print(f"\nTop {args.top_k} 相似结果:")
    print(f"{'Rank':<6}{'ID':<8}{'Pattern':<25}{'Summary':<30}{'Score':<8}{'Match'}")
    print("-" * 100)
    
    for i, (id, img, pattern, summary, trend_dict, total, trend_s, pattern_s) in enumerate(results, 1):
        # 判断是否真正匹配
        is_match = "[OK]" if total > 0.7 else ("[MID]" if total > 0.5 else "[LOW]")
        pattern_str = (pattern or "None")[:24]
        summary_str = (summary or "None")[:28]
        
        print(f"{i:<6}{id:<8}{pattern_str:<25}{summary_str:<30}{total:.2f}   {is_match}")
    
    print("\n[OK]=High sim(>0.7) [MID]=Mid sim(0.5-0.7) [LOW]=Low sim(<0.5)")
    
    conn.close()

if __name__ == "__main__":
    main()
