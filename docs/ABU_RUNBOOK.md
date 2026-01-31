# ABU Runbook（方案 A：含 PDF 抽样）

本页是 Abu 子系统的一键运行手册，覆盖环境准备、执行命令、产出验证与常见问题。按本文操作可直接“读书 + 学规则 + 出信号 + 上图表”。

## 1. 环境准备（Windows）
- 建议使用 CMD（管理员权限可避免端口/权限问题）
- 可选：创建虚拟环境并安装依赖
  ```bat
  py -3 -m venv .venv
  .\.venv\Scripts\activate
  py -3 -m pip install -U pip
  py -3 -m pip install duckdb fastapi uvicorn pymupdf requests pydantic
  ```
- 若不手动安装，批处理会自动安装 PyMuPDF；其他库建议提前装好

## 2. 快速开始（方案 A：含 PDF 抽样）
1) 设置环境变量并执行批处理（示例抽样 1000 页）
   ```bat
   set PDF_IN=C:\baidunetdiskdownload\阿布图表百科全书8800合并版-原版.pdf
   set PDF_PAGES=1000
   scripts\abu\abu_upgrade_and_run.bat
   ```
   说明：
   - `PDF_IN` 为本地 PDF 路径；`PDF_PAGES` 未设置时默认 500
   - 批处理步骤：
     1. 初始化/迁移 Abu DB（`src\data\qingniao_abu.duckdb`）
     2. 安装 PyMuPDF（如未安装）
     3. 抽样读取 PDF → `data/abu/raw_pages.jsonl`
     4. 构建 Abu 库 → `config/abu_patterns.yaml`
     5. 跑 15m 扫描（Binance→Gate 回退）并写库 + Markdown
     6. 启动后端 API（8090）

2) 打开页面与接口进行验证
   - 页面
     - Abu 图表页: http://localhost:8090/abu
     - De. 信号页: http://localhost:8090/de
   - API
     - http://localhost:8090/api/abu/status
     - http://localhost:8090/api/de/status
     - http://localhost:8090/api/hits

## 3. 产出与验证清单
- 数据库：`src\data\qingniao_abu.duckdb` → 表 `trading_signals` 含列 `symbol/score/notes`
- PDF 原始页：`data/abu/raw_pages.jsonl`（页面计数应≥抽样页数）
- Abu 模式库：`config/abu_patterns.yaml`（含按页推断的标题/模式草稿）
- 信号 Markdown：`trading_signals/ABU_top10_15m_*.md`
- Web：`web/abu/index.html`（暗色样式 + score 柱状图 + long/short 标签）
- 后端：`scripts/qingniao_be_api.py`（FastAPI/uvicorn，端口 8090）

## 4. 常用变体
- 仅跑信号 + 启服务（不读 PDF）
  ```bat
  scripts\abu\abu_upgrade_and_run.bat
  ```
- 改端口（8090 被占用时）
  ```bat
  py -3 -m uvicorn scripts.qingniao_be_api:app --host 0.0.0.0 --port 8091
  ```

## 5. 常见问题排查（FAQ）
- 端口占用（8090）
  - 解决：改端口到 8091（见上文）或释放占用进程
- 网络受限
  - 扫描会调交易所 K 线接口，需可访问外网；安装 PyMuPDF 也需网络
- DuckDB 锁
  - 若报库被占用，请关闭其它进程（包括已开的服务），再重试批处理
- PyMuPDF 未安装
  - 批处理会自动安装；或手动执行 `py -3 -m pip install pymupdf`
- PDF 输入路径包含空格/中文
  - CMD 下建议用完整路径；必要时加引号（批处理中已按参数传递）

## 6. 运行节奏与自动化
- 睡前快照 + 待办：
  ```bat
  py -3 scripts\prepare_sleep.py
  ```
  产物：`trading_signals/.sleep_snapshots/` 与 `trading_signals/.todos/gn_todo_*.json`
- 唤醒续跑：
  ```bat
  py -3 scripts\wake_resume.py --run
  ```
  说明：如设置了 `PDF_IN`，会自动走一键批处理，否则跳过 PDF 任务

## 7. 下一步（建议）
- 调参与调优：用 `config/abu_patterns.yaml` 调整 detectors/ranker 的打分权重，使 `score` 更贴合“阿布图表”的结构化知识
- 前端增强：新增 `/api/abu/history` 与多图联动（ECharts）、前排币种与稳定币过滤配置化

## 8. 文件对照表（关键脚本）
- 批处理与入口
  - `scripts/abu/abu_upgrade_and_run.bat`：一键流程
  - `scripts/start_qingniao_be_api.bat`：启动后端
- 数据库与结构
  - `src/database_design_v2.py`、`scripts/abu/migrate_abu_add_score.py`
  - `src/db_manager_trader.py`（`add_trading_signal` 支持 `symbol/score/notes`）
- PDF → 库
  - `scripts/pa_ingest_pdf.py`（→ `data/abu/raw_pages.jsonl`）
  - `scripts/abu/abu_build_library.py`（→ `config/abu_patterns.yaml`）
- 扫描与产出
  - `scripts/pa_scan_15m_top10.py`（写 DuckDB + `trading_signals/ABU_top*_15m_*.md`）
- 后端与页面
  - `scripts/qingniao_be_api.py`（API）
  - `web/abu/index.html`（前端）

—— 以上流程可重复执行；如数据库已存在，迁移脚本与构库步骤是幂等的，可安全多次运行。
