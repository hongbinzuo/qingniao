# ABU 计划生成器状态记录 (2026-02-05)

## 当前进展
- 脚本路径: `scripts/abu/generate_abu_plan.py`
- 已实现: 30币种固定排名筛选 + 视觉优先过滤 + Gemini交易计划 + 实时报告追加 + 并发执行
- 已加入: EMA20叠加到实时K线图，用于视觉匹配
- 已修复: 图表渲染强制使用 Matplotlib Agg 后端，避免 Tkinter 线程错误

## 关键功能
- 实时写入交易计划文件（信号生成即追加）
- 并发执行（默认 `ABU_CONCURRENCY=4`）
- 视觉调用计数和统计输出
- 视觉图片路径修复：支持 WSL/Windows 路径互转、默认 `data/abu/images`、按 `source_page` 回退

## Debug 断点
- 环境变量: `ABU_DEBUG_STOP_AFTER`
- 用法示例:
  ```
  $env:ABU_DEBUG_STOP_AFTER="3"
  python scripts\abu\generate_abu_plan.py
  ```
- 行为: 生成第 N 个信号后暂停，等待回车继续；启用时强制并发度=1（避免多个任务同时触发暂停）

## 输出位置
- 交易计划 Markdown:
  `trading_signals/ABU_v3_ranked_30_coins_YYYYMMDD_HHMMSS.md`
- 视觉摘要 HTML (若有记录):
  `outputs/vision_plan/vision_plan_summary_YYYYMMDD_HHMMSS.html`

## 最近修正点
- 修复 K线排序：在 `get_kline_gateio` 及使用前按 `timestamp` 排序
- 交易计划显示使用 kline 当前价（而不是 coin list 快照）
- `all_sources` 去重

## 需要注意
- PowerShell 查看报告需指定 UTF-8:
  ```
  Get-Content "C:\Users\zuoho\code\qingniao\trading_signals\ABU_v3_ranked_30_coins_*.md" -Encoding utf8 -Wait
  ```

## 下一步建议（可选）
- 增加入场距离过滤：若 `|entry-current| > X%` 则跳过信号
- 若需更快：减少 `ABU_VISION_TOP_N` 或关闭 15m
