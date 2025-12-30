# De.交易数据补充与策略沟通系统使用说明

## 系统概述

这是一个完整的系统，用于：
1. 录入De.的新对话和交易数据
2. 自动从对话中提取策略信息
3. 生成策略分析报告
4. 支持交互式策略问答

## 快速开始

### 统一入口（推荐）

使用统一入口脚本 `src/de_data_manager.py`：

```bash
# 查看帮助
python src/de_data_manager.py --help

# 录入对话
python src/de_data_manager.py add-conversation "22:26" "摸吧 我挂保本，奶娃去了"

# 录入交易记录
python src/de_data_manager.py add-trade

# 分析策略（最近7天）
python src/de_data_manager.py analyze-strategy --days 7

# 策略问答
python src/de_data_manager.py ask-strategy "De.最近用了什么策略？"

# 生成报告
python src/de_data_manager.py generate-report --days 7 --output report.md
```

## 功能详解

### 1. 对话录入

#### 方式1：命令行录入

```bash
python src/de_data_manager.py add-conversation "22:26" "第一止盈到了 嘿嘿 先落袋一千点"
```

#### 方式2：交互式录入

```bash
python src/de_data_manager.py add-conversation
```

#### 方式3：直接使用脚本

```bash
python src/add_de_conversation.py "22:26" "消息内容"
```

**功能特点**：
- 自动提取策略信息（价格、动作、策略类型）
- 自动分类对话类型（交易信号/交易执行/观点）
- 自动生成标签
- 自动关联BTC价格（如果提到时间）

### 2. 交易记录录入

#### 方式1：交互式录入

```bash
python src/de_data_manager.py add-trade
```

#### 方式2：批量录入

```bash
python src/de_data_manager.py add-trade --batch
```

批量录入格式：`时间|交易对|方向|杠杆|开仓价|平仓价|收益率|盈利`

示例：
```
2025-12-30 10:00:00|BTC/USDT|long|10|87000|87500|5.75|575
2025-12-30 11:00:00|ETH/USDT|short|5|3000|2950|1.67|50
```

### 3. 策略分析

#### 生成分析报告

```bash
# 分析最近7天的策略
python src/de_data_manager.py analyze-strategy --days 7

# 保存到文件
python src/de_data_manager.py analyze-strategy --days 7 --output strategy_report.md
```

**报告内容**：
- 数据统计（对话数、观点数、交易数）
- 策略使用频率
- 交易动作频率
- 策略概念频率
- 对话分类分布
- 价格区间分析
- 交易统计（如果有交易记录）
- 最近策略示例

### 4. 策略问答

#### 方式1：命令行问答

```bash
python src/de_data_manager.py ask-strategy "De.最近用了什么策略？"
python src/de_data_manager.py ask-strategy "De.在什么价格区间做多？" --days 14
```

#### 方式2：交互式问答

```bash
python src/de_data_manager.py ask-strategy --interactive
```

**支持的问题类型**：
- "De.最近用了什么策略？"
- "De.在什么价格区间做多/做空？"
- "De.的止损策略是什么？"
- "De.的止盈策略是什么？"
- "De.在什么市场环境下用什么策略？"
- "De.的Vegas策略是什么？"
- 其他策略相关问题

### 5. 生成报告

```bash
python src/de_data_manager.py generate-report --days 7 --output De策略报告_20251230.md
```

## 模块说明

### 核心模块

1. **`src/de_strategy_extractor.py`** - 策略提取模块
   - 从对话中提取策略信息
   - 识别价格、动作、策略类型、概念等

2. **`src/de_strategy_analyzer.py`** - 策略分析器
   - 分析策略使用频率
   - 生成策略分析报告

3. **`src/de_strategy_qa.py`** - 策略问答系统
   - 基于数据库回答策略问题
   - 支持多种问题类型

4. **`src/de_data_manager.py`** - 统一入口
   - 整合所有功能
   - 提供命令行界面

### 数据录入模块

1. **`src/add_de_conversation.py`** - 对话录入工具
   - 增强版，自动提取策略信息

2. **`src/add_de_trade_record.py`** - 交易记录录入工具
   - 交互式录入
   - 批量录入

## 数据存储

所有数据存储在：
```
data/qingniao_de.duckdb
```

**相关表**：
- `conversations` - 对话记录
- `trade_records` - 交易记录
- `trader_viewpoints` - 交易观点（自动从对话中提取）

## 使用示例

### 示例1：录入对话并查看策略信息

```bash
# 录入对话
python src/de_data_manager.py add-conversation "22:26" "摸吧 我挂保本，奶娃去了"

# 输出：
# ✓ 对话记录录入成功！ID: 4669
# 
# 提取的策略信息:
#   分类: trading_execution
#   动作: 保本
#   策略: 保本止损策略
```

### 示例2：分析最近策略

```bash
python src/de_data_manager.py analyze-strategy --days 7 --output 最近7天策略分析.md
```

### 示例3：询问策略问题

```bash
python src/de_data_manager.py ask-strategy "De.最近用了什么策略？"
```

输出示例：
```
De.最近使用的策略：

- 保本止损策略: 5次
- 分批止盈策略: 3次
- Vegas通道策略: 2次
```

### 示例4：交互式问答

```bash
python src/de_data_manager.py ask-strategy --interactive
```

## 策略提取规则

系统会自动识别以下内容：

### 策略类型
- Vegas通道策略
- FVG策略
- 区间震荡/突破策略
- 保本止损策略
- 分批止盈策略
- 形态识别策略（M顶W底）

### 交易动作
- 挂单
- 平仓
- 加仓
- 减仓
- 止损
- 止盈
- 保本

### 策略概念
- Vegas、FVG、区间、保本、止盈、止损
- SMC、币本位、U本位
- OTE、M顶W底

### 对话分类
- `trading_execution` - 交易执行
- `trading_signal` - 交易信号
- `viewpoint` - 观点
- `conversation` - 普通对话

## 注意事项

1. **时间格式**：支持多种时间格式，系统会自动转换
2. **策略提取**：系统会自动从对话中提取策略信息，无需手动标注
3. **数据关联**：对话和观点会自动关联，交易记录可以手动关联对话
4. **查询范围**：默认查询最近30天的数据，可通过 `--days` 参数调整

## 常见问题

### Q: 如何修改查询时间范围？
A: 使用 `--days` 参数，例如：`--days 14` 查询最近14天

### Q: 策略提取不准确怎么办？
A: 可以手动查看和编辑数据库，或改进 `de_strategy_extractor.py` 中的提取规则

### Q: 如何查看所有对话记录？
A: 使用数据库查询工具或编写Python脚本查询 `conversations` 表

### Q: 问答系统找不到答案？
A: 尝试使用更具体的关键词，或扩大查询时间范围（增加 `--days` 参数）

## 更新日志

- **2025-12-30**: 初始版本
  - 创建策略提取模块
  - 创建策略分析器
  - 创建策略问答系统
  - 创建统一入口脚本

