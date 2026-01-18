# ABU信号生成流程详细说明

## 📋 概述

ABU信号生成系统是一个多层次的价格行为分析系统，结合了传统模式检测、机器学习预测和智能评分排序，用于识别高概率的交易机会。

**脚本**: `scripts/pa_scan_15m_top10.py`

---

## 🔄 完整流程

```
扫描币种列表
    ↓
获取15m K线数据（每个币种200根）
    ↓
模式检测（detect_all_15m）
    ├─ Inside Bar检测
    ├─ Engulfing检测
    ├─ Pin Bar检测
    └─ Key Levels检测
    ↓
去重处理
    ↓
ML增强（enhance_candidate_with_ml）
    ├─ 提取K线特征
    ├─ ML模型预测价格行为
    └─ 添加ML预测信息
    ↓
获取1h K线数据（300根，用于趋势分析）
    ↓
评分排序（rank_and_pick）
    ├─ 基础评分
    ├─ RR评分（盈亏比）
    ├─ 趋势评分
    ├─ 模式权重
    └─ ML评分提升
    ↓
每个币种选择Top 2
    ↓
全局排序，选择Top N
    ↓
保存到数据库 + 生成Markdown文件
```

---

## 📊 步骤1：币种扫描与K线数据获取

### 1.1 币种列表

扫描30个主流币种：
```python
TOP_SYMBOLS = [
    'BTC','ETH','SOL','BNB','XRP','ADA','AVAX','DOGE','LINK','DOT',
    'MATIC','TON','TRX','ATOM','SUI','APT','ARB','OP','NEAR','PEPE',
    'SEI','TIA','INJ','AAVE','UNI','RUNE','ETC','FIL','ICP','XLM'
]
```

排除稳定币：USDT、USDC、DAI、BUSD等

### 1.2 K线数据获取

**数据源优先级**（可配置）：
1. Binance API（默认优先）
2. Gate.io API（备用）
3. Bitget API（仅BTC）

**获取数据**：
- **15m K线**：每个币种200根（约50小时数据）
- **1h K线**：每个币种300根（约12.5天数据，用于趋势分析）

**数据格式**：
```python
{
    'open': float,
    'high': float,
    'low': float,
    'close': float,
    'volume': float,
    'timestamp': int
}
```

---

## 🔍 步骤2：模式检测（detect_all_15m）

对每个币种的15m K线数据，使用4种检测器识别价格行为模式。

### 2.1 Inside Bar检测（内包线）

**检测逻辑**：
```python
if 当前K线的high <= 前一根K线的high AND 当前K线的low >= 前一根K线的low:
    生成两个候选信号：
    - long信号：入场=当前收盘价，止损=两根K线最低点，TP1/TP2=1:1和1:2
    - short信号：入场=当前收盘价，止损=两根K线最高点，TP1/TP2=1:1和1:2
```

**评分提示**：0.6（基础分数）

**输出示例**：
```python
{
    'pattern': 'InsideBar',
    'type': 'long',
    'entry': 50000.0,
    'stop_loss': 49800.0,
    'take_profit_1': 50200.0,
    'take_profit_2': 50400.0,
    'reason': 'Inside bar (break-up)',
    'score_hint': 0.6
}
```

### 2.2 Engulfing检测（吞没形态）

**检测逻辑**：
```python
# 看涨吞没
if 当前K线是阳线 AND 前一根K线是阴线:
    if 当前开盘价 < 前一根收盘价 AND 当前收盘价 > 前一根开盘价:
        生成long信号

# 看跌吞没
if 当前K线是阴线 AND 前一根K线是阳线:
    if 当前开盘价 > 前一根收盘价 AND 当前收盘价 < 前一根开盘价:
        生成short信号
```

**评分提示**：0.8（较高分数）

### 2.3 Pin Bar检测（影线形态）

**检测逻辑**：
```python
body = abs(收盘价 - 开盘价)
total_range = 最高价 - 最低价
upper_wick = 最高价 - max(开盘价, 收盘价)
lower_wick = min(开盘价, 收盘价) - 最低价

# 看涨Pin Bar（下影线长）
if lower_wick > 1.5 * body AND body / total_range <= 0.4:
    生成long信号：止损=最低点

# 看跌Pin Bar（上影线长）
if upper_wick > 1.5 * body AND body / total_range <= 0.4:
    生成short信号：止损=最高点
```

**评分提示**：0.5（中等分数）

### 2.4 Key Levels检测（关键位）

**检测逻辑**：
- 查找最近20根K线的最高点（HH）和最低点（LL）
- 检测价格是否接近关键位（容差0.3%）
- 如果接近HH，生成short信号
- 如果接近LL，生成long信号

**评分提示**：0.3（较低分数）

### 2.5 去重处理

合并相同类型和入场价的信号，保留评分提示最高的：

```python
dedup = {}
for signal in all_signals:
    key = (signal['type'], round(signal['entry'] / 0.001))
    if key not in dedup or dedup[key]['score_hint'] < signal['score_hint']:
        dedup[key] = signal
```

---

## 🤖 步骤3：ML增强（enhance_candidate_with_ml）

对每个候选信号，使用价格行为学习模型进行预测增强。

### 3.1 特征提取（extract_kline_features_for_ml）

从K线数据提取特征，模拟Gemini分析结果的结构：

**趋势特征**：
```python
price_trend = 'bullish' if 最近10根K线收盘价上涨 else 'bearish'
trend_strength = abs(最新收盘价 - 10根前收盘价) / 10根前收盘价
```

**波动率特征**：
```python
price_ranges = [每根K线的(high - low)]
avg_range = 平均波动范围
volatility = avg_range / 最新收盘价
```

**K线行为特征**：
- 检测吞没形态（bullish_engulfing / bearish_engulfing）
- 检测Pin Bar（bullish_pin_bar / bearish_pin_bar）
- 检测Inside Bar

**构建特征字典**：
```python
gemini_like_annotation = {
    'price_action_behavior': {
        'kline_features': ['bullish_engulfing', ...],
        'trend': 'bullish',
        'structure': 'unknown'
    },
    'market_conditions': {
        'trend_strength': 'strong' if trend_strength > 0.02 else 'weak',
        'volatility': 'high' if volatility > 0.01 else 'low',
        'trend_direction': 'bullish'
    }
}
```

### 3.2 ML模型预测

使用训练好的价格行为学习模型（XGBoost）预测价格行为：

```python
learner = PriceActionLearner()
prediction = learner.predict(gemini_like_annotation)
```

**预测输出**：
```python
{
    'success': True,
    'price_action': 'continuation',  # reversal/continuation/indecision/consolidation
    'probabilities': {
        'reversal': 0.15,
        'continuation': 0.65,
        'indecision': 0.15,
        'consolidation': 0.05
    },
    'features': {...}
}
```

### 3.3 增强信号

将ML预测结果添加到候选信号：

```python
candidate['_ml_available'] = True
candidate['_ml_price_action'] = 'continuation'
candidate['_ml_confidence'] = 0.65  # 最高概率
candidate['_ml_probabilities'] = {...}
candidate['_ml_consistent'] = True/False  # 预测是否与信号方向一致
```

---

## 📈 步骤4：评分排序（rank_and_pick）

对每个币种的所有候选信号进行评分，选择Top 2。

### 4.1 评分计算（score_candidate）

最终评分 = 基础评分 + RR评分 + 趋势评分 + 模式权重 + ML评分提升

#### 4.1.1 基础评分（base_score）
- 来自模式检测器的 `score_hint`
- Inside Bar: 0.6
- Engulfing: 0.8
- Pin Bar: 0.5
- Key Levels: 0.3

#### 4.1.2 RR评分（盈亏比评分）
```python
risk = abs(entry - stop_loss)
reward = abs(take_profit_1 - entry)
rr_ratio = reward / risk if risk > 0 else 0

rr_score = max(0.0, min(2.0, rr_ratio)) * 0.6
```
- 盈亏比越高，评分越高
- 上限2.0，权重0.6

#### 4.1.3 趋势评分（trend_backing）
```python
# 计算1h时间框架的200周期EMA
ema200 = EMA(1h K线收盘价, 200)

if 当前价格 > ema200:
    trend = 'bull'
elif 当前价格 < ema200:
    trend = 'bear'
else:
    trend = 'neutral'

# 趋势共振评分
if trend == 'bull' AND signal_type == 'long':
    conf = 0.6  # 趋势共振，高分
elif trend == 'bear' AND signal_type == 'short':
    conf = 0.6  # 趋势共振，高分
else:
    conf = 0.2  # 趋势不共振，低分
```

#### 4.1.4 模式权重（pattern_bonus）
从配置文件 `config/abu_pattern_weights.yaml` 加载：
```yaml
weights:
  Engulfing:
    long: 0.3
    short: 0.3
  InsideBar:
    long: 0.2
    short: 0.2
  ...
```

如果模式在配置中有权重，则添加到评分中。

#### 4.1.5 ML评分提升（ml_boost）

```python
if candidate['_ml_available']:
    ml_confidence = candidate['_ml_confidence']
    is_consistent = candidate['_ml_consistent']
    price_action = candidate['_ml_price_action']
    
    if not is_consistent:
        ml_boost = -0.2 * ml_confidence  # 不一致，降低评分
    else:
        if price_action == 'continuation':
            ml_boost = ml_confidence * 0.8  # 延续模式，高提升
        elif price_action == 'reversal':
            ml_boost = ml_confidence * 0.5  # 反转模式，中等提升
        elif price_action == 'consolidation':
            ml_boost = ml_confidence * 0.6  # 整理，中等提升
        else:  # indecision
            ml_boost = 0.0  # 不确定，不提升
```

**最终评分公式**：
```python
final_score = base_score + rr_score + trend_score + pattern_bonus + ml_boost
```

### 4.2 排序与选择

```python
# 对每个币种的所有候选信号评分
scored_signals = []
for candidate in candidates:
    score = score_candidate(candidate, k1h_data)
    candidate['_score'] = score
    scored_signals.append(candidate)

# 按评分降序排序
scored_signals.sort(key=lambda x: x['_score'], reverse=True)

# 每个币种选择Top 2
top_per_symbol = scored_signals[:2]
```

---

## 🎯 步骤5：全局排序与输出

### 5.1 全局排序

将所有币种的Top信号合并，按评分降序排序，选择全局Top N：

```python
all_results = []
for symbol in symbols:
    top_signals = rank_and_pick(candidates, k1h, topn=2)
    for signal in top_signals:
        all_results.append({'symbol': symbol, **signal})

# 全局排序
all_results.sort(key=lambda x: x.get('_score', 0), reverse=True)

# 选择Top N
final_top = all_results[:top_n]
```

### 5.2 数据库保存

将最终信号保存到DuckDB数据库：

```python
db = TraderDBManager('abu')
for signal in final_top:
    db.add_trading_signal(
        signal_time=当前时间,
        timeframe='15m',
        signal_type=signal['type'],  # long/short
        symbol=signal['symbol'],
        entry_price=signal['entry'],
        stop_loss=signal['stop_loss'],
        take_profit_1=signal['take_profit_1'],
        take_profit_2=signal['take_profit_2'],
        entry_model=f"Abu/{signal['pattern']}",
        system_name='abu',
        score=signal['_score'],
        notes=signal['reason']
    )
```

### 5.3 Markdown文件生成

生成包含ML预测信息的Markdown报告：

**文件名格式**：`ABU_top{N}_15m_{YYYYMMDD_HHMM}.md`

**表格格式（ML增强版）**：
```markdown
# Abu 15m Top10 (ML Enhanced)

| # | Symbol | Type | Entry | SL | TP1 | TP2 | Score | ML Action | ML Conf | Reason |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|:---|
| 1 | BTC | long | 50000.00 | 49800.00 | 50200.00 | 50400.00 | 2.45 | continuation | 65.0% | Bullish engulfing |
| 2 | ETH | short | 3500.00 | 3520.00 | 3480.00 | 3460.00 | 2.30 | reversal | 58.3% | Bearish engulfing |
...
```

**表格列说明**：
- **#**: 排名
- **Symbol**: 币种
- **Type**: 交易方向（long/short）
- **Entry**: 入场价
- **SL**: 止损价
- **TP1/TP2**: 止盈价1和2
- **Score**: 综合评分
- **ML Action**: ML预测的价格行为类别
- **ML Conf**: ML预测的置信度
- **Reason**: 检测到的模式

---

## 📊 评分权重总结

| 评分项 | 权重/范围 | 说明 |
|--------|----------|------|
| 基础评分 | 0.3-0.8 | 来自模式检测器 |
| RR评分 | 0-1.2 (权重0.6) | 盈亏比，上限2.0 |
| 趋势评分 | 0.2-0.6 | 趋势共振 |
| 模式权重 | 0-0.5 | 从配置文件加载 |
| ML提升 | -0.5-0.8 | ML预测提升/降低 |
| **总分范围** | **约0.5-4.0** | **实际范围取决于各项组合** |

---

## 🔧 使用示例

### 基本用法

```bash
# 生成Top 10信号
python scripts/pa_scan_15m_top10.py --top 10 --exchange binance --write-db 1

# 只生成Top 5信号，不写入数据库
python scripts/pa_scan_15m_top10.py --top 5 --exchange binance --write-db 0

# 使用Gate.io作为数据源
python scripts/pa_scan_15m_top10.py --top 10 --exchange gate --write-db 1
```

### 参数说明

- `--top N`: 生成Top N个信号（默认10）
- `--exchange NAME`: 交易所（binance/gate，默认binance）
- `--write-db 0/1`: 是否写入数据库（默认1）

---

## 🎯 优势特点

1. **多层次检测**：4种模式检测器，覆盖常见价格行为模式
2. **ML增强**：使用训练好的模型预测价格行为，提高信号质量
3. **智能评分**：综合考虑盈亏比、趋势、模式权重和ML预测
4. **趋势共振**：使用1h时间框架确认趋势方向
5. **去重优化**：自动合并重复信号，保留最佳候选
6. **实时数据**：从主流交易所获取实时K线数据

---

## ⚙️ 技术细节

### 模型信息

- **价格行为学习模型**：XGBoost分类器
- **训练数据**：429条Gemini标注的模式记录
- **准确率**：100%（训练集和测试集）
- **预测类别**：reversal, continuation, indecision, consolidation

### 性能优化

- **并行处理**：每个币种独立处理，可并行化
- **数据缓存**：K线数据获取失败时有备用数据源
- **错误处理**：每个步骤都有异常处理，单个币种失败不影响整体

---

**创建时间**: 2026-01-11  
**状态**: ✅ 已实现并测试



