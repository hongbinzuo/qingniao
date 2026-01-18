#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
千叶交易系统 - 信号生成器
根据提取的规则生成BTC、黄金、白银的交易信号
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import json

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))


class ChibaSignalGenerator:
    """千叶交易系统信号生成器"""
    
    def __init__(self):
        self.rules_file = Path(__file__).parent.parent.parent / "data" / "chiba_videos" / "rules" / "chiba_trading_rules.json"
        self.rules = self._load_rules()
        
        # 支持的市场
        self.markets = {
            'BTC': {
                'symbol': 'BTC_USDT',
                'exchange': 'gateio',
                'name': '比特币'
            },
            'GOLD': {
                'symbol': 'XAU_USD',
                'exchange': 'gateio',
                'name': '黄金'
            },
            'SILVER': {
                'symbol': 'XAG_USD',
                'exchange': 'gateio',
                'name': '白银'
            }
        }
    
    def _load_rules(self) -> Dict:
        """加载交易规则"""
        if self.rules_file.exists():
            try:
                with open(self.rules_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        # 默认规则（待从视频中提取）
        return {
            'entry_conditions': [],
            'stop_loss_rules': [],
            'take_profit_rules': [],
            'risk_management': []
        }
    
    def get_market_data(self, market: str, timeframe: str = '15m') -> Optional[List]:
        """获取市场数据"""
        try:
            import requests
            
            market_info = self.markets.get(market)
            if not market_info:
                return None
            
            symbol = market_info['symbol']
            exchange = market_info['exchange']
            
            if exchange == 'gateio':
                url = "https://api.gateio.ws/api/v4/spot/candlesticks"
                params = {
                    'currency_pair': symbol,
                    'interval': timeframe,
                    'limit': 200
                }
                response = requests.get(url, params=params, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        data.reverse()
                        klines = []
                        for k in data:
                            klines.append({
                                'timestamp': int(k[0]),
                                'open': float(k[5]),
                                'high': float(k[3]),
                                'low': float(k[4]),
                                'close': float(k[2]),
                                'volume': float(k[1])
                            })
                        return klines
        except Exception as e:
            print(f"获取{market}数据失败: {e}", file=sys.stderr)
        
        return None
    
    def generate_signals(self, markets: List[str] = None) -> Dict:
        """生成交易信号"""
        if markets is None:
            markets = ['BTC', 'GOLD', 'SILVER']
        
        print("=" * 80)
        print("千叶交易系统 - 信号生成")
        print("=" * 80)
        print()
        
        all_signals = {}
        
        for market in markets:
            print(f"分析 {self.markets[market]['name']} ({market})...")
            
            # 获取市场数据
            klines = self.get_market_data(market)
            if not klines:
                print(f"  ⚠️ 无法获取{market}数据")
                continue
            
            # 生成信号（基于规则）
            signals = self._generate_market_signals(market, klines)
            all_signals[market] = signals
            
            print(f"  ✓ 生成 {len(signals)} 个信号")
            print()
        
        return all_signals
    
    def _generate_market_signals(self, market: str, klines: List[Dict]) -> List[Dict]:
        """为特定市场生成信号"""
        signals = []
        
        if not klines:
            return signals
        
        # 获取当前价格
        current_price = klines[-1]['close']
        
        # 计算技术指标（简化版）
        # 实际应该根据从视频中提取的规则来计算
        
        # 示例信号（待根据实际规则生成）
        # 这里只是框架，实际规则需要从视频中提取
        
        return signals
    
    def save_signals(self, signals: Dict, output_path: Path = None):
        """保存信号"""
        if output_path is None:
            output_path = Path(__file__).parent.parent.parent / "trading_signals" / f"chiba_signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 生成Markdown报告
        content = self._generate_signal_report(signals)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✓ 信号已保存: {output_path}")
    
    def _generate_signal_report(self, signals: Dict) -> str:
        """生成信号报告"""
        lines = []
        lines.append("# 千叶交易系统 - 交易信号")
        lines.append("")
        lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        for market, market_signals in signals.items():
            market_name = self.markets[market]['name']
            lines.append(f"## {market_name} ({market})")
            lines.append("")
            
            if not market_signals:
                lines.append("暂无信号")
                lines.append("")
            else:
                for i, signal in enumerate(market_signals, 1):
                    lines.append(f"### 信号 {i}")
                    lines.append("")
                    lines.append(f"- **方向**: {signal.get('direction', 'N/A')}")
                    lines.append(f"- **入场**: {signal.get('entry', 'N/A')}")
                    lines.append(f"- **止损**: {signal.get('stop_loss', 'N/A')}")
                    lines.append(f"- **止盈**: {signal.get('take_profit', 'N/A')}")
                    lines.append("")
            
            lines.append("---")
            lines.append("")
        
        return "\n".join(lines)


def main():
    """主函数"""
    generator = ChibaSignalGenerator()
    
    # 生成信号
    signals = generator.generate_signals(['BTC', 'GOLD', 'SILVER'])
    
    # 保存信号
    generator.save_signals(signals)
    
    print()
    print("=" * 80)
    print("信号生成完成")
    print("=" * 80)

if __name__ == '__main__':
    main()










