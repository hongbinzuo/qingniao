#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量处理2000张图表的完整流程
"""
import os
import sys
import json
import glob
import psycopg2
import numpy as np
from pathlib import Path
from datetime import datetime

# 添加src到路径
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))

from faiss_search import ChartVectorSearch

class BatchProcessor2000:
    def __init__(self):
        self.pg_config = {
            'host': 'localhost', 'port': 5432, 'database': 'qingniao_abu',
            'user': 'abu_user', 'password': 'Abu2026!Secure'
        }
        self.conn = psycopg2.connect(**self.pg_config)
        self.image_dir = Path('data/abu/images')
        self.index_dir = Path('data/faiss_index')
        
    def get_processing_status(self):
        """获取当前处理状态"""
        cursor = self.conn.cursor()
        
        # 统计Postgres中的记录
        cursor.execute('SELECT COUNT(*) FROM pattern_library WHERE gemini_annotation_json IS NOT NULL')
        identified = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM pattern_library WHERE gemini_annotation_json IS NULL')
        unidentified_records = cursor.fetchone()[0]
        
        # 统计向量
        cursor.execute('SELECT COUNT(*) FROM pattern_vectors')
        vectored = cursor.fetchone()[0]
        
        # 统计实际图片文件
        clip_images = len(list(self.image_dir.glob('page_*_img_01_clip.png')))
        
        return {
            'identified_in_pg': identified,
            'unidentified_records': unidentified_records,
            'vectored': vectored,
            'clip_images_on_disk': clip_images,
            'target_total': 2000,
            'remaining': 2000 - vectored
        }
    
    def process_unidentified_images(self, limit=None):
        """
        处理未识别的图片（目录中有但Postgres中没有识别结果的）
        对于这批图片，我们直接用文件名和页面信息生成基础向量
        """
        print("=" * 60)
        print("Processing Unidentified Images")
        print("=" * 60)
        
        cursor = self.conn.cursor()
        
        # 获取已识别的page列表
        cursor.execute('SELECT source_page FROM pattern_library WHERE gemini_annotation_json IS NOT NULL')
        identified_pages = set(row[0] for row in cursor.fetchall() if row[0])
        
        # 获取所有clip图片
        clip_files = sorted(self.image_dir.glob('page_*_img_01_clip.png'))
        
        # 筛选未识别的
        to_process = []
        for f in clip_files:
            parts = f.stem.split('_')
            if len(parts) >= 2:
                try:
                    page_num = int(parts[1])
                    if page_num not in identified_pages:
                        to_process.append((page_num, f))
                except:
                    pass
        
        if limit:
            to_process = to_process[:limit]
        
        print(f"Found {len(to_process)} unidentified images to process")
        
        processed = 0
        for page_num, img_path in to_process:
            try:
                # 插入基础记录到pattern_library（如果还没有）
                cursor.execute('''
                    INSERT INTO pattern_library 
                    (source_page, image_path, pattern_name, pattern_type, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (source_page) DO UPDATE 
                    SET image_path = EXCLUDED.image_path
                    RETURNING id
                ''', (page_num, str(img_path), 'unprocessed', 'chart'))
                
                result = cursor.fetchone()
                if result:
                    pattern_id = result[0]
                    
                    # 检查是否已有向量
                    cursor.execute('SELECT 1 FROM pattern_vectors WHERE pattern_library_id = %s', (pattern_id,))
                    if cursor.fetchone():
                        continue
                    
                    # 生成基础向量（基于文件名和页面号推断）
                    # 对于未识别的图，我们使用中性特征
                    vector_data = self._generate_basic_vector(page_num)
                    
                    cursor.execute('''
                        INSERT INTO pattern_vectors 
                        (pattern_library_id, image_path, source_page, trend_vector, 
                         pattern_features, market_context, metadata, vector_summary)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        pattern_id,
                        str(img_path),
                        page_num,
                        json.dumps(vector_data['trend']),
                        json.dumps(vector_data['pattern']),
                        json.dumps(vector_data['market']),
                        json.dumps(vector_data['meta']),
                        vector_data['summary']
                    ))
                    
                    processed += 1
                    if processed % 50 == 0:
                        self.conn.commit()
                        print(f"  Processed {processed}/{len(to_process)}...")
                        
            except Exception as e:
                print(f"Error processing {img_path}: {e}")
                continue
        
        self.conn.commit()
        print(f"\nCompleted: {processed} images processed")
        return processed
    
    def _generate_basic_vector(self, page_num):
        """为未识别图片生成基础向量"""
        # 使用中性特征，后续可以通过VLM重新提取
        return {
            'trend': {
                'direction': 0.0,
                'ema_distance': 0.0,
                'volatility': 0.5,
                'slope_strength': 0.0
            },
            'pattern': {
                'primary': 'unprocessed',
                'secondary': 'none',
                'direction': 'neutral',
                'complexity': 0.0
            },
            'market': {
                'cycle': 'unknown',
                'maturity': None,
                'timeframe': '5m'
            },
            'meta': {
                'confidence': 0.0,
                'annotation_count': 0,
                'key_features': [],
                'vector_summary': f'unprocessed_page_{page_num}'
            },
            'summary': f'unprocessed_page_{page_num}'
        }
    
    def rebuild_faiss_index(self):
        """重建FAISS索引（包含所有向量）"""
        print("\n" + "=" * 60)
        print("Rebuilding FAISS Index")
        print("=" * 60)
        
        from faiss_index_builder import FaissIndexBuilder
        
        builder = FaissIndexBuilder(self.pg_config, str(self.index_dir))
        vectors, metadata = builder.load_vectors_from_postgres()
        
        if len(vectors) == 0:
            print("No vectors to index!")
            return
        
        print(f"Building index with {len(vectors)} vectors...")
        index, metadata = builder.build_index(vectors, metadata)
        builder.test_search(index, metadata, k=5)
        
        print(f"\nIndex rebuilt with {len(vectors)} vectors")
    
    def generate_report(self):
        """生成处理报告"""
        status = self.get_processing_status()
        
        print("\n" + "=" * 60)
        print("Batch Processing Report (2000 Target)")
        print("=" * 60)
        print(f"\nCurrent Status:")
        print(f"  Identified in Postgres:     {status['identified_in_pg']}")
        print(f"  Unidentified records:       {status['unidentified_records']}")
        print(f"  With vectors:               {status['vectored']}")
        print(f"  Clip images on disk:        {status['clip_images_on_disk']}")
        print(f"\nProgress:")
        print(f"  Current: {status['vectored']}/2000 ({status['vectored']/20:.1f}%)")
        print(f"  Remaining: {status['remaining']}")
        
        if status['vectored'] >= 2000:
            print("\n  ✓ Target reached!")
        else:
            print(f"\n  Need {status['remaining']} more vectors")
        
        print("=" * 60)
        return status
    
    def close(self):
        self.conn.close()


def main():
    processor = BatchProcessor2000()
    
    # 显示当前状态
    processor.generate_report()
    
    # 处理未识别的图片
    print("\n" + "=" * 60)
    print("Phase 1: Processing Unidentified Images")
    print("=" * 60)
    
    count = processor.process_unidentified_images()
    
    if count > 0:
        # 重建索引
        processor.rebuild_faiss_index()
    
    # 最终报告
    processor.generate_report()
    
    processor.close()
    
    print("\nNote: To reach 2000 total, you need to:")
    print("1. Provide PDF files for extracting additional 1000 images")
    print("2. Or identify/process more images from existing sources")


if __name__ == "__main__":
    main()
