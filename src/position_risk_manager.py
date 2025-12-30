# -*- coding: utf-8 -*-
"""
仓位和风险管理模块
整合De.的仓位管理、杠杆管理和扫损检测知识
"""

import sys
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from pathlib import Path

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

try:
    from get_realtime_stop_loss import (
        get_order_book_with_retry,
        get_current_price,
        analyze_liquidity_zones,
        calculate_stop_loss_by_orderbook
    )
    ORDERBOOK_AVAILABLE = True
except ImportError:
    ORDERBOOK_AVAILABLE = False

try:
    import requests
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False


class PositionRiskManager:
    """仓位和风险管理器"""
    
    def __init__(self):
        # De.的实际仓位风格（基于最新对话）
        self.de_position_style = {
            'leverage': 15,  # De.使用15x杠杆（名义杠杆）
            'effective_leverage': 12.5,  # 实际有效杠杆可能是12.5x（"你算12.5"）
            'position_size_pct': 5,  # 5%仓位逐仓（使用账户的5%作为保证金）
            'margin_mode': 'isolated',  # 逐仓模式（必须）
            'risk_attitude': 'high_risk_high_reward',  # 高风险高收益
            'max_leverage_warning': 125,  # 125x会睡不着（心理压力）
            'not_all_in': True,  # 不是梭哈（"梭哈那不是找死嘛"）
            'reason': '5%仓位逐仓，15x杠杆（实际可能12.5x），不是梭哈，高风险高收益'
        }
        
        self.leverage_rules = {
            'short_term': {
                'max_leverage': 0.5,  # 一半杠杆
                'use_limit_order': False,  # 不要挂单
                'reason': '短线震荡容易被扫，一半杠杆会玩脱靶'
            },
            'medium_long_term': {
                'max_leverage': None,  # 低杠杆，无所谓
                'use_limit_order': True,  # 可以挂单
                'reason': '低杠杆中长线无所谓，到点就进，不用看短时间的盈亏'
            },
            'de_style': {
                'leverage': 15,  # De.使用15x杠杆
                'position_size_pct': 5,  # 5%仓位逐仓
                'margin_mode': 'isolated',  # 必须逐仓
                'use_limit_order': False,  # 手动操作
                'reason': '5%仓位逐仓，15x杠杆，高风险高收益'
            }
        }
    
    def check_stop_loss_sweep(self, 
                              symbol: str = 'BTC',
                              stop_loss_price: float = None,
                              timeframe: str = '5m',
                              lookback_periods: int = 10) -> Dict:
        """
        检查5分钟K线是否扫止损
        
        Args:
            symbol: 交易对
            stop_loss_price: 止损价格
            timeframe: 时间框架（默认5m）
            lookback_periods: 回看周期数
        
        Returns:
            扫损检测结果
        """
        if not stop_loss_price:
            return {
                'swept': False,
                'reason': '未提供止损价格'
            }
        
        # 获取5分钟K线数据
        klines = self._get_klines(symbol, timeframe, lookback_periods)
        if not klines:
            return {
                'swept': False,
                'reason': '无法获取K线数据'
            }
        
        # 检查是否扫止损
        swept = False
        sweep_time = None
        sweep_candle = None
        
        for candle in klines:
            low = candle.get('low', 0)
            high = candle.get('high', 0)
            
            # 做多：检查最低价是否低于止损价
            if low <= stop_loss_price <= high:
                swept = True
                sweep_time = candle.get('datetime')
                sweep_candle = candle
                break
        
        result = {
            'swept': swept,
            'stop_loss_price': stop_loss_price,
            'timeframe': timeframe,
            'sweep_time': sweep_time,
            'sweep_candle': sweep_candle
        }
        
        if swept:
            result['reason'] = f'5分钟K线在{sweep_time}扫到止损${stop_loss_price:,.0f}'
        else:
            result['reason'] = f'5分钟K线未扫到止损${stop_loss_price:,.0f}'
        
        return result
    
    def _get_klines(self, symbol: str, timeframe: str, limit: int) -> List[Dict]:
        """获取K线数据"""
        if not API_AVAILABLE:
            return []
        
        try:
            # 尝试Gate.io API
            symbol_map = {'BTC': 'BTC_USDT', 'ETH': 'ETH_USDT'}
            trading_pair = symbol_map.get(symbol.upper(), 'BTC_USDT')
            
            url = "https://api.gateio.ws/api/v4/spot/candlesticks"
            params = {
                'currency_pair': trading_pair,
                'interval': timeframe,
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                klines = []
                for item in data:
                    klines.append({
                        'datetime': datetime.fromtimestamp(int(item[0])).strftime('%Y-%m-%d %H:%M:%S'),
                        'open': float(item[5]),
                        'high': float(item[2]),
                        'low': float(item[3]),
                        'close': float(item[4]),
                        'volume': float(item[6])
                    })
                return klines
        except Exception as e:
            print(f"获取K线数据失败: {e}", file=sys.stderr)
        
        return []
    
    def get_de_position_style(self) -> Dict:
        """
        获取De.的实际仓位风格
        
        Returns:
            De.的仓位风格信息
        """
        leverage = self.de_position_style['leverage']
        effective_leverage = self.de_position_style.get('effective_leverage', leverage)
        position_pct = self.de_position_style['position_size_pct']
        actual_exposure_pct = position_pct * effective_leverage / 100
        
        return {
            'leverage': leverage,
            'effective_leverage': effective_leverage,
            'position_size_pct': position_pct,
            'actual_exposure_pct': actual_exposure_pct,  # 实际风险暴露百分比
            'margin_mode': self.de_position_style['margin_mode'],
            'risk_attitude': self.de_position_style['risk_attitude'],
            'max_leverage_warning': self.de_position_style['max_leverage_warning'],
            'not_all_in': self.de_position_style.get('not_all_in', True),
            'reason': self.de_position_style['reason'],
            'key_points': [
                f"仓位: {position_pct}%逐仓（使用账户的{position_pct}%作为保证金）",
                f"杠杆: {leverage}x（名义）或 {effective_leverage}x（实际有效）",
                f"实际风险暴露: {actual_exposure_pct * 100:.1f}%账户价值",
                "必须使用逐仓模式（isolated margin）",
                "不是梭哈（有仓位控制）",
                "高风险高收益策略",
                f"{self.de_position_style['max_leverage_warning']}x会睡不着（心理压力）"
            ]
        }
    
    def calculate_position_risk(self,
                                leverage: float,
                                position_size_pct: float,
                                entry_price: float,
                                stop_loss_price: float,
                                account_balance: float = 10000) -> Dict:
        """
        计算仓位风险
        
        Args:
            leverage: 杠杆倍数
            position_size_pct: 仓位百分比（如5%）
            entry_price: 入场价
            stop_loss_price: 止损价
            account_balance: 账户余额
        
        Returns:
            风险分析结果
        """
        # 计算仓位大小
        position_value = account_balance * (position_size_pct / 100) * leverage
        
        # 计算止损距离
        stop_loss_distance = abs(entry_price - stop_loss_price)
        stop_loss_distance_pct = (stop_loss_distance / entry_price) * 100
        
        # 计算潜在亏损
        potential_loss = position_value * (stop_loss_distance_pct / 100)
        potential_loss_pct = (potential_loss / account_balance) * 100
        
        # 计算爆仓价格（做多）
        liquidation_price = entry_price * (1 - (1 / leverage))
        liquidation_distance_pct = ((entry_price - liquidation_price) / entry_price) * 100
        
        # 风险等级评估
        risk_level = 'low'
        if potential_loss_pct > 10:
            risk_level = 'critical'
        elif potential_loss_pct > 5:
            risk_level = 'high'
        elif potential_loss_pct > 2:
            risk_level = 'medium'
        
        # 与De.风格对比
        de_comparison = {
            'leverage_match': leverage == self.de_position_style['leverage'],
            'position_size_match': position_size_pct == self.de_position_style['position_size_pct'],
            'risk_level': risk_level,
            'warning': []
        }
        
        if leverage > self.de_position_style['max_leverage_warning']:
            de_comparison['warning'].append(f"⚠️ 杠杆{leverage}x过高，{self.de_position_style['max_leverage_warning']}x会睡不着")
        
        if potential_loss_pct > 5:
            de_comparison['warning'].append(f"⚠️ 潜在亏损{potential_loss_pct:.2f}%超过De.的5%仓位")
        
        return {
            'leverage': leverage,
            'position_size_pct': position_size_pct,
            'position_value': position_value,
            'entry_price': entry_price,
            'stop_loss_price': stop_loss_price,
            'stop_loss_distance': stop_loss_distance,
            'stop_loss_distance_pct': stop_loss_distance_pct,
            'potential_loss': potential_loss,
            'potential_loss_pct': potential_loss_pct,
            'liquidation_price': liquidation_price,
            'liquidation_distance_pct': liquidation_distance_pct,
            'risk_level': risk_level,
            'de_comparison': de_comparison
        }
    
    def get_leverage_recommendation(self,
                                   trading_style: str = 'short_term',
                                   market_condition: str = 'normal') -> Dict:
        """
        获取杠杆建议
        
        Args:
            trading_style: 交易风格（short_term/medium_long_term）
            market_condition: 市场状况（normal/volatile/trending）
        
        Returns:
            杠杆建议
        """
        rule = self.leverage_rules.get(trading_style, self.leverage_rules['short_term'])
        
        recommendation = {
            'trading_style': trading_style,
            'max_leverage': rule['max_leverage'],
            'use_limit_order': rule['use_limit_order'],
            'reason': rule['reason'],
            'market_condition': market_condition
        }
        
        # 根据市场状况调整
        if market_condition == 'volatile':
            if trading_style == 'short_term':
                recommendation['warning'] = '震荡市场，一半杠杆会玩脱靶，建议降低杠杆或等待突破'
                recommendation['suggestion'] = '等待突破后再入场，不要挂单'
        
        return recommendation
    
    def get_order_strategy(self,
                          trading_style: str = 'short_term',
                          entry_price: float = None,
                          current_price: float = None) -> Dict:
        """
        获取挂单策略建议
        
        Args:
            trading_style: 交易风格
            entry_price: 入场价
            current_price: 当前价格
        
        Returns:
            挂单策略建议
        """
        rule = self.leverage_rules.get(trading_style, self.leverage_rules['short_term'])
        
        strategy = {
            'trading_style': trading_style,
            'use_limit_order': rule['use_limit_order'],
            'reason': rule['reason']
        }
        
        if trading_style == 'short_term':
            strategy['recommendation'] = '短线不要挂单，手动操作'
            strategy['explanation'] = '短线震荡容易被扫，需要实时监控，手动操作更灵活'
            strategy['action'] = '等待突破确认后再手动入场'
        else:
            strategy['recommendation'] = '低杠杆中长线可以挂单'
            strategy['explanation'] = '低杠杆中长线无所谓，到点就进，不用看短时间的盈亏'
            strategy['action'] = '可以设置挂单，到点自动入场'
        
        # 如果有入场价，提供具体建议
        if entry_price and current_price:
            if trading_style == 'short_term':
                if abs(entry_price - current_price) / current_price < 0.01:  # 1%以内
                    strategy['suggestion'] = '价格接近，建议等待突破确认'
                else:
                    strategy['suggestion'] = f'等待价格突破${entry_price:,.0f}后再手动入场'
            else:
                strategy['suggestion'] = f'可以设置挂单在${entry_price:,.0f}'
        
        return strategy
    
    def analyze_breakout_opportunity(self,
                                   symbol: str = 'BTC',
                                   key_level: float = None,
                                   current_price: float = None) -> Dict:
        """
        分析突破机会
        
        Args:
            symbol: 交易对
            key_level: 关键价位（如89000）
            current_price: 当前价格
        
        Returns:
            突破分析结果
        """
        if not key_level or not current_price:
            return {
                'breakout': False,
                'reason': '未提供关键价位或当前价格'
            }
        
        distance_pct = abs(key_level - current_price) / current_price * 100
        
        result = {
            'key_level': key_level,
            'current_price': current_price,
            'distance_pct': distance_pct,
            'breakout': False
        }
        
        # 判断是否突破
        if current_price >= key_level:
            result['breakout'] = True
            result['direction'] = 'up'
            result['reason'] = f'已突破关键价位${key_level:,.0f}'
            result['suggestion'] = '突破确认，可以考虑入场'
        else:
            result['breakout'] = False
            result['direction'] = 'waiting'
            result['reason'] = f'未突破关键价位${key_level:,.0f}，当前价格${current_price:,.0f}'
            result['suggestion'] = '等待突破后再入场，不要挂单'
        
        return result
    
    def get_comprehensive_risk_analysis(self,
                                      symbol: str = 'BTC',
                                      entry_price: float = None,
                                      stop_loss_price: float = None,
                                      trading_style: str = 'short_term',
                                      leverage: float = None,
                                      position_size_pct: float = None,
                                      account_balance: float = 10000) -> Dict:
        """
        综合风险分析
        
        Args:
            symbol: 交易对
            entry_price: 入场价
            stop_loss_price: 止损价
            trading_style: 交易风格
            leverage: 杠杆倍数
        
        Returns:
            综合风险分析结果
        """
        # 如果未指定杠杆和仓位，使用De.的风格
        if leverage is None:
            leverage = self.de_position_style['leverage']
        if position_size_pct is None:
            position_size_pct = self.de_position_style['position_size_pct']
        
        analysis = {
            'symbol': symbol,
            'entry_price': entry_price,
            'stop_loss_price': stop_loss_price,
            'trading_style': trading_style,
            'leverage': leverage,
            'position_size_pct': position_size_pct,
            'margin_mode': 'isolated',  # 必须逐仓
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # De.的仓位风格信息
        analysis['de_position_style'] = self.get_de_position_style()
        
        # 计算仓位风险（如果有入场价和止损价）
        if entry_price and stop_loss_price:
            position_risk = self.calculate_position_risk(
                leverage=leverage,
                position_size_pct=position_size_pct,
                entry_price=entry_price,
                stop_loss_price=stop_loss_price,
                account_balance=account_balance
            )
            analysis['position_risk'] = position_risk
        
        # 1. 杠杆建议
        if trading_style == 'short_term':
            leverage_rec = self.get_leverage_recommendation('short_term', 'volatile')
            analysis['leverage_recommendation'] = leverage_rec
            if leverage and leverage > 0.5:
                analysis['leverage_warning'] = '一半杠杆会玩脱靶，建议降低杠杆'
        else:
            leverage_rec = self.get_leverage_recommendation('medium_long_term', 'normal')
            analysis['leverage_recommendation'] = leverage_rec
        
        # 2. 挂单策略
        current_price = get_current_price(symbol) if ORDERBOOK_AVAILABLE else None
        order_strategy = self.get_order_strategy(trading_style, entry_price, current_price)
        analysis['order_strategy'] = order_strategy
        
        # 3. 扫损检测
        if stop_loss_price:
            sweep_check = self.check_stop_loss_sweep(symbol, stop_loss_price, '5m', 10)
            analysis['stop_loss_sweep_check'] = sweep_check
            
            if sweep_check['swept']:
                analysis['sweep_warning'] = '⚠️ 5分钟K线已扫到止损，注意风险'
        
        # 4. 止损建议（基于订单簿）
        if ORDERBOOK_AVAILABLE and entry_price and stop_loss_price:
            order_book, exchange_name = get_order_book_with_retry(symbol, limit=50)
            if order_book and current_price:
                liquidity_analysis = analyze_liquidity_zones(order_book, current_price)
                if liquidity_analysis:
                    # 检查止损是否在流动性稀疏区
                    analysis['liquidity_analysis'] = {
                        'available': True,
                        'exchange': exchange_name,
                        'current_price': current_price
                    }
                    
                    # 检查止损是否合理
                    recommended_sl, sl_info = calculate_stop_loss_by_orderbook(
                        entry_price, 'long', order_book, current_price
                    )
                    
                    if recommended_sl:
                        analysis['recommended_stop_loss'] = {
                            'price': recommended_sl,
                            'info': sl_info,
                            'current_stop_loss': stop_loss_price,
                            'difference': abs(recommended_sl - stop_loss_price),
                            'difference_pct': abs(recommended_sl - stop_loss_price) / entry_price * 100
                        }
        
        # 5. De.风格建议
        de_recommendations = []
        de_recommendations.append(f"✅ 使用{leverage}x杠杆，{position_size_pct}%仓位逐仓")
        de_recommendations.append("✅ 必须使用逐仓模式（isolated margin），风险隔离")
        
        if leverage >= self.de_position_style['max_leverage_warning']:
            de_recommendations.append(f"⚠️ 杠杆{leverage}x过高，{self.de_position_style['max_leverage_warning']}x会睡不着")
        
        if position_size_pct > self.de_position_style['position_size_pct']:
            de_recommendations.append(f"⚠️ 仓位{position_size_pct}%超过De.的{self.de_position_style['position_size_pct']}%")
        
        # 6. 综合建议
        recommendations = []
        
        if trading_style == 'short_term':
            recommendations.append('✅ 短线不要挂单，等待突破确认后手动操作')
            recommendations.append('⚠️ 一半杠杆会玩脱靶，建议降低杠杆或等待突破')
            recommendations.append('📊 关注5分钟K线是否扫止损')
        elif trading_style == 'de_style':
            recommendations.extend(de_recommendations)
            recommendations.append('📊 高风险高收益策略，注意风险控制')
        else:
            recommendations.append('✅ 低杠杆中长线可以挂单，到点就进')
            recommendations.append('📊 不用看短时间的盈亏，关注长期趋势')
        
        if stop_loss_price and analysis.get('stop_loss_sweep_check', {}).get('swept'):
            recommendations.append('🚨 5分钟K线已扫到止损，注意风险控制')
        
        # 如果有仓位风险分析，添加风险警告
        if analysis.get('position_risk'):
            risk_info = analysis['position_risk']
            if risk_info['risk_level'] == 'critical':
                recommendations.append(f"🚨 风险等级：严重（潜在亏损{risk_info['potential_loss_pct']:.2f}%）")
            elif risk_info['risk_level'] == 'high':
                recommendations.append(f"⚠️ 风险等级：高（潜在亏损{risk_info['potential_loss_pct']:.2f}%）")
            
            # 添加爆仓警告
            if risk_info['liquidation_distance_pct'] < risk_info['stop_loss_distance_pct']:
                recommendations.append(f"⚠️ 爆仓价格${risk_info['liquidation_price']:,.0f}，距离{risk_info['liquidation_distance_pct']:.2f}%")
        
        analysis['recommendations'] = recommendations
        analysis['de_recommendations'] = de_recommendations
        
        return analysis


def get_position_risk_manager() -> PositionRiskManager:
    """获取全局仓位风险管理器实例"""
    return PositionRiskManager()


if __name__ == '__main__':
    # 测试
    manager = PositionRiskManager()
    
    print("=" * 80)
    print("仓位和风险管理测试（包含De.风格）")
    print("=" * 80)
    print()
    
    # 测试De.仓位风格
    print("1. De.的仓位风格")
    print("-" * 80)
    de_style = manager.get_de_position_style()
    print(f"杠杆: {de_style['leverage']}x")
    print(f"仓位: {de_style['position_size_pct']}%逐仓")
    print(f"保证金模式: {de_style['margin_mode']}")
    print(f"风险态度: {de_style['risk_attitude']}")
    print(f"原因: {de_style['reason']}")
    print("\n关键点:")
    for point in de_style['key_points']:
        print(f"  - {point}")
    print()
    
    # 测试仓位风险计算
    print("2. 仓位风险计算（De.风格）")
    print("-" * 80)
    position_risk = manager.calculate_position_risk(
        leverage=15,
        position_size_pct=5,
        entry_price=88710,
        stop_loss_price=88600,
        account_balance=10000
    )
    print(f"杠杆: {position_risk['leverage']}x")
    print(f"仓位: {position_risk['position_size_pct']}%")
    print(f"仓位价值: ${position_risk['position_value']:,.2f}")
    print(f"止损距离: {position_risk['stop_loss_distance_pct']:.2f}%")
    print(f"潜在亏损: ${position_risk['potential_loss']:,.2f} ({position_risk['potential_loss_pct']:.2f}%)")
    print(f"爆仓价格: ${position_risk['liquidation_price']:,.0f} (距离{position_risk['liquidation_distance_pct']:.2f}%)")
    print(f"风险等级: {position_risk['risk_level']}")
    if position_risk['de_comparison']['warning']:
        print("\n警告:")
        for warning in position_risk['de_comparison']['warning']:
            print(f"  {warning}")
    print()
    
    # 测试综合风险分析（De.风格）
    print("3. 综合风险分析（De.风格）")
    print("-" * 80)
    risk_analysis = manager.get_comprehensive_risk_analysis(
        symbol='BTC',
        entry_price=88710,
        stop_loss_price=88600,
        trading_style='de_style',
        leverage=15,
        position_size_pct=5,
        account_balance=10000
    )
    
    print("De.风格信息:")
    print(f"  - {risk_analysis['de_position_style']['reason']}")
    
    if risk_analysis.get('position_risk'):
        print("\n仓位风险:")
        pr = risk_analysis['position_risk']
        print(f"  - 潜在亏损: {pr['potential_loss_pct']:.2f}%")
        print(f"  - 风险等级: {pr['risk_level']}")
    
    print("\nDe.风格建议:")
    for rec in risk_analysis['de_recommendations']:
        print(f"  {rec}")
    
    print("\n综合建议:")
    for rec in risk_analysis['recommendations']:
        print(f"  {rec}")
    
    print()
    print("=" * 80)

