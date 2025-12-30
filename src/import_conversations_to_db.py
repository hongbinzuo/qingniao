#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将对话记录导入数据库
"""

import json
from pathlib import Path
from datetime import datetime

def import_from_json(json_file):
    """从JSON文件导入到数据库"""
    try:
        from db_config import get_db_manager
        db = get_db_manager()
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        print("请先安装数据库: pip install duckdb")
        return
    
    # 读取JSON文件
    with open(json_file, 'r', encoding='utf-8') as f:
        records = json.load(f)
    
    print(f"开始导入 {len(records)} 条记录...")
    print()
    
    for i, record in enumerate(records, 1):
        timestamp_str = record['timestamp']
        content = record['content']
        btc_price = record.get('btc_price')
        analysis = record.get('analysis', {})
        context = record.get('context', '')
        
        # 构建完整内容（包含价格和上下文）
        full_content = content
        if btc_price:
            full_content = f"[BTC价格: ${btc_price:,.2f}] {full_content}"
        if context:
            full_content = f"[上下文: {context}] {full_content}"
        
        # 添加分析信息
        if analysis.get('prices'):
            full_content += f"\n[解析价格: {', '.join(map(str, analysis['prices']))}]"
        if analysis.get('actions'):
            full_content += f"\n[交易动作: {', '.join(analysis['actions'])}]"
        if analysis.get('strategy'):
            full_content += f"\n[策略: {', '.join(analysis['strategy'])}]"
        
        # 转换为标准时间格式
        try:
            dt = datetime.strptime(timestamp_str, '%Y/%m/%d %H:%M')
            timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            timestamp = timestamp_str
        
        # 判断类别
        category = 'trading'
        if any(kw in content for kw in ['稳住', '绝望', '日常']):
            category = 'analysis'
        
        # 提取标签
        tags = []
        if '挂单' in content or '挂' in content:
            tags.append('挂单')
        if '保本' in content:
            tags.append('保本')
        if '焊死' in content:
            tags.append('固定持仓')
        if '多单' in content:
            tags.append('多单')
        if '空单' in content:
            tags.append('空单')
        
        # 添加到数据库
        try:
            vp_id = db.add_de_viewpoint(
                content=full_content,
                timestamp=timestamp,
                source='conversation',
                category=category,
                tags=tags
            )
            print(f"[OK] [{i}/{len(records)}] 已导入: {timestamp}")
            print(f"   观点ID: {vp_id}")
            if btc_price:
                print(f"   BTC价格: ${btc_price:,.2f}")
            print()
        except Exception as e:
            print(f"[ERROR] [{i}/{len(records)}] 导入失败: {e}")
            print()
    
    # 关闭数据库连接
    if hasattr(db, 'close'):
        db.close()
    
    print("=" * 80)
    print("导入完成！")
    print("=" * 80)

if __name__ == '__main__':
    json_file = Path("data/de_conversations_20251224.json")
    if json_file.exists():
        import_from_json(json_file)
    else:
        print(f"文件不存在: {json_file}")
        print("请先运行: python src/record_de_conversation_20251224.py")

