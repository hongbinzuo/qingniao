# Discord全量导出处理指南

## 📋 概述

本工具用于处理Discord频道的全量对话导出，自动完成：
- ✅ 解析Discord导出数据（支持JSON/CSV/TXT格式）
- ✅ 自动去重（基于内容和时间戳）
- ✅ 结构化处理
- ✅ 提取De.的观点和交易记录
- ✅ 自动获取BTC价格
- ✅ 正确分类（观点/交易记录/交易信号）
- ✅ 批量导入数据库

## 🚀 使用方法

### 1. 导出Discord对话

首先需要从Discord导出对话数据：

#### 方法1：使用Discord导出工具
- 使用Discord的官方导出功能（如果有）
- 或使用第三方工具如 `DiscordChatExporter`

#### 方法2：手动复制
- 如果导出工具不可用，可以手动复制对话内容
- 保存为TXT格式，每行一条消息

### 2. 准备导出文件

将导出文件放在一个目录中，支持格式：
- **JSON格式**: `messages.json` 或 `export.json`
- **CSV格式**: `messages.csv`
- **TXT格式**: `messages.txt`

#### JSON格式示例
```json
[
  {
    "author": "De.",
    "content": "15分看起来很好空",
    "timestamp": "2025/12/25 18:34"
  }
]
```

#### CSV格式示例
```csv
Timestamp,Author,Content
2025/12/25 18:34,De.,15分看起来很好空
```

#### TXT格式示例
```
[2025/12/25 18:34] De.: 15分看起来很好空
[2025/12/25 18:39] De.: 这单止损放在879即可
```

### 3. 运行处理工具

```bash
# 处理单个文件
python src/process_full_discord_export.py path/to/export.json

# 处理整个目录
python src/process_full_discord_export.py path/to/export_directory/

# 指定交易员
python src/process_full_discord_export.py path/to/export.json --trader de
```

## 🔧 功能特性

### 1. 自动去重

- 基于内容哈希和时间戳
- 自动识别重复消息
- 只保留第一次出现的消息

### 2. 智能分类

自动将消息分类为：
- **trading_execution**: 交易执行记录
- **trading_signal**: 交易信号/建议
- **viewpoint**: 观点和理论
- **conversation**: 一般对话

### 3. 自动提取

- 提取价格信息
- 提取交易动作（做多/做空/止盈/止损）
- 提取策略和概念
- 提取理论观点

### 4. BTC价格获取

- 自动获取每条消息时的BTC价格
- 支持多种时间格式
- 容错处理（如果获取失败会继续处理）

## 📊 处理流程

```
Discord导出文件
    ↓
解析文件格式（JSON/CSV/TXT）
    ↓
提取De.的消息
    ↓
去重检查
    ↓
获取BTC价格
    ↓
分类（观点/交易记录/信号）
    ↓
解析指令和观点
    ↓
保存到数据库
```

## 📝 输出统计

处理完成后会显示：
- 总消息数
- De.消息数
- 重复消息数
- 成功处理数
- 错误数

## ⚠️ 注意事项

1. **时间格式**: 支持多种时间格式，但建议使用标准格式 `YYYY-MM-DD HH:MM:SS`
2. **编码**: 确保文件使用UTF-8编码
3. **文件大小**: 大文件处理可能需要一些时间
4. **网络**: 获取BTC价格需要网络连接

## 🔍 验证结果

处理完成后，可以使用以下工具验证：

```bash
# 检查数据库记录
python src/check_database_records.py

# 按日期显示记录
python src/show_all_records_by_date.py

# 检查重复记录
python src/check_duplicate_records.py
```

## 📚 相关工具

- `src/check_database_records.py`: 检查数据库记录
- `src/show_all_records_by_date.py`: 按日期显示记录
- `src/check_duplicate_records.py`: 检查重复记录
- `src/remove_duplicate_records.py`: 清理重复记录

## 🎯 最佳实践

1. **备份数据**: 处理前备份现有数据库
2. **分批处理**: 如果数据量很大，可以分批处理
3. **验证结果**: 处理完成后验证数据完整性
4. **清理重复**: 如果发现重复，使用清理工具

## 💡 示例

```bash
# 1. 导出Discord对话到 export.json

# 2. 处理导出文件
python src/process_full_discord_export.py export.json

# 3. 验证结果
python src/show_all_records_by_date.py
```

## 🔄 更新记录

- 2025/12/29: 创建全量导出处理工具
- 支持JSON/CSV/TXT格式
- 自动去重和分类
- 自动获取BTC价格

