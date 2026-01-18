#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TensorTrade强化学习交易智能体
使用TensorTrade框架训练RL智能体，学习最优交易策略
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# 尝试导入TensorTrade
try:
    import tensortrade as tt
    from tensortrade.env import TradingEnvironment
    from tensortrade.exchanges import Exchange, SimulatedExchange
    from tensortrade.features import FeaturePipeline, FeatureUnion, FeatureSelector
    from tensortrade.actions import DiscreteActionStrategy, ContinuousActionStrategy
    from tensortrade.rewards import SimpleProfitStrategy, RiskAdjustedReturns
    from tensortrade.instruments import Instrument
    TENSORTRADE_AVAILABLE = True
except ImportError:
    TENSORTRADE_AVAILABLE = False
    print("警告: TensorTrade未安装，RL功能不可用", file=sys.stderr)
    print("请安装: pip install tensortrade", file=sys.stderr)

# 尝试导入强化学习库
try:
    import gym
    from stable_baselines3 import PPO, DQN, A2C
    from stable_baselines3.common.env_util import make_vec_env
    STABLE_BASELINES_AVAILABLE = True
except ImportError:
    STABLE_BASELINES_AVAILABLE = False
    print("警告: stable-baselines3未安装，RL训练功能受限", file=sys.stderr)


class TensorTradeRLAgent:
    """TensorTrade强化学习交易智能体"""
    
    def __init__(self, trader_id='de', model_dir: Optional[Path] = None):
        if not TENSORTRADE_AVAILABLE:
            raise ImportError("TensorTrade未安装，无法使用RL功能")
        
        self.trader_id = trader_id
        
        if model_dir is None:
            base_dir = Path(__file__).parent.parent.parent
            model_dir = base_dir / "trading_signals" / ".ml_models" / "rl_agent"
        
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.env = None
        self.model = None
        self.feature_pipeline = None
        
        # 初始化价格数据连接
        self._init_price_data()
    
    def _init_price_data(self):
        """初始化价格数据连接"""
        try:
            import duckdb
            ts_file = Path(__file__).parent.parent / "data" / "btc_price_timeseries.duckdb"
            if ts_file.exists():
                self.price_conn = duckdb.connect(str(ts_file))
            else:
                self.price_conn = None
        except:
            self.price_conn = None
    
    def load_price_data(self, timeframe: str = '5m', limit: int = 10000) -> pd.DataFrame:
        """从时序库加载价格数据"""
        if not self.price_conn:
            return pd.DataFrame()
        
        table_name = f'btc_price_{timeframe}'
        try:
            # 检查表是否存在
            tables = self.price_conn.execute("SHOW TABLES").fetchall()
            table_names = [t[0] for t in tables]
            
            if table_name not in table_names:
                print(f"  表 {table_name} 不存在", file=sys.stderr)
                return pd.DataFrame()
            
            # 加载数据
            query = f'''
                SELECT timestamp, datetime, open, high, low, close, volume
                FROM {table_name}
                ORDER BY timestamp
                LIMIT {limit}
            '''
            df = pd.read_sql(query, self.price_conn)
            
            # 确保列名符合TensorTrade要求
            df = df.rename(columns={
                'timestamp': 'date',
                'close': 'price'
            })
            
            # 设置日期索引
            if 'datetime' in df.columns:
                df['date'] = pd.to_datetime(df['datetime'])
            else:
                df['date'] = pd.to_datetime(df['date'], unit='s')
            
            df = df.set_index('date')
            
            return df[['open', 'high', 'low', 'price', 'volume']]
        except Exception as e:
            print(f"  加载价格数据失败: {e}", file=sys.stderr)
            return pd.DataFrame()
    
    def create_trading_environment(self, price_data: pd.DataFrame,
                                   initial_balance: float = 10000.0,
                                   commission: float = 0.001) -> TradingEnvironment:
        """
        创建TensorTrade交易环境
        
        Args:
            price_data: 价格数据（DataFrame，索引为日期）
            initial_balance: 初始资金
            commission: 手续费率
        
        Returns:
            TradingEnvironment对象
        """
        if not TENSORTRADE_AVAILABLE:
            raise ImportError("TensorTrade未安装")
        
        # 1. 创建交易所
        exchange = SimulatedExchange(
            base_instrument=Instrument('USDT', 2, 'USDT'),
            should_pretransform_obs=True
        )
        
        # 2. 创建特征管道（简化版）
        # 可以添加更多技术指标
        feature_pipeline = FeaturePipeline([
            FeatureSelector(['open', 'high', 'low', 'price', 'volume'])
        ])
        
        # 3. 创建动作策略（离散动作：买入/卖出/持有）
        action_strategy = DiscreteActionStrategy(
            n_actions=3,  # 0=持有, 1=买入, 2=卖出
            instrument_symbol='BTC'
        )
        
        # 4. 创建奖励策略（基于收益和风险）
        reward_strategy = RiskAdjustedReturns(
            return_algorithm='sharpe',
            risk_free_rate=0.0,
            window_size=10
        )
        
        # 5. 创建交易环境
        env = TradingEnvironment(
            exchange=exchange,
            action_strategy=action_strategy,
            reward_strategy=reward_strategy,
            feature_pipeline=feature_pipeline,
            initial_balance=initial_balance,
            base_instrument=Instrument('BTC', 8, 'BTC'),
            should_pretransform_obs=True,
            window_size=20  # 使用20个时间步的窗口
        )
        
        # 6. 设置价格数据
        env.exchange.data_frame = price_data
        
        self.env = env
        self.feature_pipeline = feature_pipeline
        
        return env
    
    def train_agent(self, price_data: pd.DataFrame, 
                   algorithm: str = 'PPO',
                   total_timesteps: int = 100000,
                   save_model: bool = True) -> Dict:
        """
        训练强化学习智能体
        
        Args:
            price_data: 价格数据
            algorithm: 算法 ('PPO', 'DQN', 'A2C')
            total_timesteps: 训练步数
            save_model: 是否保存模型
        
        Returns:
            训练结果字典
        """
        if not STABLE_BASELINES_AVAILABLE:
            raise ImportError("stable-baselines3未安装，无法训练模型")
        
        print("=" * 80)
        print(f"训练TensorTrade RL智能体 ({algorithm})")
        print("=" * 80)
        print()
        
        # 1. 创建环境
        print("创建交易环境...")
        env = self.create_trading_environment(price_data)
        print(f"✓ 环境创建完成")
        print(f"  观察空间: {env.observation_space}")
        print(f"  动作空间: {env.action_space}")
        print()
        
        # 2. 创建模型
        print(f"初始化{algorithm}模型...")
        if algorithm == 'PPO':
            model = PPO('MlpPolicy', env, verbose=1, 
                        learning_rate=3e-4,
                        n_steps=2048,
                        batch_size=64,
                        n_epochs=10,
                        gamma=0.99,
                        gae_lambda=0.95,
                        clip_range=0.2)
        elif algorithm == 'DQN':
            model = DQN('MlpPolicy', env, verbose=1,
                       learning_rate=1e-4,
                       buffer_size=100000,
                       learning_starts=1000,
                       batch_size=32,
                       gamma=0.99,
                       target_update_interval=1000)
        elif algorithm == 'A2C':
            model = A2C('MlpPolicy', env, verbose=1,
                       learning_rate=7e-4,
                       n_steps=5,
                       gamma=0.99)
        else:
            raise ValueError(f"不支持的算法: {algorithm}")
        
        self.model = model
        print(f"✓ 模型初始化完成")
        print()
        
        # 3. 训练
        print(f"开始训练（{total_timesteps}步）...")
        print("这可能需要一些时间，请耐心等待...")
        print()
        
        try:
            model.learn(total_timesteps=total_timesteps)
            print()
            print("✓ 训练完成！")
        except KeyboardInterrupt:
            print()
            print("⚠️  训练被用户中断")
        except Exception as e:
            print()
            print(f"❌ 训练失败: {e}")
            raise
        
        # 4. 保存模型
        if save_model:
            model_path = self.model_dir / f"{algorithm}_model.zip"
            model.save(str(model_path))
            print(f"✓ 模型已保存到: {model_path}")
        
        print()
        print("=" * 80)
        
        return {
            'algorithm': algorithm,
            'total_timesteps': total_timesteps,
            'model_path': str(model_path) if save_model else None
        }
    
    def load_model(self, algorithm: str = 'PPO') -> bool:
        """加载训练好的模型"""
        if not STABLE_BASELINES_AVAILABLE:
            return False
        
        model_path = self.model_dir / f"{algorithm}_model.zip"
        if not model_path.exists():
            return False
        
        # 需要先创建环境才能加载模型
        if self.env is None:
            # 使用临时数据创建环境
            temp_data = self.load_price_data(limit=100)
            if temp_data.empty:
                return False
            self.create_trading_environment(temp_data)
        
        if algorithm == 'PPO':
            self.model = PPO.load(str(model_path), env=self.env)
        elif algorithm == 'DQN':
            self.model = DQN.load(str(model_path), env=self.env)
        elif algorithm == 'A2C':
            self.model = A2C.load(str(model_path), env=self.env)
        else:
            return False
        
        return True
    
    def predict_action(self, observation: np.ndarray) -> int:
        """预测动作"""
        if self.model is None:
            raise ValueError("模型未加载，请先训练或加载模型")
        
        action, _ = self.model.predict(observation, deterministic=True)
        return int(action)
    
    def backtest(self, price_data: pd.DataFrame, 
                initial_balance: float = 10000.0) -> Dict:
        """
        回测策略
        
        Args:
            price_data: 价格数据
            initial_balance: 初始资金
        
        Returns:
            回测结果字典
        """
        if self.model is None:
            raise ValueError("模型未加载，请先训练或加载模型")
        
        # 创建环境
        env = self.create_trading_environment(price_data, initial_balance)
        
        # 重置环境
        obs = env.reset()
        
        # 回测
        done = False
        actions = []
        rewards = []
        equity = [initial_balance]
        
        while not done:
            # 预测动作
            action, _ = self.model.predict(obs, deterministic=True)
            actions.append(int(action))
            
            # 执行动作
            obs, reward, done, info = env.step(action)
            rewards.append(reward)
            
            # 记录权益
            current_balance = env.exchange.balance
            equity.append(current_balance)
        
        # 计算性能指标
        final_balance = equity[-1]
        total_return = (final_balance - initial_balance) / initial_balance
        
        # 计算最大回撤
        equity_array = np.array(equity)
        running_max = np.maximum.accumulate(equity_array)
        drawdown = (equity_array - running_max) / running_max
        max_drawdown = np.min(drawdown)
        
        return {
            'initial_balance': initial_balance,
            'final_balance': final_balance,
            'total_return': total_return,
            'total_return_pct': total_return * 100,
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': abs(max_drawdown) * 100,
            'total_trades': len([a for a in actions if a != 0]),  # 非持有动作
            'actions': actions,
            'rewards': rewards,
            'equity': equity
        }
    
    def close(self):
        """关闭连接"""
        if hasattr(self, 'price_conn') and self.price_conn:
            self.price_conn.close()


def main():
    """主函数"""
    if not TENSORTRADE_AVAILABLE:
        print("❌ TensorTrade未安装")
        print("请安装: pip install tensortrade")
        return
    
    if not STABLE_BASELINES_AVAILABLE:
        print("❌ stable-baselines3未安装")
        print("请安装: pip install stable-baselines3")
        return
    
    print("=" * 80)
    print("TensorTrade强化学习交易智能体")
    print("=" * 80)
    print()
    
    agent = TensorTradeRLAgent(trader_id='de')
    
    # 加载价格数据
    print("加载价格数据...")
    price_data = agent.load_price_data(timeframe='5m', limit=5000)
    
    if price_data.empty:
        print("❌ 无法加载价格数据")
        agent.close()
        return
    
    print(f"✓ 加载了 {len(price_data)} 条价格数据")
    print(f"  时间范围: {price_data.index[0]} 到 {price_data.index[-1]}")
    print()
    
    # 选择操作
    import sys
    print("请选择操作:")
    print("1. 训练新模型")
    print("2. 加载已有模型并回测")
    print("3. 退出")
    
    choice = input("请输入选择 (1/2/3): ").strip()
    
    if choice == '1':
        # 训练模型
        algorithm = input("选择算法 (PPO/DQN/A2C，默认PPO): ").strip() or 'PPO'
        timesteps = input("训练步数 (默认10000): ").strip()
        timesteps = int(timesteps) if timesteps else 10000
        
        result = agent.train_agent(
            price_data=price_data,
            algorithm=algorithm,
            total_timesteps=timesteps
        )
        
        print()
        print("训练完成！")
        print(f"算法: {result['algorithm']}")
        print(f"训练步数: {result['total_timesteps']}")
        if result['model_path']:
            print(f"模型路径: {result['model_path']}")
    
    elif choice == '2':
        # 加载模型并回测
        algorithm = input("选择算法 (PPO/DQN/A2C，默认PPO): ").strip() or 'PPO'
        
        if agent.load_model(algorithm=algorithm):
            print(f"✓ 成功加载{algorithm}模型")
            
            # 回测
            print()
            print("开始回测...")
            backtest_result = agent.backtest(price_data)
            
            print()
            print("=" * 80)
            print("回测结果")
            print("=" * 80)
            print(f"初始资金: ${backtest_result['initial_balance']:,.2f}")
            print(f"最终资金: ${backtest_result['final_balance']:,.2f}")
            print(f"总收益率: {backtest_result['total_return_pct']:.2f}%")
            print(f"最大回撤: {backtest_result['max_drawdown_pct']:.2f}%")
            print(f"总交易次数: {backtest_result['total_trades']}")
        else:
            print(f"❌ 无法加载{algorithm}模型")
            print("请先训练模型")
    
    agent.close()

if __name__ == '__main__':
    main()










