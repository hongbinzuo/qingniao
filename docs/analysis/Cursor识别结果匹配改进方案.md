# Cursor识别结果匹配实时价格图表改进方案

## 问题分析

### 当前识别结果的问题

查看当前Cursor识别结果（如`page_0439_img_01_clip.txt`），主要问题：

1. **特征描述过于文本化**
   - ❌ "Consecutive bull bars closing near their highs"
   - ❌ "above EMA with 2nd body completely above EMA"
   - ❌ "Possible MM up based on size of bodies"
   - ✅ 需要：`{"consecutive_bull_bars": 2, "close_to_high_ratio": 0.95, "above_ema_bars": 2}`

2. **缺少量化指标**
   - ❌ "Expect swing up of 20 points above 2nd bull bar, but need 82 tick rally"
   - ✅ 需要：`{"target_distance": 20, "min_rally_ticks": 82, "target_price": 计算值}`

3. **模式结构不清晰**
   - ❌ 只有文本描述，没有时间序列结构
   - ✅ 需要：`{"pattern_phases": [{"phase": "breakout", "bar_range": [10, 15]}, ...]}`

4. **交易信号不够具体**
   - ❌ "入场条件: Breakout Test"
   - ✅ 需要：`{"entry_conditions": {"bar_count": 2, "breakout_level": 价格, "confirmation": "close_above"}}`

5. **与Gemini格式不一致**
   - 现有匹配器期望`gemini_annotation`格式
   - Cursor结果需要转换或增强

## 改进方案

### 方案1：增强识别结果格式（推荐）

在保持原有文本描述的基础上，增加**结构化特征提取**：

```markdown
## 结构化特征（新增）

### 量化K线特征
- **consecutive_bull_bars**: 2
- **bull_bars_close_to_high_ratio**: 0.95
- **bars_above_ema**: 2
- **second_body_above_ema**: true
- **ema_position**: "above_price"

### 价格目标和关键位
- **breakout_level**: 87500.0
- **target_price_mm**: 87750.0
- **stop_loss_level**: 87300.0
- **resistance_levels**: [87500, 88000]
- **support_levels**: [87300, 87000]

### 时间序列结构
- **pattern_phases**: [
    {"phase": "trading_range", "bar_range": [0, 18], "duration": 18},
    {"phase": "bull_breakout", "bar_range": [19, 22], "duration": 3},
    {"phase": "trading_range", "bar_range": [23, 45], "duration": 23}
  ]

### 交易信号（详细）
- **entry_signal**: {
    "type": "breakout_confirmation",
    "condition": "2nd_bar_body_above_ema",
    "entry_price": "close_of_2nd_bar",
    "entry_bar_index": 21
  }
- **stop_loss**: {
    "type": "below_trading_range_low",
    "price": 87300.0,
    "distance_ticks": 200
  }
- **take_profit**: {
    "type": "measured_move",
    "method": "body_size_projection",
    "target_price": 87750.0,
    "distance_ticks": 250
  }
```

### 方案2：添加Gemini兼容格式

在识别结果中添加一个`structured_features.json`部分，与Gemini格式兼容：

```json
{
  "pattern_type": "bull_breakout",
  "pattern_subtype": "above_trading_range_mm_up",
  "direction": "long",
  "confidence": 0.85,
  "kline_features": {
    "bullish_bars": 2,
    "consecutive_bull_bars": 2,
    "bars_closing_near_high": 2,
    "bars_above_ema": 2,
    "second_body_above_ema": true
  },
  "price_action": {
    "breakout_level": 87500.0,
    "trading_range_high": 87400.0,
    "trading_range_low": 87200.0,
    "ema_value": 87350.0,
    "current_price": 87600.0
  },
  "pattern_structure": {
    "phases": [
      {
        "name": "trading_range",
        "start_bar": 0,
        "end_bar": 18,
        "characteristics": ["sideways", "consolidation"]
      },
      {
        "name": "bull_breakout",
        "start_bar": 19,
        "end_bar": 22,
        "characteristics": ["consecutive_bull_bars", "above_ema", "breakout"]
      }
    ]
  },
  "trading_signals": {
    "entry": {
      "type": "buy_the_close",
      "price": "close_of_breakout_bar",
      "condition": "2nd_body_completely_above_ema",
      "bar_index": 21
    },
    "stop_loss": {
      "type": "below_range",
      "price": 87200.0,
      "distance_pct": 0.46
    },
    "take_profit": {
      "type": "measured_move",
      "price": 87750.0,
      "method": "body_size_projection",
      "distance_pct": 1.71
    }
  },
  "market_conditions": {
    "trend": "bullish",
    "volatility": "medium",
    "context": "trading_range_breakout"
  }
}
```

### 方案3：自动特征提取脚本

创建一个后处理脚本，从Cursor识别结果中**自动提取**结构化特征：

```python
# scripts/enhance_cursor_results.py

def extract_quantified_features(cursor_result_text: str) -> Dict:
    """
    从Cursor识别结果文本中提取量化特征
    
    提取规则：
    1. 识别数值（如"20 points", "82 tick"）
    2. 识别K线特征（如"2 consecutive bull bars"）
    3. 识别价格级别（如"above EMA", "below range"）
    4. 识别模式阶段和时间序列
    """
    features = {
        "kline_features": {},
        "price_levels": {},
        "pattern_structure": {},
        "trading_signals": {}
    }
    
    # 使用正则表达式和关键词匹配提取特征
    # ...
    
    return features
```

## 实施建议

### 短期（立即可做）

1. **修改识别Prompt**
   - 在识别时要求AI同时输出文本描述和结构化数据
   - 添加JSON格式的结构化特征输出

2. **后处理增强**
   - 编写脚本对已有识别结果进行增强
   - 提取量化特征并添加到结果文件中

### 中期（1-2周）

3. **统一特征格式**
   - 将Cursor结果转换为Gemini兼容格式
   - 确保两种识别方式的结果可以统一匹配

4. **特征提取优化**
   - 建立特征提取规则库
   - 使用NLP技术从文本中提取量化特征

### 长期（1个月+）

5. **智能特征学习**
   - 训练模型自动从识别文本中提取特征
   - 优化匹配算法，提高匹配准确率

## 匹配效果评估

### 当前问题

使用当前格式匹配实时图表时：
- ❌ 无法精确匹配"consecutive bull bars closing near their highs"
- ❌ 无法计算"above EMA"的具体位置
- ❌ 无法量化"MM up"的目标价格
- ❌ 无法判断模式的演化阶段

### 改进后效果

使用结构化特征后：
- ✅ 可以精确匹配K线数量和位置
- ✅ 可以计算EMA位置并验证K线关系
- ✅ 可以计算目标价格并设置止盈
- ✅ 可以判断当前处于模式的哪个阶段

## 示例：改进前后的对比

### 改进前（当前格式）

```markdown
### 2. Bull Breakout
- **类型**: continuation
- **特征**: Bull Breakout, Consecutive bull bars closing near their highs and above EMA with 2nd body completely above EMA, Buy The Close for possible MM up
- **置信度**: 高
```

**匹配时的问题**：
- 不知道"consecutive"是几根K线
- 不知道"near their highs"的具体比例
- 不知道EMA的具体位置
- 无法计算MM目标

### 改进后（结构化格式）

```json
{
  "phase": "bull_breakout",
  "type": "continuation",
  "kline_features": {
    "consecutive_bull_bars": 2,
    "bars_closing_near_high": {
      "count": 2,
      "close_to_high_ratio": 0.95,
      "bar_indices": [19, 20]
    },
    "ema_relationship": {
      "bars_above_ema": 2,
      "second_body_above_ema": true,
      "ema_value_at_breakout": 87350.0
    }
  },
  "trading_signal": {
    "entry": {
      "type": "buy_the_close",
      "bar_index": 20,
      "condition": "2nd_body_completely_above_ema"
    },
    "take_profit": {
      "type": "measured_move",
      "method": "body_size_projection",
      "target_price": 87750.0,
      "calculation": "breakout_level + (avg_body_size * 2)"
    }
  }
}
```

**匹配时的优势**：
- ✅ 精确知道需要2根连续阳线
- ✅ 可以验证K线收盘价是否接近最高价（>95%）
- ✅ 可以计算EMA并验证K线位置
- ✅ 可以计算并设置精确的目标价格

## 下一步行动

1. **立即行动**：修改识别prompt，要求同时输出结构化特征
2. **本周完成**：编写后处理脚本，增强已有识别结果
3. **下周完成**：测试结构化特征的匹配效果
4. **持续优化**：根据匹配效果调整特征提取规则

---

**创建时间**: 2026-01-12  
**状态**: 待实施

