#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练数据准备脚本
1. 导入历史信号到数据库
2. 评估历史信号
3. 提取特征
4. 创建训练数据集
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import re
import json

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from db_manager_trader import TraderDBManager
import duckdb


class TrainingDataPreparer:
    """训练数据准备器"""
    
    def __init__(self, trader_id='de'):
        self.trader_id = trader_id
        self.db = TraderDBManager(trader_id)
        self.base_dir = Path(__file__).parent.parent.parent
        self.signals_dir = self.base_dir / "trading_signals"
        
        # 初始化价格数据连接
        self._init_price_data()
    
    def _init_price_data(self):
        """初始化价格数据连接"""
        try:
            ts_file = Path(__file__).parent.parent / "data" / "btc_price_timeseries.duckdb"
            if ts_file.exists():
                self.price_conn = duckdb.connect(str(ts_file))
            else:
                self.price_conn = None
        except:
            self.price_conn = None
    
    def parse_signal_file(self, file_path: Path) -> List[Dict]:
        """解析信号Markdown文件"""
        signals = []
        
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # 提取文件时间（从文件名或内容）
            filename = file_path.stem
            time_match = re.search(r'(\d{8})_(\d{6})', filename)
            if time_match:
                date_str = time_match.group(1)
                time_str = time_match.group(2)
                file_time = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} {time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
            else:
                # 尝试从内容中提取
                gen_time_match = re.search(r'\*\*生成时间\*\*:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', content)
                if gen_time_match:
                    file_time = gen_time_match.group(1)
                else:
                    file_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 解析信号（根据实际格式）
            # 查找信号块 - 匹配"## 一、5分钟交易信号"或"**做多**"等格式
            signal_sections = []
            
            # 方法1: 查找时间框架信号块
            tf_pattern = r'##\s*[一二三四五六七八九十]+、\s*(\d+分钟|15分钟|5分钟|1小时).*?信号(.*?)(?=##|$)'
            for match in re.finditer(tf_pattern, content, re.DOTALL):
                timeframe = match.group(1)
                section_content = match.group(2)
                signal_sections.append((timeframe, section_content))
            
            # 方法2: 查找独立信号块（"**做多**"或"**做空**"）
            if not signal_sections:
                # 查找所有信号块
                signal_block_pattern = r'\*\*做(多|空)\*\*\s*\([^)]+\)(.*?)(?=\*\*做(多|空)\*\*|##|$)'
                for match in re.finditer(signal_block_pattern, content, re.DOTALL):
                    direction = 'long' if match.group(1) == '多' else 'short'
                    section_content = match.group(2)
                    # 尝试推断时间框架
                    timeframe = '15分钟'  # 默认
                    if '5分钟' in content[:match.start()]:
                        timeframe = '5分钟'
                    elif '15分钟' in content[:match.start()]:
                        timeframe = '15分钟'
                    elif '1小时' in content[:match.start()]:
                        timeframe = '1小时'
                    signal_sections.append((timeframe, section_content, direction))
            
            # 解析每个信号块
            for section_data in signal_sections:
                if len(section_data) == 3:
                    timeframe, section_content, direction = section_data
                else:
                    timeframe, section_content = section_data
                    direction = 'long' if '做多' in section_content or 'long' in section_content.lower() else 'short'
                
                # 提取价格信息
                # 入场价
                entry_match = re.search(r'入场[：:]\s*\$?([\d,]+\.?\d*)', section_content)
                entry_price = None
                if entry_match:
                    entry_price = float(entry_match.group(1).replace(',', ''))
                
                # 止损
                stop_loss_match = re.search(r'止损[：:]\s*\$?([\d,]+\.?\d*)', section_content)
                stop_loss = None
                if stop_loss_match:
                    stop_loss = float(stop_loss_match.group(1).replace(',', ''))
                
                # 止盈
                tp_match = re.search(r'止盈[：:]\s*\$?([\d,]+\.?\d*)\s*[\(（]', section_content)
                take_profit_1 = None
                if tp_match:
                    take_profit_1 = float(tp_match.group(1).replace(',', ''))
                
                # 第二止盈
                tp2_match = re.search(r'/\s*\$?([\d,]+\.?\d*)\s*[\(（]', section_content)
                take_profit_2 = None
                if tp2_match:
                    take_profit_2 = float(tp2_match.group(1).replace(',', ''))
                
                # 如果价格提取失败，尝试从数字中提取
                if not entry_price or not stop_loss:
                    prices = re.findall(r'\$?([\d,]+\.?\d*)', section_content)
                    prices = [float(p.replace(',', '')) for p in prices if 40000 <= float(p.replace(',', '')) <= 150000]
                    
                    if len(prices) >= 2:
                        if not entry_price:
                            entry_price = prices[0]
                        if not stop_loss:
                            # 根据方向选择止损
                            if direction == 'long':
                                stop_loss = min([p for p in prices if p < entry_price], default=entry_price * 0.98)
                            else:
                                stop_loss = max([p for p in prices if p > entry_price], default=entry_price * 1.02)
                        if not take_profit_1:
                            if direction == 'long':
                                take_profit_1 = max([p for p in prices if p > entry_price], default=entry_price * 1.02)
                            else:
                                take_profit_1 = min([p for p in prices if p < entry_price], default=entry_price * 0.98)
                
                # 如果还是没有价格，跳过
                if not entry_price or not stop_loss:
                    continue
                
                # 计算止盈（如果没有提取到）
                if not take_profit_1:
                    risk = abs(entry_price - stop_loss)
                    if direction == 'long':
                        take_profit_1 = entry_price + risk * 2.5
                        take_profit_2 = entry_price + risk * 3.5
                    else:
                        take_profit_1 = entry_price - risk * 2.5
                        take_profit_2 = entry_price - risk * 3.5
                elif not take_profit_2:
                    risk = abs(entry_price - stop_loss)
                    if direction == 'long':
                        take_profit_2 = take_profit_1 + risk
                    else:
                        take_profit_2 = take_profit_1 - risk
                
                # 提取入场模型
                entry_model = 'Unknown'
                if 'FVG' in section_content or 'fvg' in section_content.lower() or '回填' in section_content:
                    entry_model = 'FVG'
                elif 'Vegas' in section_content or 'vegas' in section_content.lower():
                    entry_model = 'Vegas'
                elif '突破' in section_content:
                    entry_model = 'Breakout'
                elif '反转' in section_content or '三重底' in section_content or 'M顶' in section_content or 'W底' in section_content:
                    entry_model = 'Reversal'
                
                # 提取强度
                strength = 'medium'
                if '强' in section_content or 'strong' in section_content.lower():
                    strength = 'strong'
                elif '弱' in section_content or 'weak' in section_content.lower():
                    strength = 'weak'
                
                # 计算盈亏比
                risk = abs(entry_price - stop_loss)
                reward = abs(take_profit_1 - entry_price)
                risk_reward_ratio = reward / risk if risk > 0 else 0
                
                signals.append({
                    'signal_time': file_time,
                    'timeframe': timeframe,
                    'signal_type': direction,
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit_1': take_profit_1,
                    'take_profit_2': take_profit_2,
                    'entry_model': entry_model,
                    'strength': strength,
                    'risk_reward_ratio': risk_reward_ratio,
                    'volatility_level': 'medium',
                    'system_name': 'De.',
                    'status': 'pending',
                    'source_file': str(file_path.name)
                })
        except Exception as e:
            print(f"  解析文件失败 {file_path.name}: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
        
        return signals
    
    def import_historical_signals(self) -> int:
        """导入历史信号到数据库"""
        print("=" * 80)
        print("导入历史信号到数据库")
        print("=" * 80)
        print()
        
        if not self.signals_dir.exists():
            print(f"信号目录不存在: {self.signals_dir}")
            return 0
        
        # 查找所有信号文件
        signal_files = list(self.signals_dir.glob("BTC_de_signals_*.md"))
        
        if not signal_files:
            print("未找到信号文件")
            return 0
        
        print(f"找到 {len(signal_files)} 个信号文件")
        print()
        
        all_signals = []
        for file_path in signal_files:
            print(f"解析文件: {file_path.name}")
            signals = self.parse_signal_file(file_path)
            all_signals.extend(signals)
            print(f"  提取了 {len(signals)} 个信号")
        
        print()
        print(f"总共提取了 {len(all_signals)} 个信号")
        print()
        
        # 导入到数据库
        print("导入到数据库...")
        imported = 0
        skipped = 0
        
        for signal in all_signals:
            try:
                # 检查是否已存在（简化检查 - 只检查entry_price）
                existing_signals = self.db.get_trading_signals(limit=1000)
                existing = None
                for sig in existing_signals:
                    if abs(sig.get('entry_price', 0) - signal['entry_price']) < 1.0:
                        existing = sig
                        break
                
                if existing:
                    skipped += 1
                    continue
                
                # 导入信号
                try:
                    signal_id = self.db.add_trading_signal(
                        signal_time=signal['signal_time'],
                        timeframe=signal['timeframe'],
                        signal_type=signal['signal_type'],
                        entry_price=signal['entry_price'],
                        stop_loss=signal['stop_loss'],
                        take_profit_1=signal['take_profit_1'],
                        take_profit_2=signal['take_profit_2'],
                        entry_model=signal['entry_model'],
                        strength=signal['strength'],
                        risk_reward_ratio=signal['risk_reward_ratio'],
                        volatility_level=signal['volatility_level'],
                        system_name=signal['system_name']
                    )
                    
                    imported += 1
                except Exception as e:
                    print(f"  导入信号失败: {e}", file=sys.stderr)
                    import traceback
                    traceback.print_exc()
                    continue
                
            except Exception as e:
                print(f"  处理信号失败: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
        
        print(f"✓ 导入了 {imported} 个信号，跳过了 {skipped} 个重复信号")
        print()
        
        return imported
    
    def evaluate_historical_signals(self) -> int:
        """评估历史信号"""
        print("=" * 80)
        print("评估历史信号")
        print("=" * 80)
        print()
        
        # 获取所有pending状态的信号
        signals = self.db.get_trading_signals(status='pending', limit=1000)
        
        if not signals:
            print("没有待评估的信号")
            return 0
        
        print(f"找到 {len(signals)} 个待评估信号")
        print()
        
        evaluated = 0
        
        for signal in signals:
            try:
                # 获取信号时间
                signal_time = signal.get('signal_time')
                if not signal_time:
                    continue
                
                # 获取信号价格
                entry_price = signal.get('entry_price')
                stop_loss = signal.get('stop_loss')
                take_profit_1 = signal.get('take_profit_1')
                take_profit_2 = signal.get('take_profit_2')
                signal_type = signal.get('signal_type', 'long')
                
                # 获取信号后的价格数据
                result = self._evaluate_signal_with_price_data(
                    signal_time, entry_price, stop_loss, 
                    take_profit_1, take_profit_2, signal_type
                )
                
                if not result:
                    # 如果没有价格数据，标记为missed
                    result = {
                        'result': 'missed',
                        'evaluation_time': signal_time,
                        'exit_price': entry_price,
                        'profit_pct': 0,
                        'profit_usdt': 0,
                        'stop_loss_hit': 0,
                        'take_profit_1_hit': 0,
                        'take_profit_2_hit': 0,
                        'notes': '无价格数据'
                    }
                
                if result:
                    # 检查是否已有评估记录
                    existing_eval = self.db.get_signal_evaluation(signal['id'])
                    if existing_eval:
                        # 跳过已有评估的信号
                        continue
                    
                    # 添加评估记录
                    try:
                        self.db.add_signal_evaluation(
                            signal_id=signal['id'],
                            evaluation_time=result['evaluation_time'],
                            result=result['result'],
                            actual_entry_price=entry_price,
                            actual_exit_price=result.get('exit_price'),
                            actual_profit_pct=result.get('profit_pct', 0),
                            actual_profit_usdt=result.get('profit_usdt', 0),
                            stop_loss_hit=result.get('stop_loss_hit', 0),
                            take_profit_1_hit=result.get('take_profit_1_hit', 0),
                            take_profit_2_hit=result.get('take_profit_2_hit', 0),
                            notes=result.get('notes', '')
                        )
                        
                        # 更新信号状态（如果状态还是pending）
                        if signal.get('status') == 'pending':
                            try:
                                self.db.update_signal_status(signal['id'], result['result'])
                            except Exception as e:
                                # 如果更新失败，跳过
                                pass
                        
                        evaluated += 1
                        
                        if evaluated % 5 == 0:
                            print(f"  已评估 {evaluated}/{len(signals)} 个信号")
                    except Exception as e:
                        print(f"  添加评估记录失败 (signal_id={signal['id']}): {e}", file=sys.stderr)
                        continue
            
            except Exception as e:
                print(f"  评估信号失败 (signal_id={signal.get('id', 'unknown')}): {e}", file=sys.stderr)
        
        print()
        print(f"✓ 评估了 {evaluated} 个信号")
        print()
        
        return evaluated
    
    def _evaluate_signal_with_price_data(self, signal_time: str, entry_price: float,
                                        stop_loss: float, take_profit_1: float,
                                        take_profit_2: float, signal_type: str) -> Optional[Dict]:
        """使用价格数据评估信号"""
        if not self.price_conn:
            return None
        
        try:
            # 转换信号时间
            dt = datetime.strptime(signal_time, '%Y-%m-%d %H:%M:%S')
            signal_ts = int(dt.timestamp())
            
            # 获取信号后24小时的价格数据（5分钟K线）
            # 允许一些时间误差（±5分钟）
            start_ts = signal_ts - 300  # 提前5分钟
            end_ts = signal_ts + 24 * 3600
            
            query = '''
                SELECT timestamp, close
                FROM btc_price_5m
                WHERE timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp
            '''
            
            price_data = self.price_conn.execute(query, [start_ts, end_ts]).fetchall()
            
            if not price_data:
                # 如果没有精确匹配，尝试查找最接近的时间
                closest_query = '''
                    SELECT timestamp, close
                    FROM btc_price_5m
                    WHERE timestamp <= ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                '''
                closest = self.price_conn.execute(closest_query, [signal_ts + 3600]).fetchone()
                if closest:
                    # 使用最接近的价格数据，但标记为可能不准确
                    price_data = [(closest[0], closest[1])]
                else:
                    return None
            
            # 评估信号结果
            result = {
                'result': 'missed',
                'evaluation_time': signal_time,
                'stop_loss_hit': 0,
                'take_profit_1_hit': 0,
                'take_profit_2_hit': 0,
                'exit_price': entry_price,
                'profit_pct': 0,
                'profit_usdt': 0,
                'notes': ''
            }
            
            for ts, close_price in price_data:
                if signal_type == 'long':
                    # 检查止损
                    if close_price <= stop_loss:
                        result['result'] = 'stopped'
                        result['stop_loss_hit'] = 1
                        result['exit_price'] = stop_loss
                        result['profit_pct'] = ((stop_loss - entry_price) / entry_price) * 100
                        result['notes'] = '触发止损'
                        break
                    
                    # 检查止盈
                    if close_price >= take_profit_2:
                        result['result'] = 'completed'
                        result['take_profit_2_hit'] = 1
                        result['exit_price'] = take_profit_2
                        result['profit_pct'] = ((take_profit_2 - entry_price) / entry_price) * 100
                        result['notes'] = '触发第二止盈'
                        break
                    elif close_price >= take_profit_1:
                        result['result'] = 'completed'
                        result['take_profit_1_hit'] = 1
                        result['exit_price'] = take_profit_1
                        result['profit_pct'] = ((take_profit_1 - entry_price) / entry_price) * 100
                        result['notes'] = '触发第一止盈'
                        # 继续检查是否达到第二止盈
                
                else:  # short
                    # 检查止损
                    if close_price >= stop_loss:
                        result['result'] = 'stopped'
                        result['stop_loss_hit'] = 1
                        result['exit_price'] = stop_loss
                        result['profit_pct'] = ((entry_price - stop_loss) / entry_price) * 100
                        result['notes'] = '触发止损'
                        break
                    
                    # 检查止盈
                    if close_price <= take_profit_2:
                        result['result'] = 'completed'
                        result['take_profit_2_hit'] = 1
                        result['exit_price'] = take_profit_2
                        result['profit_pct'] = ((entry_price - take_profit_2) / entry_price) * 100
                        result['notes'] = '触发第二止盈'
                        break
                    elif close_price <= take_profit_1:
                        result['result'] = 'completed'
                        result['take_profit_1_hit'] = 1
                        result['exit_price'] = take_profit_1
                        result['profit_pct'] = ((entry_price - take_profit_1) / entry_price) * 100
                        result['notes'] = '触发第一止盈'
            
            # 计算盈利金额（假设1%仓位）
            result['profit_usdt'] = result['profit_pct'] * 0.01 * 10000  # 假设10000 USDT本金
            
            return result
            
        except Exception as e:
            print(f"  评估失败: {e}", file=sys.stderr)
            return None
    
    def create_training_dataset(self) -> Dict:
        """创建训练数据集"""
        print("=" * 80)
        print("创建训练数据集")
        print("=" * 80)
        print()
        
        # 获取所有已评估的信号
        signals = self.db.get_trading_signals(status=['completed', 'stopped'], limit=1000)
        
        if not signals:
            print("没有已评估的信号")
            return {}
        
        print(f"找到 {len(signals)} 个已评估信号")
        print()
        
        # 获取评估结果
        dataset = {
            'features': [],
            'labels': [],
            'metadata': []
        }
        
        for signal in signals:
            try:
                # 获取评估结果
                evaluation = self.db.get_signal_evaluation(signal['id'])
                if not evaluation:
                    continue
                
                # 提取特征（简化版）
                features = self._extract_signal_features(signal)
                
                # 标签（成功=1，失败=0）
                label = 1 if evaluation['result'] == 'completed' else 0
                
                dataset['features'].append(features)
                dataset['labels'].append(label)
                dataset['metadata'].append({
                    'signal_id': signal['id'],
                    'signal_time': signal['signal_time'],
                    'result': evaluation['result'],
                    'profit_pct': evaluation.get('actual_profit_pct', 0)
                })
            
            except Exception as e:
                print(f"  处理信号失败: {e}", file=sys.stderr)
        
        print(f"✓ 创建了 {len(dataset['features'])} 个训练样本")
        print()
        
        return dataset
    
    def _extract_signal_features(self, signal: Dict) -> List[float]:
        """提取信号特征"""
        features = []
        
        # 基础特征
        features.append(signal.get('entry_price', 0))
        features.append(signal.get('stop_loss', 0))
        features.append(signal.get('take_profit_1', 0))
        features.append(signal.get('take_profit_2', 0))
        features.append(signal.get('risk_reward_ratio', 0))
        
        # 距离特征（百分比）
        entry = signal.get('entry_price', 0)
        if entry > 0:
            features.append(abs((signal.get('stop_loss', 0) - entry) / entry * 100))
            features.append(abs((signal.get('take_profit_1', 0) - entry) / entry * 100))
            features.append(abs((signal.get('take_profit_2', 0) - entry) / entry * 100))
        else:
            features.extend([0, 0, 0])
        
        # 分类特征编码（简化）
        timeframe_map = {'5分钟': 1, '15分钟': 2, '1小时': 3}
        features.append(timeframe_map.get(signal.get('timeframe', '15分钟'), 2))
        
        signal_type_map = {'long': 1, 'short': 0}
        features.append(signal_type_map.get(signal.get('signal_type', 'long'), 1))
        
        strength_map = {'strong': 2, 'medium': 1, 'weak': 0}
        features.append(strength_map.get(signal.get('strength', 'medium'), 1))
        
        return features
    
    def save_training_dataset(self, dataset: Dict, output_path: Path):
        """保存训练数据集"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'features': dataset['features'],
            'labels': dataset['labels'],
            'metadata': dataset['metadata'],
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_samples': len(dataset['features'])
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ 训练数据集已保存到: {output_path}")
    
    def close(self):
        """关闭连接"""
        if hasattr(self, 'price_conn') and self.price_conn:
            self.price_conn.close()
        self.db.close()


def main():
    """主函数"""
    print("=" * 80)
    print("训练数据准备")
    print("=" * 80)
    print()
    
    preparer = TrainingDataPreparer(trader_id='de')
    
    # 1. 导入历史信号
    print("步骤1: 导入历史信号")
    imported = preparer.import_historical_signals()
    print()
    
    # 2. 评估历史信号
    print("步骤2: 评估历史信号")
    evaluated = preparer.evaluate_historical_signals()
    print()
    
    # 3. 创建训练数据集
    print("步骤3: 创建训练数据集")
    dataset = preparer.create_training_dataset()
    print()
    
    # 4. 保存训练数据集
    if dataset.get('features'):
        output_path = Path(__file__).parent.parent.parent / "trading_signals" / ".ml_models" / "training_dataset.json"
        preparer.save_training_dataset(dataset, output_path)
        print()
    
    # 总结
    print("=" * 80)
    print("数据准备完成")
    print("=" * 80)
    print(f"导入信号: {imported} 个")
    print(f"评估信号: {evaluated} 个")
    print(f"训练样本: {len(dataset.get('features', []))} 个")
    print()
    
    preparer.close()

if __name__ == '__main__':
    main()

