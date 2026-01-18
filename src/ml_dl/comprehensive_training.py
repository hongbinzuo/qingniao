#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合训练脚本
整合所有数据和功能，训练多个模型
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
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
from ml_signal_predictor import MLSignalPredictor
from ml_dl.prepare_training_data import TrainingDataPreparer

# 尝试导入深度学习库
try:
    import torch
    import numpy as np
    import pandas as pd
    from sklearn.model_selection import train_test_split
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
    DEEP_LEARNING_AVAILABLE = True
except ImportError:
    DEEP_LEARNING_AVAILABLE = False
    print("警告: 部分库未安装，某些功能可能受限", file=sys.stderr)


class ComprehensiveTrainer:
    """综合训练器"""
    
    def __init__(self, trader_id='de'):
        self.trader_id = trader_id
        self.db = TraderDBManager(trader_id)
        self.ml_predictor = MLSignalPredictor()
        self.model_dir = Path(__file__).parent.parent.parent / "trading_signals" / ".ml_models"
        self.model_dir.mkdir(parents=True, exist_ok=True)
    
    def prepare_all_data(self) -> Dict:
        """准备所有训练数据"""
        print("=" * 80)
        print("准备所有训练数据")
        print("=" * 80)
        print()
        
        # 1. 准备信号数据
        print("【1/4】准备信号数据...")
        signal_data = self._prepare_signal_data()
        print(f"✓ 信号数据: {len(signal_data.get('signals', []))} 个")
        print()
        
        # 2. 准备价格数据
        print("【2/4】准备价格数据...")
        price_data = self._prepare_price_data()
        print(f"✓ 价格数据: {len(price_data.get('klines', []))} 条")
        print()
        
        # 3. 准备对话数据
        print("【3/4】准备对话数据...")
        conversation_data = self._prepare_conversation_data()
        print(f"✓ 对话数据: {len(conversation_data.get('viewpoints', []))} 条观点")
        print()
        
        # 4. 融合数据
        print("【4/4】融合数据...")
        fused_data = self._fuse_data(signal_data, price_data, conversation_data)
        print(f"✓ 融合数据: {len(fused_data.get('samples', []))} 个样本")
        print()
        
        return fused_data
    
    def _prepare_signal_data(self) -> Dict:
        """准备信号数据"""
        signals = self.db.get_trading_signals(status=['completed', 'stopped'], limit=1000)
        evaluations = {}
        
        for signal in signals:
            eval_result = self.db.get_signal_evaluation(signal['id'])
            if eval_result:
                evaluations[signal['id']] = eval_result
        
        return {
            'signals': signals,
            'evaluations': evaluations
        }
    
    def _prepare_price_data(self) -> Dict:
        """准备价格数据"""
        try:
            import duckdb
            ts_file = Path(__file__).parent.parent / "data" / "btc_price_timeseries.duckdb"
            if ts_file.exists():
                conn = duckdb.connect(str(ts_file))
                klines = conn.execute('''
                    SELECT timestamp, datetime, open, high, low, close, volume
                    FROM btc_price_5m
                    ORDER BY timestamp
                ''').fetchall()
                conn.close()
                
                return {
                    'klines': klines,
                    'timeframe': '5m'
                }
        except:
            pass
        
        return {'klines': []}
    
    def _prepare_conversation_data(self) -> Dict:
        """准备对话数据"""
        viewpoints = self.db.get_viewpoints(limit=1000)
        # conversations表暂时不使用，使用viewpoints即可
        conversations = []
        
        return {
            'viewpoints': viewpoints,
            'conversations': conversations
        }
    
    def _fuse_data(self, signal_data: Dict, price_data: Dict, conversation_data: Dict) -> Dict:
        """融合所有数据"""
        samples = []
        
        # 为每个信号创建样本
        for signal in signal_data.get('signals', []):
            sample = {
                'signal_id': signal['id'],
                'signal': signal,
                'evaluation': signal_data['evaluations'].get(signal['id']),
                'price_context': self._get_price_context(signal, price_data),
                'conversation_context': self._get_conversation_context(signal, conversation_data)
            }
            samples.append(sample)
        
        return {
            'samples': samples,
            'price_data': price_data,
            'conversation_data': conversation_data
        }
    
    def _get_price_context(self, signal: Dict, price_data: Dict) -> Dict:
        """获取价格上下文"""
        # 简化版：返回信号时间的价格
        signal_time = signal.get('signal_time')
        if not signal_time:
            return {}
        
        try:
            dt = datetime.strptime(signal_time, '%Y-%m-%d %H:%M:%S')
            signal_ts = int(dt.timestamp())
            
            # 查找最接近的价格
            klines = price_data.get('klines', [])
            for kline in klines:
                if kline[0] >= signal_ts:
                    return {
                        'timestamp': kline[0],
                        'price': kline[5],  # close
                        'volume': kline[6]
                    }
        except:
            pass
        
        return {}
    
    def _get_conversation_context(self, signal: Dict, conversation_data: Dict) -> Dict:
        """获取对话上下文"""
        signal_time = signal.get('signal_time')
        if not signal_time:
            return {}
        
        # 查找信号时间附近的观点
        viewpoints = conversation_data.get('viewpoints', [])
        nearby_viewpoints = []
        
        try:
            signal_dt = datetime.strptime(signal_time, '%Y-%m-%d %H:%M:%S')
            
            for vp in viewpoints:
                vp_time = vp.get('timestamp')
                if vp_time:
                    try:
                        vp_dt = datetime.strptime(vp_time, '%Y-%m-%d %H:%M:%S')
                        time_diff = abs((vp_dt - signal_dt).total_seconds())
                        
                        # 24小时内的观点
                        if time_diff <= 24 * 3600:
                            nearby_viewpoints.append(vp)
                    except:
                        pass
        except:
            pass
        
        return {
            'nearby_viewpoints': nearby_viewpoints[:10]  # 最多10条
        }
    
    def train_signal_success_model(self, data: Dict) -> Dict:
        """训练信号成功率预测模型"""
        print("=" * 80)
        print("训练信号成功率预测模型")
        print("=" * 80)
        print()
        
        # 准备信号数据（使用ML预测器的格式）
        signals_data = {}
        for sample in data.get('samples', []):
            signal = sample['signal']
            evaluation = sample.get('evaluation')
            
            if not evaluation:
                continue
            
            # 转换为ML预测器格式
            system_name = signal.get('system_name', 'de')
            if system_name not in signals_data:
                signals_data[system_name] = []
            
            signals_data[system_name].append({
                'system': system_name,
                'timeframe': signal.get('timeframe', '15分钟'),
                'entry_model': signal.get('entry_model', 'Unknown'),
                'type': signal.get('signal_type', 'long'),
                'strength': signal.get('strength', 'medium'),
                'entry': signal.get('entry_price', 0),
                'stop_loss': signal.get('stop_loss', 0),
                'take_profit_1': signal.get('take_profit_1', 0),
                'take_profit_2': signal.get('take_profit_2', 0),
                'status': evaluation.get('result', 'stopped')
            })
        
        if not signals_data:
            print("没有可用的信号数据")
            return {}
        
        # 训练模型
        result = self.ml_predictor.train_model(signals_data)
        
        # 保存模型
        self.ml_predictor.save_model()
        
        print()
        print("=" * 80)
        print("训练完成")
        print("=" * 80)
        print(f"准确率: {result.get('accuracy', 0):.2%}")
        print(f"训练样本: {result.get('train_samples', 0)}")
        print(f"测试样本: {result.get('test_samples', 0)}")
        print()
        
        return result
    
    def train_all_models(self):
        """训练所有模型"""
        print("=" * 80)
        print("综合训练 - 训练所有模型")
        print("=" * 80)
        print()
        
        # 1. 准备数据
        data = self.prepare_all_data()
        
        if not data.get('samples'):
            print("没有可用的训练数据")
            return
        
        # 2. 训练信号成功率预测模型
        print()
        signal_model_result = self.train_signal_success_model(data)
        
        # 3. 其他模型（未来扩展）
        # - 价格预测模型
        # - RL交易策略模型
        # - 行为模式模型
        
        print()
        print("=" * 80)
        print("所有模型训练完成")
        print("=" * 80)
        print()
        print("训练结果:")
        print(f"  信号成功率预测模型: 准确率 {signal_model_result.get('accuracy', 0):.2%}")
        print()
    
    def close(self):
        """关闭连接"""
        self.db.close()


def main():
    """主函数"""
    trainer = ComprehensiveTrainer(trader_id='de')
    
    try:
        trainer.train_all_models()
    except KeyboardInterrupt:
        print("\n训练被用户中断")
    except Exception as e:
        print(f"\n训练失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        trainer.close()

if __name__ == '__main__':
    main()

