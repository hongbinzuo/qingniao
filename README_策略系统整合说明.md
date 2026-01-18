# De.策略系统整合说明

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│              策略问答系统（增强版）                        │
│  - 基础问答（de_strategy_qa.py）                        │
│  - 增强问答（de_enhanced_qa.py）                        │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│              策略知识库（de_strategy_knowledge_base.py）   │
│  - 策略-规则映射                                          │
│  - 概念-策略映射                                          │
│  - 规则使用统计                                           │
└──────────────┬──────────────────────────────────────────┘
               │
       ┌───────┴───────┐
       │               │
┌──────▼──────┐  ┌─────▼──────┐
│  规则引擎   │  │  ML/DL系统  │
│ (experta)   │  │ (LSTM/RL)   │
└─────────────┘  └────────────┘
```

## 新增功能

### 1. 策略知识库 (`src/de_strategy_knowledge_base.py`)

**功能**：
- 存储策略、规则、概念之间的关系
- 策略到规则的映射
- 规则到策略的反向映射
- 概念到策略的映射
- 策略关系网络分析
- 知识图谱导出

**核心类**：
- `StrategyRuleMapping`: 策略-规则映射
- `DeStrategyKnowledgeBase`: 策略知识库（整合规则引擎和ML/DL）

**使用示例**：
```python
from de_strategy_knowledge_base import DeStrategyKnowledgeBase

kb = DeStrategyKnowledgeBase()

# 获取策略的规则信息
info = kb.get_strategy_rules_info('FVG策略')
print(info['rules'])  # ['FVG_Bullish_Long', 'FVG_Bearish_Short']

# 获取策略关系网络
relationships = kb.get_strategy_relationships('FVG策略')
print(relationships['related_strategies'])  # 相关策略列表

# 保存知识图谱
kb.save_knowledge_graph('data/strategy_knowledge_graph.json')
```

### 2. 增强版问答系统 (`src/de_enhanced_qa.py`)

**功能**：
- 整合规则引擎结果
- 整合ML/DL预测结果
- 策略关系查询
- 规则使用统计
- 综合答案生成

**新增问题类型**：
- "FVG策略的规则是什么？" → 返回规则引擎规则
- "ML模型对当前市场的预测是什么？" → 返回ML/DL预测
- "Vegas策略和FVG策略有什么关系？" → 返回策略关系网络
- "FVG规则的使用统计是什么？" → 返回规则使用统计

**使用示例**：
```bash
# 基础问答
python src/de_data_manager.py ask-strategy "De.最近用了什么策略？"

# 增强版问答（整合规则引擎和ML/DL）
python src/de_data_manager.py ask-strategy "FVG策略的规则是什么？" --enhanced

# 综合答案（显示所有信息）
python src/de_data_manager.py ask-strategy "FVG策略" --enhanced --comprehensive

# 交互式增强问答
python src/de_data_manager.py ask-strategy --interactive --enhanced
```

## 策略-规则映射

### 已映射的策略

1. **FVG策略**
   - 规则: `FVG_Bullish_Long`, `FVG_Bearish_Short`
   - 概念: FVG, Fair Value Gap, 价格缺口
   - 优先级: 100（最高）
   - 适用市场: 趋势、波动

2. **Vegas通道策略**
   - 规则: `Vegas_Above_Long`, `Vegas_Below_Short`, `Vegas_Breakout`
   - 概念: Vegas, EMA144, EMA169, 动态支撑阻力
   - 优先级: 70
   - 适用市场: 趋势、震荡

3. **区间震荡策略**
   - 规则: `Range_Breakout`, `Range_Bounce`
   - 概念: 区间, 震荡, 箱体, 突破
   - 优先级: 85
   - 适用市场: 震荡

4. **保本止损策略**
   - 规则: `Breakeven_Stop_Loss`
   - 概念: 保本, 盈亏平衡, 风险管理
   - 优先级: 50
   - 适用市场: 全部

5. **分批止盈策略**
   - 规则: `Partial_Take_Profit`
   - 概念: 止盈, 分批, 风险管理
   - 优先级: 50
   - 适用市场: 全部

6. **M顶W底策略**
   - 规则: `M_Top_Short`, `W_Bottom_Long`
   - 概念: M顶, W底, 双顶, 双底, 反转形态
   - 优先级: 90
   - 适用市场: 反转、震荡

## 知识图谱

知识图谱以JSON格式存储，包含：

```json
{
  "strategies": {
    "FVG策略": {
      "rules": ["FVG_Bullish_Long", "FVG_Bearish_Short"],
      "concepts": ["FVG", "Fair Value Gap"],
      "market_conditions": ["trend", "volatile"],
      "timeframes": ["5m", "15m"],
      "priority": 100,
      "description": "..."
    }
  },
  "rules": {
    "FVG_Bullish_Long": {
      "strategies": ["FVG策略"],
      "priority": 100
    }
  },
  "concepts": {
    "FVG": {
      "strategies": ["FVG策略"],
      "usage_count": 1
    }
  }
}
```

## 整合规则引擎

### 规则引擎集成

增强版问答系统会自动检测并集成规则引擎：

```python
# 自动检测规则引擎
try:
    from trading_rules_engine import TradingRulesEngine
    rules_engine_available = True
except ImportError:
    rules_engine_available = False
```

### 规则引擎查询

当询问策略规则时，系统会：
1. 从知识库获取策略-规则映射
2. 从数据库查询规则使用情况
3. 返回规则引擎规则名称和使用示例

## 整合ML/DL系统

### ML/DL系统集成

增强版问答系统会自动检测并集成交易员大脑系统：

```python
# 自动检测ML/DL系统
try:
    from ml_dl.trading_brain_system import TradingBrainSystem
    trading_brain_available = True
except ImportError:
    trading_brain_available = False
```

### ML/DL预测查询

当询问ML预测时，系统会：
1. 调用交易员大脑系统
2. 获取市场数据
3. 生成交易信号
4. 返回预测结果和置信度

## 使用流程

### 1. 构建知识图谱

```bash
python src/de_data_manager.py build-knowledge-graph
```

这会生成 `data/strategy_knowledge_graph.json` 文件。

### 2. 使用增强版问答

```bash
# 交互式增强问答
python src/de_data_manager.py ask-strategy --interactive --enhanced

# 命令行问答
python src/de_data_manager.py ask-strategy "FVG策略的规则是什么？" --enhanced
```

### 3. 查看综合答案

```bash
python src/de_data_manager.py ask-strategy "FVG策略" --enhanced --comprehensive
```

这会显示：
- 基础答案（从数据库查询）
- 策略规则信息（规则引擎）
- ML/DL预测（如果可用）
- 策略关系网络

## 扩展策略映射

要添加新的策略映射，编辑 `src/de_strategy_knowledge_base.py`：

```python
self.strategy_to_rules = {
    '新策略名称': {
        'rules': ['规则1', '规则2'],
        'concepts': ['概念1', '概念2'],
        'market_conditions': ['市场条件'],
        'timeframes': ['时间框架'],
        'priority': 优先级,
        'description': '策略描述'
    }
}
```

## 注意事项

1. **规则引擎依赖**: 需要安装 `experta` 库
   ```bash
   pip install experta
   ```

2. **ML/DL依赖**: 需要安装 `torch` 等ML库（可选）
   ```bash
   pip install torch
   ```

3. **数据库**: 策略知识库会查询 `trader_viewpoints` 和 `conversations` 表

4. **性能**: ML/DL预测可能需要较长时间，建议在后台运行

## 未来改进

1. **向量搜索**: 使用向量数据库（如FAISS）进行语义搜索
2. **知识图谱可视化**: 使用Neo4j或D3.js可视化策略关系
3. **规则自动提取**: 从对话中自动提取新规则
4. **策略推荐**: 基于市场环境推荐适用策略
5. **规则验证**: 验证规则执行效果







