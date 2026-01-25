#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
信号结果反馈系统

定期检查生成的信号状态：
1. 信号是否被激活（入场价格是否达到）
2. 如果被激活，后续是止损还是止盈
3. 支持0.5%快速止盈和保本止损逻辑
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import requests
from abu.market_cache import MarketDataCache  # type: ignore

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

try:
    from db_manager_trader import TraderDBManager
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print("[WARN] 数据库模块不可用，将使用JSON文件存储", file=sys.stderr)


class SignalResultFeedback:
    """信号结果反馈系统"""
    
    # 检查时间间隔配置
    CHECK_INTERVAL = timedelta(minutes=1)  # 所有信号每1分钟检查一次
    
    # 快速止盈阈值
    QUICK_TAKE_PROFIT_PCT = 0.005  # 0.5%
    
    # 信号有效期（超过这个时间未激活，标记为过期）
    SIGNAL_EXPIRY_5M = timedelta(hours=2)  # 5分钟信号2小时后过期
    SIGNAL_EXPIRY_15M = timedelta(hours=4)  # 15分钟信号4小时后过期
    MAX_1M_LOOKBACK = 10080  # 最多回看7天的1分钟K线
    
    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        trader_id: str = 'abu',
        use_database: bool = True,
        load_on_init: bool = True,
    ):
        """
        初始化信号结果反馈系统
        
        Args:
            storage_dir: 信号存储目录（用于JSON备份）
            trader_id: 交易员ID（用于数据库，默认'abu'）
            use_database: 是否使用数据库存储（默认True）
            load_on_init: 是否在初始化时加载活跃信号
        """
        self.use_database = use_database and DB_AVAILABLE
        
        if storage_dir is None:
            storage_dir = ROOT / 'outputs' / 'auto_signal_status' / 'signal_feedback'
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.signals_file = self.storage_dir / 'active_signals.json'
        self.feedback_history_file = self.storage_dir / 'feedback_history.json'
        
        # 初始化数据库管理器
        if self.use_database:
            try:
                self.db = TraderDBManager(trader_id=trader_id)
                print(f"[INFO] 使用数据库存储信号数据 (trader_id={trader_id})", file=sys.stderr)
            except Exception as e:
                print(f"[WARN] 数据库初始化失败，将使用JSON文件: {e}", file=sys.stderr)
                self.use_database = False
                self.db = None
        else:
            self.db = None
            print("[INFO] 使用JSON文件存储信号数据", file=sys.stderr)
        
        self.market_cache = MarketDataCache(default_exchange='gate')

        # 加载活跃信号（从数据库或JSON）
        self.active_signals = self._load_active_signals() if load_on_init else []

    def _parse_signal_time(self, value: object) -> Optional[datetime]:
        if isinstance(value, datetime):
            return value
        if not value:
            return None
        text = str(value).strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text)
        except Exception:
            pass
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                return datetime.strptime(text, fmt)
            except Exception:
                continue
        return None

    def _json_safe(self, value: object):
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, dict):
            return {k: self._json_safe(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._json_safe(v) for v in value]
        return value

    def _get_1m_history(self, symbol: str, start_time: datetime) -> List[Dict]:
        now = datetime.now()
        start_ts = int(start_time.timestamp())
        end_ts = int(now.timestamp())
        minutes = max(1, int((end_ts - start_ts) / 60) + 2)
        limit = min(self.MAX_1M_LOOKBACK, minutes)
        if limit <= 0:
            return []
        klines, _stats = self.market_cache.get_klines(symbol, "1m", limit, exchange="gate")
        if not klines:
            return []
        return [k for k in klines if k.get("timestamp", 0) >= start_ts]
    
    def _load_active_signals(self) -> List[Dict]:
        """加载活跃信号（从数据库或JSON）"""
        if self.use_database and self.db:
            try:
                # 从数据库加载活跃信号（pending, active, partial_tp状态）
                signals = []
                for status in ['pending', 'active', 'partial_tp']:
                    db_signals = self.db.get_trading_signals(status=status, system_name='abu', limit=1000)
                    for sig in db_signals:
                        # 转换为内部格式
                        signal_dict = {
                            'signal_id': f"{sig.get('symbol', 'Unknown')}_{sig.get('timeframe', '5m')}_{sig.get('signal_time', '').replace(':', '').replace(' ', '_')}",
                            'db_id': sig.get('id'),
                            'symbol': sig.get('symbol', 'Unknown').upper(),
                            'timeframe': sig.get('timeframe', '5m'),
                            'direction': sig.get('signal_type', 'long').lower(),
                            'entry_price': sig.get('entry_price', 0),
                            'stop_loss': sig.get('stop_loss', 0),
                            'take_profit_1': sig.get('take_profit_1', 0),
                            'take_profit_2': sig.get('take_profit_2', 0),
                            'generated_time': sig.get('signal_time', datetime.now().isoformat()),
                            'status': sig.get('status', 'pending'),
                            'entry_time': sig.get('entry_time'),
                            'exit_time': sig.get('exit_time'),
                            'exit_price': sig.get('exit_price'),
                            'exit_reason': sig.get('exit_reason'),
                            'pnl_pct': sig.get('pnl_pct', 0.0),
                            'breakeven_stop_set': sig.get('breakeven_stop_set', False),
                            'quick_tp_reached': sig.get('quick_tp_reached', False),
                            'last_check_time': sig.get('last_check_time'),
                            'check_count': sig.get('check_count', 0)
                        }
                        signals.append(signal_dict)
                return signals
            except Exception as e:
                print(f"[WARN] 从数据库加载信号失败: {e}", file=sys.stderr)
                return []
        
        # 从JSON文件加载（备用方案）
        if not self.signals_file.exists():
            return []
        
        try:
            with open(self.signals_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] 加载活跃信号失败: {e}", file=sys.stderr)
            return []
    
    def _save_active_signals(self):
        """保存活跃信号（数据库会自动保存，这里只保存JSON备份）"""
        # JSON文件作为备份
        try:
            with open(self.signals_file, 'w', encoding='utf-8') as f:
                json.dump(self._json_safe(self.active_signals), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARN] 保存活跃信号备份失败: {e}", file=sys.stderr)
    
    def add_signal(self, signal: Dict, generated_time: datetime):
        """
        添加新信号到追踪列表（数据库或JSON）
        
        Args:
            signal: 信号字典（包含symbol, timeframe, entry_price, stop_loss, take_profit_1, take_profit_2, direction等）
            generated_time: 信号生成时间
        """
        signal_id = f"{signal.get('symbol', 'Unknown')}_{signal.get('timeframe', '5m')}_{generated_time.strftime('%Y%m%d%H%M%S')}"
        
        # 检查是否已存在
        existing_ids = [s.get('signal_id') for s in self.active_signals]
        if signal_id in existing_ids:
            return  # 已存在，不重复添加
        
        # 计算盈亏比
        entry_price = signal.get('entry_price', 0)
        stop_loss = signal.get('stop_loss', 0)
        take_profit_1 = signal.get('take_profit_1', 0)
        direction = signal.get('direction', 'long').lower()
        
        risk_reward_ratio = None
        if entry_price > 0 and stop_loss > 0 and take_profit_1 > 0:
            if direction == 'long':
                risk = entry_price - stop_loss
                reward = take_profit_1 - entry_price
            else:
                risk = stop_loss - entry_price
                reward = entry_price - take_profit_1
            if risk > 0:
                risk_reward_ratio = reward / risk
        
        # 添加到数据库
        if self.use_database and self.db:
            try:
                db_id = self.db.add_trading_signal(
                    signal_time=generated_time.strftime('%Y-%m-%d %H:%M:%S'),
                    timeframe=signal.get('timeframe', '5m'),
                    symbol=signal.get('symbol', 'Unknown').upper(),
                    signal_type=direction,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit_1=take_profit_1,
                    take_profit_2=signal.get('take_profit_2', 0),
                    entry_model=signal.get('pattern_name', ''),
                    strength=signal.get('strength', 'medium'),
                    risk_reward_ratio=risk_reward_ratio,
                    system_name='abu',
                    score=signal.get('score'),
                    notes=signal.get('notes')
                )
                
                # 添加到内存列表
                signal_record = {
                    'signal_id': signal_id,
                    'db_id': db_id,
                    'symbol': signal.get('symbol', 'Unknown').upper(),
                    'timeframe': signal.get('timeframe', '5m'),
                    'direction': direction,
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit_1': take_profit_1,
                    'take_profit_2': signal.get('take_profit_2', 0),
                    'generated_time': generated_time.isoformat(),
                    'status': 'pending',
                    'entry_time': None,
                    'exit_time': None,
                    'exit_price': None,
                    'exit_reason': None,
                    'pnl_pct': 0.0,
                    'breakeven_stop_set': False,
                    'quick_tp_reached': False,
                    'last_check_time': None,
                    'check_count': 0
                }
                self.active_signals.append(signal_record)
                print(f"[INFO] 已添加信号到数据库: {signal_id} (db_id={db_id})", file=sys.stderr)
                return
            except Exception as e:
                print(f"[WARN] 添加到数据库失败: {e}，使用JSON文件", file=sys.stderr)
                self.use_database = False
        
        # 添加到JSON文件（备用方案）
        signal_record = {
            'signal_id': signal_id,
            'symbol': signal.get('symbol', 'Unknown').upper(),
            'timeframe': signal.get('timeframe', '5m'),
            'direction': direction,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit_1': take_profit_1,
            'take_profit_2': signal.get('take_profit_2', 0),
            'generated_time': generated_time.isoformat(),
            'status': 'pending',
            'entry_time': None,
            'exit_time': None,
            'exit_price': None,
            'exit_reason': None,
            'pnl_pct': 0.0,
            'breakeven_stop_set': False,
            'quick_tp_reached': False,
            'last_check_time': None,
            'check_count': 0
        }
        self.active_signals.append(signal_record)
        self._save_active_signals()
        print(f"[INFO] 已添加信号到追踪: {signal_id}", file=sys.stderr)
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        获取当前价格
        
        Args:
            symbol: 币种符号（如BTC, ETH）
        
        Returns:
            当前价格，失败返回None
        """
        try:
            currency_pair = f"{symbol}_USDT"
            url = "https://api.gateio.ws/api/v4/spot/tickers"
            params = {'currency_pair': currency_pair}
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return float(data[0].get('last', 0))
        except Exception as e:
            print(f"[WARN] 获取{symbol}价格失败: {e}", file=sys.stderr)
        
        return None
    
    def check_signal_status(self, signal: Dict) -> Tuple[str, Optional[Dict]]:
        """
        检查单个信号状态
        
        Args:
            signal: 信号记录
        
        Returns:
            (状态, 更新信息字典)
        """
        symbol = signal['symbol']
        timeframe = signal['timeframe']
        direction = signal['direction']
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        take_profit_1 = signal['take_profit_1']
        take_profit_2 = signal['take_profit_2']
        status = signal['status']
        generated_time = self._parse_signal_time(signal.get('generated_time'))
        if not generated_time:
            return status, None

        klines = self._get_1m_history(symbol, generated_time)
        current_price = klines[-1]['close'] if klines else self.get_current_price(symbol)
        if not current_price or current_price <= 0:
            return status, None
        
        # 检查信号是否过期
        if timeframe == '5m':
            expiry_time = generated_time + self.SIGNAL_EXPIRY_5M
        else:
            expiry_time = generated_time + self.SIGNAL_EXPIRY_15M
        
        if datetime.now() > expiry_time and status == 'pending':
            return 'expired', {
                'exit_time': datetime.now().isoformat(),
                'exit_price': current_price,
                'exit_reason': '信号过期未激活'
            }
        
        # 如果已经结束，不再检查
        if status in ['stopped', 'full_tp', 'expired', 'quick_tp']:
            return status, None
        
        update_info = {
            'last_check_time': datetime.now().isoformat(),
            'check_count': signal.get('check_count', 0) + 1
        }

        entry_index = None
        entry_time = self._parse_signal_time(signal.get('entry_time')) if signal.get('entry_time') else None
        if klines:
            if entry_time:
                entry_ts = int(entry_time.timestamp())
                for i, k in enumerate(klines):
                    if k.get('timestamp', 0) >= entry_ts:
                        entry_index = i
                        break
            if entry_index is None and entry_price > 0:
                for i, k in enumerate(klines):
                    if k.get('low', 0) <= entry_price <= k.get('high', 0):
                        entry_index = i
                        break

        # 检查是否激活（入场）
        if status == 'pending':
            if entry_index is None:
                if datetime.now() > expiry_time:
                    return 'expired', {
                        'exit_time': datetime.now().isoformat(),
                        'exit_price': current_price,
                        'exit_reason': '信号过期未激活'
                    }
                return status, update_info
            entry_k = klines[entry_index]
            update_info['status'] = 'active'
            update_info['entry_time'] = datetime.fromtimestamp(entry_k['timestamp']).isoformat()
            update_info['entry_price_actual'] = entry_price
            status = 'active'

        if status in ['active', 'partial_tp']:
            start_idx = entry_index if entry_index is not None else 0
            effective_stop_loss = entry_price if signal.get('breakeven_stop_set', False) else stop_loss
            quick_tp_threshold = None
            if entry_price > 0:
                if direction == 'long':
                    quick_tp_threshold = entry_price * (1 + self.QUICK_TAKE_PROFIT_PCT)
                else:
                    quick_tp_threshold = entry_price * (1 - self.QUICK_TAKE_PROFIT_PCT)

            for k in klines[start_idx:]:
                high = k.get('high', 0)
                low = k.get('low', 0)
                ts = k.get('timestamp', 0)

                if direction == 'long':
                    if effective_stop_loss > 0 and low <= effective_stop_loss:
                        update_info['status'] = 'stopped'
                        update_info['exit_time'] = datetime.fromtimestamp(ts).isoformat()
                        update_info['exit_price'] = effective_stop_loss
                        update_info['exit_reason'] = '保本止损' if signal.get('breakeven_stop_set', False) else '初始止损'
                        return 'stopped', update_info
                    if quick_tp_threshold and not signal.get('quick_tp_reached', False) and high >= quick_tp_threshold:
                        update_info['quick_tp_reached'] = True
                        update_info['breakeven_stop_set'] = True
                        update_info['status'] = 'quick_tp'
                        update_info['exit_time'] = datetime.fromtimestamp(ts).isoformat()
                        update_info['exit_price'] = quick_tp_threshold
                        update_info['exit_reason'] = '快速止盈'
                        return 'quick_tp', update_info
                    if take_profit_2 > 0 and high >= take_profit_2:
                        update_info['status'] = 'full_tp'
                        update_info['exit_time'] = datetime.fromtimestamp(ts).isoformat()
                        update_info['exit_price'] = take_profit_2
                        update_info['exit_reason'] = '全部止盈（TP2）'
                        return 'full_tp', update_info
                    if take_profit_1 > 0 and high >= take_profit_1 and status != 'partial_tp':
                        update_info['status'] = 'partial_tp'
                        update_info['breakeven_stop_set'] = True
                        update_info['exit_reason'] = '部分止盈（TP1），已设置保本止损'
                        return 'partial_tp', update_info
                else:
                    if effective_stop_loss > 0 and high >= effective_stop_loss:
                        update_info['status'] = 'stopped'
                        update_info['exit_time'] = datetime.fromtimestamp(ts).isoformat()
                        update_info['exit_price'] = effective_stop_loss
                        update_info['exit_reason'] = '保本止损' if signal.get('breakeven_stop_set', False) else '初始止损'
                        return 'stopped', update_info
                    if quick_tp_threshold and not signal.get('quick_tp_reached', False) and low <= quick_tp_threshold:
                        update_info['quick_tp_reached'] = True
                        update_info['breakeven_stop_set'] = True
                        update_info['status'] = 'quick_tp'
                        update_info['exit_time'] = datetime.fromtimestamp(ts).isoformat()
                        update_info['exit_price'] = quick_tp_threshold
                        update_info['exit_reason'] = '快速止盈'
                        return 'quick_tp', update_info
                    if take_profit_2 > 0 and low <= take_profit_2:
                        update_info['status'] = 'full_tp'
                        update_info['exit_time'] = datetime.fromtimestamp(ts).isoformat()
                        update_info['exit_price'] = take_profit_2
                        update_info['exit_reason'] = '全部止盈（TP2）'
                        return 'full_tp', update_info
                    if take_profit_1 > 0 and low <= take_profit_1 and status != 'partial_tp':
                        update_info['status'] = 'partial_tp'
                        update_info['breakeven_stop_set'] = True
                        update_info['exit_reason'] = '部分止盈（TP1），已设置保本止损'
                        return 'partial_tp', update_info

            if direction == 'long' and entry_price > 0:
                update_info['pnl_pct'] = ((current_price - entry_price) / entry_price) * 100
            elif direction == 'short' and entry_price > 0:
                update_info['pnl_pct'] = ((entry_price - current_price) / entry_price) * 100
        
        return status, update_info
    
    def check_all_signals(self) -> Dict:
        """
        检查所有活跃信号（每1分钟调用一次）
        
        Returns:
            检查结果统计
        """
        stats = {
            'total': len(self.active_signals),
            'pending': 0,
            'active': 0,
            'stopped': 0,
            'quick_tp': 0,
            'partial_tp': 0,
            'full_tp': 0,
            'expired': 0,
            'updated': 0
        }
        
        updated_signals = []
        now = datetime.now()
        
        for signal in self.active_signals:
            # 只检查pending和active状态的信号（每1分钟检查一次）
            status = signal.get('status', 'pending')
            if status not in ['pending', 'active', 'partial_tp']:
                # 已结束的信号，更新统计但不再检查
                stats[status] = stats.get(status, 0) + 1
                continue
            
            # 检查是否需要检查（避免过于频繁）
            last_check = signal.get('last_check_time')
            if last_check:
                try:
                    last_check_time = datetime.fromisoformat(last_check)
                    # 如果距离上次检查不到50秒，跳过（避免API调用过于频繁）
                    if (now - last_check_time).total_seconds() < 50:
                        stats[status] = stats.get(status, 0) + 1
                        continue
                except Exception:
                    pass
            
            old_status = status
            new_status, update_info = self.check_signal_status(signal)
            
            if update_info:
                signal.update(update_info)
                if 'status' in update_info:
                    signal['status'] = update_info['status']
                updated_signals.append(signal)
                stats['updated'] += 1
                
                # 更新数据库
                if self.use_database and self.db and signal.get('db_id'):
                    try:
                        # 映射状态到数据库状态
                        db_status_map = {
                            'pending': 'pending',
                            'active': 'active',
                            'stopped': 'stopped',
                            'quick_tp': 'completed',  # 快速止盈视为完成
                            'partial_tp': 'active',  # 部分止盈仍为活跃
                            'full_tp': 'completed',
                            'expired': 'missed'
                        }
                        db_status = db_status_map.get(new_status, new_status)
                        
                        self.db.update_signal_status(
                            signal_id=signal['db_id'],
                            status=db_status,
                            entry_time=update_info.get('entry_time'),
                            exit_time=update_info.get('exit_time'),
                            exit_price=update_info.get('exit_price'),
                            exit_reason=update_info.get('exit_reason'),
                            pnl_pct=update_info.get('pnl_pct'),
                            breakeven_stop_set=update_info.get('breakeven_stop_set', signal.get('breakeven_stop_set', False)),
                            quick_tp_reached=update_info.get('quick_tp_reached', signal.get('quick_tp_reached', False)),
                            last_check_time=update_info.get('last_check_time'),
                            check_count=update_info.get('check_count', signal.get('check_count', 0)),
                            entry_price_actual=update_info.get('entry_price_actual')
                        )
                    except Exception as e:
                        print(f"[WARN] 更新数据库失败 (signal_id={signal.get('db_id')}): {e}", file=sys.stderr)
            
            # 更新统计
            stats[new_status] = stats.get(new_status, 0) + 1
        
        # 保存更新后的信号（JSON备份）
        if updated_signals:
            self._save_active_signals()
            self._save_feedback_history(updated_signals)
        
        return stats
    
    def _save_feedback_history(self, updated_signals: List[Dict]):
        """保存反馈历史（同时保存到数据库和JSON）"""
        now = datetime.now()
        
        # 保存到数据库（signal_evaluations表）
        if self.use_database and self.db:
            for signal in updated_signals:
                if signal.get('db_id') and signal.get('status') in ['stopped', 'quick_tp', 'full_tp', 'expired']:
                    try:
                        # 确定评估结果
                        result_map = {
                            'stopped': 'stopped',
                            'quick_tp': 'completed',
                            'full_tp': 'completed',
                            'expired': 'missed'
                        }
                        result = result_map.get(signal['status'], signal['status'])
                        
                        # 确定是否触发止损/止盈
                        stop_loss_hit = 1 if signal['status'] == 'stopped' else 0
                        take_profit_1_hit = 1 if signal.get('breakeven_stop_set', False) or signal['status'] in ['partial_tp', 'quick_tp'] else 0
                        take_profit_2_hit = 1 if signal['status'] == 'full_tp' else 0
                        missed = 1 if signal['status'] == 'expired' else 0
                        
                        self.db.add_signal_evaluation(
                            {
                                "signal_id": signal['db_id'],
                                "evaluation_time": now.strftime('%Y-%m-%d %H:%M:%S'),
                                "result": result,
                                "actual_entry_price": signal.get('entry_price_actual') or signal.get('entry_price'),
                                "actual_exit_price": signal.get('exit_price'),
                                "actual_profit_pct": signal.get('pnl_pct'),
                                "stop_loss_hit": stop_loss_hit,
                                "take_profit_1_hit": take_profit_1_hit,
                                "take_profit_2_hit": take_profit_2_hit,
                                "missed": missed,
                                "notes": signal.get('exit_reason'),
                            }
                        )
                    except Exception as e:
                        print(f"[WARN] 保存评估到数据库失败: {e}", file=sys.stderr)
        
        # 保存到JSON文件（备份）
        if not self.feedback_history_file.exists():
            history = []
        else:
            try:
                with open(self.feedback_history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except Exception:
                history = []
        
        # 添加新的反馈记录
        for signal in updated_signals:
            history.append({
                'signal_id': signal['signal_id'],
                'symbol': signal['symbol'],
                'timeframe': signal['timeframe'],
                'update_time': now.isoformat(),
                'old_status': signal.get('old_status', 'unknown'),
                'new_status': signal['status'],
                'entry_price': signal['entry_price'],
                'exit_price': signal.get('exit_price'),
                'pnl_pct': signal.get('pnl_pct', 0),
                'exit_reason': signal.get('exit_reason')
            })
        
        # 只保留最近1000条记录
        history = history[-1000:]
        
        try:
            with open(self.feedback_history_file, 'w', encoding='utf-8') as f:
                json.dump(self._json_safe(history), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARN] 保存反馈历史失败: {e}", file=sys.stderr)
    
    def get_feedback_report(self) -> List[str]:
        """
        生成反馈报告
        
        Returns:
            报告行列表
        """
        lines = []
        lines.append("# 信号结果反馈报告")
        lines.append("")
        lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # 统计信息
        stats = {
            'pending': [],
            'active': [],
            'stopped': [],
            'quick_tp': [],
            'partial_tp': [],
            'full_tp': [],
            'expired': []
        }
        
        for signal in self.active_signals:
            status = signal['status']
            if status in stats:
                stats[status].append(signal)
        
        lines.append("## 状态统计")
        lines.append("")
        lines.append(f"- **总信号数**: {len(self.active_signals)}")
        lines.append(f"- **待激活**: {len(stats['pending'])}")
        lines.append(f"- **交易中**: {len(stats['active'])}")
        lines.append(f"- **快速止盈**: {len(stats['quick_tp'])}")
        lines.append(f"- **部分止盈**: {len(stats['partial_tp'])}")
        lines.append(f"- **全部止盈**: {len(stats['full_tp'])}")
        lines.append(f"- **已止损**: {len(stats['stopped'])}")
        lines.append(f"- **已过期**: {len(stats['expired'])}")
        lines.append("")
        
        # 详细列表
        for status_name, status_signals in stats.items():
            if not status_signals:
                continue
            
            status_labels = {
                'pending': '待激活',
                'active': '交易中',
                'quick_tp': '快速止盈（0.5%）',
                'partial_tp': '部分止盈',
                'full_tp': '全部止盈',
                'stopped': '已止损',
                'expired': '已过期'
            }
            
            lines.append(f"## {status_labels.get(status_name, status_name)} ({len(status_signals)}个)")
            lines.append("")
            
            for signal in status_signals[:20]:  # 最多显示20个
                symbol = signal['symbol']
                timeframe = signal['timeframe']
                direction = signal['direction'].upper()
                entry = signal['entry_price']
                exit_price = signal.get('exit_price', signal.get('current_price', 0))
                pnl_pct = signal.get('pnl_pct', 0)
                
                lines.append(f"### {signal['signal_id']}")
                lines.append(f"- **币种**: {symbol}")
                lines.append(f"- **时间框架**: {timeframe}")
                lines.append(f"- **方向**: {direction}")
                lines.append(f"- **入场价**: ${entry:,.2f}")
                if exit_price > 0:
                    lines.append(f"- **退出价**: ${exit_price:,.2f}")
                if pnl_pct != 0:
                    lines.append(f"- **盈亏**: {pnl_pct:+.2f}%")
                if signal.get('exit_reason'):
                    lines.append(f"- **退出原因**: {signal['exit_reason']}")
                lines.append("")
        
        return lines


if __name__ == '__main__':
    # 测试代码
    feedback = SignalResultFeedback()
    stats = feedback.check_all_signals()
    print(f"检查完成: {stats}")
    
    report = feedback.get_feedback_report()
    print('\n'.join(report))
