#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化验证向量质量
基于已有pattern标签，无需人工判断
"""
import psycopg2
import json
import math
from collections import defaultdict, Counter
from typing import List, Tuple, Dict

def cosine_similarity(vec1: dict, vec2: dict) -> float:
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
    score = 0
    if p1.get('primary') == p2.get('primary'):
        score += 0.5
    if p1.get('secondary') == p2.get('secondary'):
        score += 0.3
    if p1.get('direction') == p2.get('direction'):
        score += 0.2
    return score

def total_similarity(v1: dict, p1: dict, v2: dict, p2: dict) -> float:
    trend_sim = cosine_similarity(v1, v2)
    pattern_sim = pattern_match_score(p1, p2)
    return trend_sim * 0.6 + pattern_sim * 0.4

class AutoValidator:
    def __init__(self):
        self.conn = psycopg2.connect(
            host='localhost', port=5432, database='qingniao_abu',
            user='abu_user', password='Abu2026!Secure'
        )
        self.data = self._load_data()
    
    def _load_data(self) -> List[Tuple]:
        """加载所有向量数据"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT v.pattern_library_id, v.trend_vector, v.pattern_features,
                   p.pattern_name, v.image_path
            FROM pattern_vectors v
            JOIN pattern_library p ON v.pattern_library_id = p.id
        ''')
        return cursor.fetchall()
    
    def calculate_intra_vs_inter(self) -> Dict:
        """计算组内vs组间相似度"""
        # 按pattern分组
        groups = defaultdict(list)
        for row in self.data:
            pid, trend, pattern, name, path = row
            groups[name or "Unknown"].append((pid, trend, pattern))
        
        results = {}
        for pattern_name, items in groups.items():
            if len(items) < 2:
                continue
            
            # 组内相似度
            intra_sims = []
            for i in range(len(items)):
                for j in range(i+1, len(items)):
                    sim = total_similarity(items[i][1], items[i][2], 
                                          items[j][1], items[j][2])
                    intra_sims.append(sim)
            
            # 组间相似度（与其他所有组比较）
            inter_sims = []
            for other_name, other_items in groups.items():
                if other_name == pattern_name or len(other_items) < 1:
                    continue
                # 随机采样5个对比
                for item in items[:3]:
                    for other in other_items[:5]:
                        sim = total_similarity(item[1], item[2],
                                              other[1], other[2])
                        inter_sims.append(sim)
            
            results[pattern_name] = {
                'count': len(items),
                'intra_avg': sum(intra_sims) / len(intra_sims) if intra_sims else 0,
                'inter_avg': sum(inter_sims) / len(inter_sims) if inter_sims else 0,
                'separation': (sum(intra_sims) / len(intra_sims) - 
                              sum(inter_sims) / len(inter_sims)) if intra_sims and inter_sims else 0
            }
        
        return results
    
    def knn_classification_test(self, k: int = 5) -> Dict:
        """KNN分类测试：看向量能否正确预测pattern类型"""
        correct = 0
        total = 0
        confusion = defaultdict(lambda: defaultdict(int))
        
        for i, (query_id, query_trend, query_pattern, query_name, _) in enumerate(self.data):
            if not query_name:
                continue
            
            # 找K近邻
            similarities = []
            for j, (target_id, target_trend, target_pattern, target_name, _) in enumerate(self.data):
                if i == j or not target_name:
                    continue
                sim = total_similarity(query_trend, query_pattern,
                                      target_trend, target_pattern)
                similarities.append((sim, target_name))
            
            similarities.sort(reverse=True)
            neighbors = similarities[:k]
            
            # 投票
            votes = Counter([n[1] for n in neighbors])
            predicted = votes.most_common(1)[0][0]
            
            confusion[query_name][predicted] += 1
            if predicted == query_name:
                correct += 1
            total += 1
        
        accuracy = correct / total if total > 0 else 0
        return {
            'accuracy': accuracy,
            'correct': correct,
            'total': total,
            'confusion': dict(confusion)
        }
    
    def find_confusion_patterns(self) -> List[Tuple]:
        """找出最容易混淆的模式对"""
        results = []
        intra_inter = self.calculate_intra_vs_inter()
        
        for pattern, stats in intra_inter.items():
            if stats['separation'] < 0:
                results.append((pattern, stats['separation'], stats['count']))
        
        return sorted(results, key=lambda x: x[1])
    
    def generate_report(self):
        """生成完整验证报告"""
        print("=" * 70)
        print("向量质量自动化验证报告")
        print("=" * 70)
        
        # 1. 基础统计
        print(f"\n[1] 数据概况")
        print(f"  总样本数: {len(self.data)}")
        
        # 2. 组内vs组间分析
        print(f"\n[2] 组内vs组间相似度分析")
        intra_inter = self.calculate_intra_vs_inter()
        
        avg_intra = sum(s['intra_avg'] for s in intra_inter.values()) / len(intra_inter)
        avg_inter = sum(s['inter_avg'] for s in intra_inter.values()) / len(intra_inter)
        avg_sep = sum(s['separation'] for s in intra_inter.values()) / len(intra_inter)
        
        print(f"  平均组内相似度: {avg_intra:.3f} (越高越好)")
        print(f"  平均组间相似度: {avg_inter:.3f} (越低越好)")
        print(f"  平均分离度: {avg_sep:.3f} (正值=可区分, >0.1=良好)")
        
        # 显示Top 5分离度最好的模式
        print(f"\n  Top 5 可区分性最好的模式:")
        sorted_patterns = sorted(intra_inter.items(), key=lambda x: x[1]['separation'], reverse=True)
        for pattern, stats in sorted_patterns[:5]:
            print(f"    {pattern}: 分离度={stats['separation']:.3f}, 样本={stats['count']}")
        
        # 显示问题模式
        print(f"\n  需要关注的模式(分离度<0):")
        bad_patterns = [(p, s['separation'], s['count']) for p, s in intra_inter.items() if s['separation'] < 0]
        bad_patterns.sort(key=lambda x: x[1])
        for pattern, sep, count in bad_patterns[:5]:
            print(f"    {pattern}: 分离度={sep:.3f}, 样本={count}")
        
        # 3. KNN分类测试
        print(f"\n[3] KNN分类准确率 (K=5)")
        knn = self.knn_classification_test(k=5)
        print(f"  准确率: {knn['accuracy']:.1%} ({knn['correct']}/{knn['total']})")
        
        if knn['accuracy'] > 0.7:
            print(f"  评价: [优秀] 向量空间能很好区分不同模式")
        elif knn['accuracy'] > 0.5:
            print(f"  评价: [良好] 能区分大部分模式，但有混淆")
        else:
            print(f"  评价: [需改进] 相似度计算需要调整权重或特征")
        
        # 4. Top 5混淆对
        print(f"\n[4] 最容易混淆的模式对")
        confusions = []
        for true_label, preds in knn['confusion'].items():
            for pred_label, count in preds.items():
                if true_label != pred_label and count > 1:
                    confusions.append((true_label, pred_label, count))
        
        confusions.sort(key=lambda x: x[2], reverse=True)
        for true, pred, count in confusions[:5]:
            print(f"    {true} 被错分为 {pred}: {count}次")
        
        # 5. 综合评估
        print(f"\n[5] 综合评估")
        score = (avg_sep + 1) * 0.5 + knn['accuracy']  # 综合得分
        if score > 1.5:
            verdict = "向量方案非常有效，可直接用于生产"
        elif score > 1.0:
            verdict = "向量方案有效，建议小调权重后使用"
        elif score > 0.5:
            verdict = "向量方案基本可用，但需要人工复核关键模式"
        else:
            verdict = "向量方案效果不佳，建议重新设计特征或改用VLM提取"
        
        print(f"  综合得分: {score:.2f}")
        print(f"  结论: {verdict}")
        
        print("\n" + "=" * 70)

if __name__ == "__main__":
    validator = AutoValidator()
    validator.generate_report()
