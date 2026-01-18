# Repository Guidelines

## 项目结构与模块组织
- `src/`：核心脚本（数据库 `db_manager_*`、价格同步 `sync_btc_prices_daily.py`、日志 `system_logger.py`、对话录入 `add_de_conversation.py` 等）。
- `rules_engine/`：交易规则引擎与配置；入口 `setup_rules_engine.py`，配置 `strategy_registry.yaml`。
- `scripts/`：日常运行、批处理与维护脚本集合。
- `data/`、`outputs/`：生成物/临时文件目录，已被 Git 忽略，勿提交；信号报告放 `outputs/trading_signals/`。
- `logs/`：运行日志专用目录（不要放到 `data/`）。
- `docs/design/`：架构、数据库与功能文档。

## 构建、测试与开发命令
### 环境初始化（Linux/macOS）
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
# 可选：规则引擎与 ES 日志
pip install pyyaml experta                 # 使用 rules_engine 时
```

### 环境初始化（Windows）
```bat
py -3 -m venv .venv
.\.venv\Scripts\activate
pip install -U pip
pip install pyyaml experta                 # 可选：规则引擎
```

### 常用运行命令
- 价格同步：
  ```bash
  python src/sync_btc_prices_daily.py
  ```
- 录入 De. 对话（时间戳, 消息）：
  ```bash
  python src/add_de_conversation.py "22:26" "BTC 87k long idea"
  ```
- 规则引擎冒烟：
  ```bash
  python rules_engine/setup_rules_engine.py
  ```
- Windows 助手：`test_price_sync.bat`、`scripts/*.bat|*.ps1`。

### 最小依赖示例
```text
# requirements-min.txt
requests
duckdb
pyyaml   # 读取规则配置（使用 rules_engine 时）
experta  # 规则引擎（仅当需要）
```

## 代码风格与命名
- Python 3.8+；PEP 8；4 空格缩进；`snake_case`（函数/模块）、`PascalCase`（类）。
- 脚本单一职责；补充精炼 docstring/必要注释。
- 长流程使用 `system_logger`/`file_logger`，避免零散 `print`。

## 测试规范
- 现有冒烟：`rules_engine/setup_rules_engine.py`、`src/test_stop_loss.py`（依赖网络）。
- 新增测试应可重复；Mock HTTP/DB，避免直连外部 API。
- 测试命名 `test_*.py`；如用 pytest：`python -m pytest`。

## 提交与 PR 规范
- 使用 Conventional Commits：`feat:`、`fix:`、`docs:`、`chore:` 等。
- PR 需包含：变更动机/范围、受影响脚本、运行与验证步骤、示例输出（如 `*_signals_*.md`）、并更新 `docs/`。
- 变更聚焦；新增生成目录需同步更新 `.gitignore`。

## 安全与配置
- 勿提交密钥/环境与数据库文件：`.env`、`*.duckdb`、`*.db` 等（已在 `.gitignore`）。

## 临时文件与清理规则
- 仅允许在 `data/` 与 `outputs/` 生成临时文件；根目录禁止生成临时文件（必要时先创建子目录）。
- 日志一律写入 `logs/`（不要放到 `data/`）。
- 删除前统一移动到 `deleting/YYYYMMDD_HHMMSS/`（默认保留 7 天，确认无误后再清理）。
- 临时文件中需要保留或可回溯的内容，清理前必须备份（如放入 `deleting/` 或 `backups/`）。
- 若不确定有用内容的归档位置，可新建专用目录后再清理。

## 架构概览
- 数据流：价格采集与同步 → 规则引擎判定 → 信号/日志输出 → 学习与评估。
- 推荐阅读：`docs/design/system/完整系统说明.md`、`docs/design/database/数据库结构设计说明.md`、`docs/design/features/信号性能分析与改进建议说明.md`。
