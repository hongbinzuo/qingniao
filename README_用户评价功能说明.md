# 用户评价功能说明

## 功能概述

系统现在支持在录入对话时添加用户评价。使用 `freelemon()` 格式来标记评价内容。

## 使用方法

### 格式

```
freelemon(评价内容)
```

支持中文和英文括号：
- `freelemon(评价内容)` - 英文括号
- `freelemon（评价内容）` - 中文括号

### 示例

```bash
# 录入对话时添加评价
python src/add_de_conversation.py "22:26" "摸吧 freelemon(这是一个保本止损的好策略) 我挂保本，奶娃去了"

# 评价会被自动提取并存储
```

### 评价提取

系统会自动：
1. **提取评价内容**：从 `freelemon()` 中提取评价文本
2. **清理对话文本**：移除评价标记，保留原始对话内容
3. **提取关键词**：自动识别评价类型（策略相关、正面评价、负面评价等）
4. **存储到数据库**：评价内容存储在 `user_evaluation` 字段，关键词存储在 `evaluation_keywords` 字段

## 数据库字段

### conversations 表新增字段

- `user_evaluation` (TEXT): 用户评价内容（多个评价用 ` | ` 分隔）
- `evaluation_keywords` (TEXT): 评价关键词（逗号分隔）

### 自动添加字段

如果字段不存在，系统会在首次使用时自动添加。也可以手动运行：

```bash
python src/add_evaluation_field.py
```

## 评价关键词

系统会自动识别以下关键词：

- **策略相关**：包含"策略"、"规则"、"方法"、"技巧"、"建议"
- **正面评价**：包含"好"、"不错"、"有效"、"成功"
- **负面评价**：包含"不好"、"无效"、"失败"、"问题"

## 使用场景

### 1. 策略评价

```
"挂87000多单 freelemon(这个价格区间很好，符合FVG策略)"
```

### 2. 执行评价

```
"第一止盈到了 freelemon(分批止盈策略执行得很好)"
```

### 3. 方法评价

```
"摸吧 freelemon(保本止损是个好方法，风险控制到位) 我挂保本"
```

### 4. 问题反馈

```
"区间突破失败 freelemon(这个区间判断有问题，需要重新分析)"
```

## 查询评价

### 通过数据库查询

```sql
-- 查询所有包含评价的对话
SELECT id, timestamp, trader_message, user_evaluation, evaluation_keywords
FROM conversations
WHERE user_evaluation IS NOT NULL
ORDER BY timestamp DESC;

-- 查询正面评价
SELECT * FROM conversations
WHERE evaluation_keywords LIKE '%正面评价%';

-- 查询策略相关评价
SELECT * FROM conversations
WHERE evaluation_keywords LIKE '%策略相关%';
```

### 通过Python查询

```python
from db_manager_trader import TraderDBManager

db = TraderDBManager('de')
conn = db._get_connection()

# 查询所有评价
evaluations = conn.execute('''
    SELECT id, timestamp, trader_message, user_evaluation, evaluation_keywords
    FROM conversations
    WHERE user_evaluation IS NOT NULL
    ORDER BY timestamp DESC
    LIMIT 20
''').fetchall()

for row in evaluations:
    print(f"[{row[1]}] {row[2]}")
    print(f"评价: {row[3]}")
    print(f"关键词: {row[4]}")
    print()
```

## 输出示例

录入对话时，系统会显示：

```
✓ 对话记录录入成功！ID: 4670

提取的策略信息:
  分类: trading_execution
  动作: 保本
  策略: 保本止损策略

提取的用户评价:
  评价1: 这是一个保本止损的好策略
  评价关键词: 策略相关, 正面评价
```

## 注意事项

1. **评价格式**：必须使用 `freelemon()` 格式，大小写不敏感
2. **多个评价**：可以在一条对话中添加多个评价，系统会自动合并
3. **评价位置**：评价可以放在对话的任何位置
4. **自动清理**：评价标记会被自动移除，不会出现在存储的对话文本中
5. **向后兼容**：如果没有评价，系统正常工作，不影响现有功能

## 未来改进

1. **评价分析**：分析评价趋势，识别策略效果
2. **评价搜索**：在问答系统中支持评价查询
3. **评价统计**：统计正面/负面评价比例
4. **策略优化**：基于评价优化策略推荐

