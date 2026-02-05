#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Auto validation for vector quality"""
import psycopg2
import math
from collections import defaultdict, Counter

class AutoValidator:
    def __init__(self):
        self.conn = psycopg2.connect(
            host='localhost', port=5432, database='qingniao_abu',
            user='abu_user', password='Abu2026!Secure'
        )
        self.data = self._load_data()
    
    def _load_data(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT v.pattern_library_id, v.trend_vector, v.pattern_features,
                   p.pattern_name
            FROM pattern_vectors v
            JOIN pattern_library p ON v.pattern_library_id = p.id
        ''')
        return cursor.fetchall()
    
    def cosine_sim(self, v1, v2):
        keys = ['direction', 'ema_distance', 'volatility', 'slope_strength']
        a = [v1.get(k, 0) for k in keys]
        b = [v2.get(k, 0) for k in keys]
        dot = sum(x*y for x,y in zip(a,b))
        norm_a = math.sqrt(sum(x*x for x in a))
        norm_b = math.sqrt(sum(x*x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0
        return dot / (norm_a * norm_b)
    
    def pattern_sim(self, p1, p2):
        score = 0
        if p1.get('primary') == p2.get('primary'): score += 0.5
        if p1.get('direction') == p2.get('direction'): score += 0.3
        return score
    
    def total_sim(self, item1, item2):
        _, t1, p1, _ = item1
        _, t2, p2, _ = item2
        return self.cosine_sim(t1, t2) * 0.6 + self.pattern_sim(p1, p2) * 0.4
    
    def validate(self):
        # Group by pattern
        groups = defaultdict(list)
        for item in self.data:
            pid, trend, pattern, name = item
            groups[name or "Unknown"].append(item)
        
        # Calculate intra vs inter similarity
        intra_avgs = []
        inter_avgs = []
        
        for pattern, items in groups.items():
            if len(items) < 2:
                continue
            # Intra-group similarities
            intra_sims = []
            for i in range(len(items)):
                for j in range(i+1, len(items)):
                    intra_sims.append(self.total_sim(items[i], items[j]))
            if intra_sims:
                intra_avgs.append(sum(intra_sims) / len(intra_sims))
            
            # Inter-group similarities (sample)
            inter_sims = []
            for other_pattern, other_items in groups.items():
                if other_pattern == pattern or len(other_items) < 1:
                    continue
                for a in items[:2]:
                    for b in other_items[:3]:
                        inter_sims.append(self.total_sim(a, b))
            if inter_sims:
                inter_avgs.append(sum(inter_sims) / len(inter_sims))
        
        avg_intra = sum(intra_avgs) / len(intra_avgs) if intra_avgs else 0
        avg_inter = sum(inter_avgs) / len(inter_avgs) if inter_avgs else 0
        separation = avg_intra - avg_inter
        
        # KNN test
        correct = 0
        total = 0
        for i, (qid, qt, qp, qname) in enumerate(self.data):
            if not qname:
                continue
            sims = []
            for j, (tid, tt, tp, tname) in enumerate(self.data):
                if i == j or not tname:
                    continue
                sims.append((self.total_sim(self.data[i], self.data[j]), tname))
            sims.sort(reverse=True)
            neighbors = [n[1] for n in sims[:5]]
            predicted = Counter(neighbors).most_common(1)[0][0]
            if predicted == qname:
                correct += 1
            total += 1
        
        knn_acc = correct / total if total > 0 else 0
        
        # Output results
        print("=" * 60)
        print("Vector Auto-Validation Report")
        print("=" * 60)
        print(f"\nTotal samples: {len(self.data)}")
        print(f"Pattern types: {len(groups)}")
        print(f"\nSimilarity Metrics:")
        print(f"  Intra-group (same pattern): {avg_intra:.3f} [higher=better]")
        print(f"  Inter-group (diff pattern): {avg_inter:.3f} [lower=better]")
        print(f"  Separation (intra - inter): {separation:.3f} [>0.1=good, >0.2=excellent]")
        print(f"\nKNN Classification (K=5):")
        print(f"  Accuracy: {knn_acc:.1%} ({correct}/{total})")
        
        # Interpretation
        score = separation + knn_acc
        print(f"\nOverall Score: {score:.2f}")
        if score > 1.0:
            print("Verdict: [GOOD] Vector scheme works well")
            print("Action: Proceed with B方案 (vector retrieval)")
        elif score > 0.6:
            print("Verdict: [ACCEPTABLE] Works but needs tuning")
            print("Action: Adjust weights or add more features")
        else:
            print("Verdict: [NEEDS WORK] Poor separability")
            print("Action: Consider VLM-based extraction instead")
        print("=" * 60)

if __name__ == "__main__":
    v = AutoValidator()
    v.validate()
