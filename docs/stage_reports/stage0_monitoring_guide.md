# 阶段0处理监控指南

## 当前状态 ✅

**进程状态**: ✅ 后台运行中（PID: 40304）  
**开始时间**: 2026-01-11 00:25:54  
**当前进度**: 10/1000 张（1.0%）

### 处理速度
- **平均速度**: 37.3 秒/张
- **预计剩余时间**: 10小时15分钟
- **预计完成时间**: 2026-01-11 10:48:37

### 成本情况
- **已花费**: $0.001250
- **预计剩余**: $0.123750
- **总预计**: $0.125000

## 监控命令

### 1. 查看实时进度
```bash
python scripts/show_progress.py
```

### 2. 检查新字段提取情况
```bash
python scripts/check_new_fields.py
```

### 3. 查看最新处理日志
```bash
Get-Content outputs\abu_gemini\gemini_analysis.log -Tail 20 -Encoding UTF8
```

### 4. 检查进程是否运行
```bash
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*abu_optimize_speed*' } | Select-Object ProcessId, CommandLine
```

## 预期指标

### 目标提取率
- ✅ chart_overview: >80%
- ✅ complete_price_path: >80%
- ✅ complete_narrative: >90%
- ✅ JSON解析错误率: <5%（排除标题页、空白页）

### 当前表现（前11条）
- 新字段提取成功率: 约57%（样本较小，待观察）
- JSON解析失败: 约43%（可能包含标题页、空白页等特殊情况）

## 注意事项

### 1. JSON解析失败 ⚠️
- **原因**: 部分图片（标题页、空白页）可能返回非标准JSON
- **处理**: 已保存原始文本到`raw`字段，可后续分析
- **影响**: 不会中断处理，继续处理下一张图片

### 2. 处理速度 📊
- **当前**: 37.3秒/张（略慢于预期20秒/张）
- **原因**: 包含API调用延迟、JSON解析、日志记录等
- **预计**: 随着处理进行，速度可能趋于稳定

### 3. 断点续传 ✅
- **支持**: 自动保存状态，支持中断后继续
- **状态文件**: `outputs/abu_gemini_analysis_state.json`
- **缓存**: `outputs/.cache/abu_gemini/{sha1}.json`

## 建议监控频率

- **第一个小时**: 每15-30分钟检查一次
- **中期（1-5小时）**: 每小时检查一次
- **后期（5-10小时）**: 每2-3小时检查一次

## 问题排查

### 如果进程停止
```bash
# 1. 检查是否出错
Get-Content outputs\abu_gemini\gemini_analysis.log -Tail 50 -Encoding UTF8

# 2. 手动重启（会从断点继续）
python scripts/abu/abu_optimize_speed.py
```

### 如果进度异常
```bash
# 检查输出文件记录数
(Get-Content outputs\abu_gemini_annotations_enhanced.jsonl | Measure-Object -Line).Lines

# 检查状态文件
Get-Content outputs\abu_gemini_analysis_state.json | python -m json.tool
```

### 如果需要停止
```bash
# 停止进程（不会丢失已处理数据）
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*abu_optimize_speed*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

## 完成后的评估

处理完成后，运行以下命令评估结果：

```bash
# 全面评估结果质量
python scripts/evaluate_rerun_need.py

# 检查新字段提取率
python scripts/check_new_fields.py
```

---

**状态**: ✅ 正常运行中  
**建议**: 定期监控，等待完成或出现异常时再介入



