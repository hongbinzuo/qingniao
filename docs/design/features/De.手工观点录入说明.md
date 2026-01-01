# De.手工观点录入系统使用说明

## 📋 功能说明

用于记录你手工提供的De.观点，包括：
- 观点内容
- 时间戳（De.说这句话的时间）
- 来源（手工录入）
- 类别（交易/分析/指令等）

## 🚀 使用方法

### 1. 交互式添加观点

```bash
python src/record_manual_de_viewpoints.py add
```

然后：
1. 输入De.的观点内容（可以多行，空行结束）
2. 输入时间戳（格式: 2025-12-30 10:30:00，直接回车使用当前时间）
3. 输入类别（可选，直接回车跳过）

### 2. 查看已记录的观点

```bash
# 查看最近20条
python src/record_manual_de_viewpoints.py show

# 查看最近50条
python src/record_manual_de_viewpoints.py show 50
```

### 3. 导出为Markdown

```bash
# 导出到默认文件
python src/record_manual_de_viewpoints.py export

# 导出到指定文件
python src/record_manual_de_viewpoints.py export De_观点记录.md
```

### 4. 批量导入

创建一个文本文件，每行一个观点，格式：
```
2025-12-30 10:30:00|De.的观点内容
2025-12-30 11:00:00|另一条观点
```

或者只有内容（使用当前时间）：
```
De.的观点内容1
De.的观点内容2
```

然后导入：
```bash
python src/record_manual_de_viewpoints.py import viewpoints.txt
```

## 📁 数据文件

**位置**: `src/de_manual_viewpoints.json`

**格式**:
```json
{
  "viewpoints": [
    {
      "id": "viewpoint_1",
      "content": "De.的观点内容",
      "timestamp": "2025-12-30 10:30:00",
      "recorded_time": "2025-12-30 10:35:00",
      "source": "manual",
      "category": "trading"
    }
  ],
  "last_updated": "2025-12-30 10:35:00",
  "total_count": 1
}
```

## 💡 使用场景

### 场景1: 记录De.的交易指令

```bash
python src/record_manual_de_viewpoints.py add
# 输入: 明天低多，多在863下面损一次，85附近再多一次，新低止损
# 时间: 2025-12-28 01:53:00
# 类别: instruction
```

### 场景2: 记录De.的市场分析

```bash
python src/record_manual_de_viewpoints.py add
# 输入: 价格在885-877都是垃圾时间
# 时间: 2025-12-21 23:00:00
# 类别: analysis
```

### 场景3: 批量录入历史观点

创建一个文件 `historical_viewpoints.txt`:
```
2025-12-20 00:39:15|如果价格875-884区间，看空
2025-12-21 10:00:00|价格在885-877都是垃圾时间
2025-12-22 15:30:00|5分钟的vegas了，894，顶不住，我也加入空军队伍
```

然后：
```bash
python src/record_manual_de_viewpoints.py import historical_viewpoints.txt
```

## 🔄 与对话录入系统的整合

手工录入的观点可以：
1. 与对话文件中的消息合并
2. 统一时间线排序
3. 用于系统学习和分析

## 📊 导出格式示例

导出的Markdown文件格式：
```markdown
# De.手工观点记录

**生成时间**: 2025-12-30 10:35:00  
**总记录数**: 3  

---

## 1. 2025-12-20 00:39:15

**来源**: manual  
**类别**: trading  
**录入时间**: 2025-12-30 10:30:00  

**内容**:

  如果价格875-884区间，看空

---
```

## ⚙️ 注意事项

1. **时间戳格式**: 建议使用 `YYYY-MM-DD HH:MM:SS` 格式
2. **内容格式**: 支持多行文本
3. **类别**: 可选值: trading, analysis, instruction, other
4. **数据备份**: 定期导出Markdown文件作为备份

---

**创建时间**: 2025-12-30

