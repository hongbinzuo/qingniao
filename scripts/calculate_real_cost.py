#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据实际花费重新计算真实成本
"""

import sys

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

def main():
    print("=" * 80)
    print("实际成本重新计算")
    print("=" * 80)
    print()
    
    # 实际数据
    actual_total_spent = 2.4  # 美元，自调用Gemini以来的总花费
    processed_images = 58     # 当前已处理的图片数
    
    # 计算实际单张成本
    actual_cost_per_image = actual_total_spent / processed_images
    
    print(f"📊 实际数据:")
    print(f"   总花费: ${actual_total_spent:.2f}")
    print(f"   已处理: {processed_images} 张")
    print(f"   实际单张成本: ${actual_cost_per_image:.4f}/张")
    print()
    
    # 重新估算总成本
    total_images = 1000
    remaining_images = total_images - processed_images
    
    estimated_total_cost = actual_cost_per_image * total_images
    estimated_remaining_cost = actual_cost_per_image * remaining_images
    
    print(f"💰 重新估算:")
    print(f"   总图片数: {total_images}")
    print(f"   已处理: {processed_images} 张 (${actual_total_spent:.2f})")
    print(f"   待处理: {remaining_images} 张")
    print(f"   预计剩余成本: ${estimated_remaining_cost:.2f}")
    print(f"   预计总成本: ${estimated_total_cost:.2f}")
    print()
    
    # 与之前的错误估算对比
    old_estimate_per_image = 0.000125
    old_total_estimate = old_estimate_per_image * total_images
    
    print(f"❌ 之前的错误估算:")
    print(f"   单张: ${old_estimate_per_image:.6f} (低估了 {actual_cost_per_image/old_estimate_per_image:.0f}倍)")
    print(f"   总计: ${old_total_estimate:.2f}")
    print()
    
    print(f"✅ 真实成本分析:")
    print(f"   实际单张成本: ${actual_cost_per_image:.4f}")
    print(f"   之前估算: ${old_estimate_per_image:.6f}")
    print(f"   差异倍数: {actual_cost_per_image/old_estimate_per_image:.0f}x")
    print()
    
    # 分析可能的原因
    print(f"🔍 成本高的可能原因:")
    print(f"   1. OpenRouter可能有额外费用（不在官方定价中）")
    print(f"   2. 图片很大，base64编码后token数很多")
    print(f"   3. Prompt非常长（400+行），增加了输入token数")
    print(f"   4. max_tokens=2000，输出可能很长")
    print(f"   5. 模型名称 google/gemini-2.5-flash-image 的实际定价可能高于预期")
    print()
    
    # 建议
    print(f"💡 建议:")
    print(f"   1. 检查OpenRouter的实际定价")
    print(f"   2. 优化Prompt长度（减少不必要的描述）")
    print(f"   3. 考虑降低max_tokens（当前2000，可能可以减少到1500）")
    print(f"   4. 检查是否有重复调用或缓存未生效")
    print(f"   5. 考虑分批处理，控制预算")
    print()
    
    # 预算预警
    if estimated_total_cost > 10:
        print(f"⚠️  预算预警:")
        print(f"   预计总成本 ${estimated_total_cost:.2f} 超过 $10")
        print(f"   建议:")
        print(f"   - 暂停处理，重新评估")
        print(f"   - 优化Prompt和参数")
        print(f"   - 考虑处理部分图片（如先处理200-300张）")
        print()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())



