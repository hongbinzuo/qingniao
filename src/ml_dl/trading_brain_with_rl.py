#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易员大脑系统 + TensorTrade强化学习
整合规则引擎、市场感知、强化学习智能体
"""

import sys
from pathlib import Path
from typing import Dict, Optional

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from ml_dl.trading_brain_system import TradingBrainSystem

# 尝试导入TensorTrade RL
try:
    from ml_dl.tensortrade_rl_agent import TensorTradeRLAgent
    TENSORTRADE_AVAILABLE = True
except ImportError:
    TENSORTRADE_AVAILABLE = False
    print("警告: TensorTrade RL未可用，将使用基础系统", file=sys.stderr)


class EnhancedTradingBrainSystem(TradingBrainSystem):
    """增强版交易员大脑系统（集成TensorTrade RL）"""
    
    def __init__(self, trader_id='de', use_rl: bool = True):
        super().__init__(trader_id)
        
        self.use_rl = use_rl and TENSORTRADE_AVAILABLE
        self.rl_agent = None
        
        if self.use_rl:
            try:
                self.rl_agent = TensorTradeRLAgent(trader_id=trader_id)
                # 尝试加载已有模型
                if self.rl_agent.load_model(algorithm='PPO'):
                    print("✓ 已加载TensorTrade RL模型", file=sys.stderr)
            except Exception as e:
                print(f"⚠️  TensorTrade RL初始化失败: {e}", file=sys.stderr)
                self.use_rl = False
                self.rl_agent = None
    
    def generate_trading_signal(self, market_data=None, use_rl_optimization=True):
        """
        生成交易信号（增强版，支持RL优化）
        
        Args:
            market_data: 市场数据
            use_rl_optimization: 是否使用RL优化
        
        Returns:
            交易信号字典（包含RL优化建议）
        """
        # 1. 使用基础系统生成信号
        base_signal = super().generate_trading_signal(market_data)
        
        # 2. 如果启用RL且模型可用，进行RL优化
        if self.use_rl and use_rl_optimization and self.rl_agent and self.rl_agent.model:
            base_signal = self._optimize_with_rl(base_signal, market_data)
        
        return base_signal
    
    def _optimize_with_rl(self, base_signal: Dict, market_data: Dict = None) -> Dict:
        """使用RL模型优化信号"""
        if not base_signal.get('signal'):
            return base_signal
        
        # 这里可以添加RL优化逻辑
        # 例如：使用RL模型评估信号质量，调整参数等
        
        # 暂时返回基础信号（未来可以增强）
        base_signal['rl_optimized'] = False
        base_signal['rl_confidence'] = None
        
        return base_signal
    
    def train_rl_agent(self, algorithm: str = 'PPO', total_timesteps: int = 10000):
        """训练RL智能体"""
        if not self.use_rl or not self.rl_agent:
            raise ValueError("RL功能未启用或RL智能体未初始化")
        
        # 加载价格数据
        price_data = self.rl_agent.load_price_data(timeframe='5m', limit=5000)
        
        if price_data.empty:
            raise ValueError("无法加载价格数据")
        
        # 训练
        result = self.rl_agent.train_agent(
            price_data=price_data,
            algorithm=algorithm,
            total_timesteps=total_timesteps
        )
        
        return result
    
    def backtest_rl_strategy(self, initial_balance: float = 10000.0) -> Dict:
        """回测RL策略"""
        if not self.use_rl or not self.rl_agent or not self.rl_agent.model:
            raise ValueError("RL模型未加载")
        
        # 加载价格数据
        price_data = self.rl_agent.load_price_data(timeframe='5m', limit=5000)
        
        if price_data.empty:
            raise ValueError("无法加载价格数据")
        
        # 回测
        result = self.rl_agent.backtest(price_data, initial_balance)
        
        return result
    
    def close(self):
        """关闭所有连接"""
        super().close()
        if self.rl_agent:
            self.rl_agent.close()


def main():
    """主函数"""
    print("=" * 80)
    print("增强版交易员大脑系统（集成TensorTrade RL）")
    print("=" * 80)
    print()
    
    # 初始化系统
    brain = EnhancedTradingBrainSystem(trader_id='de', use_rl=True)
    
    # 生成信号
    print("生成交易信号...")
    signal = brain.generate_trading_signal(use_rl_optimization=True)
    
    print()
    print("=" * 80)
    print("信号生成结果")
    print("=" * 80)
    
    if signal.get('signal'):
        s = signal['signal']
        print(f"✓ 生成交易信号")
        print()
        print(f"方向: {s['direction']}")
        print(f"入场价格: ${s['entry_price']:,.2f}")
        print(f"止损: ${s['stop_loss']:,.2f}")
        print(f"第一止盈: ${s['take_profit_1']:,.2f}")
        print(f"第二止盈: {s['take_profit_2']:,.2f}")
        print(f"置信度: {signal['confidence']:.2%}")
        
        if signal.get('rl_optimized'):
            print(f"RL优化: 是")
            if signal.get('rl_confidence'):
                print(f"RL置信度: {signal['rl_confidence']:.2%}")
        else:
            print(f"RL优化: 否（模型未加载或未启用）")
    else:
        print("✗ 未生成交易信号")
        print(f"原因: {signal.get('reason', '未知')}")
    
    print()
    print("=" * 80)
    
    # 如果RL模型可用，提供回测选项
    if brain.use_rl and brain.rl_agent and brain.rl_agent.model:
        print()
        choice = input("是否回测RL策略？(y/n): ").strip().lower()
        if choice == 'y':
            print()
            print("开始回测...")
            backtest_result = brain.backtest_rl_strategy()
            
            print()
            print("=" * 80)
            print("RL策略回测结果")
            print("=" * 80)
            print(f"初始资金: ${backtest_result['initial_balance']:,.2f}")
            print(f"最终资金: ${backtest_result['final_balance']:,.2f}")
            print(f"总收益率: {backtest_result['total_return_pct']:.2f}%")
            print(f"最大回撤: {backtest_result['max_drawdown_pct']:.2f}%")
            print(f"总交易次数: {backtest_result['total_trades']}")
    
    brain.close()

if __name__ == '__main__':
    main()










