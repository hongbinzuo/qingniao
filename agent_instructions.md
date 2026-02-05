# Agent图片处理指南

## 任务
处理指定范围的ABU图表图片，提取结构化特征并保存到数据库。

## 步骤
1. 读取提示词：`config/abu_analyzer_prompt.md`
2. 读取向量转换逻辑：`convert_batch.py`的convert_single函数
3. 对每张图片：
   - 路径：`data/abu/images/page_{num:04d}_img_01_clip.png`
   - 用Read读取图片
   - 按提示词分析，输出JSON
   - 转换为向量格式
   - 保存临时文件：`temp_gemini_{num}.json`, `temp_vector_{num}.json`
   - 执行：`python save_agent_result.py {num} {path} temp_gemini_{num}.json temp_vector_{num}.json`
4. 每10张报告进度

## 向量格式
```json
{
  "trend_vector": {"direction": 0.0, "ema_distance": 0.0, "volatility": 0.5, "slope_strength": 0.0},
  "pattern_features": {"primary": "none", "secondary": "none", "direction": "neutral", "complexity": 0.5},
  "market_context": {"cycle": "trading_range", "maturity": "middle", "timeframe": "5m"},
  "metadata": {"confidence": 0.6, "annotation_count": 0, "key_features": [], "vector_summary": "none_middle"}
}
```
