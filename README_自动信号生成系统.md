# 全自动信号生成与评估系统

## ✅ 系统已启动

系统当前配置：
- **生成间隔**: 每小时自动生成一次
- **币种数量**: Top 30（按市值排序）
- **时间框架**: 5分钟和15分钟
- **每小时信号数**: 60个（30币种 × 2时间框架）

## 📊 当前状态

查看系统状态：
```bash
python scripts\show_auto_signal_status.py
```

系统会自动：
1. ✅ 每小时生成Top 30币种的交易信号
2. ✅ 自动评估信号质量
3. ✅ 运行回测验证
4. ✅ 生成总结报告

## 📁 输出文件位置

### 交易计划（每小时生成）
- **位置**: `outputs/trading_plans/auto_generated_YYYYMMDD_HHMMSS.md`
- **内容**: 包含所有币种的5分钟和15分钟信号
- **格式**: 完整的ABU系统信号格式，包含Brooks概率、止损距离、建议仓位等

### 总结报告（每小时生成）
- **位置**: `outputs/auto_signal_status/summary_YYYYMMDD_HHMMSS.md`
- **内容**: 生成统计、评估结果、系统改进建议

### 状态文件
- **位置**: `outputs/auto_signal_status/current_status.json`
- **内容**: 当前运行状态、上次生成时间、下次生成时间

## 🔍 查看最新结果

### 查看最新交易计划
```bash
# Windows PowerShell
Get-ChildItem outputs\trading_plans\auto_generated_*.md | Sort-Object LastWriteTime -Descending | Select-Object -First 1
```

### 查看最新总结报告
```bash
# Windows PowerShell
Get-ChildItem outputs\auto_signal_status\summary_*.md | Sort-Object LastWriteTime -Descending | Select-Object -First 1
```

## 📈 数据量统计

- **每小时**: 60个信号
- **每天**: 1,440个信号
- **每周**: 10,080个信号
- **每月**: 43,200个信号

这个数据量足够进行：
- ✅ 模式识别验证
- ✅ 策略回测
- ✅ 信号质量评估
- ✅ 系统性能分析

## 🛠️ 管理命令

### 查看状态
```bash
python scripts\show_auto_signal_status.py
```

### 停止系统
```bash
scripts\stop_auto_signal_generator.bat
```

### 重新启动
```bash
scripts\start_auto_signal_generator.bat
```

### 单次测试运行
```bash
python scripts\auto_signal_generator.py --once --coins 30
```

## 📝 信号格式说明

每个信号包含：
- **模式**: Pattern from page X (模式类型)
- **方向**: LONG/SHORT
- **入场价**: 精确到合适的小数位
- **止损**: 根据时间框架动态计算
- **止盈1/止盈2**: 风险回报比至少2:1
- **置信度**: 算法匹配置信度
- **Brooks概率**: 基于Brooks价格行为规则的概率评分
- **止损距离**: 百分比
- **建议仓位**: 基于时间框架和风险计算
- **风险金额**: 每笔交易的风险金额

## ⚠️ 注意事项

1. **系统持续运行**: 系统会在后台持续运行，每小时自动生成
2. **网络要求**: 需要稳定的网络连接以获取币种列表和K线数据
3. **存储空间**: 每小时生成一个报告文件，注意磁盘空间
4. **资源消耗**: 生成30个币种的信号需要约2-3分钟

## 🔄 下次生成时间

系统会在每小时自动生成，具体时间请查看状态文件：
```bash
python scripts\show_auto_signal_status.py
```

---

**系统已启动并运行中！** 🚀

每小时会自动生成Top 30币种的5分钟和15分钟信号，并进行评估和回测。
