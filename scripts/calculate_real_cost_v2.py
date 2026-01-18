#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据实际花费重新计算真实成本（修正版）
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
    print("实际成本重新计算（修正版）")
    print("=" * 80)
    print()
    
    # 实际数据（修正）
    total_spent_since_start = 2.4  # 美元，自调用Gemini以来的总花费
    previous_test_cost = 1.8       # 美元，之前测试轮次的花费
    current_run_cost = total_spent_since_start - previous_test_cost  # 本次运行实际花费
    
    # 本次运行处理的数据
    processed_images = 68  # 当前已处理的图片数（本次运行）
    
    # 计算实际单张成本
    actual_cost_per_image = current_run_cost / processed_images
    
    print(f"📊 实际数据（修正）:")
    print(f"   总花费（自开始）: ${total_spent_since_start:.2f}")
    print(f"   之前测试轮次: ${previous_test_cost:.2f}")
    print(f"   本次运行花费: ${current_run_cost:.2f}")
    print(f"   本次已处理: {processed_images} 张")
    print(f"   实际单张成本: ${actual_cost_per_image:.4f}/张")
    print()
    
    # 重新估算总成本
    total_images = 1000
    remaining_images = total_images - processed_images
    
    estimated_total_cost = actual_cost_per_image * total_images
    estimated_remaining_cost = actual_cost_per_image * remaining_images
    
    print(f"💰 重新估算:")
    print(f"   总图片数: {total_images}")
    print(f"   已处理: {processed_images} 张 (${current_run_cost:.2f})")
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
    
    # 成本评估
    print(f"📈 成本评估:")
    if estimated_total_cost < 10:
        print(f"   ✅ 预计总成本 ${estimated_total_cost:.2f} 在可接受范围内（<$10）")
    elif estimated_total_cost < 20:
        print(f"   ⚠️  预计总成本 ${estimated_total_cost:.2f} 略高但可接受（<$20）")
    else:
        print(f"   ❌ 预计总成本 ${estimated_total_cost:.2f} 较高（>$20）")
    print()
    
    # 分析可能的原因
    print(f"🔍 成本分析:")
    print(f"   实际单张成本: ${actual_cost_per_image:.4f}")
    print(f"   比最初估算高 {actual_cost_per_image/old_estimate_per_image:.0f}倍")
    print(f"   可能原因:")
    print(f"   1. OpenRouter可能有额外费用或更高定价")
    print(f"   2. 图片很大，base64编码后token数很多")
    print(f"   3. Prompt较长（400+行），增加了输入token数")
    print(f"   4. max_tokens=1500，输出token数较多")
    print()
    
    # 建议
    print(f"💡 建议:")
    if estimated_total_cost < 10:
        print(f"   ✅ 成本在可接受范围内，可以继续处理")
        print(f"   - 继续监控实际成本")
        print(f"   - 如果成本上升，考虑优化Prompt")
    else:
        print(f"   ⚠️  成本较高，建议:")
        print(f"   - 优化Prompt长度（减少不必要的描述）")
        print(f"   - 考虑降低max_tokens（当前1500）")
        print(f"   - 分批处理，控制预算")
    print()
    
    return actual_cost_per_image

if __name__ == '__main__':
    cost_per_image = main()
    print(f"📝 更新代码时使用: ${cost_per_image:.4f}/张")



