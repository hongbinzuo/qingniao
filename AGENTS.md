# AGENTS.md - AI Coding Agent Guidelines

> This file contains essential information for AI coding agents working on this project.
> 本文档包含青鸟交易系统的关键信息，供AI编码助手参考。

---

## 1. Project Overview / 项目概览

**青鸟交易系统 (Qingniao Trading System)** 是一个基于多交易员策略的加密货币交易信号生成与分析平台。

### Core Features / 核心功能
- **多交易员支持**: De.交易系统、梦多空策略、千叶交易系统等
- **AI视觉分析**: 基于Gemini Vision的图表模式识别
- **规则引擎**: 基于Experta的智能交易规则系统
- **信号生成与评估**: 自动化交易信号生成、跟踪与性能评估
- **对话学习系统**: 自动记录和学习交易员对话
- **ML/DL集成**: 机器学习和深度学习模型用于信号优化
- **实时数据同步**: 多交易所K线数据获取与同步

### Technology Stack / 技术栈
- **Language**: Python 3.8+
- **Database**: DuckDB (主数据库), PostgreSQL (迁移中), MySQL (历史支持)
- **AI/ML**: Gemini Vision API, scikit-learn, XGBoost, PyTorch/TensorFlow (可选)
- **Rule Engine**: Experta (基于CLIPS的专家系统)
- **Technical Analysis**: TA-Lib
- **Data Processing**: pandas, numpy, requests
- **Logging**: 基于JSON Lines的自定义文件日志系统

---

## 2. Project Structure / 项目结构

```
qingniao/
├── src/                          # 核心源代码 (263+ Python文件)
│   ├── abu/                      # ABU系统 (AI视觉分析)
│   ├── chiba_trading_system/     # 千叶交易系统
│   ├── ml_dl/                    # 机器学习和深度学习模块
│   ├── pa/                       # 价格行为 (Price Action)
│   ├── db_manager*.py            # 数据库管理器
│   ├── sync_btc_prices_daily.py  # 每日价格同步
│   ├── system_logger.py          # 系统日志记录器
│   ├── file_logger.py            # 文件日志系统
│   └── generate_*_signals.py     # 信号生成脚本
├── rules_engine/                 # 规则引擎
│   ├── setup_rules_engine.py     # 规则引擎安装测试
│   ├── trading_rules_engine.py   # 交易规则引擎
│   └── strategy_registry.yaml    # 策略注册表
├── scripts/                      # 运行脚本 (250+ 脚本)
│   ├── abu_*.py                  # ABU系统脚本
│   ├── test_*.py                 # 测试脚本
│   └── *.bat                     # Windows批处理脚本
├── config/                       # 配置文件
│   ├── abu_*.yaml                # ABU模式配置
│   ├── logging_config.json       # 日志配置
│   └── strategy_registry.yaml    # 策略注册表
├── docs/                         # 文档 (200+ Markdown文件)
│   ├── design/database/          # 数据库设计文档
│   ├── design/system/            # 系统架构文档
│   ├── design/features/          # 功能设计文档
│   └── reviews/                  # 代码评审报告
├── data/                         # 数据目录 (Git忽略)
│   ├── abu/                      # ABU相关数据
│   ├── chiba_videos/             # 千叶视频分析
│   ├── kline_data/               # K线数据
│   └── logs/                     # 日志文件
├── outputs/                      # 输出目录 (Git忽略)
├── logs/                         # 运行日志目录
├── backups/                      # 备份目录
└── deleting/                     # 待删除文件暂存
```

---

## 3. Key Modules / 关键模块

### 3.1 Database Management / 数据库管理

**多数据库架构**:
- **DuckDB** (推荐): `src/db_manager_duckdb.py`, `src/db_manager_trader.py`
- **PostgreSQL**: `src/db_manager_postgres.py` (迁移中)
- **MySQL**: `src/db_manager_mysql.py` (历史支持)

**核心表结构**:
- `de_viewpoints` - De.观点和交易指令
- `conversation_logs` - 对话日志
- `trade_records` - 交易记录
- `signals` / `signal_evaluations` - 信号和评估

**数据库操作规范**:
```python
# 使用DuckDB管理器
from db_manager_duckdb import get_db_connection

with get_db_connection() as conn:
    conn.execute("SELECT * FROM de_viewpoints LIMIT 10")
```

### 3.2 Logging System / 日志系统

**双重日志架构**:
1. **系统操作日志** (`system_logger.py`): 记录信号生成、交易记录、价格同步等
2. **文件日志** (`file_logger.py`): 基于JSON Lines的详细日志，支持搜索和压缩

**日志规范**:
```python
from system_logger import log_signal_generation, log_price_sync, log_error

# 记录信号生成
log_signal_generation(
    signals_count=5,
    timeframe='15m',
    system_name='de',
    current_price=88710.0
)

# 记录价格同步
log_price_sync(
    timeframe='5m',
    records_synced=100,
    success=True
)
```

**日志配置**: `config/logging_config.json`
- 保留期限: 90天
- 自动压缩: 30天前的日志
- 格式: JSON Lines (.jsonl)

### 3.3 Signal Generation / 信号生成

**主要信号生成器**:
- `generate_btc_de_signals.py` - De.策略BTC信号
- `generate_eth_de_signals.py` - De.策略ETH信号
- `scripts/auto_signal_generator.py` - 自动化信号生成

**信号输出目录**: `outputs/trading_signals/`

### 3.4 Rules Engine / 规则引擎

**基于Experta的规则系统**:
- 规则定义: `rules_engine/strategy_registry.yaml`
- 引擎入口: `rules_engine/setup_rules_engine.py`
- 运行测试: `python rules_engine/setup_rules_engine.py`

**依赖安装**:
```bash
pip install pyyaml experta
```

### 3.5 ABU System (AI Vision) / ABU视觉系统

**AI图表分析系统**:
- 基于Gemini Vision API的图表模式识别
- Al Brooks价格行为模式库
- 向量索引快速匹配

**核心文件**:
- `src/abu/gemini_vision_analyzer.py` - Gemini视觉分析器
- `src/abu/vector_index_manager.py` - 向量索引管理
- `scripts/abu_gemini_pipeline_manager.py` - 流水线管理器

---

## 4. Build & Run Commands / 构建和运行命令

### 4.1 Environment Setup / 环境初始化

**Windows**:
```bat
py -3 -m venv .venv
.\.venv\Scripts\activate
pip install -U pip
pip install -r requirements.txt
```

**Linux/macOS**:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

### 4.2 Optional Dependencies / 可选依赖

```bash
# 机器学习和深度学习
pip install -r requirements_ml.txt

# TA-Lib技术分析 (需要先安装C库)
pip install -r requirements_ta_lib.txt

# 规则引擎
pip install pyyaml experta
```

### 4.3 Common Commands / 常用命令

```bash
# 价格同步
python src/sync_btc_prices_daily.py

# 生成交易信号
python src/generate_btc_de_signals.py

# 录入De.对话
python src/add_de_conversation.py "22:26" "BTC 87k long idea"

# 初始化数据库
python src/database_design_v2.py

# 规则引擎测试
python rules_engine/setup_rules_engine.py
```

### 4.4 Windows Batch Scripts / Windows批处理

```bat
# 启动De.系统
call scripts\start_de_system.bat

# 价格同步测试
call test_price_sync.bat

# ABU全部启动
call abu_start_all.bat
```

---

## 5. Code Style Guidelines / 代码风格规范

### 5.1 Python Style / Python风格

- **Python版本**: 3.8+
- **编码规范**: PEP 8
- **缩进**: 4空格
- **命名规范**:
  - 函数/变量: `snake_case`
  - 类: `PascalCase`
  - 常量: `UPPER_SNAKE_CASE`
  - 模块: `snake_case`
  - 私有成员: `_leading_underscore`

### 5.2 Documentation / 文档规范

- **文件头**: 包含UTF-8编码声明和文件描述
- **Docstrings**: 使用Google风格或NumPy风格
- **注释**: 中文注释为主，关键术语保留英文

```python
# -*- coding: utf-8 -*-
"""
模块功能简述

详细描述模块的功能、参数和返回值
"""

def example_function(param1: str, param2: int) -> bool:
    """
    函数功能描述
    
    Args:
        param1: 参数1描述
        param2: 参数2描述
    
    Returns:
        返回值描述
    """
    pass
```

### 5.3 Import Order / 导入顺序

```python
# 1. 标准库
import sys
import json
from datetime import datetime
from pathlib import Path

# 2. 第三方库
import pandas as pd
import numpy as np
import requests

# 3. 项目内部模块
from db_manager_duckdb import get_db_connection
from system_logger import log_signal_generation
```

---

## 6. Testing Strategy / 测试策略

### 6.1 Test Files / 测试文件

**测试脚本位置**:
- `src/test_*.py` - 单元测试
- `scripts/test_*.py` - 集成测试

**主要测试文件**:
- `src/test_stop_loss.py` - 止损逻辑测试
- `scripts/test_talib_integration.py` - TA-Lib集成测试
- `scripts/test_gemini_model.py` - Gemini模型测试
- `rules_engine/setup_rules_engine.py` - 规则引擎冒烟测试

### 6.2 Running Tests / 运行测试

```bash
# 规则引擎测试
python rules_engine/setup_rules_engine.py

# 止损逻辑测试
python src/test_stop_loss.py

# TA-Lib集成测试
python scripts/test_talib_integration.py
```

### 6.3 Testing Guidelines / 测试规范

- 使用Mock进行HTTP/DB测试，避免直连外部API
- 测试文件命名: `test_*.py`
- 确保测试可重复运行
- 新增功能需配套测试脚本

---

## 7. Security & Configuration / 安全和配置

### 7.1 Environment Variables / 环境变量

**环境文件** (Git忽略):
- `.env` - 主环境配置
- `.env.postgres` - PostgreSQL配置
- `.env.wsl` - WSL环境配置

**敏感信息**:
- API密钥 (Gemini, Gate.io, Binance等)
- 数据库密码
- 访问令牌

### 7.2 Git Ignore Rules / Git忽略规则

**不提交到Git的文件**:
```
.env*
*.duckdb
*.db
__pycache__/
.pytest_cache/
data/
outputs/
logs/
backups/
.venv/
```

### 7.3 Security Best Practices / 安全最佳实践

- 绝不提交密钥或环境配置文件
- 数据库文件使用 `.gitignore` 排除
- 使用环境变量管理敏感配置
- 定期备份重要数据到 `backups/` 目录

---

## 8. Data Management / 数据管理

### 8.1 File Locations / 文件位置

**允许生成临时文件的目录**:
- `data/` - 数据和缓存
- `outputs/` - 输出文件和信号报告
- `logs/` - 运行日志

**禁止在根目录生成临时文件**

### 8.2 Cleanup Rules / 清理规则

1. **删除前移动**: 统一移动到 `deleting/YYYYMMDD_HHMMSS/`
2. **保留期限**: 默认7天
3. **需要保留的内容**: 清理前备份到 `deleting/` 或 `backups/`
4. **不确定的内容**: 新建专用目录后再清理

### 8.3 Backup Strategy / 备份策略

```bash
# 运行备份脚本
python scripts/backup_data.py

# 设置自动备份
call scripts\setup_auto_backup.bat
```

---

## 9. Development Workflow / 开发工作流

### 9.1 Commit Convention / 提交规范

使用 **Conventional Commits**:
- `feat:` - 新功能
- `fix:` - Bug修复
- `docs:` - 文档更新
- `chore:` - 构建/工具变更
- `refactor:` - 代码重构
- `test:` - 测试相关

### 9.2 PR Requirements / PR要求

PR需包含:
1. 变更动机和范围
2. 受影响的脚本列表
3. 运行和验证步骤
4. 示例输出 (如 `*_signals_*.md`)
5. 同步更新 `docs/` 文档

### 9.3 Architecture Overview / 架构概览

**数据流**:
```
价格采集与同步 → 规则引擎判定 → 信号/日志输出 → 学习与评估
```

**推荐阅读**:
- `docs/design/system/完整系统说明.md`
- `docs/design/database/数据库结构设计说明.md`
- `docs/design/features/信号性能分析与改进建议说明.md`

---

## 10. Troubleshooting / 故障排除

### 10.1 Common Issues / 常见问题

**编码问题**:
```python
# 在文件头添加
# -*- coding: utf-8 -*-

# Windows下设置UTF-8
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
```

**数据库连接**:
```python
# 使用上下文管理器
from db_manager_duckdb import get_db_connection

with get_db_connection() as conn:
    # 执行查询
    pass
```

### 10.2 System Status / 系统状态

查看系统状态:
```bash
python scripts/check_abu_status.py
python scripts/check_latest_signals.py
```

---

## 11. Reference Links / 参考链接

- **README**: `README.md`
- **完整系统说明**: `docs/design/system/完整系统说明.md`
- **数据库设计**: `docs/design/database/数据库结构设计说明.md`
- **ABU系统**: `docs/reviews/ABU系统v3.0完整功能实现报告.md`
- **TODO列表**: `docs/TODO.md`

---

**Last Updated**: 2026-01-27
**Maintainer**: AI Coding Agent
**Language**: 中文/English
