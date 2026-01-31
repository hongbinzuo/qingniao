# ABU 机器学习和深度学习完整执行方案

## 📊 方案概述

基于ABU最新流程（模式库 + 实时匹配），设计机器学习和深度学习方案，提升模式匹配准确率和交易信号质量。

**范围**: 仅限ABU系统，不包含Dream系统

---

## 🔄 ABU ML/DL 完整主流程图

### 整体架构流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ABU ML/DL 完整流程                                │
└─────────────────────────────────────────────────────────────────────────┘

【阶段0: Gemini Vision API完整分析】✅ **已完成**
┌─────────────────────────────────────────────────────────────────────┐
│ 0.1 图片准备 ✅                                                      │
│   └─ data/abu/images/*.png (1000张图片)                             │
│   └─ pattern_library表 (1004条记录)                                 │
└─────────────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 0.2 Gemini Vision API分析 ✅ (abu_optimize_speed.py)                │
│   ├─ 增强Prompt: 提取多模式组合、K线行为、交易参数                   │
│   ├─ 批量分析: 1000张图片 ✅                                         │
│   │   ├─ 模型: google/gemini-2.5-flash-image (OpenRouter)          │
│   │   ├─ 成本: $7.97 (实际花费)                                     │
│   │   ├─ 耗时: 约21.6小时（运行3小时，休息1小时机制）                │
│   │   └─ 成功率: 95.3% (953/1000)                                   │
│   ├─ 输出: outputs/abu_gemini_annotations_enhanced.jsonl ✅         │
│   └─ 内容: patterns[], pattern_combination, trading_signals[], etc. │
└─────────────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 0.3 智能解析Gemini输出 ✅ (abu_parse_gemini_output.py)              │
│   ├─ 解析非结构化JSON                                                │
│   ├─ 提取: 多模式组合、交易参数（概率、入场、止损、止盈）            │
│   ├─ 补全: 缺失字段、标准化格式                                       │
│   └─ 输出: 标准化的结构化数据                                        │
└─────────────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 0.4 更新模式库数据 ✅ (abu_update_pattern_library_from_gemini.py)   │
│   ├─ 读取Gemini分析结果                                              │
│   ├─ 匹配pattern_library记录（通过image_path）                       │
│   ├─ 更新gemini_annotation_json字段 ✅                               │
│   ├─ 更新pattern_type（支持多模式组合）✅                            │
│   ├─ 更新key_features（K线行为特征）✅                               │
│   └─ 更新trading_signals（交易参数）✅                               │
│   └─ 结果: 953条记录已更新，613条包含完整字段                       │
└─────────────────────────────────────────────────────────────────────┘
                    ↓
【阶段1: 数据准备与收集（增强版）】✅ **部分完成**
┌─────────────────────────────────────────────────────────────────────┐
│ 1.1 模式库准备 ✅ (增强后)                                           │
│   └─ pattern_library (1,004条，已包含Gemini分析) ✅                 │
│      ├─ gemini_annotation_json: 包含多模式组合、交易参数 ✅          │
│      │   └─ 613条包含完整字段（chart_overview, complete_price_path, complete_narrative）
│      ├─ pattern_combination: "W底 + 三角形 + 突破" ✅               │
│      ├─ trading_signals: [{direction, probability, entry, sl, tp}] ✅│
│      └─ price_action_behavior: {kline_features, trend, structure} ✅ │
│      └─ 电子书关联: 32个模式已关联电子书知识 ✅                      │
└─────────────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 1.2 信号生成流程 ✅ (增强版: abu_gemini_signal_scanner_enhanced.py) │
│   ├─ 扫描TOP 20-300币种 (BTC, ETH, SOL等) ✅                        │
│   ├─ 获取K线数据 (5m/15m/1h/4h) ✅                                   │
│   ├─ 模式检测 ✅                                                      │
│   │   ├─ Gemini模式匹配 ✅                                            │
│   │   │   ├─ 查找相似的Gemini模式（基于pattern_combination）✅       │
│   │   │   ├─ 提取Gemini识别的交易参数（概率、入场、止损、止盈）✅    │
│   │   │   ├─ 匹配K线行为特征 ✅                                       │
│   │   │   └─ 电子书知识验证 ✅（可选，置信度加成最多+0.3）           │
│   │   ├─ TA-Lib验证 ✅（可选）                                        │
│   │   └─ Al Brooks特殊模式检测 ✅（可选）                             │
│   │   └─ 价格行为学习预测 ⚠️（待实施，ML模型训练）                   │
│   ├─ 评分排序 ✅                                                      │
│   │   ├─ 规则评分 (RR + trend + pattern_bonus) ✅                    │
│   │   ├─ Gemini概率加权 ✅                                            │
│   │   │   └─ 如果Gemini识别了概率，作为额外权重 ✅                   │
│   │   ├─ 电子书验证加成 ✅（最多+0.3置信度）                         │
│   │   └─ ML评分提升 ⚠️（待实施，ML模型训练）                         │
│   └─ 输出Top N信号 ✅ → trading_signals表 + Markdown文件             │
│       └─ 信号中包含: pattern_combination, gemini_probability等 ✅    │
└─────────────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 1.3 记录匹配历史 (新增: abu_record_match_history.py)                 │
│   ├─ 从每个生成的信号提取:                                            │
│   │   ├─ pattern_type (模式类型)                                     │
│   │   ├─ pattern_id (关联pattern_library)                            │
│   │   ├─ entry_price, stop_loss, take_profit_1/2                    │
│   │   ├─ direction (long/short)                                      │
│   │   └─ symbol, timeframe                                           │
│   ├─ 提取市场特征:                                                    │
│   │   ├─ trend_backing (EMA200趋势)                                  │
│   │   ├─ volatility (波动率)                                         │
│   │   ├─ volume_ratio (成交量比)                                     │
│   │   ├─ rsi (RSI指标)                                               │
│   │   └─ market_state (bull/bear/neutral)                            │
│   ├─ 保存K线上下文 (klines_context_json)                              │
│   └─ 写入 pattern_match_history 表 (status='pending')                │
└─────────────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 1.4 信号评估 (新增: abu_evaluate_signals.py)                         │
│   ├─ 读取待评估信号 (status='pending')                                │
│   ├─ 获取历史K线数据 (匹配后288小时窗口)                              │
│   ├─ 判断结果:                                                        │
│   │   ├─ TP命中: take_profit_1/2 触发 → result='tp'                 │
│   │   ├─ SL命中: stop_loss 触发 → result='sl'                       │
│   │   └─ 未命中: 窗口内未触发 → result='none'                        │
│   ├─ 计算: profit_pct, hit_time                                      │
│   ├─ 更新 pattern_match_history (match_result, hit_time, profit_pct) │
│   └─ 创建 signal_evaluations 记录                                    │
└─────────────────────────────────────────────────────────────────────┘
                    ↓
【阶段2: ML模型训练（增强版）】
┌─────────────────────────────────────────────────────────────────────┐
│ 2.0 价格行为特征学习模型 (abu_price_action_learner.py) ⭐ 新增      │
│   ├─ 数据准备:                                                        │
│   │   ├─ 从gemini_annotation_json提取特征                            │
│   │   │   ├─ 模式组合特征 (pattern_count, combination)              │
│   │   │   ├─ K线行为特征 (engulfing, pin_bar, inside_bar)          │
│   │   │   ├─ 交易参数特征 (probability, risk_reward_ratio)          │
│   │   │   └─ 市场条件特征 (trend_strength, volatility)              │
│   │   ├─ 从实际K线数据提取特征                                        │
│   │   │   ├─ actual_trend, actual_volatility                        │
│   │   │   └─ price_action_match_score                                │
│   │   └─ 标签: 价格行为类别 (reversal/continuation/indecision)       │
│   ├─ 模型训练:                                                        │
│   │   ├─ 特征工程: 组合Gemini特征 + K线特征                          │
│   │   ├─ 模型: XGBoost分类器（预测价格行为）                         │
│   │   ├─ 输出: 价格行为类别 + 概率                                   │
│   │   └─ 评估: 准确率、混淆矩阵                                       │
│   ├─ 应用:                                                            │
│   │   ├─ 在信号检测时，匹配相似的Gemini模式                          │
│   │   ├─ 使用价格行为学习模型预测当前K线的行为                        │
│   │   └─ 结合Gemini识别的交易参数（概率、入场、止损、止盈）          │
│   └─ 模型保存: abu_price_action_model.pkl                            │
└─────────────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 2.1 模式匹配成功率预测模型 (abu_pattern_match_predictor.py) 增强    │
│   ├─ 数据准备:                                                        │
│   │   ├─ 从 pattern_match_history 读取训练数据                       │
│   │   ├─ 特征提取:                                                    │
│   │   │   ├─ 模式特征: pattern_type, pattern_confidence             │
│   │   │   ├─ 市场特征: trend, volatility, volume, rsi              │
│   │   │   └─ 交易特征: entry, sl, tp, rr_ratio                      │
│   │   └─ 标签: success (1=TP, 0=SL/None)                            │
│   ├─ 模型训练:                                                        │
│   │   ├─ 数据划分: train/test (80/20)                                │
│   │   ├─ 基线模型: Random Forest                                     │
│   │   ├─ 提升模型: XGBoost / LightGBM                                │
│   │   └─ 深度学习: LSTM / Transformer (可选)                         │
│   ├─ 模型评估:                                                        │
│   │   ├─ accuracy, precision, recall, F1                            │
│   │   ├─ ROC-AUC                                                    │
│   │   └─ 特征重要性分析                                               │
│   └─ 模型保存: .pkl文件 → trading_signals/.ml_models/                │
└─────────────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 2.2 候选信号评分模型 (abu_candidate_scorer.py)                       │
│   ├─ 数据准备:                                                        │
│   │   ├─ 从 pattern_match_history 构建训练样本                       │
│   │   ├─ 特征: 候选信号的所有特征 + 市场上下文                         │
│   │   └─ 标签: 实际表现分数 (基于profit_pct归一化)                    │
│   ├─ 模型训练:                                                        │
│   │   ├─ LightGBM Regressor (回归任务，输出评分)                     │
│   │   └─ 目标: 预测信号的最终表现分数                                 │
│   └─ 模型保存: candidate_scorer.pkl                                  │
└─────────────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 2.3 模式权重优化器 (abu_pattern_weight_optimizer.py)                 │
│   ├─ 数据准备:                                                        │
│   │   ├─ 统计各模式的历史胜率                                         │
│   │   ├─ 计算: win_rate, avg_profit, sharpe_ratio                   │
│   │   └─ 当前权重: config/abu_pattern_weights.yaml                   │
│   ├─ 优化算法:                                                        │
│   │   ├─ 方法1: 多臂老虎机 (Thompson Sampling)                       │
│   │   ├─ 方法2: 强化学习 (Q-Learning)                                │
│   │   └─ 方法3: 遗传算法 (Genetic Algorithm)                         │
│   ├─ 优化目标:                                                        │
│   │   ├─ 最大化: 组合信号胜率                                         │
│   │   ├─ 最大化: 平均盈亏比                                           │
│   │   └─ 最大化: Sharpe比率                                           │
│   └─ 输出: 更新的 abu_pattern_weights.yaml                           │
└─────────────────────────────────────────────────────────────────────┘
                    ↓
【阶段3: ML模型集成与使用】
┌─────────────────────────────────────────────────────────────────────┐
│ 3.1 增强信号生成流程 (pa_scan_15m_top10.py 增强版)                   │
│   ├─ 模式检测 (不变)                                                  │
│   ├─ ML预测成功率 (新增)                                              │
│   │   ├─ 加载模式匹配预测模型                                         │
│   │   ├─ 对每个候选信号预测成功率                                     │
│   │   └─ candidate['ml_success_prob'] = predictor.predict(...)      │
│   ├─ ML评分 (新增，可选)                                              │
│   │   ├─ 如果ML评分器可用，使用ML评分替代规则评分                     │
│   │   ├─ 否则，结合规则评分和ML预测概率                               │
│   │   └─ final_score = combine(rule_score, ml_prob)                 │
│   ├─ 评分排序 (增强)                                                  │
│   │   └─ 考虑ML预测概率调整排序                                       │
│   └─ 输出Top10信号 (已包含ML预测信息)                                 │
└─────────────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 3.2 自动记录匹配历史 (集成到信号生成流程)                             │
│   ├─ 生成信号后自动调用 record_match_history()                       │
│   ├─ 提取匹配信息并保存到 pattern_match_history                      │
│   └─ 异步触发评估任务 (如启用)                                        │
└─────────────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 3.3 定期模型重训练 (abu_retrain_ml_models.py)                        │
│   ├─ 每周/每月自动触发                                                │
│   ├─ 使用最新数据重新训练模型                                         │
│   ├─ A/B测试: 对比新旧模型性能                                       │
│   ├─ 如果新模型更好: 替换旧模型                                       │
│   └─ 否则: 保留旧模型                                                 │
└─────────────────────────────────────────────────────────────────────┘
                    ↓
【阶段4: 持续优化与监控】
┌─────────────────────────────────────────────────────────────────────┐
│ 4.1 模型性能监控 (abu_ml_model_evaluation.py)                        │
│   ├─ 监控指标:                                                        │
│   │   ├─ 预测准确率 (实际TP率 vs 预测概率)                            │
│   │   ├─ 信号质量 (Top10信号的实际胜率)                               │
│   │   ├─ 盈亏比改善 (对比规则评分)                                    │
│   │   └─ 模型漂移检测                                                 │
│   ├─ 生成报告:                                                        │
│   │   └─ outputs/abu/ml_model_performance_*.md                       │
│   └─ 告警: 如果性能下降 > 10%                                         │
└─────────────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 4.2 模式权重自动更新 (定时任务)                                       │
│   ├─ 每月运行权重优化器                                               │
│   ├─ 基于最近3个月数据优化权重                                        │
│   ├─ 更新 config/abu_pattern_weights.yaml                            │
│   └─ 无需重启服务，下次加载自动生效                                   │
└─────────────────────────────────────────────────────────────────────┘
```

### 详细数据流

```
【信号生成时的数据流】
┌──────────────────────────────────────────────────────────────┐
│ K线数据获取                                                   │
│   ├─ 15m K线 (200根) → 模式检测                              │
│   └─ 1h K线 (300根) → 趋势分析                               │
└──────────────────────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────────────────┐
│ 模式检测 (detectors.py)                                       │
│   ├─ 输入: 15m K线数据                                        │
│   ├─ 输出: candidates[] 候选信号列表                          │
│   │   └─ {pattern, type, entry, sl, tp1, tp2, reason, score_hint} │
│   └─ 模式类型: InsideBar, Engulfing, PinBar, KeyLevel        │
└──────────────────────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────────────────┐
│ ML预测成功率 (可选，如果模型可用)                              │
│   ├─ 加载模型: abu_pattern_match_predictor.pkl                │
│   ├─ 提取特征:                                                 │
│   │   ├─ pattern_type, pattern_confidence                    │
│   │   ├─ trend, volatility, volume, rsi                      │
│   │   └─ entry, sl, tp, rr_ratio                            │
│   ├─ 预测: success_probability                               │
│   └─ 添加: candidate['ml_success_prob'] = prob               │
└──────────────────────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────────────────┐
│ 评分排序 (ranker.py，增强版)                                  │
│   ├─ 规则评分 (现有):                                          │
│   │   ├─ base_score (score_hint)                             │
│   │   ├─ rr_score (盈亏比，权重0.6)                           │
│   │   ├─ trend_backing (趋势共振，权重0.6)                     │
│   │   └─ pattern_bonus (模式权重，从YAML加载)                  │
│   ├─ ML评分 (可选):                                           │
│   │   └─ 如果ML评分器可用，使用ML评分                          │
│   ├─ 综合评分:                                                │
│   │   └─ final_score = combine(rule_score, ml_prob)          │
│   └─ 排序: 按final_score降序                                   │
└──────────────────────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────────────────┐
│ 输出Top10信号                                                 │
│   ├─ 写入数据库: trading_signals表                            │
│   ├─ 生成Markdown: ABU_top10_15m_*.md                         │
│   └─ 自动记录: pattern_match_history表 (新增)                  │
│       ├─ pattern_id, pattern_type                             │
│       ├─ entry_price, sl, tp1, tp2                           │
│       ├─ direction, symbol, timeframe                         │
│       ├─ klines_context_json                                  │
│       ├─ market_features_json                                 │
│       └─ match_result='pending'                               │
└──────────────────────────────────────────────────────────────┘
```

### 关键决策点

```
【是否使用ML模型？】
                    ↓
        ┌───────────┴───────────┐
        │ 模型文件是否存在？      │
        └───────────┬───────────┘
                    ↓
        ┌───────────┴───────────┐
     YES │                   NO │
        ↓                       ↓
┌──────────────┐      ┌──────────────────┐
│ 使用ML评分   │      │ 使用规则评分      │
│ - 加载模型   │      │ - 回退到原逻辑    │
│ - 预测概率   │      │ - 不破坏现有流程  │
│ - 增强评分   │      └──────────────────┘
└──────────────┘
```

```
【模式权重优化策略】
                    ↓
        ┌───────────┴───────────┐
        │ 是否启用自动优化？      │
        └───────────┬───────────┘
                    ↓
        ┌───────────┴───────────┐
     YES │                   NO │
        ↓                       ↓
┌──────────────┐      ┌──────────────────┐
│ 每月优化     │      │ 手动优化          │
│ - 读取历史   │      │ - 人工分析        │
│ - 计算权重   │      │ - 更新YAML        │
│ - 更新YAML   │      └──────────────────┘
└──────────────┘
```

---

## 🔄 现有ABU流程梳理

### 1. ABU模式库流程（增强版）

```
PDF提取 → 图片提取 → Gemini Vision分析 → 智能解析 → 模式库(数据库) → 价格行为学习 → 实时检测器 → ML增强评分 → 交易信号
    ↓         ↓            ↓              ↓            ↓              ↓              ↓            ↓           ↓
PyMuPDF  1000张图片   Gemini Vision API  解析器    pattern_library  特征学习模型   detectors.py  ML评分器   top10信号
```

**重要说明**：
- **每页PDF包含复杂信息**：不只是单一模式，而是多模式组合（W底+三角形+其他）+ K线走势 + 交易参数
- **Gemini需要识别**：模式组合、K线行为、概率、入场/止损/止盈点、市场条件等
- **需要智能解析**：将Gemini的非结构化输出转换为结构化数据
- **需要机器学习**：从Gemini识别的内容中学习价格行为特征，而不仅仅是模式匹配

**核心组件**:
- **模式库**: `src/data/qingniao_abu.duckdb` (表: `pattern_library`)
  - ✅ **当前状态**: 1,004条记录，Gemini分析已完成（953条成功）
  - ✅ **完成状态**: 已通过Gemini Vision API分析1,000张图片，提取结构化信息
  - ✅ **数据质量**: 613条包含完整字段（chart_overview, complete_price_path, complete_narrative）
  
- **实时检测器** (`src/abu/detectors.py`):
  - `detect_inside_bar()` - 内包线检测
  - `detect_engulfing()` - 吞没形态检测
  - `detect_pin_bar()` - 影线形态检测
  - `detect_key_levels()` - 关键位检测
  
- **评分排序器** (`src/abu/ranker.py`):
  - `score_candidate()` - 基于规则评分
    - base_score (0.6权重)
    - RR_score (0.6权重)
    - trend_backing (0.6权重)
    - pattern_bonus (从config/abu_pattern_weights.yaml加载)
  - `rank_and_pick()` - 排序并选择top10

**输出**: `trading_signals/ABU_top*.md` - Top10交易信号文件

### 2. ABU信号生成流程

```
实时K线获取 → 模式检测 → 评分排序 → Top10信号 → 数据库存储
    ↓            ↓           ↓           ↓            ↓
多币种扫描  detectors.py  ranker.py   Markdown    trading_signals
```

**核心组件**:
- **信号生成** (`scripts/pa_scan_15m_top10.py`):
  - 扫描TOP30币种（BTC, ETH, SOL等）
  - 获取15m和1h K线数据
  - 调用 `detect_all_15m()` 检测模式
  - 使用 `rank_and_pick()` 评分排序
  - 输出Top10信号到Markdown文件
  
- **价格评估** (未来扩展):
  - 评估历史信号的实际表现
  - 判断: tp_hit, sl_hit, profit_pct
  - 更新 `signal_evaluations` 表

**输出**: 
- `trading_signals/ABU_top*.md` - Top10信号文件
- 数据库: `trading_signals` 表 (system_name='abu')
- 评估: `signal_evaluations` 表 (待实施)

## 🔍 关键环节：Gemini Vision API 完整分析流程

### 步骤0: Gemini Vision API 分析1000张图片 ✅ **已完成**

**完成状态**：
- ✅ 图片数量: 1000张（`data/abu/images/*.png`）
- ✅ 分析完成: 953张成功（95.3%成功率）
- ✅ 可用数据: 957张（91.4%可用率）
- ✅ 数据库状态: pattern_library表已更新，953条记录包含`gemini_annotation_json`
- ✅ 完整字段: 613条记录包含完整字段（chart_overview, complete_price_path, complete_narrative）
- ✅ 成本: $7.97（实际花费，平均$0.008/张）

**完成时间**: 2026-01-11（阶段0已完成，无需重复执行）

#### 0.1 增强的Gemini Prompt设计

**现有Prompt问题**：
- 只提取单一模式名称
- 缺少多模式组合识别
- 缺少交易参数提取（概率、入场、止损、止盈）
- 缺少K线行为特征

**增强后的Prompt**（更新 `scripts/abu/abu_gemini_annotate.py`）:

```python
ENHANCED_PROMPT = """
You are an expert price-action trading analyst. Analyze this chart image and extract ALL relevant trading information in structured JSON format.

IMPORTANT: Each page may contain:
- Multiple pattern combinations (e.g., "W底 + 三角形 + 突破")
- K-line price action behavior (trends, reversals, continuations)
- Trading signals with probabilities, entry/stop/profit levels
- Market conditions and context

Extract the following structure:
{
  "patterns": [
    {
      "name": "W底",  // 或 "Head and Shoulders", "Triangle", "Engulfing" 等
      "type": "reversal",  // reversal/continuation/indecision
      "location": "bottom",  // top/bottom/middle
      "confidence": 0.85
    },
    {
      "name": "Triangle",
      "type": "continuation",
      "location": "middle",
      "confidence": 0.75
    }
  ],
  "pattern_combination": "W底 + 三角形 + 突破",  // 整体组合描述
  "price_action_behavior": {
    "trend": "bullish",  // bullish/bearish/neutral
    "structure": "higher_lows",  // higher_lows/lower_highs/consolidation
    "kline_features": ["engulfing", "pin_bar", "inside_bar"],  // K线特征列表
    "volume_behavior": "increasing"  // increasing/decreasing/stable
  },
  "trading_signals": [
    {
      "direction": "long",  // long/short
      "entry_condition": "回调到W底颈线附近",  // 入场条件描述
      "entry_price_hint": "87,500",  // 如果图表标注了价格
      "stop_loss_hint": "87,000",  // 止损价格
      "take_profit_1_hint": "88,500",  // 第一止盈
      "take_profit_2_hint": "89,000",  // 第二止盈
      "probability": 75,  // 成功率百分比（如 "75% chance"）
      "target": "test_of_high_of_day",  // test_of_high_of_day/test_of_low_of_day/fibonacci_level等
      "risk_reward_ratio": 2.5,  // 盈亏比（如果可计算）
      "timeframe_hint": "15m"  // 时间框架提示
    }
  ],
  "market_conditions": {
    "context": "small PB bull trend",  // 市场环境描述
    "trend_strength": "strong",  // strong/moderate/weak
    "volatility": "low",  // high/medium/low
    "key_levels": ["87,500", "88,000", "89,000"]  // 关键价位
  },
  "annotations": [
    {
      "label": "A",  // 图表标注（A/B/C等）
      "description": "W底左底",
      "price": 86500
    },
    {
      "label": "Entry",
      "description": "入场点：回调到颈线",
      "price": 87500
    }
  ],
  "text_notes": [
    "20-Gap bar buy in small PB bull trend so 75% chance of test of high of day",
    "三角形突破后目标位89,000"
  ],
  "confidence": 0.90
}

CRITICAL REQUIREMENTS:
1. Identify ALL patterns visible, not just one
2. Extract ALL trading signals with entry/stop/profit if mentioned
3. Capture probability percentages if stated (e.g., "75% chance")
4. Extract K-line behavior features (engulfing, pin bar, inside bar, etc.)
5. Note pattern combinations and their relationships
6. Extract market context descriptions
7. Identify key price levels marked on the chart
8. Be precise with price levels if visible on the chart

Respond with ONLY valid JSON, no additional text.
"""
```

#### 0.2 Gemini分析执行流程

**脚本**: `scripts/abu/abu_gemini_annotate_enhanced.py` (新建，增强版)

```bash
# 完整分析1000张图片
python scripts/abu/abu_gemini_annotate_enhanced.py \
    --model gemini-1.5-pro \
    --limit 0 \  # 0表示处理所有图片
    --context-window 2 \
    --sleep-ms 1000 \  # API限流，每张图片间隔1秒
    --output outputs/abu_gemini_annotations_enhanced.jsonl

# 分批处理（推荐，避免长时间运行中断）
# 第一批：1-300
python scripts/abu/abu_gemini_annotate_enhanced.py --start-idx 0 --end-idx 300

# 第二批：301-600
python scripts/abu/abu_gemini_annotate_enhanced.py --start-idx 300 --end-idx 600

# 第三批：601-1000
python scripts/abu/abu_gemini_annotate_enhanced.py --start-idx 600 --end-idx 1000
```

**成本估算**:
- Gemini 1.5 Pro: 约 $0.0025/张图片
- 1000张图片: 约 $2.5 USD
- Gemini 1.5 Flash: 约 $0.000125/张图片（更快更便宜）
- 1000张图片: 约 $0.125 USD（推荐使用Flash）

**输出**: `outputs/abu_gemini_annotations_enhanced.jsonl`
- 每行一个JSON对象，包含图片路径和Gemini分析结果

#### 0.3 智能解析Gemini输出

**问题**: Gemini返回的JSON可能不完整、格式不一致，需要智能解析和补全

**实现**: `scripts/abu/abu_parse_gemini_output.py` (新建)

```python
class GeminiOutputParser:
    """智能解析Gemini Vision API输出"""
    
    def parse_gemini_result(self, gemini_output: Dict) -> Dict:
        """解析Gemini输出，补全缺失字段"""
        result = {
            'patterns': [],
            'pattern_combination': '',
            'price_action_behavior': {},
            'trading_signals': [],
            'market_conditions': {},
            'annotations': [],
            'text_notes': [],
            'confidence': 0.0
        }
        
        # 1. 解析patterns（支持多模式）
        if isinstance(gemini_output.get('patterns'), list):
            result['patterns'] = gemini_output['patterns']
        elif gemini_output.get('pattern'):
            # 单一模式，转换为列表
            result['patterns'] = [{
                'name': gemini_output['pattern'],
                'type': self._infer_pattern_type(gemini_output['pattern']),
                'confidence': gemini_output.get('confidence', 0.5)
            }]
        
        # 2. 提取pattern_combination
        if gemini_output.get('pattern_combination'):
            result['pattern_combination'] = gemini_output['pattern_combination']
        else:
            # 从patterns列表推断组合
            pattern_names = [p['name'] for p in result['patterns']]
            if len(pattern_names) > 1:
                result['pattern_combination'] = ' + '.join(pattern_names)
        
        # 3. 解析trading_signals（提取交易参数）
        if isinstance(gemini_output.get('trading_signals'), list):
            result['trading_signals'] = gemini_output['trading_signals']
        else:
            # 从单一字段推断
            signal = self._extract_signal_from_text(gemini_output)
            if signal:
                result['trading_signals'] = [signal]
        
        # 4. 从text_notes提取额外信息
        text_notes = gemini_output.get('text_notes', [])
        if isinstance(text_notes, str):
            text_notes = [text_notes]
        
        # 从文本中提取概率、价格等
        for note in text_notes:
            extracted = self._parse_trading_note(note)
            if extracted:
                # 合并到trading_signals
                result['trading_signals'].append(extracted)
        
        # 5. 解析price_action_behavior
        result['price_action_behavior'] = gemini_output.get('price_action_behavior', {})
        if not result['price_action_behavior']:
            # 从patterns和market_conditions推断
            result['price_action_behavior'] = self._infer_price_action(result)
        
        return result
    
    def _parse_trading_note(self, text: str) -> Optional[Dict]:
        """从文本提取交易信息（如 "75% chance of test of high"）"""
        import re
        
        # 提取概率
        prob_match = re.search(r'(\d+)%', text)
        probability = int(prob_match.group(1)) if prob_match else None
        
        # 提取方向
        direction = None
        if re.search(r'\b(buy|long|做多|买入)\b', text, re.I):
            direction = 'long'
        elif re.search(r'\b(sell|short|做空|卖出)\b', text, re.I):
            direction = 'short'
        
        # 提取目标
        target = None
        if 'test of high' in text.lower() or 'test of high of day' in text.lower():
            target = 'test_of_high_of_day'
        elif 'test of low' in text.lower() or 'test of low of day' in text.lower():
            target = 'test_of_low_of_day'
        
        if direction or probability:
            return {
                'direction': direction,
                'probability': probability,
                'target': target,
                'entry_condition': text[:200]  # 保留原始文本
            }
        return None
```

#### 0.4 更新模式库数据

**脚本**: `scripts/abu/abu_update_pattern_library_from_gemini.py` (新建)

```python
def update_pattern_library_from_gemini():
    """将Gemini分析结果更新到pattern_library表"""
    db = TraderDBManager('abu')
    conn = db._get_connection()
    
    # 读取Gemini输出
    parser = GeminiOutputParser()
    annotations_file = Path('outputs/abu_gemini_annotations_enhanced.jsonl')
    
    updated_count = 0
    for line in annotations_file.open():
        record = json.loads(line)
        image_path = record['image']
        gemini_result = record['result']
        
        # 解析Gemini输出
        parsed = parser.parse_gemini_result(gemini_result)
        
        # 查找对应的pattern_library记录（通过image_path）
        pattern_record = conn.execute('''
            SELECT id FROM pattern_library 
            WHERE image_path LIKE ?
        ''', (f'%{Path(image_path).name}%',)).fetchone()
        
        if pattern_record:
            pattern_id = pattern_record[0]
            
            # 更新gemini_annotation_json
            conn.execute('''
                UPDATE pattern_library
                SET gemini_annotation_json = ?,
                    pattern_type = ?,
                    direction = ?,
                    key_features = ?,
                    confidence = ?,
                    updated_at = ?
                WHERE id = ?
            ''', (
                json.dumps(parsed, ensure_ascii=False),
                parsed['patterns'][0]['name'] if parsed['patterns'] else None,
                parsed['trading_signals'][0]['direction'] if parsed['trading_signals'] else None,
                json.dumps(parsed['price_action_behavior'], ensure_ascii=False),
                parsed['confidence'],
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                pattern_id
            ))
            updated_count += 1
    
    conn.commit()
    print(f"✓ 更新了 {updated_count} 条模式库记录")
```

---

## 🎯 ML/DL应用场景

### 场景0: 价格行为特征学习（基于Gemini分析）⭐⭐⭐ (最高优先级)

**目标**: 从Gemini识别的模式组合和K线行为中，使用机器学习学习价格行为特征

**数据源**:
- Gemini分析结果: `gemini_annotation_json` 字段（包含多模式组合、K线特征、交易参数）
- 历史价格数据: K线数据用于验证和训练

**特征工程**:
```python
def extract_price_action_features(gemini_annotation: Dict, klines: List[Dict]) -> Dict:
    """从Gemini分析结果和K线数据提取价格行为特征"""
    features = {
        # 1. 模式组合特征
        'pattern_count': len(gemini_annotation['patterns']),
        'pattern_types': [p['type'] for p in gemini_annotation['patterns']],
        'has_reversal': any(p['type'] == 'reversal' for p in gemini_annotation['patterns']),
        'has_continuation': any(p['type'] == 'continuation' for p in gemini_annotation['patterns']),
        'pattern_combination': gemini_annotation.get('pattern_combination', ''),
        
        # 2. K线行为特征（从Gemini识别）
        'kline_features': gemini_annotation['price_action_behavior'].get('kline_features', []),
        'has_engulfing': 'engulfing' in gemini_annotation['price_action_behavior'].get('kline_features', []),
        'has_pin_bar': 'pin_bar' in gemini_annotation['price_action_behavior'].get('kline_features', []),
        'has_inside_bar': 'inside_bar' in gemini_annotation['price_action_behavior'].get('kline_features', []),
        'trend_structure': gemini_annotation['price_action_behavior'].get('structure', ''),
        
        # 3. 交易参数特征（从Gemini提取）
        'signal_count': len(gemini_annotation['trading_signals']),
        'avg_probability': np.mean([s.get('probability', 0) for s in gemini_annotation['trading_signals']]),
        'risk_reward_ratio': np.mean([s.get('risk_reward_ratio', 0) for s in gemini_annotation['trading_signals']]),
        
        # 4. 市场条件特征
        'market_context': gemini_annotation['market_conditions'].get('context', ''),
        'trend_strength': gemini_annotation['market_conditions'].get('trend_strength', ''),
        'volatility_level': gemini_annotation['market_conditions'].get('volatility', ''),
        
        # 5. 从实际K线数据计算的特征（用于验证）
        'actual_trend': calculate_actual_trend(klines),
        'actual_volatility': calculate_volatility(klines),
        'actual_volume_change': calculate_volume_change(klines),
        'price_action_match_score': compare_price_action(klines, gemini_annotation)
    }
    return features
```

**ML模型设计**:
```python
class PriceActionLearner:
    """价格行为特征学习器"""
    
    def train_price_action_model(self, training_data):
        """训练价格行为识别模型"""
        # 输入: Gemini识别的特征 + 实际K线特征
        # 输出: 价格行为类别（reversal/continuation/indecision）
        
        X = []
        y = []
        
        for record in training_data:
            # 从Gemini分析提取特征
            gemini_features = self.extract_gemini_features(record['gemini_annotation'])
            
            # 从实际K线提取特征
            kline_features = self.extract_kline_features(record['klines'])
            
            # 组合特征
            combined_features = {**gemini_features, **kline_features}
            X.append(combined_features)
            
            # 标签：基于后续价格表现
            label = self.infer_price_action_label(record['klines'], record['signal'])
            y.append(label)
        
        # 训练模型
        model = XGBoostClassifier()
        model.fit(X, y)
        return model
    
    def predict_price_action(self, gemini_annotation: Dict, klines: List[Dict]) -> Dict:
        """预测当前K线的价格行为"""
        features = extract_price_action_features(gemini_annotation, klines)
        prediction = self.model.predict([features])[0]
        probability = self.model.predict_proba([features])[0]
        
        return {
            'price_action': prediction,  # reversal/continuation/indecision
            'probability': probability,
            'features': features
        }
```

**实现文件**: `src/ml_dl/abu_price_action_learner.py`

**集成到信号生成**:
```python
# src/abu/detectors.py 增强版
def detect_with_price_action_learning(klines, gemini_patterns):
    """结合Gemini分析和价格行为学习的检测"""
    
    # 1. 传统检测（现有逻辑）
    candidates = detect_all_15m(klines)
    
    # 2. 从Gemini模式库匹配
    learner = PriceActionLearner()
    
    for candidate in candidates:
        # 查找相似的Gemini模式
        similar_patterns = find_similar_gemini_patterns(candidate, gemini_patterns)
        
        for gemini_pattern in similar_patterns:
            # 学习价格行为
            price_action = learner.predict_price_action(
                gemini_pattern['gemini_annotation'],
                klines
            )
            
            # 增强候选信号
            candidate['price_action_prediction'] = price_action
            candidate['pattern_combination'] = gemini_pattern['pattern_combination']
            candidate['gemini_probability'] = gemini_pattern['trading_signals'][0].get('probability', 0)
            
            # 如果Gemini识别了交易参数，优先使用
            if gemini_pattern['trading_signals']:
                signal = gemini_pattern['trading_signals'][0]
                candidate['ml_entry_hint'] = signal.get('entry_price_hint')
                candidate['ml_tp_hint'] = signal.get('take_profit_1_hint')
                candidate['ml_sl_hint'] = signal.get('stop_loss_hint')
    
    return candidates
```

---

### 场景1: 模式匹配成功率预测 ⭐⭐⭐ (高优先级)

**目标**: 预测模式库中的模式在实时K线中匹配后的成功率

**现有流程中的位置**:
```
模式库 → 实时检测器 → [ML预测成功率] → 评分排序 → Top10信号
```

**数据源**:
1. **历史匹配记录** (需新建表):
   - `pattern_match_history` 表
   - 字段: pattern_id, match_time, klines_context, match_result (tp/sl), actual_hit_time
   
2. **模式特征** (已有):
   - `pattern_library` 表: pattern_type, features_json, confidence
   
3. **实时K线上下文**:
   - 检测时刻的K线数据、技术指标、市场状态

**ML模型设计**:
- **特征工程**:
  ```python
  features = {
      # 模式特征
      'pattern_type': categorical,  # Triangle/HeadAndShoulders/InsideBar等
      'pattern_confidence': float,  # 模式置信度
      'pattern_features': dict,     # 模式几何特征
      
      # 市场上下文特征
      'trend_strength': float,      # 趋势强度 (EMA200)
      'volatility': float,          # 波动率
      'volume_ratio': float,        # 成交量比
      'rsi': float,                 # RSI指标
      'market_state': categorical,  # bull/bear/neutral
      
      # 检测时刻特征
      'entry_price': float,
      'stop_loss_distance_pct': float,
      'take_profit_distance_pct': float,
      'risk_reward_ratio': float,
      'timeframe': categorical,     # 15m/1h/4h
  }
  ```

- **标签**:
  - 二分类: `success` (1=TP命中, 0=SL命中或未命中)
  - 回归: `hit_time_hours` (从匹配到TP/SL的时间)

- **模型选择**:
  1. **基线模型**: Random Forest / XGBoost (快速验证)
  2. **深度学习**: 
     - LSTM (时序特征)
     - CNN+LSTM (K线图像 + 时序)
     - Transformer (注意力机制，捕捉模式特征重要性)

**实现文件**: `src/ml_dl/abu_pattern_match_predictor.py`

---

### 场景2: 模式权重优化 ⭐⭐⭐ (高优先级)

**目标**: 基于历史表现优化 `config/abu_pattern_weights.yaml` 中的模式权重

**现有问题**:
- 当前权重是人工设定的固定值
- 无法根据历史表现自适应调整

**ML/DL方案**:
1. **收集历史数据**:
   - 从 `pattern_match_history` 统计每个模式的胜率
   - 计算: win_rate, avg_profit, avg_loss, sharpe_ratio

2. **强化学习优化权重**:
   ```python
   # 状态: 当前权重配置 + 市场状态
   # 动作: 调整各模式权重 (±0.1)
   # 奖励: 组合信号的胜率提升 + 盈亏比改善
   ```

3. **多臂老虎机 (Multi-Armed Bandit)**:
   - 快速探索不同权重组合
   - 平衡探索与利用

**实现文件**: `src/ml_dl/abu_pattern_weight_optimizer.py`

**输出**: 自动更新 `config/abu_pattern_weights.yaml`

---

### 场景3: 候选信号评分优化 ⭐⭐ (中优先级)

**目标**: 使用ML模型替代 `src/abu/ranker.py` 中的规则评分

**现有评分公式** (rule-based):
```python
score = base_score * 0.6 + rr_score * 0.6 + trend_backing * 0.6 + pattern_bonus
```

**ML评分模型**:
- **训练数据**: 历史候选信号 + 实际表现 (TP/SL)
- **特征**: 
  - 现有特征 (entry, sl, tp, pattern, trend)
  - 扩展特征 (volatility, volume, market_regime, time_features)
  
- **模型**: 
  - Gradient Boosting (XGBoost/LightGBM) - 可解释性强
  - 神经网络 - 捕捉复杂非线性关系

**优势**:
- 自动学习特征重要性
- 捕捉规则无法表达的复杂模式
- 可随数据积累持续优化

**实现文件**: `src/ml_dl/abu_candidate_scorer.py`

**集成方式**:
```python
# src/abu/ranker.py
def score_candidate(c: Dict, k1h: List[Dict]) -> float:
    # 如果ML模型可用，优先使用
    if ml_scorer.is_available():
        return ml_scorer.predict_score(c, k1h)
    # 否则使用规则评分
    return rule_based_score(c, k1h)
```

---

### 场景4: 模式识别增强 (深度学习) ⭐ (低优先级，长期)

**目标**: 使用深度学习直接从K线图像识别模式

**方案**:
- **CNN模型**: 将K线数据转换为图像，使用CNN识别形态
- **对比学习**: 将PDF模式图片与实时K线图片对比，计算相似度
- **Transformer**: 将K线序列作为token，使用注意力机制识别模式

**数据准备**:
- PDF模式图片: `data/abu/images/`
- 实时K线图片: 从K线数据生成

**实现文件**: `src/ml_dl/abu_pattern_vision_matcher.py`

---

## 📋 实施计划

### 阶段0: Gemini Vision API完整分析（必须首先完成，1-2周）

**⚠️ 重要说明：成本控制和健壮性**

- ✅ **成本控制**：强制使用 `gemini-1.5-flash`，禁止Pro模型
- ✅ **去重机制**：SHA1检查、输出文件检查、缓存检查，确保每张图片只分析一次
- ✅ **断点续传**：支持中断后继续，不浪费API调用
- ✅ **独立模块**：只用于图形识别，不做其他用途
- ✅ **日志完整**：详细记录处理状态，便于排查问题

#### 0.1 Gemini Vision 图形识别模块（独立模块，成本可控）

**文件**: `src/abu/gemini_vision_analyzer.py` (新建，独立模块)

**设计原则**（严格遵循）:
1. ✅ **独立模块**: 只用于图形识别，不做其他用途
2. ✅ **成本控制**: 强制使用 `gemini-1.5-flash`（禁止使用Pro）
3. ✅ **去重机制**: 
   - SHA1检查（文件内容去重）
   - 输出文件检查（避免重复写入）
   - 缓存检查（避免重复API调用）
4. ✅ **断点续传**: 
   - 状态文件保存（`outputs/abu_gemini_analysis_state.json`）
   - 支持中断后继续，不浪费API调用
   - 自动跳过已处理的图片
5. ✅ **健壮性**: 
   - 完整的错误处理和重试机制（最多3次）
   - 异常捕获和日志记录
   - 每10张保存一次状态
6. ✅ **日志完整**: 
   - 详细日志文件（`outputs/abu_gemini/gemini_analysis.log`）
   - 记录每张图片的处理状态、耗时、成本
   - 记录所有错误和警告
7. ✅ **输入输出明确**:
   - 输入: `data/abu/images/*.png` (1000张图片)
   - 输出: `outputs/abu_gemini_annotations_enhanced.jsonl`
   - 状态: `outputs/abu_gemini_analysis_state.json`
   - 缓存: `outputs/.cache/abu_gemini/{sha1}.json`
   - 日志: `outputs/abu_gemini/gemini_analysis.log`

**成本控制机制**:
- **模型强制**: 自动检测并禁止使用Pro模型
- **成本估算**: 实时显示每次调用成本和总成本
- **API限流**: 默认1秒间隔（可配置）
- **批量控制**: 支持分批处理，控制单次运行成本

**断点续传机制**:
- 状态文件结构:
  ```json
  {
    "start_time": "2026-01-10 10:00:00",
    "last_update": "2026-01-10 10:30:00",
    "total_images": 1000,
    "completed_count": 300,
    "failed_count": 5,
    "skipped_count": 50,
    "images": [
      {
        "image_path": "data/abu/images/page_0001_img_01_xxx.png",
        "image_sha1": "abc123...",
        "status": "completed",  // pending/processing/completed/failed/skipped
        "processed_at": "2026-01-10 10:05:00",
        "retry_count": 0,
        "error_message": null
      },
      ...
    ],
    "settings": {
      "model": "gemini-1.5-flash",
      "sleep_ms": 1000,
      "max_retries": 3
    }
  }
  ```

**使用方式**:

```bash
# 设置API Key（必须）
export GEMINI_API_KEY="your_api_key"

# 方式1: 完整处理1000张图片（自动断点续传）
python -m src.abu.gemini_vision_analyzer \
    --api-key $GEMINI_API_KEY \
    --model gemini-1.5-flash \
    --resume  # 默认开启，从上次中断处继续

# 方式2: 分批处理（推荐，控制成本）
# 第一批：1-300
python -m src.abu.gemini_vision_analyzer \
    --start-idx 0 --end-idx 300 \
    --sleep-ms 1000

# 第二批：301-600（自动跳过已处理）
python -m src.abu.gemini_vision_analyzer \
    --start-idx 300 --end-idx 600 \
    --resume  # 自动从状态文件恢复

# 第三批：601-1000
python -m src.abu.gemini_vision_analyzer \
    --start-idx 600 \
    --resume

# 方式3: 查看当前状态（不执行分析）
python -m src.abu.gemini_vision_analyzer --status

# 方式4: 测试模式（只处理前10张）
python -m src.abu.gemini_vision_analyzer --limit 10

# 方式5: 强制重新分析（忽略缓存和已处理记录，谨慎使用）
python -m src.abu.gemini_vision_analyzer --force
```

**成本估算**:
- Gemini 1.5 Flash: 约 $0.000125/张图片
- 1000张图片: 约 **$0.125 USD** (12.5美分)
- 实际成本可能略有差异，以Gemini官方定价为准

**输出文件格式** (`outputs/abu_gemini_annotations_enhanced.jsonl`):
```json
{
  "image": "data/abu/images/page_0001_img_01_xxx.png",
  "sha1": "abc123def456...",
  "page": 1,
  "result": {
    "patterns": [
      {"name": "W底", "type": "reversal", "location": "bottom", "confidence": 0.85},
      {"name": "三角形", "type": "continuation", "location": "middle", "confidence": 0.75}
    ],
    "pattern_combination": "W底 + 三角形 + 突破",
    "price_action_behavior": {
      "trend": "bullish",
      "structure": "higher_lows",
      "kline_features": ["engulfing", "pin_bar"],
      "volume_behavior": "increasing"
    },
    "trading_signals": [
      {
        "direction": "long",
        "entry_condition": "回调到W底颈线附近",
        "entry_price_hint": 87500,
        "stop_loss_hint": 87000,
        "take_profit_1_hint": 88500,
        "take_profit_2_hint": 89000,
        "probability": 75,
        "target": "test_of_high_of_day",
        "risk_reward_ratio": 2.5,
        "timeframe_hint": "15m"
      }
    ],
    "market_conditions": {
      "context": "small PB bull trend",
      "trend_strength": "strong",
      "volatility": "low",
      "key_levels": ["87500", "88000", "89000"]
    },
    "annotations": [
      {"label": "A", "description": "W底左底", "price": 86500}
    ],
    "text_notes": [
      "20-Gap bar buy in small PB bull trend so 75% chance of test of high of day"
    ],
    "confidence": 0.90
  },
  "cached": false,
  "elapsed_seconds": 2.34,
  "estimated_cost_usd": 0.000125
}
```

**状态检查命令**:
```bash
# 查看处理状态
python -m src.abu.gemini_vision_analyzer --status

# 输出示例:
# {
#   "status": "in_progress",
#   "start_time": "2026-01-10 10:00:00",
#   "last_update": "2026-01-10 10:30:00",
#   "total_images": 1000,
#   "completed": 300,
#   "failed": 5,
#   "skipped": 50,
#   "pending": 645,
#   "progress_pct": 35.0,
#   "estimated_remaining_cost": 0.080625
# }
```

#### 0.2 智能解析Gemini输出（独立模块的一部分）

**文件**: `scripts/abu/abu_parse_gemini_output.py` (新建)

**功能**:
- 解析Gemini返回的JSON（可能不完整或格式不一致）
- 从text_notes提取交易参数（概率、价格等）
- 补全缺失字段
- 标准化格式
- 验证解析结果

**输入**: `outputs/abu_gemini_annotations_enhanced.jsonl` (Gemini分析结果)

**输出**: `outputs/abu_gemini_parsed.jsonl` (解析后的标准化结果)

**执行**:
```bash
# 解析Gemini输出
python scripts/abu/abu_parse_gemini_output.py \
    --input outputs/abu_gemini_annotations_enhanced.jsonl \
    --output outputs/abu_gemini_parsed.jsonl \
    --verify  # 验证解析结果，报告错误

# 输出格式: 标准化的parsed字段 + 原始结果 + 解析错误
```

**解析能力**:
- 支持多种JSON格式（列表/单一对象/嵌套结构）
- 从文本自动提取：概率、方向、价格、目标
- 智能补全：缺失字段从其他字段推断
- 错误记录：记录所有解析错误，便于排查

#### 0.3 更新模式库数据（独立模块的一部分）

**文件**: `scripts/abu/abu_update_pattern_library_from_gemini.py` (新建)

**功能**:
- 读取解析后的Gemini结果
- 匹配pattern_library记录（通过image_path或page_number）
- 更新gemini_annotation_json字段
- 提取并更新pattern_type, direction, key_features等字段
- 支持预览模式（--dry-run）

**执行**:
```bash
# 预览模式（不实际更新，先检查）
python scripts/abu/abu_update_pattern_library_from_gemini.py \
    --input outputs/abu_gemini_parsed.jsonl \
    --dry-run

# 实际更新（确认无误后执行）
python scripts/abu/abu_update_pattern_library_from_gemini.py \
    --input outputs/abu_gemini_parsed.jsonl \
    --skip-existing  # 跳过已有gemini_annotation_json的记录（默认）
```

**更新内容**:
- `gemini_annotation_json`: 完整的解析结果（JSON格式）
- `pattern_type`: 从patterns提取（支持多模式，取第一个）
- `direction`: 从trading_signals提取
- `key_features`: 从price_action_behavior提取（K线特征）
- `confidence`: 从解析结果提取
- `updated_at`: 更新时间戳

#### 0.4 验证Gemini分析结果

**文件**: `scripts/abu/abu_verify_gemini_analysis.py` (新建)

**功能**:
- 检查更新后的数据质量
- 统计：
  - 有多少条记录有gemini_annotation_json（覆盖率）
  - 模式组合分布（"W底+三角形"有多少条）
  - 交易参数完整性（有多少条有probability、entry_price等）
  - 置信度分布
- 生成质量报告

**执行**:
```bash
python scripts/abu/abu_verify_gemini_analysis.py \
    --output outputs/abu_gemini_verification_report.md
```

**报告内容**:
- 覆盖率统计
- 模式类型分布
- 交易参数完整性
- 置信度分布
- 质量评分

---

### 阶段1: 数据准备 (1-2周)

#### 1.1 创建/扩展模式匹配历史表

**现有表**: `pattern_matches` 已存在但为空，需要扩展字段

```sql
-- 检查现有表结构（已有9个字段）
-- 扩展字段以支持ML训练
ALTER TABLE pattern_matches ADD COLUMN IF NOT EXISTS pattern_type TEXT;
ALTER TABLE pattern_matches ADD COLUMN IF NOT EXISTS entry_price REAL;
ALTER TABLE pattern_matches ADD COLUMN IF NOT EXISTS stop_loss REAL;
ALTER TABLE pattern_matches ADD COLUMN IF NOT EXISTS take_profit_1 REAL;
ALTER TABLE pattern_matches ADD COLUMN IF NOT EXISTS take_profit_2 REAL;
ALTER TABLE pattern_matches ADD COLUMN IF NOT EXISTS direction TEXT;
ALTER TABLE pattern_matches ADD COLUMN IF NOT EXISTS klines_context_json TEXT;
ALTER TABLE pattern_matches ADD COLUMN IF NOT EXISTS market_features_json TEXT;
ALTER TABLE pattern_matches ADD COLUMN IF NOT EXISTS match_result TEXT;
ALTER TABLE pattern_matches ADD COLUMN IF NOT EXISTS hit_time TEXT;
ALTER TABLE pattern_matches ADD COLUMN IF NOT EXISTS profit_pct REAL;
ALTER TABLE pattern_matches ADD COLUMN IF NOT EXISTS signal_id INTEGER;

-- 如果表不存在，创建完整表
CREATE TABLE IF NOT EXISTS pattern_match_history (
    id INTEGER PRIMARY KEY,
    pattern_id INTEGER,              -- 模式库中的pattern_id
    signal_id INTEGER,               -- 关联的trading_signal id
    pattern_type TEXT,               -- Triangle/HeadAndShoulders等
    match_time TEXT NOT NULL,        -- 匹配时间
    symbol TEXT,                     -- BTC/USDT等
    timeframe TEXT,                  -- 15m/1h等
    entry_price REAL,
    stop_loss REAL,
    take_profit_1 REAL,
    take_profit_2 REAL,
    direction TEXT,                  -- long/short
    match_confidence REAL,           -- 匹配置信度（已有字段）
    klines_context_json TEXT,        -- 匹配时的K线上下文(JSON)
    market_features_json TEXT,       -- 市场特征(JSON): trend, volatility等
    match_details_json TEXT,         -- 匹配详情（已有字段）
    match_result TEXT,               -- tp/sl/none（待评估后更新）
    hit_time TEXT,                   -- 实际TP/SL触发时间
    profit_pct REAL,                 -- 实际盈亏百分比
    created_at TEXT NOT NULL,
    FOREIGN KEY (pattern_id) REFERENCES pattern_library(id),
    FOREIGN KEY (signal_id) REFERENCES trading_signals(id)
);
```

#### 1.2 记录模式匹配历史

**实现**: `scripts/abu/abu_record_match_history.py`

在每次生成ABU信号后，记录:
- 哪些模式被匹配了
- 匹配时的市场状态
- 后续的价格表现 (TP/SL结果)

**执行方式**:
```bash
# 生成ABU信号时自动记录
python scripts/pa_scan_15m_top10.py --record-match-history

# 或批量回测历史信号
python scripts/abu/abu_backtest_pattern_matches.py --start-date 2025-01-01
```

#### 1.3 信号评估数据收集

**数据源**:
- `trading_signals` 表 (system_name='abu')
- `signal_evaluations` 表 (待创建评估记录)

**实施信号评估**:
```python
# 评估ABU历史信号的实际表现
def evaluate_abu_signals():
    db = TraderDBManager('abu')
    signals = db.get_trading_signals(system_name='abu', status='pending')
    
    for signal in signals:
        # 基于历史K线评估
        result = price_eval_signal(signal)
        
        # 更新评估表
        db.add_signal_evaluation(
            signal_id=signal['id'],
            evaluation_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            result=result['result'],  # tp/sl/none
            actual_entry_price=signal['entry_price'],
            actual_exit_price=result.get('exit_price'),
            actual_profit_pct=result.get('profit_pct', 0),
            stop_loss_hit=1 if result['result'] == 'sl' else 0,
            take_profit_1_hit=1 if result['result'] == 'tp' else 0,
            notes=f"自动评估: {result.get('hit_time', '未触发')}"
        )
        
        # 更新信号状态
        db.update_signal_status(signal['id'], result['result'])
```

---

### 阶段2: ML模型训练 (2-3周)

#### 2.0 价格行为特征学习模型（最高优先级）⭐

**文件**: `src/ml_dl/abu_price_action_learner.py` (新建)

**训练数据准备**:
```python
def prepare_price_action_training_data():
    """从Gemini分析结果和实际K线数据准备训练数据"""
    db = TraderDBManager('abu')
    conn = db._get_connection()
    
    # 获取所有有Gemini标注的模式
    patterns = conn.execute('''
        SELECT id, gemini_annotation_json, image_path
        FROM pattern_library
        WHERE gemini_annotation_json IS NOT NULL 
          AND gemini_annotation_json != ''
    ''').fetchall()
    
    training_data = []
    for pattern_id, gemini_json, image_path in patterns:
        try:
            gemini_ann = json.loads(gemini_json)
            
            # 提取Gemini识别的特征
            gemini_features = extract_gemini_features(gemini_ann)
            
            # 获取实际K线数据（从图像路径推断币种和时间，或从数据库获取）
            klines = get_klines_for_pattern(pattern_id, image_path)
            
            if klines:
                # 提取实际K线特征
                kline_features = extract_kline_features(klines)
                
                # 组合特征
                combined_features = {**gemini_features, **kline_features}
                
                # 标签：基于后续价格表现推断价格行为
                # 如果后续价格反转 → reversal
                # 如果后续价格延续 → continuation
                # 否则 → indecision
                label = infer_price_action_label(klines, gemini_ann)
                
                training_data.append({
                    'features': combined_features,
                    'label': label,
                    'pattern_id': pattern_id,
                    'gemini_annotation': gemini_ann
                })
        except Exception as e:
            print(f"处理模式 {pattern_id} 失败: {e}")
            continue
    
    return training_data
```

**特征提取函数**:
```python
def extract_gemini_features(gemini_ann: Dict) -> Dict:
    """从Gemini分析结果提取特征"""
    return {
        # 模式组合特征
        'pattern_count': len(gemini_ann.get('patterns', [])),
        'has_reversal_pattern': any(p.get('type') == 'reversal' for p in gemini_ann.get('patterns', [])),
        'has_continuation_pattern': any(p.get('type') == 'continuation' for p in gemini_ann.get('patterns', [])),
        'pattern_combination': gemini_ann.get('pattern_combination', ''),
        
        # K线行为特征
        'kline_features': gemini_ann.get('price_action_behavior', {}).get('kline_features', []),
        'has_engulfing': 'engulfing' in (gemini_ann.get('price_action_behavior', {}).get('kline_features', [])),
        'has_pin_bar': 'pin_bar' in (gemini_ann.get('price_action_behavior', {}).get('kline_features', [])),
        'has_inside_bar': 'inside_bar' in (gemini_ann.get('price_action_behavior', {}).get('kline_features', [])),
        'trend_structure': gemini_ann.get('price_action_behavior', {}).get('structure', ''),
        
        # 交易参数特征
        'signal_count': len(gemini_ann.get('trading_signals', [])),
        'avg_probability': np.mean([s.get('probability', 0) for s in gemini_ann.get('trading_signals', [])]),
        'avg_rr_ratio': np.mean([s.get('risk_reward_ratio', 0) for s in gemini_ann.get('trading_signals', [])]),
        
        # 市场条件特征
        'trend_strength': gemini_ann.get('market_conditions', {}).get('trend_strength', ''),
        'volatility_level': gemini_ann.get('market_conditions', {}).get('volatility', ''),
    }

def extract_kline_features(klines: List[Dict]) -> Dict:
    """从实际K线数据提取特征"""
    closes = [k['close'] for k in klines]
    highs = [k['high'] for k in klines]
    lows = [k['low'] for k in klines]
    volumes = [k.get('volume', 0) for k in klines]
    
    return {
        # 趋势特征
        'price_trend': calculate_trend(closes),
        'trend_strength': calculate_trend_strength(closes),
        
        # 波动特征
        'volatility': calculate_volatility(closes),
        'range_expansion': calculate_range_expansion(highs, lows),
        
        # 成交量特征
        'volume_trend': calculate_volume_trend(volumes),
        'volume_spike': detect_volume_spike(volumes),
        
        # K线形态特征
        'actual_engulfing': detect_engulfing_actual(klines),
        'actual_pin_bar': detect_pin_bar_actual(klines),
        'actual_inside_bar': detect_inside_bar_actual(klines),
    }
```

**模型训练**:
```python
class PriceActionLearner:
    """价格行为特征学习器"""
    
    def train(self, training_data):
        """训练价格行为识别模型"""
        X = [self.features_to_vector(d['features']) for d in training_data]
        y = [d['label'] for d in training_data]  # reversal/continuation/indecision
        
        # 数据划分
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
        
        # 训练模型
        model = XGBoostClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1
        )
        model.fit(X_train, y_train)
        
        # 评估
        accuracy = model.score(X_test, y_test)
        feature_importance = dict(zip(self.feature_names, model.feature_importances_))
        
        return {
            'model': model,
            'accuracy': accuracy,
            'feature_importance': feature_importance
        }
    
    def predict_price_action(self, gemini_annotation: Dict, klines: List[Dict]) -> Dict:
        """预测当前K线的价格行为"""
        gemini_features = extract_gemini_features(gemini_annotation)
        kline_features = extract_kline_features(klines)
        combined_features = {**gemini_features, **kline_features}
        
        X = [self.features_to_vector(combined_features)]
        prediction = self.model.predict(X)[0]
        probability = self.model.predict_proba(X)[0]
        
        return {
            'price_action': prediction,  # reversal/continuation/indecision
            'probability': dict(zip(self.model.classes_, probability)),
            'features': combined_features
        }
```

**训练命令**:
```bash
python src/ml_dl/abu_price_action_learner.py --train
```

#### 2.1 模式匹配成功率预测模型（增强版）

**文件**: `src/ml_dl/abu_pattern_match_predictor.py`

```python
class ABUPatternMatchPredictor:
    """ABU模式匹配成功率预测器"""
    
    def prepare_features(self, match_history):
        """准备训练特征"""
        features = []
        for record in match_history:
            feat = {
                'pattern_type': record['pattern_type'],
                'pattern_confidence': record['pattern_confidence'],
                'trend_strength': record['market_features']['trend'],
                'volatility': record['market_features']['volatility'],
                'risk_reward_ratio': record['risk_reward_ratio'],
                # ... 更多特征
            }
            features.append(feat)
        return features
    
    def train(self, match_history, labels):
        """训练模型"""
        X = self.prepare_features(match_history)
        y = labels  # 1=TP, 0=SL/None
        
        # 数据划分
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
        
        # 训练模型
        model = XGBoostClassifier()
        model.fit(X_train, y_train)
        
        # 评估
        accuracy = model.score(X_test, y_test)
        return model, accuracy
```

**训练命令**:
```bash
python src/ml_dl/abu_pattern_match_predictor.py --train
```

**使用方式**:
```python
predictor = ABUPatternMatchPredictor()
predictor.load_model()

# 在匹配模式时预测成功率
for candidate in detected_candidates:
    success_prob = predictor.predict_success_probability(candidate, market_context)
    candidate['ml_success_prob'] = success_prob
```

#### 2.2 模式权重优化器

**文件**: `src/ml_dl/abu_pattern_weight_optimizer.py`

```python
class ABUPatternWeightOptimizer:
    """模式权重优化器 (强化学习)"""
    
    def optimize_weights(self, match_history, current_weights):
        """优化模式权重"""
        # 使用Thompson Sampling或UCB算法
        # 探索不同权重组合，选择最优
        
        best_weights = current_weights
        best_score = self.evaluate_weights(current_weights, match_history)
        
        for iteration in range(100):
            # 生成新权重组合
            new_weights = self.sample_weights(current_weights)
            
            # 评估
            score = self.evaluate_weights(new_weights, match_history)
            
            if score > best_score:
                best_weights = new_weights
                best_score = score
        
        return best_weights
```

**执行方式**:
```bash
# 基于历史数据优化权重
python src/ml_dl/abu_pattern_weight_optimizer.py \
    --history-table pattern_match_history \
    --output config/abu_pattern_weights.yaml
```

#### 2.3 候选信号评分模型

**文件**: `src/ml_dl/abu_candidate_scorer.py`

**训练数据准备**:
```python
# 从历史匹配记录构建训练数据
def prepare_scoring_training_data():
    # 获取历史候选信号 (所有检测到的信号，不只是top10)
    # 获取对应的实际表现 (TP/SL)
    # 提取特征
    
    training_data = []
    for match_record in match_history:
        candidate = {
            'pattern': match_record['pattern_type'],
            'entry': match_record['entry_price'],
            'stop_loss': match_record['stop_loss'],
            # ... 更多特征
        }
        label = 1 if match_record['match_result'] == 'tp' else 0
        training_data.append((candidate, label))
    
    return training_data
```

**模型训练**:
```python
class ABUCandidateScorer:
    """候选信号ML评分器"""
    
    def train(self, training_data):
        X, y = zip(*training_data)
        model = LightGBMRegressor()  # 回归，输出评分
        model.fit(X, y)
        return model
    
    def predict_score(self, candidate, market_context):
        """预测候选信号的评分"""
        features = self.extract_features(candidate, market_context)
        score = self.model.predict([features])[0]
        return score
```

**集成到现有流程**:
```python
# src/abu/ranker.py
from ml_dl.abu_candidate_scorer import ABUCandidateScorer

_ML_SCORER = None

def get_ml_scorer():
    global _ML_SCORER
    if _ML_SCORER is None:
        _ML_SCORER = ABUCandidateScorer()
        _ML_SCORER.load_model()  # 如果模型存在则加载
    return _ML_SCORER

def score_candidate(c: Dict, k1h: List[Dict]) -> float:
    # 优先使用ML评分
    ml_scorer = get_ml_scorer()
    if ml_scorer.is_available():
        try:
            ml_score = ml_scorer.predict_score(c, k1h)
            return ml_score
        except Exception:
            pass  # 回退到规则评分
    
    # 规则评分 (现有逻辑)
    base = c.get('score_hint') or 0.0
    # ... 现有代码 ...
```

### 阶段3: 模型集成与优化 (1-2周)

#### 3.1 集成到现有流程

**ABU信号生成流程增强**:
```python
# scripts/pa_scan_15m_top10.py 或类似的信号生成脚本

# 1. 检测候选信号 (现有)
candidates = detect_all_patterns(klines)

# 2. ML预测成功率 (新增)
if ml_predictor.is_available():
    for candidate in candidates:
        candidate['ml_success_prob'] = ml_predictor.predict(candidate, klines)
        # 更新score_hint，结合ML预测
        candidate['score_hint'] = combine_ml_and_rule_score(
            candidate['score_hint'], 
            candidate['ml_success_prob']
        )

# 3. 评分排序 (现有，但可能使用ML评分器)
ranked = rank_and_pick(candidates, klines_1h, topn=10)

# 4. 记录匹配历史 (新增)
record_match_history(ranked, klines, market_context)
```

#### 3.2 模型评估与监控

**创建评估脚本**: `scripts/abu/abu_ml_model_evaluation.py`

```python
def evaluate_ml_models():
    """评估所有ML模型的性能"""
    results = {}
    
    # 1. 模式匹配预测模型
    predictor = ABUPatternMatchPredictor()
    accuracy = predictor.evaluate_on_test_set()
    results['pattern_match_predictor'] = accuracy
    
    # 2. 候选信号评分模型
    scorer = ABUCandidateScorer()
    correlation = scorer.evaluate_correlation_with_actual_performance()
    results['candidate_scorer'] = correlation
    
    return results
```

**定期重训练**:
```bash
# 每周自动重训练模型
python scripts/abu/abu_retrain_ml_models.py --auto
```

#### 3.3 A/B测试框架

**对比ML评分 vs 规则评分**:
```python
# 生成两套信号
rule_based_signals = generate_signals_rule_based()  # 现有方法
ml_based_signals = generate_signals_ml_based()      # ML增强方法

# 跟踪后续表现
compare_performance(rule_based_signals, ml_based_signals)
```

---

## 💾 数据库容量评估

### 当前数据库状态

**数据库文件**: `src/data/qingniao_abu.duckdb`
- **当前大小**: 10.76 MB
- **表数量**: 15个
- **主要数据**:
  - `pattern_library`: 1,004条记录 (1.64 MB)
  - `trading_signals`: 73条记录 (135 KB)
  - 其他表: 多为空表，待使用

### 容量估算

#### 1. pattern_library 表（模式库）

**当前状态**:
- 记录数: 1,004条
- 平均行大小: ~1.7 KB (包含JSON字段)
- 总大小: 1.64 MB

**未来增长**:
- 模式库相对稳定，预计最多增加至2,000条
- 增长空间: 约 1.7 MB
- **容量充足** ✅

#### 2. pattern_match_history 表（新增，用于ML训练）

**表结构**:
```sql
- pattern_id (INTEGER): 8 bytes
- signal_id (INTEGER): 8 bytes
- pattern_type (TEXT): ~20 bytes
- match_time (TEXT): ~20 bytes
- symbol (TEXT): ~10 bytes
- timeframe (TEXT): ~5 bytes
- entry_price, stop_loss, take_profit_1, take_profit_2 (REAL): 32 bytes
- direction (TEXT): ~5 bytes
- match_confidence (REAL): 8 bytes
- klines_context_json (TEXT): ~1,000 bytes (最近200根K线的简化JSON)
- market_features_json (TEXT): ~500 bytes (市场特征JSON)
- match_details_json (TEXT): ~200 bytes
- match_result, hit_time (TEXT): ~50 bytes
- profit_pct (REAL): 8 bytes
- created_at (TEXT): ~20 bytes

总计: ~1,894 bytes/条（约1.9 KB/条）
```

**数据增长估算**:
- 假设每天生成 **10个信号**
- 每个信号平均匹配 **3个模式**
- 每天匹配记录: 10 × 3 = **30条**
- 每月匹配记录: 30 × 30 = **900条**
- 每年匹配记录: 30 × 365 = **10,950条**

**容量计算**:
- 每天增长: 30条 × 1.9 KB = **57 KB**
- 每月增长: 900条 × 1.9 KB = **1.71 MB**
- 每年增长: 10,950条 × 1.9 KB = **20.8 MB**

**5年容量估算**:
- 5年记录数: 10,950 × 5 = **54,750条**
- 5年数据量: 20.8 MB × 5 = **104 MB**
- 加上索引和开销: 约 **115 MB**

#### 3. trading_signals 表

**当前状态**:
- 记录数: 73条
- 平均行大小: ~1.9 KB
- 总大小: 135 KB

**未来增长**:
- 每天10个信号
- 每年: 10 × 365 = **3,650条**
- 5年: 3,650 × 5 = **18,250条**
- 5年数据量: 18,250 × 1.9 KB = **34.7 MB**

#### 4. signal_evaluations 表

**数据增长估算**:
- 假设评估所有信号（100%评估率）
- 每年评估记录: 3,650条
- 5年评估记录: 18,250条
- 平均行大小: ~1.4 KB
- 5年数据量: 18,250 × 1.4 KB = **25.6 MB**

### 总容量估算

| 表名 | 当前大小 | 5年后估算 | 备注 |
|------|---------|----------|------|
| pattern_library | 1.64 MB | 3.3 MB | 模式库增长有限 |
| pattern_match_history | 0 MB | 115 MB | ML训练数据（主要增长点）|
| trading_signals | 135 KB | 34.7 MB | 信号记录 |
| signal_evaluations | 0 MB | 25.6 MB | 评估记录 |
| 其他表 | 9 MB | 15 MB | 索引、开销等 |
| **总计** | **10.76 MB** | **193.6 MB** | **< 200 MB** |

### DuckDB容量评估结论

**✅ 容量充足，完全够用**

**依据**:
1. **DuckDB理论限制**:
   - 最大数据库大小: 无硬性限制（取决于磁盘空间）
   - 单表最大行数: ~2^63 (9.2 quintillion)
   - 单行最大大小: 建议 < 1MB
   - 推荐单表行数: < 10亿行（性能最佳）

2. **实际需求**:
   - 5年后数据库大小: **< 200 MB**
   - 最大单表记录数: **54,750条** (pattern_match_history)
   - 远低于DuckDB性能推荐值（< 10亿行）

3. **性能考虑**:
   - 200 MB数据量对DuckDB来说很小
   - 查询性能: **毫秒级** (< 10ms)
   - 索引开销: **< 20 MB** (估算)

4. **扩容建议**:
   - **短期（1-2年）**: 无需扩容，容量充足
   - **中期（3-5年）**: 可考虑定期归档历史数据（> 1年的数据）
   - **长期（5年以上）**: 实施数据归档策略，保留最近2年数据用于ML训练

### 数据归档策略（可选，5年后实施）

**归档方案**:
```sql
-- 归档1年以上的匹配历史
CREATE TABLE pattern_match_history_archive_2025 AS
SELECT * FROM pattern_match_history
WHERE created_at < '2025-01-01';

DELETE FROM pattern_match_history
WHERE created_at < '2025-01-01';
```

**保留策略**:
- 保留最近 **2年** 数据用于ML训练
- 归档更早的数据到单独数据库
- ML模型只需最近数据即可，历史数据主要用于回测

---

## 📊 数据要求

### 最小数据量

1. **模式匹配历史**: 
   - 最少: 100条匹配记录（约3-4天数据）
   - 推荐: 500+ 条记录（约2-3周数据）
   - 理想: 2,000+ 条记录（约2-3个月数据）

2. **信号评估记录**:
   - 最少: 50条已评估的信号（约1周数据）
   - 推荐: 200+ 条记录（约1个月数据）
   - 理想: 1,000+ 条记录（约3个月数据）

### 数据质量要求

- 匹配记录必须包含实际表现 (TP/SL)
- 市场特征必须完整
- 时间序列数据必须连续

---

## 🚀 快速开始

### 1. 安装依赖

```bash
# 基础ML库
pip install scikit-learn pandas numpy joblib

# 提升模型
pip install xgboost lightgbm

# 深度学习 (可选)
# pip install torch tensorflow

# 可视化 (可选)
pip install matplotlib seaborn
```

或使用 `requirements_ml.txt`:
```bash
pip install -r requirements_ml.txt
```

### 2. 准备数据

```bash
# 步骤0: Gemini Vision API完整分析1000张图片（必须先完成）
# 使用独立模块，支持断点续传、去重、成本控制
python -m src.abu.gemini_vision_analyzer \
    --api-key $GEMINI_API_KEY \
    --model gemini-1.5-flash \
    --sleep-ms 1000 \
    --resume  # 断点续传

# 查看处理状态
python -m src.abu.gemini_vision_analyzer --status

# 步骤0.5: 智能解析并更新模式库
# 解析Gemini输出（标准化格式）
python scripts/abu/abu_parse_gemini_output.py \
    --input outputs/abu_gemini_annotations_enhanced.jsonl \
    --output outputs/abu_gemini_parsed.jsonl

# 更新模式库（预览模式，先检查）
python scripts/abu/abu_update_pattern_library_from_gemini.py \
    --input outputs/abu_gemini_parsed.jsonl \
    --dry-run

# 实际更新（确认无误后）
python scripts/abu/abu_update_pattern_library_from_gemini.py \
    --input outputs/abu_gemini_parsed.jsonl

# 验证分析结果
python scripts/abu/abu_verify_gemini_analysis.py \
    --output outputs/abu_gemini_verification_report.md

# 步骤1: 创建模式匹配历史表
python scripts/abu/abu_init_ml_tables.py

# 步骤2: 回测历史信号，生成匹配记录
python scripts/abu/abu_backtest_pattern_matches.py --start-date 2025-01-01

# 步骤3: 评估ABU历史信号（生成评估数据）
python scripts/abu/abu_evaluate_signals.py --start-date 2025-01-01
```

### 3. 训练模型

```bash
# 训练价格行为特征学习模型（最高优先级）
python src/ml_dl/abu_price_action_learner.py --train

# 训练模式匹配预测模型
python src/ml_dl/abu_pattern_match_predictor.py --train

# 训练候选信号评分模型
python src/ml_dl/abu_candidate_scorer.py --train

# 优化模式权重（可选，基于历史数据）
python src/ml_dl/abu_pattern_weight_optimizer.py --optimize
```

### 4. 使用模型

```bash
# 生成ABU信号 (自动使用ML模型)
python scripts/pa_scan_15m_top10.py --use-ml

# 优化模式权重
python src/ml_dl/abu_pattern_weight_optimizer.py --optimize
```

---

## 📈 预期效果

### 短期 (1个月)

**阶段0完成（必须）**:
- ✅ Gemini Vision API完整分析1000张图片
- ✅ 智能解析Gemini输出，提取多模式组合和交易参数
- ✅ 更新pattern_library表，gemini_annotation_json字段填充率 > 80%
- ✅ 验证Gemini分析结果质量

**阶段1-2开始**:
- ✅ 建立模式匹配历史数据收集机制
- ✅ 训练价格行为特征学习模型（基于Gemini分析）
- ✅ 训练基础ML模型 (Random Forest/XGBoost)
- ✅ ML模型准确率 > 60% (优于随机)

### 中期 (3个月)

- ✅ 模式权重自动优化
- ✅ ML评分模型替代部分规则评分
- ✅ 模式匹配预测准确率 > 70%
- ✅ 信号质量提升 (胜率+5%, 盈亏比+10%)

### 长期 (6个月)

- ✅ 深度学习模型 (LSTM/Transformer)
- ✅ 端到端优化 (从模式识别到信号生成)
- ✅ 模式匹配预测准确率 > 80%
- ✅ 交易信号质量显著提升 (胜率+10%, 盈亏比+20%)

---

## 📝 注意事项

1. **数据质量**: 确保模式匹配历史和信号评估数据准确完整
2. **模型版本管理**: 使用模型版本控制，支持回滚
3. **过拟合防范**: 使用交叉验证，监控验证集表现
4. **实时性要求**: ML预测延迟 < 100ms
5. **可解释性**: 提供特征重要性分析，便于调试

---

## 🔗 相关文件

### 现有文件
- `src/abu/detectors.py` - 模式检测器
- `src/abu/ranker.py` - 评分排序器
- `scripts/pa_scan_15m_top10.py` - ABU信号生成脚本
- `config/abu_pattern_weights.yaml` - 模式权重配置
- `src/data/qingniao_abu.duckdb` - ABU数据库

### 新增文件（按优先级排序）

#### 阶段0: Gemini分析相关 ✅ **已完成**
- ✅ `src/abu/gemini_vision_analyzer.py` - **核心模块**：Gemini Vision图形识别分析器
  - ✅ 独立模块：只用于图形识别，不做其他用途
  - ✅ 成本控制：强制使用Flash，禁止Pro
  - ✅ 去重机制：SHA1检查、输出文件检查、缓存检查
  - ✅ 断点续传：状态文件保存，支持中断后继续
  - ✅ 健壮性：完整错误处理、重试机制、详细日志
  - ✅ 运行/休息机制：运行3小时，休息1小时
- ✅ `scripts/abu/abu_parse_gemini_output.py` - 智能解析Gemini输出（标准化格式）
- ✅ `scripts/abu/abu_update_pattern_library_from_gemini.py` - 更新模式库数据
- ✅ `scripts/abu/abu_verify_gemini_analysis.py` - 验证Gemini分析结果质量
- ✅ `scripts/abu/abu_optimize_speed.py` - 速度优化版分析脚本
- ✅ `scripts/abu/abu_run_stage0_full.py` - 完整版分析脚本

#### 阶段1-2: ML模型相关 ⚠️ **待实施**
- ⚠️ `src/ml_dl/abu_price_action_learner.py` - 价格行为特征学习器（最高优先级）
- ⚠️ `src/ml_dl/abu_pattern_match_predictor.py` - 模式匹配预测器
- ⚠️ `src/ml_dl/abu_pattern_weight_optimizer.py` - 权重优化器
- ⚠️ `src/ml_dl/abu_candidate_scorer.py` - ML评分器

#### 阶段1: 数据准备相关 ⚠️ **待实施**
- ⚠️ `scripts/abu/abu_record_match_history.py` - 记录匹配历史
- ⚠️ `scripts/abu/abu_evaluate_signals.py` - 评估ABU信号
- ⚠️ `scripts/abu/abu_backtest_pattern_matches.py` - 回测历史匹配
- ⚠️ `scripts/abu/abu_init_ml_tables.py` - 初始化ML相关表

#### 电子书集成相关 ✅ **已完成**
- ✅ `src/abu/ebook_knowledge_retriever.py` - 电子书知识检索器
- ✅ `scripts/abu/abu_create_ebook_tables.py` - 创建电子书表
- ✅ `scripts/abu/abu_extract_ebook_text.py` - 提取电子书文本
- ✅ `scripts/abu/abu_analyze_ebook_text.py` - 分析电子书文本
- ✅ `scripts/abu/abu_link_ebook_to_patterns.py` - 关联电子书和模式

#### 信号生成相关 ✅ **已完成**
- ✅ `scripts/abu/abu_gemini_signal_scanner_enhanced.py` - 增强信号扫描器
- ✅ `scripts/abu/abu_gemini_signal_scanner.py` - 基础信号扫描器
- ✅ `src/abu/gemini_pattern_matcher_enhanced.py` - 增强模式匹配器（含电子书验证）
- ✅ `src/abu/gemini_pattern_matcher_talib_enhanced.py` - TA-Lib增强版
- ✅ `src/abu/gemini_pattern_matcher_al_brooks_enhanced.py` - Al Brooks增强版

#### 阶段3-4: 模型集成与监控
- `scripts/abu/abu_retrain_ml_models.py` - 定期重训练模型
- `scripts/abu/abu_ml_model_evaluation.py` - 模型评估脚本
- `scripts/abu/check_abu_db_size.py` - 数据库容量检查脚本

#### 现有文件增强
- `src/abu/detectors.py` - 需要增强：集成Gemini模式匹配和价格行为学习
- `src/abu/ranker.py` - 需要增强：集成Gemini概率和价格行为预测
- `scripts/pa_scan_15m_top10.py` - 需要增强：使用增强后的检测器和评分器

---

---

## 📋 实施优先级总结

### P0（立即执行，必须完成）

1. **Gemini Vision API完整分析1000张图片** ⭐⭐⭐
   - 使用增强Prompt提取多模式组合、K线行为、交易参数
   - 智能解析Gemini输出
   - 更新pattern_library表
   - **这是所有ML训练的基础，必须首先完成**

2. **价格行为特征学习模型** ⭐⭐⭐
   - 基于Gemini分析结果学习价格行为特征
   - 学习模式组合、K线行为、交易参数的关系
   - **核心：从Gemini识别的内容中学习，而不仅仅是模式匹配**

### P1（1-2周内）

3. **模式匹配成功率预测模型**
4. **候选信号评分模型（集成Gemini概率）**
5. **信号生成流程增强（集成Gemini和价格行为学习）**

### P2（1个月内）

6. **模式权重自动优化**
7. **模型集成与A/B测试**
8. **模型性能监控**

---

**创建时间**: 2026-01-10  
**最后更新**: 2026-01-10（完善Gemini模块：成本控制、断点续传、健壮性）  
**状态**: 方案设计完成，待实施 🔄  

**关键变更**: 
- ✅ 添加Gemini Vision API完整分析1000张图片的流程（阶段0）
- ✅ 创建独立模块 `src/abu/gemini_vision_analyzer.py`（成本可控、断点续传、去重）
- ✅ 添加智能解析Gemini输出的系统
- ✅ 添加价格行为特征学习模型（最高优先级）
- ✅ 增强信号生成流程，集成Gemini匹配和价格行为学习
- ✅ 移除Dream系统相关内容
- ✅ **完善成本控制机制**：强制Flash、去重、成本估算
- ✅ **完善健壮性**：断点续传、错误处理、详细日志

**相关文档**:
- `docs/design/features/Gemini_Vision_模块使用说明.md` - 快速使用指南

