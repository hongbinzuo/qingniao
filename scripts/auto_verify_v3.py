#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test different weight combinations to find optimal"""
import psycopg2
import math
from collections import defaultdict, Counter

class WeightOptimizer:
    def __init__(self):
        self.conn = psycopg2.connect(
            host='localhost', port=5432, database='qingniao_abu',
            user='abu_user', password='Abu2026!Secure'
        )
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT v.trend_vector, v.pattern_features, p.pattern_name
            FROM pattern_vectors v
            JOIN pattern_library p ON v.pattern_library_id = p.id
        ''')
        self.data = [(row[0], row[1], row[2]) for row in cursor.fetchall() if row[2]]
    
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
        if p1.get('secondary') == p2.get('secondary'): score += 0.2
        return score
    
    def test_weight(self, trend_w, pattern_w):
        """Test a specific weight combination"""
        def total_sim(i, j):
            t1, p1, _ = self.data[i]
            t2, p2, _ = self.data[j]
            return self.cosine_sim(t1, t2) * trend_w + self.pattern_sim(p1, p2) * pattern_w
        
        correct = 0
        for i in range(len(self.data)):
            sims = []
            for j in range(len(self.data)):
                if i != j:
                    sims.append((total_sim(i, j), self.data[j][2]))
            sims.sort(reverse=True)
            neighbors = [n[1] for n in sims[:5]]
            predicted = Counter(neighbors).most_common(1)[0][0]
            if predicted == self.data[i][2]:
                correct += 1
        
        return correct / len(self.data)
    
    def find_optimal(self):
        print("Testing different weight combinations...")
        print("Format: trend_weight:pattern_weight -> accuracy")
        print("-" * 50)
        
        best_acc = 0
        best_weights = None
        
        # Test different combinations
        weights_to_test = [
            (0.5, 0.5),   # Equal
            (0.4, 0.6),   # More pattern
            (0.3, 0.7),   # Even more pattern
            (0.6, 0.4),   # More trend (current)
            (0.7, 0.3),   # Even more trend
            (0.2, 0.8),   # Heavy pattern
        ]
        
        for tw, pw in weights_to_test:
            acc = self.test_weight(tw, pw)
            marker = ""
            if acc > best_acc:
                best_acc = acc
                best_weights = (tw, pw)
                marker = " <-- BEST"
            print(f"  {tw:.1f}:{pw:.1f} -> {acc:.1%}{marker}")
        
        print("-" * 50)
        print(f"\nOptimal: trend={best_weights[0]}, pattern={best_weights[1]}")
        print(f"Best accuracy: {best_acc:.1%}")
        
        # Calculate improvement
        current = self.test_weight(0.6, 0.4)
        improvement = (best_acc - current) / current * 100
        print(f"Improvement over current (0.6:0.4): +{improvement:.1f}%")

if __name__ == "__main__":
    opt = WeightOptimizer()
    opt.find_optimal()
