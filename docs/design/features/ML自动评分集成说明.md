# ML自动评分集成说明

## ✅ 已完成的功能

### 1. 信号生成时自动ML评分 ✅

**文件**: `src/generate_btc_de_signals.py`

**集成内容**:
- 在生成5分钟和15分钟信号后，自动使用ML模型预测成功率
- 将ML评分添加到信号字典中：
  - `ml_score`: 成功概率（0-1）
  - `ml_confidence`: 置信度
  - `ml_prediction`: 预测结果（1=成功，0=失败）

### 2. 报告中显示ML预测结果 ✅

在交易信号报告中显示：
- **ML预测成功率**: X% (预测: 成功/失败, 置信度: Y%)

### 3. 自动模型加载 ✅

- 系统启动时自动尝试加载ML模型
- 如果模型已训练，自动为信号添加评分
- 如果模型未训练，正常生成信号（不影响功能）

## 📊 使用效果

### 报告中的显示示例

```
**做多** (强)
入场: $87,500
止损: $87,000
止盈: $88,000 (50%) / $88,500 (50%)
**入场模型**: FVG回填
**入场原因**: 【FVG回填】上涨FVG做多机会，FVG区间(87450-87460)，价格可能回填到87450
**ML预测成功率**: 72.3% (预测: 成功, 置信度: 75.5%)
```

## 🔧 工作原理

### 1. 模型初始化

```python
# 在generate_trading_plan()函数开始时
ml_predictor = None
if ML_PREDICTOR_AVAILABLE:
    ml_predictor = MLSignalPredictor()  # 自动加载已训练的模型
```

### 2. 信号评分

```python
# 生成信号后，自动添加ML评分
if ml_predictor and ml_predictor.is_trained:
    ml_prediction = ml_predictor.predict_signal_success(signal)
    signal['ml_score'] = ml_prediction['success_probability']
    signal['ml_confidence'] = ml_prediction['confidence']
    signal['ml_prediction'] = ml_prediction['prediction']
```

### 3. 报告生成

```python
# 在报告中显示ML评分
if signal.get('ml_score') is not None:
    plan.append(f"**ML预测成功率**: {ml_score:.1%} (预测: {ml_pred}, 置信度: {ml_confidence:.1%})")
```

## 📋 使用步骤

### 1. 安装依赖（如果还没安装）

```bash
pip install -r requirements_ml.txt
```

### 2. 训练模型（需要至少10个已完成信号）

```bash
cd src
python train_ml_model.py
```

### 3. 运行系统

```bash
# 正常运行，系统会自动使用ML模型
python src/unified_trading_system.py --system all
```

### 4. 查看结果

生成的信号报告中会自动包含ML预测结果。

## ⚙️ 配置选项

### 可选：使用ML评分筛选信号

如果需要只显示ML评分高于阈值的信号，可以修改代码：

```python
# 在generate_trading_plan()中，筛选信号
if analysis_5m['signals']:
    # 使用ML评分筛选（例如只显示成功率>60%的信号）
    filtered_signals = [s for s in analysis_5m['signals'] 
                       if s.get('ml_score', 0.5) > 0.6]
    if filtered_signals:
        best_signal = max(filtered_signals, key=lambda x: x.get('ml_score', 0))
    else:
        # 如果没有高评分信号，使用原有逻辑
        best_signal = max(analysis_5m['signals'], key=lambda x: 3 if x['strength'] == 'strong' else 2 if x['strength'] == 'medium' else 1)
```

### 可选：按ML评分排序

```python
# 按ML评分排序信号
signals_sorted = sorted(analysis_5m['signals'], 
                       key=lambda x: x.get('ml_score', 0), 
                       reverse=True)
```

## 📈 模型性能监控

### 查看模型信息

模型元数据保存在 `trading_signals/.ml_models/model_metadata.json`：

```json
{
  "is_trained": true,
  "feature_names": [...],
  "saved_time": "2025-12-28 16:30:00"
}
```

### 重新训练模型

当有新的数据时，重新训练模型：

```bash
cd src
python train_ml_model.py
```

系统会自动使用新训练的模型。

## 🔍 故障排除

### ML评分未显示

可能原因：
1. ML模型未训练
   - 解决：运行 `python src/train_ml_model.py` 训练模型
2. scikit-learn未安装
   - 解决：`pip install scikit-learn pandas`
3. 数据不足（少于10个已完成信号）
   - 解决：等待更多信号完成后再训练

### ML预测失败

如果看到 "ML预测失败" 的警告：
- 检查模型文件是否完整
- 尝试重新训练模型
- 查看错误信息，可能是特征不匹配

## 💡 最佳实践

1. **定期重新训练**: 每新增50-100个已完成信号后重新训练模型
2. **监控准确率**: 关注模型训练时的准确率，如果过低可能需要调整特征
3. **结合其他指标**: ML评分是辅助工具，应该结合技术分析和市场环境判断
4. **逐步信任**: 随着数据积累，模型准确性会提高

## 🎯 未来改进

- [ ] 添加更多特征（市场指标、时间特征等）
- [ ] 实现自动定期重新训练
- [ ] 添加模型性能监控和报告
- [ ] 支持多个模型集成
- [ ] 根据ML评分调整仓位大小

---

**创建时间**: 2025-12-28  
**状态**: 已完成并集成 ✅




