# 青鸟交易系统

## 🎯 项目简介

青鸟交易系统是一个基于De.交易策略的BTC交易信号生成系统，支持多交易员、实时订单簿止损、对话记录与学习等功能。

---

## ✨ 核心功能

- **De.交易系统** - 基于De.交易策略的BTC信号生成
- **实时订单簿止损** - 基于订单簿流动性的动态止损
- **多交易员支持** - 支持De.、梦等多个交易员
- **对话记录与学习** - 自动记录交易员对话并学习
- **信号评估** - 科学评估交易信号表现
- **数据库管理** - 多交易员分库架构

---

## 📁 项目结构

```
qingniao/
├── src/              # 源代码
│   ├── generate_btc_de_signals.py    # De.交易信号生成
│   ├── db_manager_*.py               # 数据库管理
│   ├── conversation_logger.py       # 对话记录
│   └── ...
├── docs/design/      # 设计文档
│   ├── database/     # 数据库设计
│   ├── system/       # 系统架构
│   └── features/     # 功能设计
├── rules_engine/     # 规则引擎
│   └── strategy_registry.yaml
├── data/             # 数据文件（不提交到Git）
└── trading_signals/   # 交易信号输出（不提交到Git）
```

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
- **数据库设计**: `docs/design/database/`
- **系统架构**: `docs/design/system/`
- **功能说明**: `docs/design/features/`

---

## 🔧 开发

### Git版本管理

**提交到Git**:
- ✅ 源代码
- ✅ 设计文档
- ✅ 配置文件

**不提交到Git**:
- ❌ 数据库文件（`.duckdb`）
- ❌ 输出文件（`trading_signals/`）
- ❌ 临时文件

详见 `.gitignore`

---

## 📄 许可证

[待定]

---

**最后更新**: 2025-12-30
