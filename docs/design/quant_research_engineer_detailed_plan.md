# Quant Research Engineer 细化计划（可执行）

## Phase 1 研究流水线（MVP，可复现）
- 输入: config/research_runs.yaml（symbols、timeframes、days、features、label）
- 处理: scripts/research/run_research_pipeline.py
  - 读取数据 -> 计算特征 -> 切分 train/val/test -> 生成基线结果
- 输出: outputs/research/runs/<run_id>/
  - dataset.csv
  - metrics.json
  - report.md
- 验收: 同一 config 重跑结果一致；报告包含样本数/窗口/指标/版本签名

## Phase 2 Edge Attribution（Top-3~5 因子）
- 输入: Phase 1 的 dataset + PnL（信号/回测结果）
- 处理: scripts/research/run_attribution.py
  - 方案: 稀疏线性优先（必要时再加 SHAP）
- 输出: outputs/research/attribution/<run_id>.md
  - Top 因子、贡献度、证据样本、置信度
- 验收: Top 因子在不同切分下稳定；报告可复核

## Phase 3 因子库与版本化
- 输入: config/factors_registry.yaml（name/version/source/frequency/quality）
- 处理: scripts/research/build_factors.py
  - 多源对齐、缺失处理、质量统计
- 输出: outputs/factors/<version>/
  - 因子数据与 quality_report.md
- 验收: 缺失率/延迟/异常值可量化；版本可回放

## Phase 4 稳健性验证
- 输入: Phase 1/2 的 run_id
- 处理:
  - scripts/research/run_walk_forward.py
  - scripts/research/check_bias.py
- 输出: outputs/research/robustness/<run_id>.md
- 验收: OOS 指标+偏差结论清晰（lookahead/survivorship/selection）

## Phase 5 执行层最小闭环
- 输入: 信号与风控配置
- 处理:
  - src/executor/order_state.py（状态机）
  - src/executor/executor.py（幂等/重试）
- 输出: outputs/execution/events/<date>.jsonl
- 验收: 单笔订单全链路可回放、可审计

## Phase 6 可验证工具调用协议
- 输入: 关键调用（数据/执行/风控）
- 处理: src/infra/verified_call.py
  - 统一输出 ok/err + reason + evidence
- 输出: logs/verified_calls/*.log + 结构化记录
- 验收: 任一调用可追踪证据与失败原因
