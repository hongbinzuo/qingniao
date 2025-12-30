"""
智能交易规则引擎 - 基于experta专家系统
将De.交易系统的所有规则转换为可执行的智能规则系统
"""

try:
    from experta import *
except ImportError:
    print("警告: experta未安装，请运行: pip install experta")
    print("或者运行: python setup_rules_engine.py")
    raise

import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
try:
    import yaml
except ImportError:
    print("警告: PyYAML未安装，请运行: pip install pyyaml")
    raise


# ==================== 事实类（Facts） ====================

@dataclass
class MarketData:
    """市场数据事实"""
    current_price: float
    ema_144: Optional[float] = None
    ema_169: Optional[float] = None
    vwap: Optional[float] = None
    rsi: Optional[float] = None
    timeframe: str = "15m"
    timestamp: float = 0.0


@dataclass
class TechnicalPattern:
    """技术形态事实"""
    pattern_type: str  # 'm_top', 'w_bottom', 'fvg_bullish', 'fvg_bearish'
    is_valid: bool = True
    price_level: Optional[float] = None
    confidence: float = 0.0
    details: Dict = None


@dataclass
class SupportResistance:
    """支撑阻力事实"""
    support_levels: List[float]
    resistance_levels: List[float]
    nearest_support: Optional[float] = None
    nearest_resistance: Optional[float] = None


@dataclass
class LiquidityAnalysis:
    """流动性分析事实"""
    dense_bid_zones: List[float]
    dense_ask_zones: List[float]
    no_trade_zones: List[Dict] = None
    current_price: float = 0.0


@dataclass
class TradingSignal:
    """交易信号事实"""
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


# ==================== 规则引擎 ====================

class TradingRulesEngine(KnowledgeEngine):
    """智能交易规则引擎"""
    
    def __init__(self):
        super().__init__()
        self.signals = []
        self.market_context = {}
    
    # ========== 事实声明 ==========
    
    @DefFacts()
    def _initial_facts(self):
        """初始化事实"""
        yield Fact(action="analyze_market")
    
    # ========== 市场分析规则 ==========
    
    @Rule(
        Fact(action="analyze_market"),
        AS.market << Fact(market_data=MATCH.md)
    )
    def check_market_data(self, market):
        """检查市场数据完整性"""
        md = market['market_data']
        if md and md.get('current_price', 0) > 0:
            self.declare(Fact(market_ready=True))
    
    # ========== FVG规则（优先级最高） ==========
    
    @Rule(
        Fact(market_ready=True),
        AS.market << Fact(market_data=MATCH.md),
        AS.pattern << Fact(pattern=MATCH.p)
    )
    def fvg_bullish_long_signal(self, market, pattern):
        """FVG看涨做多信号"""
        p = pattern['pattern']
        if p.get('pattern_type') != 'fvg_bullish' or not p.get('is_valid'):
            return
        
        md = market['market_data']
        current_price = md.get('current_price', 0)
        price_level = p.get('price_level', float('inf'))
        
        if current_price >= price_level:
            return
        
        fvg_low = price_level
        
        entry = fvg_low * 1.002  # FVG下沿上方0.2%
        stop_loss = entry * 0.98  # 简化计算，实际应使用智能止损
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
            priority=100,  # 最高优先级
            timeframe=md.get('timeframe', '15m'),
            rule_name='FVG_Bullish_Long'
        )
        self.signals.append(signal)
        self.declare(Fact(signal_generated=True, signal_type='long', rule='FVG_Bullish'))
    
    @Rule(
        Fact(market_ready=True),
        AS.market << Fact(market_data=MATCH.md),
        AS.pattern << Fact(pattern=MATCH.p)
    )
    def fvg_bearish_short_signal(self, market, pattern):
        """FVG看跌做空信号"""
        p = pattern['pattern']
        if p.get('pattern_type') != 'fvg_bearish' or not p.get('is_valid'):
            return
        
        md = market['market_data']
        current_price = md.get('current_price', 0)
        price_level = p.get('price_level', 0)
        
        if current_price <= price_level:
            return
        
        fvg_high = price_level
        
        entry = fvg_high * 1.002  # FVG上沿上方0.2%
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
            timeframe=md.get('timeframe', '15m'),
            rule_name='FVG_Bearish_Short'
        )
        self.signals.append(signal)
        self.declare(Fact(signal_generated=True, signal_type='short', rule='FVG_Bearish'))
    
    # ========== M顶/W底规则 ==========
    
    @Rule(
        Fact(market_ready=True),
        AS.market << Fact(market_data=MATCH.md),
        AS.pattern << Fact(pattern=MATCH.p)
    )
    def m_top_short_signal(self, market, pattern):
        """M顶做空信号（De.规则：15分钟M顶很好看）"""
        p = pattern['pattern']
        if p.get('pattern_type') != 'm_top' or not p.get('is_valid'):
            return
        
        md = market['market_data']
        current_price = md.get('current_price', 0)
        price_level = p.get('price_level', 0)
        
        if abs(current_price - price_level) / max(current_price, price_level, 1) >= 0.01:
            return
        
        neckline = price_level
        
        entry = neckline * 1.002  # 腰线上方0.2%
        stop_loss = entry * 1.015  # 简化计算
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
            reason=f'M顶形态确认，回踩到腰线{neckline:.0f}附近，等待反弹做空',
            priority=90,
            timeframe=md.get('timeframe', '15m'),
            rule_name='M_Top_Short'
        )
        self.signals.append(signal)
        self.declare(Fact(signal_generated=True, signal_type='short', rule='M_Top'))
    
    @Rule(
        Fact(market_ready=True),
        AS.market << Fact(market_data=MATCH.md),
        AS.pattern << Fact(pattern=MATCH.p)
    )
    def w_bottom_long_signal(self, market, pattern):
        """W底做多信号"""
        p = pattern['pattern']
        if p.get('pattern_type') != 'w_bottom' or not p.get('is_valid'):
            return
        
        md = market['market_data']
        current_price = md.get('current_price', 0)
        price_level = p.get('price_level', 0)
        
        if abs(current_price - price_level) / max(current_price, price_level, 1) >= 0.01:
            return
        
        neckline = price_level
        
        entry = neckline * 0.998  # 腰线下方0.2%
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
            reason=f'W底形态确认，反弹到腰线{neckline:.0f}附近，等待回调做多',
            priority=90,
            timeframe=md.get('timeframe', '15m'),
            rule_name='W_Bottom_Long'
        )
        self.signals.append(signal)
        self.declare(Fact(signal_generated=True, signal_type='long', rule='W_Bottom'))
    
    # ========== Vegas通道规则 ==========
    
    @Rule(
        Fact(market_ready=True),
        AS.market << Fact(market_data=MATCH.md)
    )
    def vegas_above_long_signal(self, market):
        """价格在Vegas上方，做多信号"""
        md = market['market_data']
        current_price = md.get('current_price', 0)
        ema_169 = md.get('ema_169', 0)
        
        if current_price <= ema_169 or ema_169 <= 0:
            return
        
        
        entry = ema_169 * 1.002  # Vegas上方0.2%
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
            timeframe=md.get('timeframe', '15m'),
            rule_name='Vegas_Above_Long'
        )
        self.signals.append(signal)
    
    @Rule(
        Fact(market_ready=True),
        AS.market << Fact(market_data=MATCH.md)
    )
    def vegas_below_short_signal(self, market):
        """价格在Vegas下方，做空信号"""
        md = market['market_data']
        current_price = md.get('current_price', 0)
        ema_144 = md.get('ema_144', 0)
        
        if current_price >= ema_144 or ema_144 <= 0:
            return
        
        
        entry = ema_144 * 0.998  # Vegas下方0.2%
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
            timeframe=md.get('timeframe', '15m'),
            rule_name='Vegas_Below_Short'
        )
        self.signals.append(signal)
    
    # ========== 支撑阻力规则 ==========
    
    @Rule(
        Fact(market_ready=True),
        AS.market << Fact(market_data=MATCH.md),
        AS.sr << Fact(support_resistance=MATCH.sr_data)
    )
    def support_bounce_long_signal(self, market, sr):
        """支撑位反弹做多信号"""
        md = market['market_data']
        sr_data = sr['support_resistance']
        current_price = md.get('current_price', 0)
        nearest_support = sr_data.get('nearest_support', 0)
        
        if nearest_support <= 0 or current_price <= nearest_support * 1.01:
            return
        
        
        entry = nearest_support * 1.01  # 支撑位上方1%
        stop_loss = nearest_support * 0.99
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
            reason=f'价格从支撑位{nearest_support:.0f}反弹确认，挂单在{entry:.0f}等待回调',
            priority=60,
            timeframe=md.get('timeframe', '15m'),
            rule_name='Support_Bounce_Long'
        )
        self.signals.append(signal)
    
    # ========== 786斐波那契回撤位规则 ==========
    
    @Rule(
        Fact(market_ready=True),
        AS.market << Fact(market_data=MATCH.md),
        AS.ote << Fact(ote_analysis=MATCH.ote_data)
    )
    def ote_below_618_short_signal(self, market, ote):
        """价格跌破618，可能继续下跌"""
        ote_data = ote['ote_analysis']
        if not ote_data.get('below_618', False):
            return
        
        md = market['market_data']
        current_price = md.get('current_price', 0)
        fib_786 = ote_data.get('fib_786', current_price)
        
        # 结合W底反弹未破786的规则
        entry = fib_786 * 1.002
        stop_loss = entry * 1.015
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
            reason=f'W底反弹未破786回撤位{fib_786:.0f}，可能是看空信号',
            priority=80,
            timeframe=md.get('timeframe', '15m'),
            rule_name='OTE_Below_618_Short'
        )
        self.signals.append(signal)
    
    # ========== 突破交易规则（De.规则：这把上去突破873可以进） ==========
    
    @Rule(
        Fact(market_ready=True),
        AS.market << Fact(market_data=MATCH.md),
        Fact(breakout_level=MATCH.level)
    )
    def breakout_long_signal(self, market, level):
        """突破交易规则：价格突破关键位后做多（De.规则：这把上去突破873可以进）"""
        md = market['market_data']
        current_price = md.get('current_price', 0)
        breakout_price = level['price']
        
        # 检查是否已经突破（当前价格高于突破位）
        if current_price <= breakout_price:
            return
        
        # 检查是否刚突破（价格在突破位上方1%以内，避免太远）
        if current_price > breakout_price * 1.01:
            return
        
        # 入场价格：突破位上方0.2%，挂单等待确认
        entry = breakout_price * 1.002
        # 止损：突破位下方1-2%
        stop_loss = breakout_price * 0.99
        risk = entry - stop_loss
        
        if risk > 0:
            take_profit_1 = entry + risk * 2.5  # 1:2.5盈亏比
            take_profit_2 = entry + risk * 3.5  # 1:3.5盈亏比
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
            priority=85,  # 高优先级，仅次于M顶/W底
            timeframe=md.get('timeframe', '15m'),
            rule_name='Breakout_Long'
        )
        self.signals.append(signal)
        self.declare(Fact(signal_generated=True, signal_type='long', rule='Breakout'))
    
    # ========== 垃圾时间规则 ==========
    
    @Rule(
        Fact(market_ready=True),
        AS.market << Fact(market_data=MATCH.md),
        Fact(is_garbage_time=True)
    )
    def garbage_time_wait(self, market):
        """垃圾时间，建议等待"""
        md = market['market_data']
        signal = TradingSignal(
            signal_type='wait',
            strength='weak',
            entry=0,
            stop_loss=0,
            take_profit_1=0,
            take_profit_2=0,
            reason='垃圾时间，建议等待突破',
            priority=0,
            timeframe=md.get('timeframe', '15m'),
            rule_name='Garbage_Time_Wait'
        )
        self.signals.append(signal)
    
    # ========== 规则冲突解决 ==========
    
    @Rule(
        AS.s1 << Fact(signal_generated=True, signal_type=MATCH.t1, priority=MATCH.p1),
        AS.s2 << Fact(signal_generated=True, signal_type=MATCH.t2, priority=MATCH.p2),
        TEST(lambda p1, p2: p1 < p2)
    )
    def resolve_signal_conflict(self, s1, s2):
        """解决信号冲突，保留优先级高的信号"""
        # 移除优先级低的信号
        self.retract(s1)
    
    def get_signals(self) -> List[TradingSignal]:
        """获取生成的信号，按优先级排序"""
        return sorted(self.signals, key=lambda s: s.priority, reverse=True)
    
    def reset(self):
        """重置引擎"""
        self.signals = []
        self.market_context = {}
        self.reset()


# ==================== 规则配置管理 ====================

class RuleConfigManager:
    """规则配置管理器"""
    
    def __init__(self, config_file: str = "trading_rules_config.yaml"):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self) -> Dict:
        """加载规则配置"""
        default_config = {
            'rules': {
                'fvg': {
                    'enabled': True,
                    'priority': 100,
                    'min_confidence': 0.7
                },
                'm_top': {
                    'enabled': True,
                    'priority': 90,
                    'min_confidence': 0.8
                },
                'w_bottom': {
                    'enabled': True,
                    'priority': 90,
                    'min_confidence': 0.8
                },
                'vegas': {
                    'enabled': True,
                    'priority': 70,
                    'min_confidence': 0.6
                },
                'support_resistance': {
                    'enabled': True,
                    'priority': 60,
                    'min_confidence': 0.6
                },
                'ote': {
                    'enabled': True,
                    'priority': 80,
                    'min_confidence': 0.7
                }
            },
            'risk_management': {
                'min_risk_reward': 2.5,
                'max_stop_loss_pct': 0.05,
                'min_stop_loss_pct': 0.01
            }
        }
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return {**default_config, **(config or {})}
        except FileNotFoundError:
            return default_config
    
    def save_config(self):
        """保存规则配置"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, allow_unicode=True, default_flow_style=False)
    
    def update_rule(self, rule_name: str, enabled: bool = None, priority: int = None):
        """更新规则配置"""
        if rule_name in self.config.get('rules', {}):
            if enabled is not None:
                self.config['rules'][rule_name]['enabled'] = enabled
            if priority is not None:
                self.config['rules'][rule_name]['priority'] = priority
            self.save_config()


# ==================== 主接口 ====================

def analyze_with_rules_engine(market_data: Dict, patterns: List[Dict], 
                             support_resistance: Dict, ote_analysis: Dict = None,
                             is_garbage_time: bool = False) -> List[TradingSignal]:
    """
    使用规则引擎分析市场并生成交易信号
    
    Args:
        market_data: 市场数据
        patterns: 技术形态列表
        support_resistance: 支撑阻力数据
        ote_analysis: OTE分析数据
        is_garbage_time: 是否垃圾时间
    
    Returns:
        交易信号列表
    """
    engine = TradingRulesEngine()
    
    # 声明市场数据事实
    engine.declare(Fact(market_data=market_data))
    
    # 声明技术形态事实
    for pattern in patterns:
        engine.declare(Fact(pattern=pattern))
    
    # 声明支撑阻力事实
    engine.declare(Fact(support_resistance=support_resistance))
    
    # 声明OTE分析事实
    if ote_analysis:
        engine.declare(Fact(ote_analysis=ote_analysis))
    
    # 声明垃圾时间事实
    if is_garbage_time:
        engine.declare(Fact(is_garbage_time=True))
    
    # 声明突破位事实（De.规则：这把上去突破873可以进）
    if breakout_levels:
        for level in breakout_levels:
            engine.declare(Fact(breakout_level={'price': level}))
    
    # 运行规则引擎
    engine.run()
    
    # 获取生成的信号
    signals = engine.get_signals()
    
    return signals


if __name__ == "__main__":
    # 示例使用
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
    
    signals = analyze_with_rules_engine(
        market_data=market_data,
        patterns=patterns,
        support_resistance=support_resistance,
        is_garbage_time=False
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

