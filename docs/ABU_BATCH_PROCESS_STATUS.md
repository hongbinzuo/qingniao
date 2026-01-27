# ABU 批量图片处理任务 - 进度保存文档

> **创建时间**: 2026-01-28 02:50+08:00  
> **状态**: 准备就绪，等待执行  
> **任务范围**: 图片 601-1000 (共400张)

---

## 1. 任务概述

### 目标
使用 Kimi CLI 的 Sub Agent 功能批量分析 ABU 图表图片 (page_0601_img_01_clip.png ~ page_1000_img_01_clip.png)

### 处理参数
- **图片范围**: 601-1000 (共400张)
- **图片路径**: `C:\Users\zuoho\code\qingniao\data\abu\images\`
- **每批处理**: 5张图片
- **并发数**: 3个 Sub Agent
- **每轮处理**: 15张图片
- **总轮数**: 27轮
- **预估时间**: 1.5-2小时

### 图片命名格式
```
page_0601_img_01_clip.png
page_0602_img_01_clip.png
...
page_1000_img_01_clip.png
```

---

## 2. 执行方案

### 2.1 Sub Agent 配置

需要创建的 Sub Agent 配置文件:

**文件**: `config/abu_image_analyzer.yaml`
```yaml
version: 1
agent:
  name: abu_image_analyzer
  extend: default
  system_prompt_path: ./abu_analyzer_prompt.md
  exclude_tools:
    - "kimi_cli.tools.multiagent:Task"  # 排除Task避免嵌套
```

**文件**: `config/abu_analyzer_prompt.md` (需要创建)
- 包含 `ENHANCED_PROMPT` 内容
- 来自 `src/abu/gemini_vision_analyzer.py` 第101行

### 2.2 分批策略

```
第1轮:  601-605, 606-610, 611-615
第2轮:  616-620, 621-625, 626-630
第3轮:  631-635, 636-640, 641-645
...
第27轮: 991-995, 996-1000
```

### 2.3 轮次明细表

| 轮次 | Agent 1 | Agent 2 | Agent 3 | 状态 |
|-----|---------|---------|---------|------|
| 1 | 601-605 | 606-610 | 611-615 | ⏳ 待处理 |
| 2 | 616-620 | 621-625 | 626-630 | ⏳ 待处理 |
| 3 | 631-635 | 636-640 | 641-645 | ⏳ 待处理 |
| ... | ... | ... | ... | ... |
| 27 | 991-995 | 996-1000 | - | ⏳ 待处理 |

---

## 3. 容错机制

### 3.1 多级重试
1. **Sub Agent 内部**: 单张图片失败重试3次
2. **主 Agent 级别**: 整批失败重试3次
3. **轮次级别**: 某轮失败后继续下一轮

### 3.2 进度保存
- **进度文件**: `outputs/abu_progress_601_1000.json`
- **结果文件**: `outputs/abu_results_601_1000.jsonl` (JSON Lines格式)
- **保存频率**: 每完成一批立即保存

### 3.3 断点续传
支持中断后从上次进度继续执行

---

## 4. 关键文件清单

### 已存在的关键文件
| 文件路径 | 说明 |
|---------|------|
| `src/abu/gemini_vision_analyzer.py` | 包含 ENHANCED_PROMPT 提示词 |
| `data/abu/images/` | 图片存储目录 |
| `scripts/vector_prompt.txt` | 向量提示词文件 |
| `selected_300_images.json` | 已选图片索引 |

### 需要创建的文件
| 文件路径 | 说明 | 状态 |
|---------|------|------|
| `config/abu_image_analyzer.yaml` | Sub Agent 配置 | ⏳ 待创建 |
| `config/abu_analyzer_prompt.md` | 分析提示词 | ⏳ 待创建 |
| `outputs/abu_progress_601_1000.json` | 进度跟踪 | 自动生成 |
| `outputs/abu_results_601_1000.jsonl` | 结果存储 | 自动生成 |

---

## 5. 执行步骤 (恢复时使用)

### 步骤 1: 创建 Sub Agent 配置
```bash
# 创建 abu_image_analyzer.yaml
# 创建 abu_analyzer_prompt.md (从 gemini_vision_analyzer.py 复制 ENHANCED_PROMPT)
```

### 步骤 2: 启动 Kimi CLI
```bash
cd c:\Users\zuoho\code\qingniao
kimi --agent-file config/abu_image_analyzer.yaml
```

### 步骤 3: 执行批量处理
在主 Agent 中运行批量处理脚本或手动调用 Task 工具

### 步骤 4: 监控进度
查看 `outputs/abu_progress_601_1000.json` 了解处理进度

---

## 6. 风险与注意事项

### API 限制
- 注意 API 配额消耗
- 如遇 429 错误，增加轮次间暂停时间

### 文件大小
- 单张图片最大 100MB
- 所有图片均应远小于此限制

### 中断恢复
- 可随时按 Ctrl+C 中断
- 进度自动保存，重启后可继续

---

## 7. 相关代码参考

### ENHANCED_PROMPT 来源
```python
# src/abu/gemini_vision_analyzer.py
# 第 101-200 行
ENHANCED_PROMPT = """You are an expert price-action trading analyst..."""
```

### 图片读取工具
- `ReadMediaFile`: 读取图片文件 (最大100MB)

### Task 工具用法
```python
Task(
    description="分析图表批次",
    subagent_name="abu_image_analyzer",
    prompt="分析图片: [...]"
)
```

---

## 8. Git 状态

### 当前分支
```
feat/sentiment-weighting-combo-snapshot
```

### 未提交更改
- `.env.example`
- `AGENTS.md`
- `config/abu_best_practices.yaml`
- `config/brooks_pattern_constraints.yaml`
- `scripts/pa_scan_15m_top10.py`

### 未跟踪文件
- 多个处理脚本和验证文件
- 文档文件

---

## 9. 联系与恢复

### 恢复工作时
1. 查看本文件了解任务状态
2. 检查 `outputs/abu_progress_601_1000.json` 确认进度
3. 从断点继续执行

### 上次更新时间
2026-01-28 02:50+08:00

---

**注意**: 本文档随 git 提交保存，可在任何克隆的仓库中查看。
