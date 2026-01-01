# 机器学习功能集成说明

## 快速开始

### 1. 安装依赖

```bash
# 方法1：使用requirements文件
pip install -r requirements_ml.txt

# 方法2：手动安装
pip install scikit-learn pandas numpy joblib
```

### 2. 训练模型

```bash
# 在src目录下运行
cd src
python train_ml_model.py
```

### 3. 使用模型预测

模型训练完成后，会在生成新信号时自动使用（如果已集成）。

## 当前集成状态

✅ **已完成**:
- 机器学习预测模块 (`src/ml_signal_predictor.py`)
- 模型训练脚本 (`src/train_ml_model.py`)
- 集成到统一系统（已添加ML预测器初始化）

⏳ **待集成**:
- 在信号生成时自动使用ML评分（可选）
- 在报告中显示ML预测结果（可选）
- 自动定期重新训练模型（可选，已预留接口）

## 下一步集成建议

### 方案1：在信号生成时添加ML评分（推荐）

在 `src/generate_btc_de_signals.py` 中，生成信号后添加ML评分：

```python
# 在analyze_timeframe函数中，生成信号后
if self.ml_predictor and self.ml_predictor.is_trained:
    for signal in signals:
        prediction = self.ml_predictor.predict_signal_success(signal)
        signal['ml_score'] = prediction['success_probability']
        signal['ml_confidence'] = prediction['confidence']
```

### 方案2：在报告中显示ML评分

在生成交易计划时，显示ML预测结果：

```python
# 在报告中添加
if signal.get('ml_score'):
    plan.append(f"**ML预测成功率**: {signal['ml_score']:.1%} (置信度: {signal.get('ml_confidence', 0):.1%})")
```

### 方案3：使用ML评分筛选信号

只显示ML评分高于阈值的信号：

```python
# 筛选高质量信号
high_quality_signals = [s for s in signals if s.get('ml_score', 0) > 0.6]
```

## 手动训练模型

### 何时训练
- 首次使用：至少有10个已完成的信号
- 定期更新：每新增50-100个已完成信号后重新训练
- 模型性能下降时：如果发现预测不准，重新训练

### 训练命令

```bash
cd src
python train_ml_model.py
```

## 查看模型信息

模型保存在 `trading_signals/.ml_models/` 目录下：

- `signal_predictor_model.pkl`: 训练好的模型
- `label_encoders.pkl`: 特征编码器
- `model_metadata.json`: 模型元数据（训练时间、特征列表等）

## 使用示例

### Python代码中使用

```python
from src.ml_signal_predictor import MLSignalPredictor

# 初始化预测器（自动加载已有模型）
predictor = MLSignalPredictor()

# 预测信号
signal = {
    'system': 'de',
    'timeframe': '5分钟',
    'entry_model': 'FVG回填',
    'type': 'long',
    'entry': 87500,
    'stop_loss': 87000,
    'take_profit_1': 88000,
    'take_profit_2': 88500
}

result = predictor.predict_signal_success(signal)
print(f"成功概率: {result['success_probability']:.2%}")
```

## 注意事项

1. **首次使用**: 需要先有足够的历史数据（至少10个已完成信号）才能训练模型
2. **数据质量**: 数据越多、质量越高，模型预测越准确
3. **定期更新**: 建议定期重新训练模型，纳入新的数据
4. **特征工程**: 当前使用基础特征，未来可以根据实际情况添加更多特征

## 未来改进

- [ ] 添加更多特征（市场指标、时间特征等）
- [ ] 尝试不同的算法（XGBoost、LightGBM等）
- [ ] 自动特征选择
- [ ] 模型集成（Ensemble）
- [ ] 实时预测集成到信号生成流程

---

**创建时间**: 2025-12-28




