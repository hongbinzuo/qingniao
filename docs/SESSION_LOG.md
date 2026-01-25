# Session Log

## 2026-01-25

### 已完成
- 修复扫描脚本在 `pattern_library` 匹配处的缩进错误，恢复扫描输出。
- 实时监控脚本记录扫描 stdout/stderr，方便定位失败原因，并在找不到扫描文件时回退到上一份输出。
- 扫描输出新增溯源字段：`Source / PatternId / ImagePath / Page`，方便定位到原始图片。
- 统一模式库支持 `gemini_pro` / `gemini_pro3` 分类；从 `gemini_annotation_json` 的 `_meta.gemini_model` 识别模型。
- 批量导入脚本支持 `--gemini-model`，写入 `_meta.gemini_model` 以标记模型来源。
- 扫描仅使用 `gemini_pro3` 模式源（不启用 Brooks / Cursor）。
- 扫描报告新增 Gemini 模式库统计（pro3/pro/flash/total）。
- 新增每小时信号跟踪脚本，按北京时间起点记录状态变化到本地文档。
- 修复信号跟踪在 `system_name` 过滤时的数据库查询参数缺失问题。
- 修复扫描写库调用，确保 `pa_scan_15m_top10.py` 能正确写入 `trading_signals`。
- 新增市场结构上下文判断模块（`strong_trend/trading_range/broad_channel`），并在扫描阶段做背景不匹配拦截。
- 扫描结果补充 `Context=<label>` 到 reason，用于溯源背景判断。
- 新增从 `outputs/trading_signals/ABU_top*.md` 回填 Postgres 的脚本，避免信号丢失。
- 扫描写库失败改为输出告警，便于追踪失败原因。
- 增加 EMA20 乖离特征（`dist_to_ema_pct`），用于逆势信号降权。
- 宽幅通道场景下逆势单若 EMA 乖离不足则下调评分，并写入原因说明。
- 修复交易信号查询入参可能为字符串导致的时间范围报错（强制转换 limit/days）。
- 跟踪器初始化可跳过自动加载活跃信号，避免数据库读取异常导致降级。
- 扫描过滤新增 RIDE/TRALA（及其 PERP 形式）忽略规则。
- 跟踪器改为回看信号后的1分钟K线，按触达顺序判断止盈/止损并更新状态。
- 跟踪器支持自定义周期（`--interval-minutes`），可设置为15分钟。
- 跟踪器JSON备份支持datetime/Decimal序列化，并修复评估写库参数传递。

### TODO
- 重新运行 `abu_realtime_monitor.py --once`，确认新输出包含溯源字段和 Pro3 统计行。
- 复核 BCH 的 `Source/PatternId/ImagePath/Page` 是否指向 Pro3 识别结果。
- 如仍无信号或匹配异常，检查 `pattern_library` 中是否已写入 Pro3 标记。
- 运行每小时跟踪脚本并确认 `ABU_signal_hourly_tracking.md` 持续追加。
- 运行 `pa_scan_15m_top10.py` 并检查 `Context=` 输出与背景不匹配过滤效果。
- 如数据库仍为空，运行 `abu_backfill_signals_from_md.py` 做回填。
- 观察 CHZ 等逆势信号是否出现 `EMA乖离不足` 降权提示，并确认分数变化。
