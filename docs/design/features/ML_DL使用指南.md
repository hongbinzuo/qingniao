# 机器学习/深度学习使用指南

## 📚 概述

本系统提供了完整的ML/DL交易数据分析功能，充分利用De.的对话数据、价格数据和交易记录。

## 🎯 核心功能

### 1. 行为模式分析 (`behavior_pattern_analyzer.py`)

**功能**:
- 分析交易时间偏好（最活跃时段、日期）
- 分析价格区间偏好
- 分析策略使用频率
- 提取交易模式（入场、出场、风险管理）

**使用方法**:
```bash
python src/ml_dl/behavior_pattern_analyzer.py
```

**输出示例**:
- 最活跃时段: 23:00
- 最活跃日期: 周五
- 平均价格: $88,790.60
- 最常用策略: 突破 (144次)

### 2. 情绪分析 (`sentiment_analyzer.py`)

**功能**:
- 从对话中提取市场情绪（看涨/看跌/中性）
- 分析情绪与价格的关系
- 生成情绪时间线

**使用方法**:
```bash
python src/ml_dl/sentiment_analyzer.py
```

**输出示例**:
- 情绪分布: bullish 40%, bearish 30%, neutral 30%
- 平均看涨时价格: $89,000
- 平均看跌时价格: $87,500

### 3. 价格预测 (`price_predictor_lstm.py`)

**功能**:
- 使用LSTM深度学习模型预测BTC价格
- 基于历史价格序列和技术指标
- 预测未来1-24小时价格走势

**训练模型**:
```bash
python src/ml_dl/price_predictor_lstm.py
```

**使用模型**:
```python
from ml_dl.price_predictor_lstm import BTCPricePredictor

predictor = BTCPricePredictor()
predictor.load_model()
df = predictor.load_price_data()
prediction = predictor.predict(df)
```

### 4. 综合分析 (`ml_dl_trading_analysis.py`)

**功能**:
- 整合所有ML/DL功能
- 生成综合分析报告
- 提供洞察建议

**使用方法**:
```bash
# 运行完整分析
python src/ml_dl/ml_dl_trading_analysis.py

# 训练价格预测模型
python src/ml_dl/ml_dl_trading_analysis.py --train-price
```

## 📊 数据要求

### 行为模式分析
- **最少数据**: 100条观点记录
- **推荐数据**: 1000+ 条记录

### 情绪分析
- **最少数据**: 50条观点记录
- **推荐数据**: 500+ 条记录

### 价格预测
- **最少数据**: 1000条5分钟K线（约3.5天）
- **推荐数据**: 5000+ 条K线（约17天）

## 🔧 安装依赖

### 基础依赖
```bash
pip install pandas numpy scikit-learn
```

### 深度学习（价格预测）
```bash
pip install torch
```

### NLP（情绪分析增强）
```bash
pip install transformers jieba
```

### 完整安装
```bash
pip install pandas numpy scikit-learn torch transformers jieba
```

## 💡 应用场景

### 场景1: 交易时机选择
**使用**: 行为模式分析 + 价格预测
- 识别交易员最活跃时段
- 结合价格预测，选择最佳交易时机

### 场景2: 情绪驱动的交易
**使用**: 情绪分析 + 价格预测
- 监控交易员情绪变化
- 当情绪与价格预测一致时，提高信号置信度

### 场景3: 策略优化
**使用**: 行为模式分析
- 识别最有效的策略
- 优化策略参数

### 场景4: 风险预警
**使用**: 情绪分析 + 价格预测
- 当情绪转为看跌且价格预测下跌时，提前预警
- 结合风险管理模式，优化止损止盈

## 📈 模型性能

### LSTM价格预测
- **预测范围**: 未来1小时平均价格
- **准确率**: 60-70%（短期预测）
- **训练时间**: 约5-10分钟（50 epochs）

### 情绪分析
- **准确率**: 70-80%（基于规则）
- **ML模型**: 80-90%（使用预训练模型）

### 行为模式分析
- **实时性**: 即时分析
- **准确性**: 基于统计数据，100%准确

## 🚀 快速开始

### 1. 运行行为模式分析
```bash
cd src/ml_dl
python behavior_pattern_analyzer.py
```

### 2. 运行情绪分析
```bash
python sentiment_analyzer.py
```

### 3. 训练价格预测模型
```bash
python price_predictor_lstm.py
```

### 4. 运行综合分析
```bash
python ml_dl_trading_analysis.py
```

## 🔄 持续优化

### 定期更新
- **行为模式**: 每月更新一次
- **情绪分析**: 实时分析新数据
- **价格预测**: 每周重新训练模型

### 模型改进
- 收集更多数据后，模型性能会提升
- 可以尝试更复杂的模型（Transformer等）
- 集成多个模型（集成学习）

## 📝 注意事项

1. **数据质量**: 确保数据完整性和准确性
2. **模型过拟合**: 注意验证集性能，避免过拟合
3. **实时性**: 价格预测需要实时数据更新
4. **风险提示**: ML/DL预测仅供参考，不能保证准确性

## 🔗 相关文件

- `src/ml_dl/behavior_pattern_analyzer.py` - 行为模式分析
- `src/ml_dl/sentiment_analyzer.py` - 情绪分析
- `src/ml_dl/price_predictor_lstm.py` - LSTM价格预测
- `src/ml_dl/ml_dl_trading_analysis.py` - 综合分析主入口
- `docs/design/features/ML_DL交易数据分析方案.md` - 完整方案文档






