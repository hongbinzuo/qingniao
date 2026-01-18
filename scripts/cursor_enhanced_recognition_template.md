# Cursor AI增强识别模板（用于实时匹配）

## 识别要求

在识别图片时，**必须同时输出**：
1. 原有的文本描述（便于人类阅读）
2. **结构化JSON特征**（便于程序匹配）

## 输出格式

```markdown
# Cursor AI识别结果 - {image_name}

## 图表概览
（原有格式保持不变）

## 结构化特征（新增 - JSON格式）

```json
{
  "pattern_type": "bull_breakout",
  "pattern_subtype": "above_trading_range_mm_up",
  "direction": "long",
  "confidence": 0.85,
  
  "kline_features": {
    "consecutive_bull_bars": 2,
    "bull_bars_closing_near_high": {
      "count": 2,
      "min_ratio": 0.90,
      "bar_indices": [19, 20]
    },
    "bars_above_ema": 2,
    "second_body_above_ema": true,
    "ema_relationship": "above_price"
  },
  
  "price_levels": {
    "breakout_level": 87500.0,
    "trading_range": {
      "high": 87400.0,
      "low": 87200.0
    },
    "support_levels": [87200.0, 87000.0],
    "resistance_levels": [87500.0, 88000.0]
  },
  
  "pattern_structure": {
    "phases": [
      {
        "phase": "trading_range",
        "start_bar": 0,
        "end_bar": 18,
        "duration": 18,
        "characteristics": ["sideways", "consolidation"]
      },
      {
        "phase": "bull_breakout",
        "start_bar": 19,
        "end_bar": 22,
        "duration": 3,
        "characteristics": ["consecutive_bull_bars", "above_ema", "breakout"]
      }
    ],
    "total_bars": 22
  },
  
  "trading_signals": {
    "entry": {
      "type": "buy_the_close",
      "bar_index": 20,
      "condition": "2nd_body_completely_above_ema",
      "price_calculation": "close_of_breakout_bar"
    },
    "stop_loss": {
      "type": "below_trading_range_low",
      "price": 87200.0,
      "distance_pct": 0.46,
      "reason": "below_range_low"
    },
    "take_profit": {
      "type": "measured_move",
      "method": "body_size_projection",
      "target_price": 87750.0,
      "distance_pct": 1.71,
      "calculation": "breakout_level + (avg_body_size * 2)"
    }
  },
  
  "quantified_indicators": {
    "ema_position": "above_price",
    "measured_move": {
      "enabled": true,
      "method": "body_size",
      "target_distance": 250.0,
      "units": "ticks"
    },
    "rally_requirements": {
      "min_ticks": 82,
      "target_points": 20
    }
  },
  
  "market_conditions": {
    "trend": "bullish",
    "volatility": "medium",
    "context": "trading_range_breakout",
    "time_of_day": "midday"
  }
}
```

## 原有格式（保持不变）
（原有的文本描述、模式识别、交易信号等部分）

## 特征提取规则

### 1. K线特征量化
- **consecutive_bull_bars**: 连续阳线数量
- **close_to_high_ratio**: 收盘价接近最高价的比例（0-1）
- **bars_above_ema**: 在EMA上方的K线数量

### 2. 价格级别提取
- 从图表中识别具体的价格数值
- 如果无法精确识别，使用相对描述（如"above_ema"）

### 3. 模式阶段划分
- 按照时间顺序划分模式的不同阶段
- 记录每个阶段的起始和结束K线索引

### 4. 交易信号量化
- 入场：具体的K线位置和价格
- 止损：具体的价格或计算方式
- 止盈：目标价格或计算方法

### 5. 数值提取
- 从文本中提取所有数值（如"20 points", "82 tick"）
- 保持原始单位和数值

## 注意事项

1. **如果无法确定具体数值**，使用描述性标记（如"unknown", "relative"）
2. **保持JSON格式有效**，确保可以解析
3. **数值单位要明确**（ticks, points, percentage）
4. **bar_index从0开始计数**，第一根K线为0

## 示例输出

见上面的JSON格式示例。

