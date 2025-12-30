"""
应用高优先级优化方案
批量替换止损调用并集成确认机制
"""

import re

def apply_optimizations():
    """应用优化方案"""
    file_path = 'generate_btc_multi_tf_plan.py'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换所有 calculate_smart_stop_loss 调用为三级止损系统
    # 模式1: stop_loss = calculate_smart_stop_loss(entry, 'long', ...)
    pattern1 = r"stop_loss = calculate_smart_stop_loss\(entry, 'long', klines, fvgs, sr, key_levels, ema_144, ema_169\)"
    replacement1 = """stop_loss, stop_source, stop_info = calculate_three_tier_stop_loss(
                entry, 'long', klines, fvgs, sr, key_levels, ema_144, ema_169, current_price
            )"""
    content = re.sub(pattern1, replacement1, content)
    
    # 模式2: stop_loss = calculate_smart_stop_loss(entry, 'short', ...)
    pattern2 = r"stop_loss = calculate_smart_stop_loss\(entry, 'short', klines, fvgs, sr, key_levels, ema_144, ema_169\)"
    replacement2 = """stop_loss, stop_source, stop_info = calculate_three_tier_stop_loss(
                entry, 'short', klines, fvgs, sr, key_levels, ema_144, ema_169, current_price
            )"""
    content = re.sub(pattern2, replacement2, content)
    
    # 在信号字典中添加止损来源信息（如果还没有）
    # 查找 signal = { ... 'stop_loss': stop_loss, ... } 模式
    # 在 'stop_loss': stop_loss 后添加 'stop_loss_source': stop_source
    
    # 保存文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("优化方案已应用")

if __name__ == "__main__":
    apply_optimizations()


