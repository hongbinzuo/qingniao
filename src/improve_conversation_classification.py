#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进对话分类：更准确地区分观点和交易记录
特别处理包含图片的交易记录
"""

import json
from pathlib import Path
import sys
import re

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def classify_content(content, has_screenshot=False):
    """
    分类对话内容
    返回: (category, confidence, tags)
    """
    content_lower = content.lower()
    
    # 交易执行记录特征（已完成或进行中的交易）
    execution_keywords = [
        '已经', '目前', '昨天', '今天', '刚才',
        '止盈了', '止损了', '吃了', '拿下', '成交了',
        '扫了', '追单', '挂单', '执行',
        '盈利', '亏损', '赚了', '亏了',
        '点', '已经.*点', '目前.*点'
    ]
    
    # 交易信号特征（建议或计划）
    signal_keywords = [
        '可以', '应该', '建议', '可以空', '可以多',
        '看起来', '很好', '机会', '可以进',
        '目标', '止损', '止盈', '挂',
        '如果.*可以', '如果.*应该'
    ]
    
    # 观点特征（理论、逻辑、概念）
    viewpoint_keywords = [
        '理论', '逻辑', '道理', '意义', '概念',
        '认为', '觉得', '应该', '可能', '大概',
        '永远', '都是', '不是', '没有',
        '策略', '方法', '方式', '理念',
        '因为', '所以', '但是', '如果',
        '组织', '庄家', '巨鲸', '市场'
    ]
    
    # 检查交易执行记录
    execution_score = sum(1 for kw in execution_keywords if re.search(kw, content))
    has_price_and_action = bool(re.search(r'\d{3,4}', content)) and (
        '止盈' in content or '止损' in content or '空' in content or '多' in content or
        '吃了' in content or '拿下' in content or '点' in content
    )
    
    # 检查交易信号
    signal_score = sum(1 for kw in signal_keywords if re.search(kw, content))
    
    # 检查观点
    viewpoint_score = sum(1 for kw in viewpoint_keywords if re.search(kw, content))
    
    # 如果有截图，更可能是交易记录
    if has_screenshot:
        execution_score += 2
    
    # 分类决策
    if execution_score >= 2 or (has_price_and_action and execution_score >= 1):
        return ('trading_execution', 'high', ['交易记录', '执行记录'])
    elif signal_score >= 2 or (has_price_and_action and signal_score >= 1):
        return ('trading_signal', 'high', ['交易信号', '交易建议'])
    elif viewpoint_score >= 2:
        return ('viewpoint', 'high', ['观点', '理论'])
    elif has_price_and_action:
        return ('trading_signal', 'medium', ['交易相关'])
    else:
        return ('conversation', 'low', ['一般对话'])

def update_conversation_files():
    """更新所有对话文件的分类"""
    data_dir = Path("data")
    json_files = list(data_dir.glob("de_conversations_*.json"))
    
    print("=" * 80)
    print("改进对话分类：区分观点和交易记录")
    print("=" * 80)
    print()
    
    total_updated = 0
    total_records = 0
    
    for json_file in json_files:
        print(f"处理: {json_file.name}")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                records = json.load(f)
            
            updated = 0
            
            for record in records:
                total_records += 1
                content = record.get('content', '')
                has_screenshot = record.get('has_screenshot', False)
                original_category = record.get('category', '')
                
                # 重新分类
                new_category, confidence, tags = classify_content(content, has_screenshot)
                
                if new_category != original_category:
                    record['category'] = new_category
                    record['classification_confidence'] = confidence
                    record['classification_tags'] = tags
                    if original_category:
                        record['original_category'] = original_category
                    updated += 1
                    total_updated += 1
                else:
                    # 即使分类相同，也添加分类信息
                    if 'classification_confidence' not in record:
                        record['classification_confidence'] = confidence
                        record['classification_tags'] = tags
            
            if updated > 0:
                # 保存更新后的文件
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(records, f, ensure_ascii=False, indent=2)
                print(f"  ✅ 更新 {updated}/{len(records)} 条记录")
            else:
                print(f"  ℹ️  无需更新 ({len(records)} 条记录)")
            
            # 显示分类统计
            categories = {}
            for r in records:
                cat = r.get('category', 'unknown')
                categories[cat] = categories.get(cat, 0) + 1
            print(f"  分类: {categories}")
            print()
            
        except Exception as e:
            print(f"  ❌ 处理失败: {e}")
            print()
    
    print("=" * 80)
    print(f"分析完成！")
    print(f"  总记录数: {total_records}")
    print(f"  更新记录: {total_updated}")
    print("=" * 80)
    
    print("\n分类规则:")
    print("  📊 trading_execution: 交易执行记录")
    print("     - 包含: 已经/目前/昨天/今天 + 价格 + 交易动作")
    print("     - 包含截图: 更可能是交易记录")
    print("  📈 trading_signal: 交易信号/建议")
    print("     - 包含: 可以/应该/建议 + 价格 + 交易动作")
    print("  💡 viewpoint: 观点和理论")
    print("     - 包含: 理论/逻辑/概念/策略等")
    print("  💬 conversation: 一般对话")

if __name__ == '__main__':
    update_conversation_files()


