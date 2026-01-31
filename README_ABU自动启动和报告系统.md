# ABU自动启动和报告系统使用说明

**创建时间**: 2026-01-15  
**系统版本**: ABU v3.0

---

## 🚀 快速开始

### 一键启动所有系统

**Windows**:
```batch
双击运行: scripts/abu/abu_start_all.bat
```

这将自动启动：
1. ✅ **模式匹配信号生成系统** - 每小时运行一次
2. ✅ **视觉匹配系统** - 每4小时运行一次（Gemini Flash）
3. ⚠️ **每日报告生成** - 需要设置定时任务（见下方）

### 电脑休眠/唤醒后

**如果电脑休眠后唤醒**：
- **睡眠模式（Sleep）**: 进程会继续运行，无需重新启动 ✅
- **休眠模式（Hibernate）**: 进程会恢复，但建议检查一下
- **完全关机/重启**: 需要重新启动系统

**推荐方案**：设置开机自动启动（见下方）

### 检查并启动系统（推荐）

如果不确定系统是否在运行，可以使用检查脚本：
```batch
双击运行: scripts/abu/abu_check_and_start.bat
```

这个脚本会：
- 检查系统是否在运行
- 如果未运行，自动启动
- 如果已运行，跳过启动

---

## 📋 系统组件说明

### 1. 模式匹配信号生成系统

**脚本**: `scripts/auto_signal_generator.py`

**功能**:
- 每小时自动生成Top 30币种的交易信号
- 自动评估信号质量
- 自动运行回测
- 自动反馈信号结果

**运行方式**:
```batch
python scripts\auto_signal_generator.py --interval 1.0 --coins 30
```

**输出**:
- 交易计划: `outputs/trading_plans/auto_generated_*.md`
- 状态文件: `outputs/auto_signal_status/summary_*.md`

### 2. 视觉匹配系统（Gemini Flash）

**脚本**: `scripts/abu/abu_vision_scanner_4h.py`

**功能**:
- 每4小时运行一次（成本控制）
- 使用Gemini Flash进行深度视觉匹配
- 扫描Top 10币种（成本控制）

**运行方式**:
```batch
python scripts\abu\abu_vision_scanner_4h.py --interval 14400 --symbols 10
```

**输出**:
- 视觉匹配结果: `outputs/vision_matching/vision_results_*.json`

### 3. 每日报告生成系统

**脚本**: `scripts/generate_daily_summary_report.py`

**功能**:
- 生成每日总结报告
- 对比模式匹配和视觉匹配效果
- 纵向对比（与前一天）
- 横向对比（模式匹配 vs 视觉匹配）

**运行方式**:
```batch
# 生成今天的报告
python scripts\generate_daily_summary_report.py

# 生成指定日期的报告
python scripts\generate_daily_summary_report.py --date 2026-01-15
```

**输出**:
- 每日报告: `outputs/daily_reports/daily_summary_YYYYMMDD.md`

---

## ⚙️ 设置自动启动和报告

### 1. 设置开机自动启动（推荐）

**让系统在电脑启动时自动运行**：

**方法1: 使用批处理文件（推荐，最简单）**:
```batch
# 以管理员身份运行
双击运行: scripts/abu/setup_abu_auto_start.bat
```

**方法2: 使用PowerShell（如果方法1失败）**:
```powershell
# 以管理员身份运行PowerShell
cd C:\Users\zuoho\code\qingniao
powershell -ExecutionPolicy Bypass -File "scripts\abu\setup_abu_auto_start.ps1"
```

这将创建一个Windows任务计划，系统启动时自动检查并启动ABU系统。

**好处**：
- ✅ 电脑重启后自动启动
- ✅ 电脑休眠唤醒后自动检查
- ✅ 无需手动运行启动脚本

### 2. 设置每日报告自动生成

**方法1: 使用批处理文件（推荐）**:
```batch
# 以管理员身份运行
双击运行: setup_daily_report.bat
```

**方法2: 使用PowerShell**:
```powershell
# 以管理员身份运行PowerShell
cd C:\Users\zuoho\code\qingniao
powershell -ExecutionPolicy Bypass -File "scripts\setup_daily_report_task.ps1"
```

这将创建一个Windows任务计划，每天00:05自动生成报告。

### 方法2: 手动设置Windows任务计划

1. 打开"任务计划程序"（Task Scheduler）
2. 创建基本任务
3. 名称: `ABU_Daily_Report`
4. 触发器: 每天 00:05
5. 操作: 启动程序
   - 程序: `python`
   - 参数: `scripts\generate_daily_summary_report.py`
   - 起始于: `C:\Users\zuoho\code\qingniao`

---

## 📊 每日报告内容

### 1. 执行摘要
- 模式匹配运行次数
- 视觉匹配运行次数
- 生成信号总数
- 已完成信号数

### 2. 模式匹配效果分析
- 运行次数
- 生成信号总数
- 平均每次信号数
- 按时间框架分布

### 3. 视觉匹配效果分析
- 运行次数
- 匹配总数
- 平均分数（算法、视觉、综合）

### 4. 横向对比
- 匹配数量对比
- 运行频率对比
- 质量对比

### 5. 纵向对比
- 与前一天的数据对比
- 信号数变化
- 匹配数变化

### 6. 信号质量分析
- 总信号数
- 平均评分
- 已完成信号统计（胜率、平均收益）

### 7. 改进建议
- 基于数据分析的改进建议

---

## 🔍 查看报告

### 查看今天的报告

```batch
# 生成报告
python scripts\generate_daily_summary_report.py

# 报告位置
outputs\daily_reports\daily_summary_YYYYMMDD.md
```

### 查看历史报告

所有报告保存在 `outputs/daily_reports/` 目录下，按日期命名。

---

## 📝 使用流程（3天测试）

### 第1天

1. **启动系统**:
   ```batch
   双击运行: scripts/abu/abu_start_all.bat
   ```

2. **设置每日报告**:
   ```powershell
   .\scripts\setup_daily_report_task.ps1
   ```

3. **等待系统运行**:
   - 模式匹配每小时运行
   - 视觉匹配每4小时运行
   - 每日报告每天00:05生成

### 第2天

1. **查看第1天报告**:
   ```batch
   # 报告位置
   outputs\daily_reports\daily_summary_20260115.md
   ```

2. **系统继续自动运行**（无需操作）

### 第3天

1. **查看第2天报告**:
   ```batch
   outputs\daily_reports\daily_summary_20260116.md
   ```

2. **系统继续自动运行**（无需操作）

### 第4天

1. **查看第3天报告**:
   ```batch
   outputs\daily_reports\daily_summary_20260117.md
   ```

2. **对比3天的报告**，分析系统效果

---

## 🛠️ 故障排查

### 系统未启动

1. 检查Python环境:
   ```batch
   python --version
   ```

2. 检查依赖:
   ```batch
   pip list | findstr "duckdb requests"
   ```

### 报告未生成

1. 手动运行报告生成:
   ```batch
   python scripts\generate_daily_summary_report.py
   ```

2. 检查任务计划:
   ```powershell
   Get-ScheduledTask -TaskName ABU_Daily_Report
   ```

### 视觉匹配未运行

1. 检查API密钥:
   ```batch
   echo %OPENROUTER_API_KEY%
   ```

2. 手动运行一次:
   ```batch
   python scripts\abu\abu_vision_scanner_4h.py --once
   ```

---

## 📈 监控系统状态

### 查看信号生成状态

```batch
python scripts\show_auto_signal_status.py
```

### 查看优化就绪状态

```batch
python scripts\check_ml_optimization_readiness.py
```

### 查看优化历史

```batch
python scripts\query_ml_optimization_results.py
```

---

## 🎯 总结

**一键启动**: 运行 `scripts/abu/abu_start_all.bat` 即可启动所有系统

**自动运行**: 
- 模式匹配：每小时自动运行
- 视觉匹配：每4小时自动运行
- 每日报告：每天00:05自动生成

**查看报告**: 
- 位置: `outputs/daily_reports/daily_summary_YYYYMMDD.md`
- 包含：模式匹配效果、视觉匹配效果、横向对比、纵向对比

**持续3天**: 系统会自动运行3天，每天生成一份报告

---

**状态**: ✅ 已实现  
**下一步**: 运行 `scripts/abu/abu_start_all.bat` 启动系统
