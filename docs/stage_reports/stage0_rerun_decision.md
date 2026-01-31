# 阶段0重新运行决策报告

## 评估结果

### 当前结果质量分析（639条记录）

**问题发现：**
1. ❌ **chart_overview缺失率: 100%** (639/639)
2. ❌ **complete_price_path缺失率: 100%** (639/639)
3. ❌ **complete_narrative缺失率: 100%** (639/639)

**良好指标：**
- ✅ JSON解析错误率: 0.3% (2/639) - 极低
- ✅ 平均patterns: 3.0/张 - 良好
- ✅ 平均signals: 1.2/张 - 可接受

## 问题根源

当前结果是在**Prompt优化之前**生成的，因此：
- 缺少新要求的关键字段（chart_overview, complete_price_path, complete_narrative）
- 这些字段是完整图表描述的核心，对后续ML训练至关重要
- 虽然patterns和signals提取率不错，但缺少整体上下文信息

## 决策：重新运行全部1000张图片

### 理由
1. **已优化Prompt** - 明确要求返回完整字段（chart_overview, complete_price_path, complete_narrative）
2. **已改进JSON解析** - 更健壮的解析逻辑，支持多种格式
3. **当前结果质量不达标** - 关键字段缺失率100%，无法满足后续ML训练需求

### 优化措施
1. **Prompt增强**：
   - 明确要求描述整张图的完整情况
   - 要求返回complete_narrative（完整叙述）
   - 要求返回chart_overview（图表概览）
   - 要求返回complete_price_path（完整价格路径）
   - 强调JSON格式要求（纯JSON，无markdown）

2. **JSON解析改进**：
   - 多种解析方法（直接解析、markdown提取、括号匹配）
   - JSON格式修复（移除尾随逗号、转义控制字符）
   - 更详细的错误日志

## 执行计划

1. ✅ **清空现有输出** - `python scripts/abu/abu_reset_stage0.py`
2. ✅ **重新处理全部1000张图片** - `python scripts/abu/abu_optimize_speed.py`
3. ⏳ **监控处理进度** - 预计耗时约5.5小时
4. ⏳ **处理完成后验证** - 检查新字段提取率
5. ⏳ **如有问题，进一步优化Prompt**

## 预期结果

- ✅ chart_overview提取率: >80%
- ✅ complete_price_path提取率: >80%
- ✅ complete_narrative提取率: >90%
- ✅ JSON解析错误率: <5%
- ✅ 平均patterns: >2.0/张
- ✅ 平均signals: >0.8/张

## 成本估算

- 总图片数: 1000张
- 单张成本: $0.000125（Gemini 2.5 Flash Image）
- 总预计成本: $0.125（约¥0.9元）

## 时间估算

- 平均处理速度: 20秒/张（含API延迟和日志）
- 总预计时间: 约5.5小时
- 建议：后台运行，定期检查进度

---

**生成时间**: 2026-01-11 00:20
**状态**: 已启动重新运行



