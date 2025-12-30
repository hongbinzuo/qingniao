"""
简化版规则引擎 - 不依赖experta，直接实现规则逻辑
用于Python 3.12兼容性
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
try:
    from dynamic_priority import calculate_dynamic_priority, check_rule_resonance, get_market_context
except ImportError:
    # 如果动态优先级模块不存在，使用默认优先级
    def calculate_dynamic_priority(base_priority, rule_name, market_context, timeframe='15m'):
        return base_priority
    def check_rule_resonance(signals):
        return signals
    def get_market_context(klines, current_price):
        return {'trend': 'neutral', 'volatility': 0}


@dataclass
class TradingSignal:
    """交易信号"""
    signal_type: str  # 'long', 'short', 'wait'
    strength: str  # 'strong', 'medium', 'weak'
    entry: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    reason: str
    priority: int = 0
    timeframe: str = "15m"
    rule_name: str = ""
    confirmed: bool = False  # 是否经过确认
    confirmations: List[str] = field(default_factory=list)  # 确认列表
    resonance: bool = False  # 是否与其他规则共振
    resonance_rules: List[str] = field(default_factory=list)  # 共振的规则列表


class SimpleRulesEngine:
    """简化版规则引擎"""
    
    def __init__(self):
        self.signals = []
        self.rules = []
    
    def add_rule(self, rule_func, priority=50):
        """添加规则"""
        self.rules.append((rule_func, priority))
        self.rules.sort(key=lambda x: x[1], reverse=True)  # 按优先级排序
    
    def analyze(self, market_data: Dict, patterns: List[Dict] = None, 
                support_resistance: Dict = None, ote_analysis: Dict = None,
                is_garbage_time: bool = False, breakout_levels: List[float] = None,
                klines: List[Dict] = None):
        """分析市场并生成信号（支持动态优先级）"""
        self.signals = []
        
        context = {
            'market_data': market_data,
            'patterns': patterns or [],
            'support_resistance': support_resistance or {},
            'ote_analysis': ote_analysis,
            'is_garbage_time': is_garbage_time,
            'breakout_levels': breakout_levels or []
        }
        
        # 获取市场环境上下文（用于动态优先级）
        current_price = market_data.get('current_price', 0)
        market_context = get_market_context(klines or [], current_price) if klines else {'trend': 'neutral', 'volatility': 0}
        timeframe = market_data.get('timeframe', '15m')
        
        # 执行所有规则（使用动态优先级）
        for rule_func, base_priority in self.rules:
            try:
                # 计算动态优先级
                rule_name = rule_func.__name__
                dynamic_priority = calculate_dynamic_priority(
                    base_priority, rule_name, market_context, timeframe
                )
                
                # 执行规则
                rule_func(context, self)
                
                # 更新最后添加的信号优先级（如果规则添加了信号）
                if self.signals:
                    last_signal = self.signals[-1]
                    if last_signal.rule_name == rule_name.replace('_rule', '').replace('_', '_').title():
                        last_signal.priority = dynamic_priority
            except Exception as e:
                print(f"规则执行错误: {e}", file=__import__('sys').stderr)
        
        # 检查规则共振
        self.signals = check_rule_resonance(self.signals)
        
        # 按优先级排序
        self.signals.sort(key=lambda s: s.priority, reverse=True)
        return self.signals
    
    def add_signal(self, signal: TradingSignal):
        """添加信号"""
        self.signals.append(signal)


# ==================== 规则定义 ====================

def fvg_bullish_rule(context, engine):
    """FVG看涨规则"""
    market_data = context['market_data']
    patterns = context['patterns']
    current_price = market_data.get('current_price', 0)
    
    for pattern in patterns:
        if pattern.get('pattern_type') == 'fvg_bullish' and pattern.get('is_valid'):
            price_level = pattern.get('price_level', 0)
            if current_price < price_level:
                entry = price_level * 1.002
                stop_loss = entry * 0.98
                risk = entry - stop_loss
                take_profit_1 = entry + risk * 2.5
                take_profit_2 = entry + risk * 3.5
                
                signal = TradingSignal(
                    signal_type='long',
                    strength='strong',
                    entry=entry,
                    stop_loss=stop_loss,
                    take_profit_1=take_profit_1,
                    take_profit_2=take_profit_2,
                    reason=f'FVG做多机会，挂单在{entry:.0f}等待回填',
                    priority=100,
                    timeframe=market_data.get('timeframe', '15m'),
                    rule_name='FVG_Bullish_Long'
                )
                engine.add_signal(signal)


def fvg_bearish_rule(context, engine):
    """FVG看跌规则"""
    market_data = context['market_data']
    patterns = context['patterns']
    current_price = market_data.get('current_price', 0)
    
    for pattern in patterns:
        if pattern.get('pattern_type') == 'fvg_bearish' and pattern.get('is_valid'):
            price_level = pattern.get('price_level', 0)
            if current_price > price_level:
                entry = price_level * 1.002
                stop_loss = entry * 1.02
                risk = stop_loss - entry
                take_profit_1 = entry - risk * 2.5
                take_profit_2 = entry - risk * 3.5
                
                signal = TradingSignal(
                    signal_type='short',
                    strength='strong',
                    entry=entry,
                    stop_loss=stop_loss,
                    take_profit_1=take_profit_1,
                    take_profit_2=take_profit_2,
                    reason=f'FVG做空机会，挂单在{entry:.0f}等待回填',
                    priority=100,
                    timeframe=market_data.get('timeframe', '15m'),
                    rule_name='FVG_Bearish_Short'
                )
                engine.add_signal(signal)


def m_top_rule(context, engine):
    """M顶规则（De.规则：15分钟M顶很好看）"""
    market_data = context['market_data']
    patterns = context['patterns']
    current_price = market_data.get('current_price', 0)
    
    for pattern in patterns:
        if pattern.get('pattern_type') == 'm_top' and pattern.get('is_valid'):
            price_level = pattern.get('price_level', 0)
            if abs(current_price - price_level) / max(current_price, price_level, 1) < 0.01:
                entry = price_level * 1.002
                stop_loss = entry * 1.015
                risk = stop_loss - entry
                take_profit_1 = entry - risk * 2.5
                take_profit_2 = entry - risk * 3.5
                
                signal = TradingSignal(
                    signal_type='short',
                    strength='strong',
                    entry=entry,
                    stop_loss=stop_loss,
                    take_profit_1=take_profit_1,
                    take_profit_2=take_profit_2,
                    reason=f'M顶形态确认，回踩到腰线{price_level:.0f}附近，等待反弹做空',
                    priority=90,
                    timeframe=market_data.get('timeframe', '15m'),
                    rule_name='M_Top_Short'
                )
                engine.add_signal(signal)


def w_bottom_rule(context, engine):
    """W底规则"""
    market_data = context['market_data']
    patterns = context['patterns']
    current_price = market_data.get('current_price', 0)
    
    for pattern in patterns:
        if pattern.get('pattern_type') == 'w_bottom' and pattern.get('is_valid'):
            price_level = pattern.get('price_level', 0)
            if abs(current_price - price_level) / max(current_price, price_level, 1) < 0.01:
                entry = price_level * 0.998
                stop_loss = entry * 0.985
                risk = entry - stop_loss
                take_profit_1 = entry + risk * 2.5
                take_profit_2 = entry + risk * 3.5
                
                signal = TradingSignal(
                    signal_type='long',
                    strength='strong',
                    entry=entry,
                    stop_loss=stop_loss,
                    take_profit_1=take_profit_1,
                    take_profit_2=take_profit_2,
                    reason=f'W底形态确认，反弹到腰线{price_level:.0f}附近，等待回调做多',
                    priority=90,
                    timeframe=market_data.get('timeframe', '15m'),
                    rule_name='W_Bottom_Long'
                )
                engine.add_signal(signal)


def breakout_rule(context, engine):
    """突破规则（De.规则：这把上去突破873可以进）"""
    market_data = context['market_data']
    breakout_levels = context.get('breakout_levels', [])
    current_price = market_data.get('current_price', 0)
    
    for breakout_price in breakout_levels:
        # 检查是否已经突破（当前价格高于突破位）
        if current_price <= breakout_price:
            continue
        
        # 检查是否刚突破（价格在突破位上方1%以内）
        if current_price > breakout_price * 1.01:
            continue
        
        # 入场价格：突破位上方0.2%
        entry = breakout_price * 1.002
        # 止损：突破位下方1%
        stop_loss = breakout_price * 0.99
        risk = entry - stop_loss
        
        if risk > 0:
            take_profit_1 = entry + risk * 2.5
            take_profit_2 = entry + risk * 3.5
        else:
            take_profit_1 = entry * 1.025
            take_profit_2 = entry * 1.035
        
        signal = TradingSignal(
            signal_type='long',
            strength='strong',
            entry=entry,
            stop_loss=stop_loss,
            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2,
            reason=f'价格突破关键位{breakout_price:.0f}，挂单在{entry:.0f}等待确认做多（De.规则：这把上去突破873可以进）',
            priority=85,
            timeframe=market_data.get('timeframe', '15m'),
            rule_name='Breakout_Long'
        )
        engine.add_signal(signal)


def vegas_above_rule(context, engine):
    """Vegas上方规则"""
    market_data = context['market_data']
    current_price = market_data.get('current_price', 0)
    ema_169 = market_data.get('ema_169', 0)
    
    if current_price > ema_169 and ema_169 > 0:
        entry = ema_169 * 1.002
        stop_loss = ema_169 * 0.99
        risk = entry - stop_loss
        take_profit_1 = entry + risk * 2.5
        take_profit_2 = entry + risk * 3.5
        
        signal = TradingSignal(
            signal_type='long',
            strength='medium',
            entry=entry,
            stop_loss=stop_loss,
            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2,
            reason=f'价格在Vegas通道上方，从Vegas反弹确认，等待回调入场',
            priority=70,
            timeframe=market_data.get('timeframe', '15m'),
            rule_name='Vegas_Above_Long'
        )
        engine.add_signal(signal)


def vegas_below_rule(context, engine):
    """Vegas下方规则"""
    market_data = context['market_data']
    current_price = market_data.get('current_price', 0)
    ema_144 = market_data.get('ema_144', 0)
    
    if current_price < ema_144 and ema_144 > 0:
        entry = ema_144 * 0.998
        stop_loss = ema_144 * 1.01
        risk = stop_loss - entry
        take_profit_1 = entry - risk * 2.5
        take_profit_2 = entry - risk * 3.5
        
        signal = TradingSignal(
            signal_type='short',
            strength='medium',
            entry=entry,
            stop_loss=stop_loss,
            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2,
            reason=f'价格在Vegas通道下方，从Vegas回落确认，等待反弹入场',
            priority=70,
            timeframe=market_data.get('timeframe', '15m'),
            rule_name='Vegas_Below_Short'
        )
        engine.add_signal(signal)


def garbage_time_rule(context, engine):
    """垃圾时间规则"""
    if context.get('is_garbage_time', False):
        market_data = context['market_data']
        signal = TradingSignal(
            signal_type='wait',
            strength='weak',
            entry=0,
            stop_loss=0,
            take_profit_1=0,
            take_profit_2=0,
            reason='垃圾时间，建议等待突破',
            priority=0,
            timeframe=market_data.get('timeframe', '15m'),
            rule_name='Garbage_Time_Wait'
        )
        engine.add_signal(signal)


# ==================== 主接口 ====================

def create_rules_engine():
    """创建规则引擎并注册所有规则"""
    engine = SimpleRulesEngine()
    
    # 注册所有规则（按优先级）
    engine.add_rule(fvg_bullish_rule, priority=100)
    engine.add_rule(fvg_bearish_rule, priority=100)
    engine.add_rule(m_top_rule, priority=90)
    engine.add_rule(w_bottom_rule, priority=90)
    engine.add_rule(breakout_rule, priority=85)
    engine.add_rule(vegas_above_rule, priority=70)
    engine.add_rule(vegas_below_rule, priority=70)
    engine.add_rule(garbage_time_rule, priority=0)
    
    return engine


def analyze_with_rules_engine(market_data: Dict, patterns: List[Dict] = None, 
                             support_resistance: Dict = None, ote_analysis: Dict = None,
                             is_garbage_time: bool = False, breakout_levels: List[float] = None) -> List[TradingSignal]:
    """
    使用规则引擎分析市场并生成交易信号
    
    Args:
        market_data: 市场数据
        patterns: 技术形态列表
        support_resistance: 支撑阻力数据
        ote_analysis: OTE分析数据
        is_garbage_time: 是否垃圾时间
        breakout_levels: 突破位列表
    
    Returns:
        交易信号列表
    """
    engine = create_rules_engine()
    signals = engine.analyze(
        market_data=market_data,
        patterns=patterns,
        support_resistance=support_resistance,
        ote_analysis=ote_analysis,
        is_garbage_time=is_garbage_time,
        breakout_levels=breakout_levels
    )
    return signals


if __name__ == "__main__":
    # 测试
    market_data = {
        'current_price': 87000,
        'ema_144': 86800,
        'ema_169': 86900,
        'vwap': 87050,
        'rsi': 55.0,
        'timeframe': '15m',
        'timestamp': datetime.now().timestamp()
    }
    
    patterns = [
        {
            'pattern_type': 'm_top',
            'is_valid': True,
            'price_level': 88000,
            'confidence': 0.85
        }
    ]
    
    support_resistance = {
        'nearest_support': 86500,
        'nearest_resistance': 87500,
        'support_levels': [86500, 86000],
        'resistance_levels': [87500, 88000]
    }
    
    breakout_levels = [87300]  # De.规则：突破873
    
    signals = analyze_with_rules_engine(
        market_data=market_data,
        patterns=patterns,
        support_resistance=support_resistance,
        breakout_levels=breakout_levels
    )
    
    print(f"生成了 {len(signals)} 个交易信号:")
    for signal in signals:
        print(f"\n{signal.rule_name}:")
        print(f"  类型: {signal.signal_type}")
        print(f"  强度: {signal.strength}")
        print(f"  入场: ${signal.entry:.2f}")
        print(f"  止损: ${signal.stop_loss:.2f}")
        print(f"  止盈1: ${signal.take_profit_1:.2f}")
        print(f"  止盈2: ${signal.take_profit_2:.2f}")
        print(f"  理由: {signal.reason}")

