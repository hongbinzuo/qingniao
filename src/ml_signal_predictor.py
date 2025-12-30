#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机器学习信号预测模块
基于历史信号数据训练模型，预测新信号的成功率
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import numpy as np

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 尝试导入机器学习库
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("警告: pandas未安装，某些功能可能受限", file=sys.stderr)

try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import LabelEncoder
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
    import joblib
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("警告: scikit-learn未安装，机器学习功能不可用", file=sys.stderr)
    print("请安装: pip install scikit-learn pandas", file=sys.stderr)


class MLSignalPredictor:
    """机器学习信号预测器"""
    
    def __init__(self, model_dir: Optional[Path] = None):
        """
        初始化预测器
        
        Args:
            model_dir: 模型保存目录，默认使用 trading_signals/.ml_models
        """
        if model_dir is None:
            base_dir = Path(__file__).parent.parent
            model_dir = base_dir / "trading_signals" / ".ml_models"
        
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.model = None
        self.label_encoders = {}
        self.feature_names = []
        self.is_trained = False
        
        # 模型文件路径
        self.model_file = self.model_dir / "signal_predictor_model.pkl"
        self.encoders_file = self.model_dir / "label_encoders.pkl"
        self.metadata_file = self.model_dir / "model_metadata.json"
        
        # 尝试加载已有模型
        self.load_model()
    
    def prepare_features(self, signals_data: Dict) -> Tuple[List[Dict], List[int]]:
        """
        从信号数据中提取特征和标签
        
        Args:
            signals_data: 信号数据字典（从SignalTracker.load_signals()获取）
        
        Returns:
            (features, labels) 特征列表和标签列表
            labels: 1表示成功（full_tp），0表示失败（stopped）
        """
        features = []
        labels = []
        
        for system_name, signals in signals_data.items():
            for signal in signals:
                # 使用已完成的信号（stopped、full_tp）和错过的信号（missed，方向正确但未接到）
                if signal.get('status') not in ['stopped', 'full_tp', 'missed']:
                    continue
                
                # 提取特征
                feature = {
                    'system': signal.get('system', 'unknown'),
                    'timeframe': signal.get('timeframe', 'unknown'),
                    'entry_model': signal.get('entry_model', '未知模型'),
                    'type': signal.get('type', 'unknown'),  # 'long' or 'short'
                    'strength': signal.get('strength', 'medium'),
                    # 数值特征（归一化）
                    'entry': signal.get('entry', 0),
                    'stop_loss': signal.get('stop_loss', 0),
                    'take_profit_1': signal.get('take_profit_1', 0),
                    'take_profit_2': signal.get('take_profit_2', 0),
                }
                
                # 计算额外特征
                entry = feature['entry']
                if entry > 0:
                    # 止损距离（百分比）
                    feature['stop_loss_distance_pct'] = abs(feature['stop_loss'] - entry) / entry * 100
                    # 第一止盈距离（百分比）
                    feature['tp1_distance_pct'] = abs(feature['take_profit_1'] - entry) / entry * 100
                    # 第二止盈距离（百分比）
                    feature['tp2_distance_pct'] = abs(feature['take_profit_2'] - entry) / entry * 100
                    # 盈亏比
                    if feature['stop_loss_distance_pct'] > 0:
                        feature['risk_reward_ratio'] = feature['tp1_distance_pct'] / feature['stop_loss_distance_pct']
                    else:
                        feature['risk_reward_ratio'] = 0
                else:
                    feature['stop_loss_distance_pct'] = 0
                    feature['tp1_distance_pct'] = 0
                    feature['tp2_distance_pct'] = 0
                    feature['risk_reward_ratio'] = 0
                
                # 对于错过的信号，添加入场价合理性特征
                if signal.get('status') == 'missed':
                    # 入场价与生成时价格的差距（如果可用）
                    entry_distance_pct = signal.get('entry_distance_pct')
                    if entry_distance_pct is not None:
                        feature['entry_distance_from_current_pct'] = abs(entry_distance_pct)
                    else:
                        feature['entry_distance_from_current_pct'] = 0
                    # 方向是否正确（1表示正确，0表示错误）
                    feature['direction_correct'] = 1 if signal.get('direction_correct', False) else 0
                else:
                    feature['entry_distance_from_current_pct'] = 0
                    feature['direction_correct'] = 0
                
                features.append(feature)
                
                # 标签：1表示成功（full_tp），0表示失败（stopped或missed）
                # 对于missed状态，虽然方向正确，但因为未接到也算失败
                label = 1 if signal.get('status') == 'full_tp' else 0
                labels.append(label)
        
        return features, labels
    
    def train_model(self, signals_data: Dict, test_size: float = 0.2) -> Dict:
        """
        训练预测模型
        
        Args:
            signals_data: 信号数据字典
            test_size: 测试集比例
        
        Returns:
            训练结果字典（包含准确率等信息）
        """
        if not SKLEARN_AVAILABLE:
            return {'error': 'scikit-learn未安装，无法训练模型'}
        
        # 准备特征和标签
        features_list, labels = self.prepare_features(signals_data)
        
        if len(features_list) < 10:
            return {
                'error': f'数据不足（仅{len(features_list)}个样本），至少需要10个已完成的信号才能训练模型',
                'samples': len(features_list)
            }
        
        # 转换为DataFrame（如果pandas可用）
        if PANDAS_AVAILABLE:
            df = pd.DataFrame(features_list)
            
            # 分离分类特征和数值特征
            categorical_features = ['system', 'timeframe', 'entry_model', 'type', 'strength']
            numerical_features = ['stop_loss_distance_pct', 'tp1_distance_pct', 'tp2_distance_pct', 'risk_reward_ratio']
            
            # 编码分类特征
            X_encoded = df[numerical_features].copy()
            self.label_encoders = {}
            
            for feature in categorical_features:
                if feature in df.columns:
                    le = LabelEncoder()
                    X_encoded[feature] = le.fit_transform(df[feature].astype(str))
                    self.label_encoders[feature] = le
            
            X = X_encoded.values
            y = np.array(labels)
            self.feature_names = numerical_features + categorical_features
            
        else:
            # 如果没有pandas，使用简单的手动编码
            # 这里简化处理，只使用数值特征
            X = np.array([[f['stop_loss_distance_pct'], f['tp1_distance_pct'], 
                          f['tp2_distance_pct'], f['risk_reward_ratio']] 
                         for f in features_list])
            y = np.array(labels)
            self.feature_names = ['stop_loss_distance_pct', 'tp1_distance_pct', 
                                 'tp2_distance_pct', 'risk_reward_ratio']
        
        # 划分训练集和测试集
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )
        
        # 训练模型（使用随机森林）
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced'  # 处理类别不平衡
        )
        
        self.model.fit(X_train, y_train)
        
        # 评估模型
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        # 计算预测概率（用于评估）
        y_pred_proba = self.model.predict_proba(X_test)[:, 1]
        
        self.is_trained = True
        
        # 保存模型
        self.save_model()
        
        # 返回训练结果
        result = {
            'accuracy': float(accuracy),
            'train_samples': len(X_train),
            'test_samples': len(X_test),
            'total_samples': len(features_list),
            'feature_importance': {}
        }
        
        # 特征重要性
        if hasattr(self.model, 'feature_importances_'):
            feature_importance = dict(zip(self.feature_names, self.model.feature_importances_))
            result['feature_importance'] = {k: float(v) for k, v in 
                                           sorted(feature_importance.items(), 
                                                 key=lambda x: x[1], reverse=True)}
        
        return result
    
    def predict_signal_success(self, signal: Dict) -> Dict:
        """
        预测信号的成功率
        
        Args:
            signal: 信号字典
        
        Returns:
            {
                'success_probability': float,  # 成功概率（0-1）
                'prediction': int,  # 预测结果（1=成功，0=失败）
                'confidence': float  # 置信度
            }
        """
        if not self.is_trained or self.model is None:
            return {
                'error': '模型未训练',
                'success_probability': 0.5,  # 默认50%
                'prediction': 1,
                'confidence': 0.0
            }
        
        # 提取特征
        entry = signal.get('entry', 0)
        stop_loss = signal.get('stop_loss', 0)
        tp1 = signal.get('take_profit_1', 0)
        tp2 = signal.get('take_profit_2', 0)
        
        # 计算数值特征
        if entry > 0:
            stop_loss_distance_pct = abs(stop_loss - entry) / entry * 100
            tp1_distance_pct = abs(tp1 - entry) / entry * 100
            tp2_distance_pct = abs(tp2 - entry) / entry * 100
            risk_reward_ratio = tp1_distance_pct / stop_loss_distance_pct if stop_loss_distance_pct > 0 else 0
        else:
            stop_loss_distance_pct = 0
            tp1_distance_pct = 0
            tp2_distance_pct = 0
            risk_reward_ratio = 0
        
        # 构建特征向量（简化版本，只使用数值特征）
        if PANDAS_AVAILABLE and self.label_encoders:
            # 如果有编码器，使用完整特征
            try:
                feature_dict = {
                    'stop_loss_distance_pct': stop_loss_distance_pct,
                    'tp1_distance_pct': tp1_distance_pct,
                    'tp2_distance_pct': tp2_distance_pct,
                    'risk_reward_ratio': risk_reward_ratio,
                    'system': signal.get('system', 'unknown'),
                    'timeframe': signal.get('timeframe', 'unknown'),
                    'entry_model': signal.get('entry_model', '未知模型'),
                    'type': signal.get('type', 'unknown'),
                    'strength': signal.get('strength', 'medium'),
                }
                
                # 编码分类特征
                X = np.zeros((1, len(self.feature_names)))
                for i, feat_name in enumerate(self.feature_names):
                    if feat_name in ['stop_loss_distance_pct', 'tp1_distance_pct', 
                                    'tp2_distance_pct', 'risk_reward_ratio']:
                        X[0, i] = feature_dict[feat_name]
                    elif feat_name in self.label_encoders:
                        try:
                            X[0, i] = self.label_encoders[feat_name].transform([feature_dict[feat_name]])[0]
                        except:
                            X[0, i] = 0  # 如果编码失败，使用0
            except:
                # 如果出错，使用简化特征
                X = np.array([[stop_loss_distance_pct, tp1_distance_pct, 
                             tp2_distance_pct, risk_reward_ratio]])
        else:
            # 简化版本，只使用数值特征
            X = np.array([[stop_loss_distance_pct, tp1_distance_pct, 
                         tp2_distance_pct, risk_reward_ratio]])
        
        # 预测
        try:
            prediction = self.model.predict(X)[0]
            probabilities = self.model.predict_proba(X)[0]
            success_probability = probabilities[1]  # 成功的概率
            confidence = max(probabilities)  # 置信度（最大概率）
            
            return {
                'success_probability': float(success_probability),
                'prediction': int(prediction),
                'confidence': float(confidence)
            }
        except Exception as e:
            return {
                'error': f'预测失败: {str(e)}',
                'success_probability': 0.5,
                'prediction': 1,
                'confidence': 0.0
            }
    
    def save_model(self):
        """保存模型和编码器"""
        if not SKLEARN_AVAILABLE or self.model is None:
            return
        
        try:
            # 保存模型
            joblib.dump(self.model, self.model_file)
            
            # 保存编码器
            joblib.dump(self.label_encoders, self.encoders_file)
            
            # 保存元数据
            metadata = {
                'is_trained': self.is_trained,
                'feature_names': self.feature_names,
                'saved_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存模型失败: {e}", file=sys.stderr)
    
    def load_model(self) -> bool:
        """
        加载已保存的模型
        
        Returns:
            是否成功加载
        """
        if not SKLEARN_AVAILABLE:
            return False
        
        try:
            if not self.model_file.exists():
                return False
            
            # 加载模型
            self.model = joblib.load(self.model_file)
            
            # 加载编码器
            if self.encoders_file.exists():
                self.label_encoders = joblib.load(self.encoders_file)
            
            # 加载元数据
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    self.is_trained = metadata.get('is_trained', False)
                    self.feature_names = metadata.get('feature_names', [])
            
            return self.is_trained
        except Exception as e:
            print(f"加载模型失败: {e}", file=sys.stderr)
            return False



