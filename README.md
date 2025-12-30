# qimeng2 项目

## 🎯 项目简介

qimeng2项目包含两部分：

1. **青鸟交易系统** ⭐ - 当前主要开发系统
2. **遗留工具** - 之前的工具和项目

---

## ✅ 青鸟交易系统（核心）

### 功能

- **De.交易系统** - 基于De.交易策略的BTC信号生成
- **实时订单簿止损** - 基于订单簿流动性的动态止损
- **多交易员支持** - 支持De.、梦等多个交易员
- **对话记录与学习** - 自动记录交易员对话并学习
- **信号评估** - 科学评估交易信号表现

### 核心目录

- **`src/`** - 源代码
  - `generate_btc_de_signals.py` - De.交易信号生成
  - `db_manager_*.py` - 数据库管理
  - `conversation_logger.py` - 对话记录
  - 等等

- **`docs/design/`** - 设计文档
  - `database/` - 数据库设计
  - `system/` - 系统架构
  - `features/` - 功能设计

- **`rules_engine/`** - 规则引擎
  - `strategy_registry.yaml` - 策略注册

- **`data/`** - 数据文件（数据库文件不提交到Git）

---

## 📦 遗留内容

### qimeng2-app/ - Rust加密货币分析器

Rust编写的加密货币交易分析工具，从CoinGecko API获取数据并生成交易计划。

**状态**: 独立工具，保留但不活跃开发

### 其他遗留工具

- `downloads/` - Notion PDF下载工具
- `scan_results/` - 扫描结果
- `twitter_downloader/` - Twitter下载器

**状态**: 历史工具，保留但不活跃开发

---

## 🚀 快速开始

### 环境要求

- Python 3.8+
- DuckDB（推荐）或 MySQL

### 安装依赖

```bash
pip install -r requirements.txt
pip install -r requirements_db.txt
```

### 生成交易信号

```bash
python src/generate_btc_de_signals.py
```

### 初始化数据库

```bash
python src/database_design_v2.py
```

---

## 📚 文档

- **设计文档**: `docs/design/`
- **项目结构**: `项目结构说明.md`
- **数据库设计**: `docs/design/database/`
- **版本管理**: `docs/design/版本管理建议.md`

---

## 🔧 开发

### Git版本管理

**提交到Git**:
- ✅ 青鸟系统源代码
- ✅ 设计文档
- ✅ 配置文件模板

**不提交到Git**:
- ❌ 数据库文件（`.duckdb`）
- ❌ 输出文件（`outputs/`, `trading_signals/`）
- ❌ 遗留工具（`qimeng2-app/`）
- ❌ 临时文件

详见 `.gitignore`

---

## 📝 项目结构

详见 `项目结构说明.md`

---

## 📄 许可证

[待定]

---

**最后更新**: 2025-12-30

