#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试电子书集成功能
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

print("=" * 80)
print("电子书集成功能测试")
print("=" * 80)
print()

# 测试1: 电子书知识检索器
print("测试1: 电子书知识检索器")
print("-" * 80)
try:
    from abu.ebook_knowledge_retriever import EbookKnowledgeRetriever
    
    retriever = EbookKnowledgeRetriever('abu')
    
    # 测试获取模式信息
    pattern_info = retriever.get_pattern_info('Wedge')
    print(f"✅ 获取Wedge模式信息: {len(pattern_info)} 条")
    if pattern_info:
        info = pattern_info[0]
        print(f"   模式名称: {info['pattern_name']}")
        print(f"   模式类型: {info['pattern_type']}")
        print(f"   电子书引用数: {len(info['ebook_references'])}")
        print(f"   电子书详情数: {len(info['ebook_details'])}")
    
    # 测试获取交易规则
    rules = retriever.get_trading_rules('Triangle')
    print(f"\n✅ 获取Triangle交易规则: {len(rules)} 条")
    if rules:
        print(f"   第一条规则来源: {rules[0]['book']}")
        print(f"   规则字段: {list(rules[0]['rules'].keys())}")
    
    # 测试获取模式描述
    desc = retriever.get_pattern_description('InsideBar')
    if desc:
        print(f"\n✅ 获取InsideBar模式描述")
        print(f"   模式名称: {desc['pattern_name']}")
        print(f"   电子书描述数: {len(desc['ebook_descriptions'])}")
        print(f"   交易规则数: {len(desc['trading_rules'])}")
    
    retriever.close()
    print("\n✅ 测试1通过\n")
    
except Exception as e:
    print(f"❌ 测试1失败: {e}")
    import traceback
    traceback.print_exc()
    print()

# 测试2: 模式匹配器集成
print("测试2: 模式匹配器电子书验证集成")
print("-" * 80)
try:
    from abu.gemini_pattern_matcher_enhanced import EnhancedGeminiPatternMatcher
    
    matcher = EnhancedGeminiPatternMatcher(use_ebook=True)
    
    if matcher.use_ebook:
        print("✅ 电子书验证已启用")
        print(f"   电子书检索器: {'已初始化' if matcher.ebook_retriever else '未初始化'}")
    else:
        print("⚠️  电子书验证未启用")
    
    print("\n✅ 测试2通过\n")
    
except Exception as e:
    print(f"❌ 测试2失败: {e}")
    import traceback
    traceback.print_exc()
    print()

# 测试3: 数据库统计
print("测试3: 数据库统计")
print("-" * 80)
try:
    from db_manager_trader import TraderDBManager
    
    db = TraderDBManager('abu')
    conn = db._get_connection()
    
    # 电子书知识库统计
    ebook_count = conn.execute('SELECT COUNT(*) FROM ebook_knowledge_base').fetchone()[0]
    print(f"✅ 电子书知识库记录数: {ebook_count}")
    
    # 模式库关联统计
    linked_count = conn.execute('''
        SELECT COUNT(*) FROM pattern_library 
        WHERE ebook_references IS NOT NULL 
          AND ebook_references != '' 
          AND ebook_references != '[]'
    ''').fetchone()[0]
    print(f"✅ 已关联电子书的模式数: {linked_count}")
    
    # 有文本描述的模式数
    desc_count = conn.execute('''
        SELECT COUNT(*) FROM pattern_library 
        WHERE text_description IS NOT NULL AND text_description != ''
    ''').fetchone()[0]
    print(f"✅ 有文本描述的模式数: {desc_count}")
    
    db.close()
    print("\n✅ 测试3通过\n")
    
except Exception as e:
    print(f"❌ 测试3失败: {e}")
    import traceback
    traceback.print_exc()
    print()

print("=" * 80)
print("✅ 所有测试完成")
print("=" * 80)



