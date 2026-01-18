#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABU价格行为特征学习模型

功能：
- 从Gemini分析结果学习价格行为特征
- 使用XGBoost模型预测价格行为类别（reversal/continuation/indecision）
- 支持首次训练和增量训练

数据源：
- pattern_library表的gemini_annotation_json字段
- 从Gemini分析结果提取特征（模式组合、K线行为、交易参数等）

模型：
- XGBoost分类器
- 输入：Gemini特征 + 模式特征
- 输出：价格行为类别（reversal/continuation/indecision/consolidation）

使用：
    # 首次训练（使用所有可用数据）
    python src/ml_dl/abu_price_action_learner.py --train

    # 增量训练（使用新数据）
    python src/ml_dl/abu_price_action_learner.py --retrain

    # 预测
    python src/ml_dl/abu_price_action_learner.py --predict
"""

from __future__ import annotations
import sys
import os
import json
import pickle
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / 'src'
MODELS_DIR = ROOT / 'models' / 'abu'
MODELS_DIR.mkdir(parents=True, exist_ok=True)

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from db_manager_trader import TraderDBManager

# 尝试导入ML库
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    print("警告: numpy未安装，某些功能可能受限", file=sys.stderr)

try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("警告: xgboost未安装，模型训练功能不可用", file=sys.stderr)
    print("请安装: pip install xgboost", file=sys.stderr)

try:
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
    from sklearn.preprocessing import LabelEncoder
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    LabelEncoder = None
    print("警告: scikit-learn未安装，模型评估功能可能受限", file=sys.stderr)

# 模型文件路径
MODEL_FILE = MODELS_DIR / 'price_action_model.pkl'
MODEL_STATE_FILE = MODELS_DIR / 'price_action_model_state.json'
TRAINING_DATA_FILE = MODELS_DIR / 'training_data_cache.json'


class PriceActionLearner:
    """价格行为特征学习器"""
    
    def __init__(self):
        self.model = None
        self.feature_names = []
        self.label_encoder = LabelEncoder() if LabelEncoder else None
        self.model_state = self._load_model_state()
    
    def _load_model_state(self) -> Dict:
        """加载模型状态"""
        if MODEL_STATE_FILE.exists():
            try:
                with MODEL_STATE_FILE.open('r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  加载模型状态失败: {e}", file=sys.stderr)
        
        return {
            'first_trained_at': None,
            'last_trained_at': None,
            'last_trained_samples': 0,
            'training_data_hash': None,
            'model_version': '1.0',
            'accuracy': 0.0,
            'feature_importance': {}
        }
    
    def _save_model_state(self):
        """保存模型状态"""
        try:
            with MODEL_STATE_FILE.open('w', encoding='utf-8') as f:
                json.dump(self.model_state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️  保存模型状态失败: {e}", file=sys.stderr)
    
    def load_model(self) -> bool:
        """加载已训练的模型"""
        if MODEL_FILE.exists():
            try:
                with MODEL_FILE.open('rb') as f:
                    model_data = pickle.load(f)
                    self.model = model_data['model']
                    self.feature_names = model_data.get('feature_names', [])
                    # 加载标签编码器（如果存在）
                    if 'label_encoder' in model_data:
                        self.label_encoder = model_data['label_encoder']
                    elif LabelEncoder:
                        # 如果旧模型没有label_encoder，创建一个（兼容性处理）
                        self.label_encoder = LabelEncoder()
                return True
            except Exception as e:
                print(f"⚠️  加载模型失败: {e}", file=sys.stderr)
        return False
    
    def save_model(self):
        """保存模型"""
        if self.model is None:
            return
        
        try:
            model_data = {
                'model': self.model,
                'feature_names': self.feature_names,
                'label_encoder': self.label_encoder,
                'trained_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'version': self.model_state.get('model_version', '1.0')
            }
            with MODEL_FILE.open('wb') as f:
                pickle.dump(model_data, f)
            
            self._save_model_state()
            print(f"✓ 模型已保存: {MODEL_FILE}")
        except Exception as e:
            print(f"⚠️  保存模型失败: {e}", file=sys.stderr)
    
    def extract_gemini_features(self, gemini_ann: Dict) -> Dict:
        """从Gemini分析结果提取特征"""
        if not gemini_ann:
            return {}
        
        # 确保是parsed格式（如果传入的是原始格式，尝试提取parsed字段）
        parsed = gemini_ann.get('parsed', gemini_ann) if isinstance(gemini_ann, dict) else {}
        
        patterns = parsed.get('patterns', [])
        price_action = parsed.get('price_action_behavior', {})
        trading_signals = parsed.get('trading_signals', [])
        market_conditions = parsed.get('market_conditions', {})
        
        # 模式类型统计
        pattern_types = [p.get('type', 'unknown') for p in patterns if isinstance(p, dict)]
        has_reversal = any(t == 'reversal' for t in pattern_types)
        has_continuation = any(t == 'continuation' for t in pattern_types)
        has_consolidation = any(t == 'consolidation' for t in pattern_types)
        
        # K线特征
        kline_features = price_action.get('kline_features', [])
        if isinstance(kline_features, str):
            kline_features = []
        elif not isinstance(kline_features, list):
            kline_features = []
        
        # 提取K线特征名称
        kline_feature_names = []
        if isinstance(kline_features, list):
            for feat in kline_features:
                if isinstance(feat, dict):
                    kline_feature_names.append(feat.get('feature', ''))
                elif isinstance(feat, str):
                    kline_feature_names.append(feat)
        
        has_engulfing = any('engulf' in str(f).lower() for f in kline_feature_names)
        has_pin_bar = any('pin' in str(f).lower() for f in kline_feature_names)
        has_inside_bar = any('inside' in str(f).lower() for f in kline_feature_names)
        
        # 交易信号特征
        signal_count = len(trading_signals) if isinstance(trading_signals, list) else 0
        avg_probability = 0.0
        avg_rr_ratio = 0.0
        
        if signal_count > 0 and isinstance(trading_signals, list):
            probs = []
            rrs = []
            for sig in trading_signals:
                if isinstance(sig, dict):
                    if 'probability' in sig:
                        try:
                            probs.append(float(sig['probability']))
                        except:
                            pass
                    if 'risk_reward_ratio' in sig:
                        try:
                            rrs.append(float(sig['risk_reward_ratio']))
                        except:
                            pass
            
            if probs and NUMPY_AVAILABLE:
                avg_probability = float(np.mean(probs))
            elif probs:
                avg_probability = sum(probs) / len(probs)
            
            if rrs and NUMPY_AVAILABLE:
                avg_rr_ratio = float(np.mean(rrs))
            elif rrs:
                avg_rr_ratio = sum(rrs) / len(rrs)
        
        # 趋势特征
        trend = price_action.get('trend', 'unknown')
        trend_strength = market_conditions.get('trend_strength', 'unknown')
        volatility = market_conditions.get('volatility', 'unknown')
        structure = price_action.get('structure', 'unknown')
        
        features = {
            # 模式特征
            'pattern_count': len(patterns),
            'has_reversal_pattern': 1 if has_reversal else 0,
            'has_continuation_pattern': 1 if has_continuation else 0,
            'has_consolidation_pattern': 1 if has_consolidation else 0,
            'pattern_combination_length': len(parsed.get('pattern_combination', '')),
            
            # K线特征
            'kline_feature_count': len(kline_feature_names),
            'has_engulfing': 1 if has_engulfing else 0,
            'has_pin_bar': 1 if has_pin_bar else 0,
            'has_inside_bar': 1 if has_inside_bar else 0,
            
            # 交易信号特征
            'signal_count': signal_count,
            'avg_probability': avg_probability,
            'avg_rr_ratio': avg_rr_ratio,
            
            # 趋势特征（编码为数值）
            'trend_bullish': 1 if 'bull' in str(trend).lower() else 0,
            'trend_bearish': 1 if 'bear' in str(trend).lower() else 0,
            'trend_neutral': 1 if 'neutral' in str(trend).lower() or 'unknown' in str(trend).lower() else 0,
            'trend_strength_strong': 1 if 'strong' in str(trend_strength).lower() else 0,
            'trend_strength_weak': 1 if 'weak' in str(trend_strength).lower() else 0,
            'volatility_high': 1 if 'high' in str(volatility).lower() else 0,
            'volatility_low': 1 if 'low' in str(volatility).lower() else 0,
            'structure_hh_hl': 1 if 'higher_highs' in str(structure).lower() else 0,
            'structure_lh_ll': 1 if 'lower_highs' in str(structure).lower() else 0,
            
            # 置信度
            'confidence': float(parsed.get('confidence', 0.0))
        }
        
        return features
    
    def infer_label_from_patterns(self, patterns: List[Dict]) -> str:
        """从模式类型推断价格行为标签"""
        if not patterns:
            return 'indecision'
        
        pattern_types = [p.get('type', '') for p in patterns if isinstance(p, dict)]
        
        # 优先级：reversal > continuation > consolidation > indecision
        if any(t == 'reversal' for t in pattern_types):
            return 'reversal'
        elif any(t == 'continuation' for t in pattern_types):
            return 'continuation'
        elif any(t == 'consolidation' for t in pattern_types):
            return 'consolidation'
        else:
            return 'indecision'
    
    def prepare_training_data(self, min_confidence: float = 0.0) -> Tuple[List[Dict], List[str]]:
        """准备训练数据"""
        db = TraderDBManager('abu')
        conn = db._get_connection()
        
        # 获取所有有Gemini标注的模式
        query = '''
            SELECT id, gemini_annotation_json, pattern_type
            FROM pattern_library
            WHERE gemini_annotation_json IS NOT NULL 
              AND gemini_annotation_json != ''
            ORDER BY id
        '''
        records = conn.execute(query).fetchall()
        
        X = []
        y = []
        metadata = []
        
        print(f"准备训练数据: 找到 {len(records)} 条记录")
        
        for pattern_id, gemini_json, pattern_type in records:
            try:
                gemini_ann = json.loads(gemini_json)
                
                # 提取特征
                features = self.extract_gemini_features(gemini_ann)
                
                # 跳过特征太少的记录
                if len(features) < 5:
                    continue
                
                # 提取标签（从模式类型推断）
                parsed = gemini_ann.get('parsed', gemini_ann) if isinstance(gemini_ann, dict) else gemini_ann
                patterns = parsed.get('patterns', [])
                label = self.infer_label_from_patterns(patterns)
                
                # 如果没有从模式推断出标签，使用pattern_type
                if label == 'indecision' and pattern_type:
                    if 'reversal' in pattern_type.lower():
                        label = 'reversal'
                    elif 'continuation' in pattern_type.lower():
                        label = 'continuation'
                    elif 'consolidation' in pattern_type.lower():
                        label = 'consolidation'
                
                # 过滤低置信度
                confidence = features.get('confidence', 0.0)
                if confidence < min_confidence:
                    continue
                
                X.append(features)
                y.append(label)
                metadata.append({
                    'pattern_id': pattern_id,
                    'pattern_type': pattern_type,
                    'label': label,
                    'confidence': confidence
                })
                
            except Exception as e:
                print(f"⚠️  处理模式 {pattern_id} 失败: {e}", file=sys.stderr)
                continue
        
        db.close()
        
        print(f"✓ 准备完成: {len(X)} 条有效训练样本")
        print(f"  标签分布: {dict(zip(*np.unique(y, return_counts=True))) if NUMPY_AVAILABLE else '统计中...'}")
        
        return X, y, metadata
    
    def features_to_vector(self, features: Dict) -> List[float]:
        """将特征字典转换为向量"""
        if not self.feature_names:
            # 首次使用，从特征字典提取特征名
            self.feature_names = sorted(features.keys())
        
        vector = []
        for name in self.feature_names:
            value = features.get(name, 0.0)
            if isinstance(value, (int, float)):
                vector.append(float(value))
            else:
                vector.append(0.0)
        
        return vector
    
    def train(self, retrain: bool = False, test_size: float = 0.2) -> Dict:
        """训练模型"""
        if not XGBOOST_AVAILABLE or not SKLEARN_AVAILABLE:
            return {
                'success': False,
                'error': '缺少必要的库（xgboost或scikit-learn）'
            }
        
        # 加载已有模型（如果是增量训练）
        if retrain and MODEL_FILE.exists():
            self.load_model()
        
        # 准备训练数据
        X_dicts, y, metadata = self.prepare_training_data()
        
        if len(X_dicts) < 10:
            return {
                'success': False,
                'error': f'训练数据太少（{len(X_dicts)}条），至少需要10条'
            }
        
        # 转换为向量
        if not self.feature_names:
            # 从第一个样本提取特征名
            self.feature_names = sorted(X_dicts[0].keys())
        
        X = [self.features_to_vector(f) for f in X_dicts]
        
        # 标签编码（将字符串标签转换为数字）
        if self.label_encoder is None and LabelEncoder:
            self.label_encoder = LabelEncoder()
        
        if self.label_encoder is not None:
            # 编码所有标签（包括训练集和测试集的所有可能标签）
            y_encoded = self.label_encoder.fit_transform(y)
            # 数据划分
            X_train, X_test, y_train, y_test = train_test_split(
                X, y_encoded, test_size=test_size, random_state=42, stratify=y_encoded
            )
        else:
            # 如果没有LabelEncoder，直接使用原始标签（可能在某些XGBoost版本中失败）
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42, stratify=y
            )
            y_test_original = y_test  # 保存原始标签用于报告
        
        print(f"\n训练集: {len(X_train)} 条")
        print(f"测试集: {len(X_test)} 条")
        
        # 训练模型
        if self.model is None or not retrain:
            # 首次训练
            print("\n开始首次训练...")
            self.model = XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42,
                eval_metric='mlogloss'
            )
        else:
            # 增量训练（使用warm_start）
            print("\n开始增量训练...")
            # XGBoost不支持真正的增量训练，所以重新训练整个数据集
            # 但可以使用之前的模型作为初始值（这里简化处理，重新训练）
            self.model = XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42,
                eval_metric='mlogloss'
            )
        
        self.model.fit(X_train, y_train)
        
        # 评估
        train_accuracy = self.model.score(X_train, y_train)
        test_accuracy = self.model.score(X_test, y_test)
        
        print(f"\n训练准确率: {train_accuracy:.4f}")
        print(f"测试准确率: {test_accuracy:.4f}")
        
        # 特征重要性
        feature_importance = {}
        if hasattr(self.model, 'feature_importances_'):
            for i, name in enumerate(self.feature_names):
                if i < len(self.model.feature_importances_):
                    feature_importance[name] = float(self.model.feature_importances_[i])
        
        # 分类报告
        y_pred_encoded = self.model.predict(X_test)
        # 将预测结果转换回原始标签
        if self.label_encoder is not None:
            y_pred = self.label_encoder.inverse_transform(y_pred_encoded)
            y_test_original = self.label_encoder.inverse_transform(y_test)
        else:
            y_pred = y_pred_encoded
            y_test_original = y_test
        
        if SKLEARN_AVAILABLE:
            print("\n分类报告:")
            print(classification_report(y_test_original, y_pred))
        
        # 更新状态
        is_first_training = self.model_state.get('first_trained_at') is None
        if is_first_training:
            self.model_state['first_trained_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        self.model_state['last_trained_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.model_state['last_trained_samples'] = len(X_dicts)
        self.model_state['accuracy'] = float(test_accuracy)
        self.model_state['feature_importance'] = feature_importance
        
        # 保存模型
        self.save_model()
        
        return {
            'success': True,
            'train_accuracy': float(train_accuracy),
            'test_accuracy': float(test_accuracy),
            'train_samples': len(X_train),
            'test_samples': len(X_test),
            'total_samples': len(X_dicts),
            'feature_importance': feature_importance,
            'is_first_training': is_first_training
        }
    
    def predict(self, gemini_annotation: Dict) -> Dict:
        """预测价格行为"""
        if self.model is None:
            if not self.load_model():
                return {
                    'success': False,
                    'error': '模型未训练或加载失败'
                }
        
        features = self.extract_gemini_features(gemini_annotation)
        X = [self.features_to_vector(features)]
        
        try:
            prediction_encoded = self.model.predict(X)[0]
            probabilities = self.model.predict_proba(X)[0]
            
            # 将预测结果转换回原始标签
            if self.label_encoder is not None:
                prediction = self.label_encoder.inverse_transform([prediction_encoded])[0]
                classes = self.label_encoder.classes_
            else:
                prediction = prediction_encoded
                classes = self.model.classes_
            
            prob_dict = {}
            for i, cls in enumerate(classes):
                prob_dict[str(cls)] = float(probabilities[i])
            
            return {
                'success': True,
                'price_action': str(prediction),
                'probabilities': prob_dict,
                'features': features
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_needs_retrain(self, current_count: int) -> bool:
        """检查是否需要重新训练"""
        last_count = self.model_state.get('last_trained_samples', 0)
        
        # 如果数据量增加了10%以上，建议重新训练
        if last_count == 0:
            return True  # 从未训练过
        
        increase_ratio = (current_count - last_count) / last_count if last_count > 0 else 0
        return increase_ratio >= 0.1  # 增长超过10%


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='ABU价格行为特征学习模型')
    parser.add_argument('--train', action='store_true', help='首次训练')
    parser.add_argument('--retrain', action='store_true', help='增量训练')
    parser.add_argument('--predict', action='store_true', help='预测（测试）')
    parser.add_argument('--check', action='store_true', help='检查是否需要重新训练')
    
    args = parser.parse_args()
    
    learner = PriceActionLearner()
    
    if args.check:
        # 检查是否需要重新训练
        db = TraderDBManager('abu')
        conn = db._get_connection()
        current_count = conn.execute('''
            SELECT COUNT(*) FROM pattern_library
            WHERE gemini_annotation_json IS NOT NULL AND gemini_annotation_json != ''
        ''').fetchone()[0]
        db.close()
        
        needs_retrain = learner.check_needs_retrain(current_count)
        print(f"当前数据量: {current_count}")
        print(f"上次训练数据量: {learner.model_state.get('last_trained_samples', 0)}")
        print(f"是否需要重新训练: {needs_retrain}")
        return 0
    
    if args.train:
        result = learner.train(retrain=False)
        if result.get('success'):
            print(f"\n✓ 训练完成")
            print(f"  测试准确率: {result['test_accuracy']:.4f}")
            print(f"  训练样本: {result['train_samples']}")
            print(f"  测试样本: {result['test_samples']}")
            return 0
        else:
            print(f"\n✗ 训练失败: {result.get('error')}")
            return 1
    
    if args.retrain:
        result = learner.train(retrain=True)
        if result.get('success'):
            print(f"\n✓ 增量训练完成")
            print(f"  测试准确率: {result['test_accuracy']:.4f}")
            print(f"  训练样本: {result['train_samples']}")
            print(f"  测试样本: {result['test_samples']}")
            return 0
        else:
            print(f"\n✗ 增量训练失败: {result.get('error')}")
            return 1
    
    if args.predict:
        # 测试预测功能
        print("预测功能需要提供Gemini分析结果（暂未实现测试）")
        return 0
    
    # 默认显示状态
    if MODEL_FILE.exists():
        learner.load_model()
        print("模型状态:")
        print(f"  首次训练: {learner.model_state.get('first_trained_at', 'N/A')}")
        print(f"  最后训练: {learner.model_state.get('last_trained_at', 'N/A')}")
        print(f"  训练样本数: {learner.model_state.get('last_trained_samples', 0)}")
        print(f"  准确率: {learner.model_state.get('accuracy', 0):.4f}")
    else:
        print("模型未训练，请先运行 --train")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

