# ABU Gemini处理流程管理器使用说明

## 📋 概述

`scripts/abu_gemini_pipeline_manager.py` 是一个综合的管理工具，用于管理Gemini分析的完整处理流程：

1. **Gemini分析**（步骤1）：使用Gemini Vision API分析图片（完整版约9000+张）
2. **解析Gemini输出**（步骤2）：解析Gemini分析结果，标准化格式
3. **更新pattern_library表**（步骤3）：将解析结果更新到数据库
4. **ML模型训练**（步骤4）：价格行为特征学习模型训练（增量训练）

## 🔄 处理流程

```
Gemini分析（gemini_vision_analyzer.py）
    ↓
解析输出（abu_parse_gemini_output.py）
    ↓
更新数据库（abu_update_pattern_library_from_gemini.py）
    ↓
ML模型训练（abu_price_action_learner.py，增量训练）
```

## 📊 进度跟踪

管理器跟踪所有步骤的进度：

- **步骤1 - Gemini分析**：从 `outputs/abu_gemini_analysis_state.json` 读取
- **步骤2 - 解析Gemini输出**：统计输入/输出文件行数
- **步骤3 - 更新pattern_library表**：从脚本输出提取统计信息
- **步骤4 - ML模型训练**：增量训练，数据量增加10%以上时自动触发

进度信息保存在 `outputs/abu_gemini_pipeline_state.json`。

**注意**：总体进度只计算前3个步骤（各占33.3%），ML训练步骤独立显示（不计入总体进度）。

## 🚀 使用方式

### 1. 运行一次（处理已有输出）

```bash
python scripts/abu_gemini_pipeline_manager.py
```

这将：
- 更新Gemini分析状态
- 运行解析步骤（如果有新数据）
- 运行数据库更新步骤（如果有新数据）
- 运行ML模型训练步骤（如果数据量增加10%以上）
- 显示所有步骤的进度

### 2. 启用轮询模式（定时处理）

```bash
# 每4小时轮询一次（默认）
python scripts/abu_gemini_pipeline_manager.py --poll

# 每6小时轮询一次
python scripts/abu_gemini_pipeline_manager.py --poll --interval 6
```

轮询模式将：
- 定期运行所有步骤
- 自动处理新的Gemini输出
- 持续监控和处理，直到手动停止（Ctrl+C）

### 3. 只运行指定步骤

```bash
# 只运行解析步骤
python scripts/abu_gemini_pipeline_manager.py --step parse

# 只运行数据库更新步骤
python scripts/abu_gemini_pipeline_manager.py --step update_db
```

## 📁 文件说明

### 输入文件
- `outputs/abu_gemini_annotations_enhanced.jsonl`：Gemini分析结果（步骤1输入）
- `outputs/abu_gemini_parsed.jsonl`：解析后的结果（步骤2输入）

### 输出文件
- `outputs/abu_gemini_parsed.jsonl`：解析后的标准化结果（步骤1输出）
- `outputs/abu_gemini_pipeline_state.json`：处理流程状态
- `outputs/abu_gemini/pipeline_manager.log`：处理日志

### 状态文件
- `outputs/abu_gemini_analysis_state.json`：Gemini分析状态（由gemini_vision_analyzer生成）

## 📈 进度查看

运行管理器时会自动显示进度：

```
================================================================================
Gemini处理流程进度
================================================================================

总体进度: 47.4%

步骤1 - Gemini分析:
  状态: running
  进度: 42.4% (424/1000)

步骤2 - 解析Gemini输出:
  状态: completed
  进度: 100.0% (431/431)

步骤3 - 更新pattern_library表:
  状态: completed
  进度: 100.0% (匹配: 431, 更新: 431, 跳过: 0)

步骤4 - ML模型训练:
  状态: completed
  上次训练样本数: 431
  准确率: 0.7500
================================================================================
```

## 🔍 日志和监控

### 日志文件
- `outputs/abu_gemini/pipeline_manager.log`：详细的处理日志（JSON格式）

### 日志内容
- 步骤开始/完成
- 进度更新
- 错误和异常
- 关键操作记录

### 错误处理
- 所有错误都会记录到日志和状态文件
- 状态文件中的 `errors` 字段保存最近100条错误记录
- 步骤失败时会记录详细错误信息

## ⚙️ 工作原理

### 增量处理
- 解析步骤：检查输出文件行数，只处理新数据
- 数据库更新：使用 `--skip-existing` 参数，自动跳过已有记录

### 状态管理
- 每个步骤的状态保存在 `pipeline_state.json`
- 步骤状态：`pending`（待处理）、`running`（运行中）、`completed`（已完成）、`failed`（失败）
- 状态文件会在每次操作后自动更新

### 轮询机制
- 轮询模式会定期运行所有步骤
- 每次轮询会检查是否有新数据需要处理
- 如果步骤已完成，会跳过（除非有新数据）

## 🎯 典型使用场景

### 场景1：Gemini分析进行中，处理已有输出

```bash
# Gemini正在运行（40%进度），现在处理已有输出
python scripts/abu_gemini_pipeline_manager.py
```

这将：
- 处理已有的429条记录（解析+数据库更新）
- 显示当前进度（Gemini 42.4%，解析100%，数据库更新100%）

### 场景2：设置定时轮询，自动处理新输出

```bash
# 每4小时自动处理新输出
python scripts/abu_gemini_pipeline_manager.py --poll --interval 4
```

这将：
- 立即运行一次（处理已有输出）
- 每4小时自动运行一次
- 持续运行直到手动停止

### 场景3：只更新数据库（解析已完成）

```bash
# 只运行数据库更新步骤
python scripts/abu_gemini_pipeline_manager.py --step update_db
```

## ⚠️ 注意事项

1. **Gemini分析正在运行时**：
   - 可以安全运行解析和数据库更新步骤
   - 只会处理已有的输出（不会影响Gemini分析）

2. **数据库更新**：
   - 使用 `--skip-existing` 参数，不会重复更新已有记录
   - 新增的记录会自动更新到数据库

3. **轮询模式**：
   - 需要手动停止（Ctrl+C）
   - 建议在后台运行或使用系统服务

4. **进度跟踪**：
   - 总体进度 = Gemini分析进度 * 33.3% + 解析进度 * 33.3% + 数据库更新进度 * 33.3%
   - ML训练步骤独立显示，不计入总体进度
   - Gemini分析进度会从 `gemini_analysis_state.json` 实时读取

5. **ML模型训练**：
   - 在数据库更新完成后自动检查是否需要训练
   - 数据量增加10%以上时自动触发增量训练
   - 详见：`docs/stage_reports/增量训练机制说明.md`

## 📝 下一步

### ✅ 已完成

1. **价格行为特征学习模型**（`src/ml_dl/abu_price_action_learner.py`）✅
   - 模型已训练完成（429条样本）
   - 测试准确率：100%
   - 模型文件：`models/abu/price_action_model.pkl`
   - 已集成到处理流程管理器

### 🔄 下一步计划

根据 `docs/design/features/ABU_ML_DL完整执行方案.md`，下一步需要：

1. **数据准备阶段**（需要先完成）：
   - 创建 `pattern_match_history` 表（模式匹配历史）
   - 实现 `scripts/abu_record_match_history.py`（记录匹配历史）
   - 实现 `scripts/abu_evaluate_signals.py`（信号评估）
   - 收集足够的训练数据（至少需要数百条评估记录）

2. **模式匹配成功率预测模型**（`src/ml_dl/abu_pattern_match_predictor.py`）
   - 依赖：`pattern_match_history` 表数据
   - 功能：预测模式匹配的成功率
   - 数据要求：需要足够的历史匹配和评估数据

3. **候选信号评分模型**（`src/ml_dl/abu_candidate_scorer.py`）
   - 依赖：`pattern_match_history` 表数据
   - 功能：对候选信号进行评分
   - 数据要求：需要足够的历史匹配和评估数据

**建议顺序**：
1. 先完成数据收集机制（记录和评估历史信号）
2. 等待积累足够的训练数据（建议至少500+条评估记录）
3. 再训练模式匹配成功率预测模型和候选信号评分模型

详见：`docs/design/features/ABU_ML_DL完整执行方案.md`

---
**创建时间**: 2026-01-11  
**状态**: ✅ 可用

