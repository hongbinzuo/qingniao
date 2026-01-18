# ABU Gemini信号生成系统设计

## 📋 概述

全新的信号生成系统，基于Gemini Vision API学习的价格行为特征库进行实时匹配，替代原有的简单模式检测器。

**核心思想**：
- 从pattern_library表读取Gemini分析的价格行为特征（429个模式，未来扩展到9000+）
- 获取实时TOP 20加密货币的K线数据（15分钟、1小时级别，7天范围）
- 将实时K线特征与模式库特征进行匹配
- 匹配度高的模式生成交易信号

---

## 🔄 系统架构

```
TOP 20 加密货币列表
    ↓
获取实时K线数据（15m/1h，7天范围）
    ↓
从pattern_library加载Gemini特征（429个模式）
    ↓
提取实时K线特征
    ├─ K线行为特征（engulfing, pin_bar, inside_bar等）
    ├─ 趋势特征（15m和1h时间框架）
    ├─ 波动率特征
    └─ 成交量特征
    ↓
特征匹配（calculate_similarity）
    ├─ K线特征匹配（权重0.4）
    ├─ 趋势匹配（权重0.3）
    ├─ 波动率匹配（权重0.2）
    └─ ML模型预测匹配（权重0.1，可选）
    ↓
计算匹配度（相似度分数0.0-1.0）
    ↓
过滤低匹配度信号（默认阈值0.5）
    ↓
生成交易信号
    ├─ 从Gemini标注提取交易参数（方向、止损、止盈）
    ├─ 计算综合评分（相似度 + 概率）
    └─ 添加模式信息
    ↓
全局排序，选择Top N
    ↓
保存到数据库 + 生成Markdown报告
```

---

## 📊 核心组件

### 1. GeminiPatternMatcher（模式匹配器）

**文件**: `src/abu/gemini_pattern_matcher.py`

**主要功能**：

#### 1.1 加载模式库
```python
def _load_pattern_library(self):
    """从数据库加载所有有Gemini标注的模式"""
    # 查询pattern_library表
    # 解析gemini_annotation_json字段
    # 构建模式库索引
```

- 从`pattern_library`表读取所有有Gemini标注的记录
- 解析`gemini_annotation_json`字段
- 当前：429个模式，未来扩展到9000+

#### 1.2 实时特征提取
```python
def extract_realtime_features(klines_15m, klines_1h) -> Dict:
    """从实时K线数据提取特征"""
```

**提取的特征**：
- **K线行为特征**：
  - 吞没形态（bullish_engulfing, bearish_engulfing）
  - Pin Bar（bullish_pin_bar, bearish_pin_bar）
  - Inside Bar
- **趋势特征**：
  - 15m时间框架趋势（bullish/bearish/neutral）
  - 1h时间框架趋势
  - 趋势强度（基于EMA200）
- **波动率特征**：
  - 价格波动范围
  - 波动率等级（high/low）
- **成交量特征**：
  - 平均成交量
  - 近期成交量比率

#### 1.3 特征匹配算法
```python
def calculate_similarity(realtime_features, pattern_annotation) -> float:
    """计算实时特征与模式库特征的相似度"""
```

**匹配维度**（加权平均）：
1. **K线特征匹配**（权重0.4）
   - 计算实时K线特征与模式K线特征的交集
   - 使用Jaccard相似度：`intersection / union`

2. **趋势匹配**（权重0.3）
   - 完全匹配：1.0
   - 一方为neutral：0.5
   - 其他：0.0

3. **波动率匹配**（权重0.2）
   - 完全匹配：1.0
   - 部分匹配：0.5

4. **ML模型预测匹配**（权重0.1，可选）
   - 使用价格行为学习模型预测实时K线的价格行为
   - 与模式类型进行比较

**最终相似度** = 加权平均，范围0.0-1.0

#### 1.4 模式匹配
```python
def match_patterns(klines_15m, klines_1h, min_similarity=0.5, max_matches=10):
    """匹配模式库中的模式"""
```

- 对每个币种的K线数据，匹配所有模式
- 过滤低于阈值的匹配（默认0.5）
- 按相似度排序，返回Top N

#### 1.5 信号生成
```python
def generate_signal_from_match(match, current_price, klines_15m):
    """从匹配结果生成交易信号"""
```

**信号参数来源**：
1. **方向**：从Gemini标注的trading_signals提取，或从pattern_type推断
2. **入场价**：当前价格
3. **止损**：从Gemini标注提取，或从K线数据计算（最近低点/高点）
4. **止盈**：从Gemini标注提取，或基于止损计算（默认1.5:1 RR）
5. **概率**：从Gemini标注提取，或使用相似度作为概率

---

### 2. ABU Gemini信号扫描器

**文件**: `scripts/abu_gemini_signal_scanner.py`

**主要流程**：

#### 2.1 初始化
- 加载模式匹配器（自动加载模式库）
- 设置扫描参数

#### 2.2 扫描币种
对TOP 20加密货币：
1. 获取K线数据：
   - 15m K线：672根（7天）
   - 1h K线：168根（7天）
2. 匹配模式：
   - 调用`match_patterns()`
   - 每个币种最多匹配N个模式（默认3个）
3. 生成信号：
   - 为每个匹配生成交易信号
   - 计算综合评分

#### 2.3 信号评分
```python
score = (similarity * 0.7 + probability * 0.3) * 100
```

- 相似度权重：0.7
- 概率权重：0.3
- 范围：0-100

#### 2.4 输出
1. **数据库**：保存到`trading_signals`表
2. **Markdown报告**：包含匹配详情和信号参数

---

## 🎯 优势特点

### 相比原有系统的改进

1. **丰富的模式库**：
   - 原有：4种简单模式（Inside Bar, Engulfing, Pin Bar, Key Levels）
   - 现在：429个Gemini学习的复杂模式（未来扩展到9000+）

2. **智能匹配**：
   - 原有：简单的规则检测
   - 现在：多维度特征匹配，考虑K线行为、趋势、波动率等

3. **学习能力**：
   - 原有：固定规则
   - 现在：基于Gemini Vision API学习的真实价格行为模式

4. **可扩展性**：
   - 模式库持续增长（400页 → 1000页 → 9000页）
   - 匹配算法可以优化和增强

5. **ML集成**：
   - 可选使用价格行为学习模型辅助匹配
   - 未来可以加入深度学习模型

---

## 📈 使用方式

### 基本用法

```bash
# 生成Top 10信号
python scripts/abu_gemini_signal_scanner.py --top 10 --exchange binance --write-db 1

# 调整匹配阈值（更严格）
python scripts/abu_gemini_signal_scanner.py --top 10 --min-similarity 0.6

# 每个币种匹配更多模式
python scripts/abu_gemini_signal_scanner.py --top 10 --max-matches-per-symbol 5
```

### 参数说明

- `--top N`: 生成Top N个信号（默认10）
- `--exchange NAME`: 交易所（binance/gate，默认binance）
- `--write-db 0/1`: 是否写入数据库（默认1）
- `--min-similarity FLOAT`: 最小相似度阈值（0.0-1.0，默认0.5）
- `--max-matches-per-symbol N`: 每个币种最大匹配数（默认3）

---

## 🔧 技术细节

### 数据需求

1. **模式库数据**：
   - 来源：`pattern_library`表的`gemini_annotation_json`字段
   - 当前规模：429个模式
   - 目标规模：9000+模式

2. **实时K线数据**：
   - 时间框架：15分钟、1小时
   - 数据范围：7天
   - 数据量：
     - 15m: 672根K线（7天 × 96根/天）
     - 1h: 168根K线（7天 × 24根/天）

3. **数据源**：
   - Binance API（优先）
   - Gate.io API（备用）

### 匹配算法优化空间

1. **特征权重优化**：
   - 当前权重是固定的，可以根据历史表现优化
   - 可以使用机器学习优化权重

2. **深度学习集成**：
   - 可以使用CNN处理K线图像特征
   - 可以使用LSTM处理时序特征
   - 可以使用Transformer处理模式特征

3. **相似度计算优化**：
   - 可以使用更复杂的相似度算法（余弦相似度、编辑距离等）
   - 可以引入模式的结构特征匹配

---

## 📊 输出格式

### Markdown报告

```markdown
# ABU Gemini信号 Top10

**生成时间**: 2026-01-11 09:15:00
**模式库规模**: 429 个模式
**匹配阈值**: 50%

| # | Symbol | Direction | Entry | SL | TP1 | TP2 | Similarity | Score | Pattern |
|---|---|:---:|---:|---:|---:|---:|---:|:---:|---|
| 1 | BTC | long | 50000.00 | 49800.00 | 50200.00 | 50400.00 | 75% | 82.50 | Head and Shoulders |
...
```

### 数据库记录

- `system_name`: 'abu'
- `entry_model`: 'Abu/Gemini/{pattern_name}'
- `score`: 综合评分（0-100）
- `notes`: 匹配详情和相似度

---

## 🚀 未来改进方向

1. **模式库扩展**：
   - 继续Gemini分析，扩展到9000+模式
   - 提高模式覆盖度

2. **匹配算法优化**：
   - 引入深度学习模型
   - 优化特征权重
   - 引入模式结构匹配

3. **性能优化**：
   - 模式库索引优化
   - 并行匹配处理
   - 缓存机制

4. **信号质量提升**：
   - 加入更多过滤条件
   - 引入历史表现数据
   - 实时信号验证

---

**创建时间**: 2026-01-11  
**状态**: ✅ 已实现



