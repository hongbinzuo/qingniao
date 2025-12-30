# 策略管理系统使用说明

## 概述

策略管理系统用于管理所有交易策略文档和配置。目前已注册的策略包括：

- **梦多空策略** - 涨幅榜做空 + 追多交易系统

## 文件结构

```
rules_engine/
├── strategy_registry.yaml    # 策略注册表（配置文件）
├── strategy_manager.py       # 策略管理器（Python类）
└── README_STRATEGY.md        # 本文件
```

策略文档：
```
梦多空策略.md                 # 梦多空策略完整文档
```

## 快速开始

### 1. 列出所有策略

```python
from rules_engine.strategy_manager import StrategyManager

manager = StrategyManager()
strategies = manager.list_strategies(enabled_only=True)

for strategy in strategies:
    print(f"- {strategy.display_name}: {strategy.description}")
    print(f"  优先级: {strategy.priority}, 类型: {strategy.strategy_type}")
```

### 2. 获取策略详情

```python
# 获取策略摘要
summary = manager.get_strategy_summary('meng_duo_kong')
print(summary)

# 读取策略文档
doc_content = manager.read_strategy_document('meng_duo_kong')
print(doc_content)
```

### 3. 启用/禁用策略

```python
# 禁用策略
manager.enable_strategy('meng_duo_kong', enabled=False)

# 启用策略
manager.enable_strategy('meng_duo_kong', enabled=True)
```

## 策略配置格式

策略注册表（`strategy_registry.yaml`）使用YAML格式，包含以下字段：

```yaml
strategies:
  strategy_id:                    # 策略唯一标识
    name: "策略名称"              # 内部名称
    display_name: "显示名称"      # 显示名称
    description: "策略描述"       # 策略描述
    source: "策略来源"            # 策略来源（可选）
    document_path: "文档路径"     # 策略文档路径（相对路径）
    enabled: true                 # 是否启用
    priority: 75                  # 优先级（数字越大优先级越高）
    strategy_type: "策略类型"     # 策略类型
    target_assets: "目标资产"     # 目标交易资产
    core_logic: "核心逻辑"        # 核心交易逻辑
    created_date: "创建日期"      # 创建日期
    updated_date: "更新日期"      # 更新日期
    
    parameters:                   # 策略参数（可选）
      # 策略特定参数...
    
    market_conditions:            # 市场环境要求（可选）
      # 市场条件...
    
    technical_tools:              # 技术工具（可选）
      # 使用的技术工具列表...
    
    success_rate:                 # 成功率预期（可选）
      # 成功率信息...
    
    risk_warnings:                # 风险提示（可选）
      # 风险警告列表...
```

## 添加新策略

要添加新策略，需要：

1. **创建策略文档**：在项目根目录创建策略的Markdown文档

2. **在注册表中添加配置**：编辑 `strategy_registry.yaml`，添加新策略配置

3. **验证策略**：使用 `strategy_manager.py` 测试策略是否正确加载

示例：

```yaml
strategies:
  new_strategy:
    name: "新策略"
    display_name: "新策略"
    description: "策略描述"
    document_path: "../新策略.md"
    enabled: true
    priority: 50
    # ... 其他配置
```

## API 参考

### StrategyManager 类

#### 方法

- `__init__(config_file: str = "strategy_registry.yaml")`  
  初始化策略管理器

- `load_config() -> Dict`  
  加载策略配置文件

- `get_strategy(strategy_id: str) -> Optional[StrategyInfo]`  
  获取指定策略信息

- `list_strategies(enabled_only: bool = True) -> List[StrategyInfo]`  
  列出所有策略（按优先级排序）

- `get_strategy_document_path(strategy_id: str) -> Optional[Path]`  
  获取策略文档路径

- `read_strategy_document(strategy_id: str) -> Optional[str]`  
  读取策略文档内容

- `get_strategy_summary(strategy_id: str) -> Dict`  
  获取策略摘要信息（包含所有配置）

- `enable_strategy(strategy_id: str, enabled: bool = True)`  
  启用/禁用策略

- `save_config()`  
  保存配置到文件

### StrategyInfo 数据类

包含策略的基本信息：
- `name`: 策略名称
- `display_name`: 显示名称
- `description`: 策略描述
- `source`: 策略来源
- `document_path`: 文档路径
- `enabled`: 是否启用
- `priority`: 优先级
- `strategy_type`: 策略类型
- `target_assets`: 目标资产
- `core_logic`: 核心逻辑
- `created_date`: 创建日期
- `updated_date`: 更新日期

## 已注册策略

### 梦多空策略 (meng_duo_kong)

- **名称**: 梦多空策略
- **类型**: 涨幅榜策略
- **目标资产**: 山寨币（涨幅榜常客）
- **核心逻辑**: 空涨幅榜 + 追多
- **优先级**: 75
- **策略来源**: 我的小女人

**主要特点**:
- 做空策略：24小时涨幅>20%，等待1.618-2.0扩展位区间做空
- 做多策略：24小时涨幅8%-12%追涨
- 成功率：做空约80%，做多依赖市场环境
- 扫描频率：每小时

**文档路径**: `../梦多空策略.md`

## 注意事项

1. **文档路径**: 使用相对路径时，相对于 `rules_engine` 目录的父目录
2. **优先级**: 数字越大优先级越高，用于策略排序
3. **启用状态**: 只有启用的策略才会在 `list_strategies(enabled_only=True)` 中显示
4. **配置文件**: 修改 `strategy_registry.yaml` 后，策略管理器会自动加载新配置

## 示例脚本

运行测试脚本：

```bash
cd rules_engine
python strategy_manager.py
```

这将显示所有已注册的策略及其详细信息。




