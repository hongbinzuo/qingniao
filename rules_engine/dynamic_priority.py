"""
动态优先级系统
根据市场环境、时间框架、规则组合动态调整规则优先级
"""

from typing import Dict, Optional


def calculate_dynamic_priority(
    base_priority: int,
    rule_name: str,
    market_context: Dict,
    timeframe: str = '15m'
) -> int:
    """
    动态优先级计算：
    - 基础优先级：规则固有重要性
    - 市场环境调整：根据当前市场状态
    - 时间框架调整：不同时间框架重要性不同
    - 规则组合：多规则共振，优先级提升
    """
    priority = base_priority
    
    # 市场环境调整
    trend = market_context.get('trend', 'neutral')
    volatility = market_context.get('volatility', 0)
    
    if trend == 'strong':
        # 强趋势：突破规则优先级提升
        if 'breakout' in rule_name.lower():
            priority += 20
        # FVG规则在强趋势中也很重要
        if 'fvg' in rule_name.lower():
            priority += 10
    elif trend == 'ranging':
        # 震荡：M顶/W底规则优先级提升
        if 'm_top' in rule_name.lower() or 'w_bottom' in rule_name.lower():
            priority += 15
        # Vegas通道规则在震荡中重要
        if 'vegas' in rule_name.lower():
            priority += 10
    
    # 时间框架调整
    if timeframe == '15m':
        # 15分钟：De.特别关注M顶
        if 'm_top' in rule_name.lower():
            priority += 10
        # 15分钟：Vegas通道也很重要
        if 'vegas' in rule_name.lower():
            priority += 5
    elif timeframe == '5m':
        # 5分钟：快速进出，FVG和突破规则重要
        if 'fvg' in rule_name.lower() or 'breakout' in rule_name.lower():
            priority += 5
    elif timeframe == '1h':
        # 1小时：趋势确认，Vegas通道和支撑阻力重要
        if 'vegas' in rule_name.lower() or 'support' in rule_name.lower() or 'resistance' in rule_name.lower():
            priority += 5
    
    # 市场波动性调整
    if volatility > 0.02:
        # 高波动：FVG规则优先级提升
        if 'fvg' in rule_name.lower():
            priority += 5
    elif volatility < 0.01:
        # 低波动：M顶/W底规则优先级提升
        if 'm_top' in rule_name.lower() or 'w_bottom' in rule_name.lower():
            priority += 5
    
    return priority


def check_rule_resonance(signals: list) -> list:
    """
    检查规则共振：
    - 多规则共振：优先级提升
    - 规则冲突：使用更高级别的规则
    """
    # 按优先级排序
    signals.sort(key=lambda s: s.priority, reverse=True)
    
    # 检查规则共振
    for i, signal1 in enumerate(signals):
        for signal2 in signals[i+1:]:
            if is_resonance(signal1, signal2):
                signal1.priority += 10
                signal1.resonance = True
                signal1.resonance_rules = getattr(signal1, 'resonance_rules', []) + [signal2.rule_name]
    
    # 检查规则冲突
    signals_to_remove = []
    for i, signal1 in enumerate(signals):
        for signal2 in signals[i+1:]:
            if is_conflict(signal1, signal2):
                # 保留优先级高的，移除优先级低的
                if signal1.priority > signal2.priority:
                    signals_to_remove.append(signal2)
                else:
                    signals_to_remove.append(signal1)
    
    # 移除冲突的信号
    for signal in signals_to_remove:
        if signal in signals:
            signals.remove(signal)
    
    return signals


def is_resonance(signal1, signal2) -> bool:
    """检查两个信号是否共振（同向且互补）"""
    # 同向
    if signal1.signal_type != signal2.signal_type:
        return False
    
    # 互补（不同规则但同向）
    if signal1.rule_name != signal2.rule_name:
        return True
    
    return False


def is_conflict(signal1, signal2) -> bool:
    """检查两个信号是否冲突（反向）"""
    # 反向
    if signal1.signal_type != signal2.signal_type:
        # 检查入场价是否接近
        if abs(signal1.entry - signal2.entry) / max(signal1.entry, signal2.entry) < 0.01:
            return True
    
    return False


def get_market_context(klines: list, current_price: float) -> Dict:
    """获取市场环境上下文"""
    if not klines or len(klines) < 20:
        return {'trend': 'neutral', 'volatility': 0}
    
    closes = [k['close'] for k in klines[-20:]]
    
    # 计算趋势
    price_change = (closes[-1] - closes[-20]) / closes[-20] if len(closes) >= 20 else 0
    
    if price_change > 0.02:
        trend = 'strong_up'
    elif price_change > 0.005:
        trend = 'up'
    elif price_change < -0.02:
        trend = 'strong_down'
    elif price_change < -0.005:
        trend = 'down'
    else:
        trend = 'ranging'
    
    # 计算波动性
    returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
    volatility = sum(abs(r) for r in returns) / len(returns) if returns else 0
    
    return {
        'trend': trend,
        'volatility': volatility,
        'price_change': price_change
    }


