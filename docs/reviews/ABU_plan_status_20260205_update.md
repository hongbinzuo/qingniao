# ABU 计划生成器状态记录（更新）(2026-02-05)

## 最近变更摘要
- **时间框架**: 移除 5m，新增 1h 和 4h（当前为 15m/1h/4h）
- **实时写入**: 信号生成即追加到报告
- **并发执行**: 支持 `ABU_CONCURRENCY`
- **Brooks校验**: 集成 `BrooksTradingValidator`（严格模式默认开启）
- **方向规则**: 模式方向不明时默认不出信号（可用 `ABU_ALLOW_NEUTRAL_DIRECTION=1` 放开）
- **止损/止盈**: 采用 Brooks 风格最小止损距离 + RR≥2:1（TP1=2R，TP2=3R）
- **视觉**: 生成 Top N 匹配 HTML（默认 Top 5）
- **币种过滤**: 排除稳定币 + 杠杆代币（如 3L/3S/5L/5S/10L/10S/BULL/BEAR/UP/DOWN/LONG/SHORT）

## 关键脚本
- `scripts/abu/generate_abu_plan.py`

## 输出位置
- 交易计划: `trading_signals/ABU_v3_ranked_30_coins_YYYYMMDD_HHMMSS.md`
- 视觉摘要: `outputs/vision_plan/vision_plan_summary_YYYYMMDD_HHMMSS.html`
- Top 匹配: `outputs/vision_plan/vision_top_matches_YYYYMMDD_HHMMSS.html`

## 常用环境变量
- `ABU_CONCURRENCY=4`
- `ABU_VISION_FILTER=1`
- `ABU_VISION_TOP_MATCHES=5`
- `ABU_BROOKS_VALIDATE=1`
- `ABU_BROOKS_STRICT=1`
- `ABU_ALLOW_NEUTRAL_DIRECTION=0`
- `ABU_RR_TP1=2.0`
- `ABU_RR_TP2=3.0`
- `ABU_COIN_LIST_REFRESH=1`（刷新币种列表）
- `ABU_DEBUG_STOP_AFTER=3`（生成3个信号后暂停）

## 提醒
- PowerShell 查看报告：  
  `Get-Content .\trading_signals\ABU_v3_ranked_30_coins_*.md -Encoding utf8 -Wait`

