#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABU系统v3.0回测引擎

借鉴nofx回测框架设计，支持：
1. 交易计划回测
2. 账户管理（资金、仓位、手续费、滑点）
3. 性能指标计算
4. 权益曲线记录
5. 检查点保存（支持断点续传）
6. 自动化回测
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import statistics

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False
    print("[WARN] duckdb未安装，回测功能受限", file=sys.stderr)


@dataclass
class BacktestAccount:
    """回测账户"""
    initial_balance: float = 10000.0  # 初始资金
    cash: float = 10000.0  # 可用资金
    equity: float = 10000.0  # 总权益
    fee_bps: float = 5.0  # 手续费（基点，0.05%）
    slippage_bps: float = 2.0  # 滑点（基点，0.02%）
    
    # 持仓
    positions: Dict[str, Dict] = field(default_factory=dict)  # {symbol: position_info}
    
    # 统计
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_fees: float = 0.0
    total_slippage: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    
    def reset(self):
        """重置账户"""
        self.cash = self.initial_balance
        self.equity = self.initial_balance
        self.positions = {}
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_fees = 0.0
        self.total_slippage = 0.0
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
    
    def calculate_fee(self, order_value: float) -> float:
        """计算手续费"""
        return order_value * (self.fee_bps / 10000.0)
    
    def apply_slippage(self, price: float, direction: str) -> float:
        """应用滑点"""
        slippage_pct = self.slippage_bps / 10000.0
        if direction == 'long':
            return price * (1 + slippage_pct)  # 买入时价格更高
        else:
            return price * (1 - slippage_pct)  # 卖出时价格更低
    
    def open_position(self, symbol: str, direction: str, quantity: float, 
                     entry_price: float, current_price: float) -> Dict:
        """开仓"""
        # 应用滑点
        actual_price = self.apply_slippage(entry_price, direction)
        
        # 计算订单价值
        order_value = quantity * actual_price
        
        # 计算手续费
        fee = self.calculate_fee(order_value)
        
        # 计算滑点成本
        slippage_cost = abs(actual_price - entry_price) * quantity
        
        # 检查资金是否足够
        if self.cash < order_value + fee:
            return {'success': False, 'reason': '资金不足'}
        
        # 扣除资金
        self.cash -= (order_value + fee)
        self.total_fees += fee
        self.total_slippage += slippage_cost
        
        # 记录持仓
        self.positions[symbol] = {
            'symbol': symbol,
            'direction': direction,
            'quantity': quantity,
            'entry_price': actual_price,
            'entry_time': datetime.now(),
            'current_price': current_price,
            'unrealized_pnl': 0.0,
            'unrealized_pnl_pct': 0.0
        }
        
        self.total_trades += 1
        
        return {
            'success': True,
            'entry_price': actual_price,
            'fee': fee,
            'slippage': slippage_cost,
            'order_value': order_value
        }
    
    def close_position(self, symbol: str, exit_price: float, 
                      reason: str = 'manual') -> Dict:
        """平仓"""
        if symbol not in self.positions:
            return {'success': False, 'reason': '无持仓'}
        
        position = self.positions[symbol]
        direction = position['direction']
        quantity = position['quantity']
        entry_price = position['entry_price']
        
        # 应用滑点
        actual_exit_price = self.apply_slippage(exit_price, 'short' if direction == 'long' else 'long')
        
        # 计算订单价值
        order_value = quantity * actual_exit_price
        
        # 计算手续费
        fee = self.calculate_fee(order_value)
        
        # 计算滑点成本
        slippage_cost = abs(actual_exit_price - exit_price) * quantity
        
        # 计算盈亏
        if direction == 'long':
            pnl = (actual_exit_price - entry_price) * quantity
        else:
            pnl = (entry_price - actual_exit_price) * quantity
        
        net_pnl = pnl - fee - slippage_cost
        
        # 更新资金
        self.cash += order_value - fee
        self.total_fees += fee
        self.total_slippage += slippage_cost
        self.realized_pnl += net_pnl
        
        # 统计
        if net_pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        # 移除持仓
        del self.positions[symbol]
        
        return {
            'success': True,
            'exit_price': actual_exit_price,
            'pnl': pnl,
            'net_pnl': net_pnl,
            'fee': fee,
            'slippage': slippage_cost,
            'reason': reason
        }
    
    def update_unrealized_pnl(self, symbol: str, current_price: float):
        """更新未实现盈亏"""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        direction = position['direction']
        quantity = position['quantity']
        entry_price = position['entry_price']
        
        if direction == 'long':
            pnl = (current_price - entry_price) * quantity
        else:
            pnl = (entry_price - current_price) * quantity
        
        position['current_price'] = current_price
        position['unrealized_pnl'] = pnl
        position['unrealized_pnl_pct'] = (pnl / (entry_price * quantity)) * 100
        
        self.unrealized_pnl = sum(p['unrealized_pnl'] for p in self.positions.values())
    
    def get_equity(self) -> float:
        """获取总权益"""
        self.equity = self.cash + sum(p['unrealized_pnl'] for p in self.positions.values())
        return self.equity


@dataclass
class EquityPoint:
    """权益点"""
    timestamp: int
    datetime: str
    equity: float
    cash: float
    unrealized_pnl: float
    realized_pnl: float
    drawdown_pct: float
    max_equity: float


@dataclass
class TradeEvent:
    """交易事件"""
    timestamp: int
    datetime: str
    symbol: str
    action: str  # 'open' or 'close'
    direction: str  # 'long' or 'short'
    quantity: float
    price: float
    fee: float
    slippage: float
    pnl: float
    net_pnl: float
    reason: str
    signal_id: Optional[str] = None


@dataclass
class BacktestMetrics:
    """回测指标"""
    total_return_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    profit_factor: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    total_fees: float = 0.0
    total_slippage: float = 0.0
    best_symbol: str = ''
    worst_symbol: str = ''
    symbol_stats: Dict[str, Dict] = field(default_factory=dict)


class BacktestEngine:
    """回测引擎"""
    
    def __init__(
        self,
        initial_balance: float = 10000.0,
        fee_bps: float = 5.0,
        slippage_bps: float = 2.0,
        position_size_pct: float = 0.1,  # 10%仓位
        max_position_pct: float = 0.3,  # 最大30%仓位
        use_breakeven_stop: bool = True  # 使用保本止损
    ):
        """
        初始化回测引擎
        
        Args:
            initial_balance: 初始资金
            fee_bps: 手续费（基点）
            slippage_bps: 滑点（基点）
            position_size_pct: 单笔仓位百分比
            max_position_pct: 最大总仓位百分比
            use_breakeven_stop: 是否使用保本止损
        """
        self.account = BacktestAccount(
            initial_balance=initial_balance,
            fee_bps=fee_bps,
            slippage_bps=slippage_bps
        )
        
        self.position_size_pct = position_size_pct
        self.max_position_pct = max_position_pct
        self.use_breakeven_stop = use_breakeven_stop
        
        # 价格数据连接
        self.price_conn = None
        self._init_price_data()
        
        # 回测结果
        self.equity_curve: List[EquityPoint] = []
        self.trade_events: List[TradeEvent] = []
        self.active_signals: Dict[str, Dict] = {}  # {signal_id: signal_info}
        self.completed_signals: List[Dict] = []
        
        # 统计
        self.max_equity = initial_balance
        self.min_equity = initial_balance
    
    def _init_price_data(self):
        """初始化价格数据连接"""
        if not DUCKDB_AVAILABLE:
            return
        
        try:
            ts_file = ROOT / "data" / "btc_price_timeseries.duckdb"
            if ts_file.exists():
                self.price_conn = duckdb.connect(str(ts_file))
        except Exception as e:
            print(f"[WARN] 价格数据连接失败: {e}", file=sys.stderr)
    
    def get_price_at_time(self, symbol: str, timestamp: int, timeframe: str = '5m') -> Optional[float]:
        """获取指定时间的价格"""
        if not self.price_conn:
            return None
        
        try:
            table_name = f"btc_price_{timeframe}"
            result = self.price_conn.execute(f'''
                SELECT close
                FROM {table_name}
                WHERE timestamp <= ?
                ORDER BY timestamp DESC
                LIMIT 1
            ''', [timestamp]).fetchone()
            
            if result:
                return float(result[0])
        except Exception as e:
            pass
        
        return None
    
    def get_klines_after_time(self, symbol: str, start_timestamp: int, 
                              timeframe: str = '5m', limit: int = 1000) -> List[Dict]:
        """获取指定时间之后的K线数据"""
        if not self.price_conn:
            return []
        
        try:
            # 尝试币种特定的表，如果不存在则使用BTC表（兼容性）
            table_name = f"{symbol.lower()}_price_{timeframe}"
            try:
                # 检查表是否存在
                self.price_conn.execute(f"SELECT 1 FROM {table_name} LIMIT 1").fetchone()
            except:
                # 如果不存在，使用BTC表（作为默认）
                table_name = f"btc_price_{timeframe}"
            
            results = self.price_conn.execute(f'''
                SELECT timestamp, open, high, low, close, volume
                FROM {table_name}
                WHERE timestamp >= ?
                ORDER BY timestamp
                LIMIT ?
            ''', [start_timestamp, limit]).fetchall()
            
            klines = []
            for row in results:
                klines.append({
                    'timestamp': int(row[0]),
                    'open': float(row[1]),
                    'high': float(row[2]),
                    'low': float(row[3]),
                    'close': float(row[4]),
                    'volume': float(row[5]) if row[5] else 0.0
                })
            return klines
        except Exception as e:
            return []
    
    def backtest_signal(self, signal: Dict, timeframe: str = '5m', validate_brooks_rules: bool = True) -> Dict:
        """
        回测单个信号
        
        Args:
            signal: 信号字典，包含：
                - pattern_name, pattern_type, source
                - direction: 'long' or 'short'
                - entry_price: 入场价
                - stop_loss: 止损价
                - take_profit_1: 止盈1
                - take_profit_2: 止盈2
                - confidence: 置信度
                - signal_time: 信号时间（可选）
            timeframe: 时间框架
        
        Returns:
            回测结果
        """
        signal_id = signal.get('pattern_id') or f"signal_{int(time.time())}"
        direction = signal.get('direction', 'long').lower()
        entry_price = signal.get('entry_price', 0)
        stop_loss = signal.get('stop_loss', 0)
        take_profit_1 = signal.get('take_profit_1', 0)
        take_profit_2 = signal.get('take_profit_2', 0)
        signal_time = signal.get('signal_time')
        
        if not all([entry_price, stop_loss, take_profit_1]):
            return {'success': False, 'reason': '信号参数不完整'}
        
        # 验证止损方向
        if direction == 'long' and stop_loss >= entry_price:
            return {'success': False, 'reason': '做多止损应在入场价下方'}
        if direction == 'short' and stop_loss <= entry_price:
            return {'success': False, 'reason': '做空止损应在入场价上方'}
        
        # 确定信号时间
        if signal_time:
            if isinstance(signal_time, str):
                signal_dt = datetime.strptime(signal_time, '%Y-%m-%d %H:%M:%S')
            else:
                signal_dt = signal_time
        else:
            signal_dt = datetime.now() - timedelta(hours=1)  # 默认1小时前
        
        signal_timestamp = int(signal_dt.timestamp())
        
        # 获取币种符号
        symbol = signal.get('symbol', 'BTC').upper()
        
        # 获取K线数据
        klines = self.get_klines_after_time(symbol, signal_timestamp, timeframe, limit=1000)
        if not klines:
            return {'success': False, 'reason': '无价格数据'}
        
        # 计算仓位大小
        position_value = self.account.equity * self.position_size_pct
        quantity = position_value / entry_price
        
        # 开仓
        open_result = self.account.open_position(symbol, direction, quantity, entry_price, entry_price)
        if not open_result['success']:
            return {'success': False, 'reason': open_result['reason']}
        
        # 记录交易事件
        self.trade_events.append(TradeEvent(
            timestamp=signal_timestamp,
            datetime=signal_dt.strftime('%Y-%m-%d %H:%M:%S'),
            symbol=symbol,
            action='open',
            direction=direction,
            quantity=quantity,
            price=open_result['entry_price'],
            fee=open_result['fee'],
            slippage=open_result['slippage'],
            pnl=0.0,
            net_pnl=0.0,
            reason='signal_entry',
            signal_id=signal_id
        ))
        
        # 保本止损逻辑
        current_stop_loss = stop_loss
        tp1_reached = False
        entry_reached = False
        
        # 回测逻辑：遍历K线检查止损/止盈
        result = {
            'signal_id': signal_id,
            'success': True,
            'status': 'unknown',
            'exit_reason': None,
            'entry_price': open_result['entry_price'],
            'exit_price': entry_price,
            'exit_time': None,
            'pnl': 0.0,
            'pnl_pct': 0.0,
            'max_profit_pct': 0.0,
            'max_loss_pct': 0.0,
            'duration_hours': 0.0,
            'tp1_reached': False,
            'tp2_reached': False,
            'stop_loss_hit': False,
            'breakeven_stop_hit': False
        }
        
        for kline in klines:
            k_time = datetime.fromtimestamp(kline['timestamp'])
            high = kline['high']
            low = kline['low']
            close = kline['close']
            
            # 检查是否到达入场价
            if not entry_reached:
                if direction == 'long' and low <= entry_price * 1.001:
                    entry_reached = True
                elif direction == 'short' and high >= entry_price * 0.999:
                    entry_reached = True
            
            # 更新未实现盈亏
            self.account.update_unrealized_pnl('BTC', close)
            equity = self.account.get_equity()
            
            # 记录权益点
            if len(self.equity_curve) == 0 or (kline['timestamp'] - self.equity_curve[-1].timestamp) >= 3600:
                max_equity = max(self.max_equity, equity)
                min_equity = min(self.min_equity, equity)
                drawdown = (max_equity - equity) / max_equity if max_equity > 0 else 0
                
                self.equity_curve.append(EquityPoint(
                    timestamp=kline['timestamp'],
                    datetime=k_time.strftime('%Y-%m-%d %H:%M:%S'),
                    equity=equity,
                    cash=self.account.cash,
                    unrealized_pnl=self.account.unrealized_pnl,
                    realized_pnl=self.account.realized_pnl,
                    drawdown_pct=drawdown * 100,
                    max_equity=max_equity
                ))
                
                self.max_equity = max_equity
                self.min_equity = min_equity
            
            # 计算最大浮盈/浮亏
            if direction == 'long':
                profit_pct = ((high - entry_price) / entry_price) * 100
                loss_pct = ((low - entry_price) / entry_price) * 100
            else:
                profit_pct = ((entry_price - low) / entry_price) * 100
                loss_pct = ((entry_price - high) / entry_price) * 100
            
            result['max_profit_pct'] = max(result['max_profit_pct'], profit_pct)
            result['max_loss_pct'] = min(result['max_loss_pct'], loss_pct)
            
            # 检查止盈1
            if take_profit_1 and not tp1_reached:
                if direction == 'long' and high >= take_profit_1:
                    if not entry_reached:
                        # 入场价未到但先到止盈1，信号无效
                        close_result = self.account.close_position(symbol, entry_price, 'invalid_signal')
                        result['status'] = 'invalid'
                        result['exit_reason'] = '入场价未到但先到止盈1'
                        result['exit_price'] = close_result.get('exit_price', entry_price)
                        result['exit_time'] = k_time.strftime('%Y-%m-%d %H:%M:%S')
                        result['pnl'] = close_result.get('net_pnl', 0)
                        result['pnl_pct'] = 0.0
                        result['duration_hours'] = (k_time - signal_dt).total_seconds() / 3600
                        break
                    
                    tp1_reached = True
                    result['tp1_reached'] = True
                    
                    # 移动止损到保本位
                    if self.use_breakeven_stop:
                        current_stop_loss = entry_price
                
                elif direction == 'short' and low <= take_profit_1:
                    if not entry_reached:
                        close_result = self.account.close_position(symbol, entry_price, 'invalid_signal')
                        result['status'] = 'invalid'
                        result['exit_reason'] = '入场价未到但先到止盈1'
                        result['exit_price'] = close_result.get('exit_price', entry_price)
                        result['exit_time'] = k_time.strftime('%Y-%m-%d %H:%M:%S')
                        result['pnl'] = close_result.get('net_pnl', 0)
                        result['pnl_pct'] = 0.0
                        result['duration_hours'] = (k_time - signal_dt).total_seconds() / 3600
                        break
                    
                    tp1_reached = True
                    result['tp1_reached'] = True
                    
                    if self.use_breakeven_stop:
                        current_stop_loss = entry_price
            
            # 检查止盈2
            if take_profit_2:
                if direction == 'long' and high >= take_profit_2:
                    close_result = self.account.close_position(symbol, take_profit_2, 'take_profit_2')
                    result['status'] = 'completed'
                    result['exit_reason'] = '触发止盈2'
                    result['exit_price'] = close_result.get('exit_price', take_profit_2)
                    result['exit_time'] = k_time.strftime('%Y-%m-%d %H:%M:%S')
                    result['pnl'] = close_result.get('net_pnl', 0)
                    result['pnl_pct'] = ((take_profit_2 - entry_price) / entry_price) * 100
                    result['tp2_reached'] = True
                    result['duration_hours'] = (k_time - signal_dt).total_seconds() / 3600
                    break
                
                elif direction == 'short' and low <= take_profit_2:
                    close_result = self.account.close_position(symbol, take_profit_2, 'take_profit_2')
                    result['status'] = 'completed'
                    result['exit_reason'] = '触发止盈2'
                    result['exit_price'] = close_result.get('exit_price', take_profit_2)
                    result['exit_time'] = k_time.strftime('%Y-%m-%d %H:%M:%S')
                    result['pnl'] = close_result.get('net_pnl', 0)
                    result['pnl_pct'] = ((entry_price - take_profit_2) / entry_price) * 100
                    result['tp2_reached'] = True
                    result['duration_hours'] = (k_time - signal_dt).total_seconds() / 3600
                    break
            
            # 检查止损
            if direction == 'long' and low <= current_stop_loss:
                close_result = self.account.close_position(symbol, current_stop_loss, 
                                                          'breakeven_stop' if current_stop_loss == entry_price else 'stop_loss')
                result['status'] = 'partial_tp' if current_stop_loss == entry_price else 'stopped'
                result['exit_reason'] = '保本止损' if current_stop_loss == entry_price else '触发止损'
                result['exit_price'] = close_result.get('exit_price', current_stop_loss)
                result['exit_time'] = k_time.strftime('%Y-%m-%d %H:%M:%S')
                result['pnl'] = close_result.get('net_pnl', 0)
                result['pnl_pct'] = ((current_stop_loss - entry_price) / entry_price) * 100
                result['stop_loss_hit'] = True
                result['breakeven_stop_hit'] = (current_stop_loss == entry_price)
                result['duration_hours'] = (k_time - signal_dt).total_seconds() / 3600
                break
            
            elif direction == 'short' and high >= current_stop_loss:
                close_result = self.account.close_position(symbol, current_stop_loss,
                                                          'breakeven_stop' if current_stop_loss == entry_price else 'stop_loss')
                result['status'] = 'partial_tp' if current_stop_loss == entry_price else 'stopped'
                result['exit_reason'] = '保本止损' if current_stop_loss == entry_price else '触发止损'
                result['exit_price'] = close_result.get('exit_price', current_stop_loss)
                result['exit_time'] = k_time.strftime('%Y-%m-%d %H:%M:%S')
                result['pnl'] = close_result.get('net_pnl', 0)
                result['pnl_pct'] = ((entry_price - current_stop_loss) / entry_price) * 100
                result['stop_loss_hit'] = True
                result['breakeven_stop_hit'] = (current_stop_loss == entry_price)
                result['duration_hours'] = (k_time - signal_dt).total_seconds() / 3600
                break
            
            # 如果超过48小时仍未触发，平仓
            if (k_time - signal_dt).total_seconds() > 48 * 3600:
                close_result = self.account.close_position(symbol, close, 'timeout')
                result['status'] = 'timeout'
                result['exit_reason'] = '超时（48小时）'
                result['exit_price'] = close_result.get('exit_price', close)
                result['exit_time'] = k_time.strftime('%Y-%m-%d %H:%M:%S')
                result['pnl'] = close_result.get('net_pnl', 0)
                result['pnl_pct'] = ((close - entry_price) / entry_price) * 100 if direction == 'long' else ((entry_price - close) / entry_price) * 100
                result['duration_hours'] = 48.0
                break
        
        # 记录交易事件
        if 'close_result' in locals():
            self.trade_events.append(TradeEvent(
                timestamp=kline['timestamp'],
                datetime=result.get('exit_time', k_time.strftime('%Y-%m-%d %H:%M:%S')),
                symbol=symbol,
                action='close',
                direction=direction,
                quantity=quantity,
                price=close_result.get('exit_price', result.get('exit_price', entry_price)),
                fee=close_result.get('fee', 0),
                slippage=close_result.get('slippage', 0),
                pnl=close_result.get('pnl', 0),
                net_pnl=close_result.get('net_pnl', 0),
                reason=result.get('exit_reason', 'unknown'),
                signal_id=signal_id
            ))
        
        # 添加信号信息
        result['pattern_name'] = signal.get('pattern_name', '')
        result['pattern_type'] = signal.get('pattern_type', '')
        result['source'] = signal.get('source', '')
        result['confidence'] = signal.get('confidence', 0.0)
        
        self.completed_signals.append(result)
        return result
    
    def calculate_metrics(self) -> BacktestMetrics:
        """计算回测指标"""
        if not self.completed_signals:
            return BacktestMetrics()
        
        # 基础统计
        total_trades = len(self.completed_signals)
        winning_trades = len([s for s in self.completed_signals if s.get('pnl', 0) > 0])
        losing_trades = len([s for s in self.completed_signals if s.get('pnl', 0) < 0])
        
        # 盈亏统计
        profits = [s.get('pnl', 0) for s in self.completed_signals if s.get('pnl', 0) > 0]
        losses = [abs(s.get('pnl', 0)) for s in self.completed_signals if s.get('pnl', 0) < 0]
        
        avg_win = statistics.mean(profits) if profits else 0.0
        avg_loss = statistics.mean(losses) if losses else 0.0
        
        # 总收益
        total_return = (self.account.equity - self.account.initial_balance) / self.account.initial_balance
        total_return_pct = total_return * 100
        
        # 最大回撤
        if self.equity_curve:
            max_equity = max([e.equity for e in self.equity_curve])
            min_equity_after_max = min([e.equity for e in self.equity_curve 
                                       if e.timestamp >= next((e.timestamp for e in self.equity_curve if e.equity == max_equity), 0)])
            max_drawdown_pct = ((max_equity - min_equity_after_max) / max_equity) * 100 if max_equity > 0 else 0.0
        else:
            max_drawdown_pct = 0.0
        
        # Sharpe比率
        if len(self.completed_signals) > 1:
            returns = [s.get('pnl_pct', 0) for s in self.completed_signals]
            if len(returns) > 1:
                mean_return = statistics.mean(returns)
                std_return = statistics.stdev(returns) if len(returns) > 1 else 0
                sharpe_ratio = mean_return / std_return if std_return > 0 else 0
            else:
                sharpe_ratio = 0.0
        else:
            sharpe_ratio = 0.0
        
        # 盈亏比
        total_profit = sum(profits) if profits else 0.0
        total_loss = sum(losses) if losses else 0.0
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # 胜率
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
        
        # 按币种统计
        symbol_stats = defaultdict(lambda: {'trades': 0, 'wins': 0, 'losses': 0, 'total_pnl': 0.0})
        for signal in self.completed_signals:
            symbol = signal.get('symbol', 'BTC')
            symbol_stats[symbol]['trades'] += 1
            if signal.get('pnl', 0) > 0:
                symbol_stats[symbol]['wins'] += 1
            else:
                symbol_stats[symbol]['losses'] += 1
            symbol_stats[symbol]['total_pnl'] += signal.get('pnl', 0)
        
        # 找出最佳和最差币种
        best_symbol = max(symbol_stats.items(), key=lambda x: x[1]['total_pnl'])[0] if symbol_stats else ''
        worst_symbol = min(symbol_stats.items(), key=lambda x: x[1]['total_pnl'])[0] if symbol_stats else ''
        
        return BacktestMetrics(
            total_return_pct=total_return_pct,
            max_drawdown_pct=max_drawdown_pct,
            sharpe_ratio=sharpe_ratio,
            profit_factor=profit_factor,
            win_rate=win_rate,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            avg_win=avg_win,
            avg_loss=avg_loss,
            total_fees=self.account.total_fees,
            total_slippage=self.account.total_slippage,
            best_symbol=best_symbol,
            worst_symbol=worst_symbol,
            symbol_stats=dict(symbol_stats)
        )
    
    def reset(self):
        """重置回测引擎"""
        self.account.reset()
        self.equity_curve = []
        self.trade_events = []
        self.active_signals = {}
        self.completed_signals = []
        self.max_equity = self.account.initial_balance
        self.min_equity = self.account.initial_balance
    
    def close(self):
        """关闭连接"""
        if self.price_conn:
            self.price_conn.close()
