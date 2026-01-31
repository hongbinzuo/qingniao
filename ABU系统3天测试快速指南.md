# ABU系统3天测试快速指南

**目标**: 电脑开启后自动运行，3天后拿到3份每日报告

---

## 🚀 第一步：一键启动（只需做一次）

### Windows用户

#### 方案1: 手动启动（当前）

1. **双击运行**: `scripts/abu/abu_start_all.bat`

2. **会打开两个窗口**:
   - `ABU模式匹配` - 每小时生成信号（Top 30币种）
   - `ABU视觉匹配` - 每4小时视觉匹配（Top 10币种，成本控制）

3. **设置每日报告**（可选，推荐）:
   ```powershell
   # 以管理员身份运行PowerShell
   cd C:\Users\zuoho\code\qingniao
   .\scripts\setup_daily_report_task.ps1
   ```

#### 方案2: 开机自动启动（推荐，一劳永逸）

1. **设置开机自动启动**:
   ```batch
   # 以管理员身份运行
   双击运行: scripts/abu/setup_abu_auto_start.bat
   ```
   或者使用PowerShell:
   ```powershell
   # 以管理员身份运行PowerShell
   cd C:\Users\zuoho\code\qingniao
   powershell -ExecutionPolicy Bypass -File "scripts\abu\setup_abu_auto_start.ps1"
   ```

2. **设置每日报告**:
   ```batch
   # 以管理员身份运行
   双击运行: setup_daily_report.bat
   ```
   或者使用PowerShell:
   ```powershell
   powershell -ExecutionPolicy Bypass -File "scripts\setup_daily_report_task.ps1"
   ```

**好处**：
- ✅ 电脑重启后自动启动
- ✅ 电脑休眠唤醒后自动检查并启动
- ✅ 无需每次手动运行

#### 电脑休眠/唤醒后

- **如果设置了开机自动启动**：系统会自动检查并启动，无需手动操作 ✅
- **如果没有设置自动启动**：
  - 睡眠模式：进程会继续运行，无需操作 ✅
  - 休眠模式：建议运行 `scripts/abu/abu_check_and_start.bat` 检查一下
  - 完全关机/重启：需要重新运行 `scripts/abu/abu_start_all.bat` 或 `scripts/abu/abu_check_and_start.bat`

---

## ✅ 第二步：验证系统运行

### 检查模式匹配是否运行

查看窗口 `ABU模式匹配`，应该看到：
```
开始循环生成信号（每 3600 秒 = 1.0 小时）
```

### 检查视觉匹配是否运行

查看窗口 `ABU视觉匹配`，应该看到：
```
开始循环视觉匹配扫描（每 14400 秒 = 4.0 小时）
```

### 手动生成一次报告（测试）

```batch
python scripts\generate_daily_summary_report.py
```

报告位置: `outputs\daily_reports\daily_summary_YYYYMMDD.md`

---

## 📊 第三步：查看每日报告

### 第1天报告（明天早上）

**位置**: `outputs\daily_reports\daily_summary_YYYYMMDD.md`

**内容**:
- 模式匹配效果（运行次数、信号数）
- 视觉匹配效果（运行次数、匹配数、分数）
- 横向对比（模式匹配 vs 视觉匹配）
- 纵向对比（与前一天，第1天没有）
- 信号质量分析
- 改进建议

### 第2天报告

**位置**: `outputs\daily_reports\daily_summary_YYYYMMDD.md`

**新增内容**:
- 纵向对比：与第1天的数据对比

### 第3天报告

**位置**: `outputs\daily_reports\daily_summary_YYYYMMDD.md`

**新增内容**:
- 纵向对比：与第2天的数据对比

---

## 🔍 报告查看方式

### 方式1: 直接打开Markdown文件

用任何文本编辑器或Markdown查看器打开：
```
outputs\daily_reports\daily_summary_20260115.md
```

### 方式2: 在命令行查看

```batch
type outputs\daily_reports\daily_summary_20260115.md
```

### 方式3: 使用VS Code或Cursor

直接在编辑器中打开文件即可。

---

## 📋 报告内容说明

### 1. 执行摘要
- 模式匹配运行了多少次
- 视觉匹配运行了多少次
- 生成了多少信号
- 完成了多少信号

### 2. 模式匹配效果
- 每小时运行一次
- 每次生成多少信号
- 按时间框架（5m/15m）分布

### 3. 视觉匹配效果
- 每4小时运行一次
- 每次匹配多少模式
- 平均分数（算法、视觉、综合）

### 4. 横向对比
- **匹配数量**: 模式匹配 vs 视觉匹配
- **运行频率**: 每小时 vs 每4小时
- **质量对比**: 平均评分对比

### 5. 纵向对比
- **第1天**: 无对比（基准）
- **第2天**: 与第1天对比
- **第3天**: 与第2天对比

### 6. 信号质量分析
- 总信号数
- 平均评分
- 已完成信号的胜率
- 平均收益

### 7. 改进建议
- 基于数据分析的自动建议

---

## ⚠️ 注意事项

### 1. 电脑休眠/唤醒

**如果设置了开机自动启动**：
- ✅ 电脑休眠唤醒后，系统会自动检查并启动
- ✅ 无需手动操作

**如果没有设置自动启动**：
- **睡眠模式（Sleep）**: 进程会继续运行，无需操作 ✅
- **休眠模式（Hibernate）**: 建议运行 `scripts/abu/abu_check_and_start.bat` 检查
- **完全关机/重启**: 需要重新运行启动脚本

### 2. 保持电脑开启

系统需要持续运行，建议：
- 不要关闭启动的窗口
- 可以锁屏，但不要完全关机
- 保持网络连接

### 2. 检查系统运行

每天检查一次：
- 两个窗口是否还在运行
- 是否有错误信息
- 报告是否正常生成

### 3. 手动生成报告（如果自动任务失败）

```batch
# 生成今天的报告
python scripts\generate_daily_summary_report.py

# 生成指定日期的报告
python scripts\generate_daily_summary_report.py --date 2026-01-15
```

---

## 🎯 3天后

### 收集报告

3天后，您应该有3份报告：
1. `daily_summary_20260115.md` - 第1天
2. `daily_summary_20260116.md` - 第2天
3. `daily_summary_20260117.md` - 第3天

### 对比分析

打开3份报告，对比：
- **纵向趋势**: 信号数、匹配数是否增加
- **质量变化**: 胜率、平均收益是否改善
- **系统稳定性**: 运行次数是否正常

---

## 🛠️ 故障处理

### 系统停止运行

1. **检查并启动**（推荐）:
   ```batch
   双击运行: scripts/abu/abu_check_and_start.bat
   ```
   这个脚本会自动检查系统状态，如果未运行则自动启动。

2. **或手动重新启动**:
   ```batch
   双击运行: scripts/abu/abu_start_all.bat
   ```

3. **检查错误**: 查看窗口中的错误信息

### 报告未生成

1. **手动生成**:
   ```batch
   python scripts\generate_daily_summary_report.py
   ```

2. **检查任务计划**:
   ```powershell
   Get-ScheduledTask -TaskName ABU_Daily_Report
   ```

### 视觉匹配未运行

1. **检查API密钥**:
   ```batch
   echo %OPENROUTER_API_KEY%
   ```

2. **手动测试**:
   ```batch
   python scripts\abu\abu_vision_scanner_4h.py --once
   ```

---

## 📞 快速命令参考

```batch
# 启动所有系统
scripts/abu/abu_start_all.bat

# 查看信号状态
python scripts\show_auto_signal_status.py

# 生成每日报告
python scripts\generate_daily_summary_report.py

# 查看优化就绪状态
python scripts\check_ml_optimization_readiness.py

# 查看优化历史
python scripts\query_ml_optimization_results.py
```

---

## ✅ 检查清单

### 启动时
- [ ] 运行 `scripts/abu/abu_start_all.bat`
- [ ] 看到两个窗口打开
- [ ] 设置每日报告任务（可选）

### 每天检查
- [ ] 系统窗口还在运行
- [ ] 报告已生成（`outputs\daily_reports\`）

### 3天后
- [ ] 收集3份报告
- [ ] 对比分析效果
- [ ] 查看改进建议

---

**就这么简单！** 🎉

运行 `scripts/abu/abu_start_all.bat`，然后等待3天，每天查看报告即可。
