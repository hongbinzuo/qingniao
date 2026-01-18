# Cursor AI增强识别指南（结构化特征版）

## 说明

从本次开始，所有识别结果都将包含：
1. **原有文本描述**（便于人类阅读）
2. **结构化JSON特征**（便于程序匹配实时价格图表）

## 识别Prompt

在Cursor中识别图片时，使用以下prompt（已保存到 `scripts/cursor_enhanced_prompt.txt`）：

```
你是专业的交易图表分析专家。请详细分析这张价格行为图表图片，并按照以下格式输出识别结果：

[包含文本描述和结构化JSON的要求]
```

完整prompt内容请查看：`scripts/cursor_enhanced_prompt.txt`

## 输出格式要求

### 1. 文本描述部分（保持原有格式）
- 图表概览
- 关键概念
- 完整价格路径
- 模式识别
- 交易信号
- 价格行为分析
- 市场条件
- 完整叙述

### 2. 结构化JSON部分（新增）

在文本描述之后，必须包含一个有效的JSON对象，格式如下：

```json
{
  "pattern_type": "模式类型",
  "pattern_subtype": "子类型",
  "direction": "long/short/neutral",
  "confidence": 0.85,
  "kline_features": { ... },
  "price_levels": { ... },
  "pattern_structure": { ... },
  "trading_signals": { ... },
  "quantified_indicators": { ... },
  "market_conditions": { ... }
}
```

完整格式模板请查看：`scripts/cursor_enhanced_recognition_template.md`

## 特征提取规则

1. **数值提取**：从文本中提取所有数值（如"20 points", "82 tick"）
2. **K线特征量化**：连续K线数量、收盘价比例、EMA关系等
3. **价格级别**：突破位、支撑阻力位（如果可见）
4. **模式阶段**：按时间顺序划分，记录K线索引
5. **交易信号**：具体的入场、止损、止盈条件

## 注意事项

- JSON必须有效，可以解析
- 如果无法确定具体数值，使用null
- bar_index从0开始计数
- 数值单位要明确（ticks, points, percentage）

## 示例结果

查看增强版识别结果示例：
- `outputs/cursor_ai_recognition/results/page_0439_img_01_clip_enhanced.txt`

## 下一步

1. 使用增强prompt重新识别图片
2. 从结果中提取JSON并单独保存
3. 用于实时价格图表匹配

