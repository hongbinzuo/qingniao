# ✅ PostgreSQL 迁移准备完成

## 📋 已完成的准备工作

### ✅ 1. 环境检查
- PostgreSQL 18.1 已安装在 `C:\Program Files\PostgreSQL\18\`
- Python 依赖已安装：`psycopg2-binary-2.9.11`, `python-dotenv`

### ✅ 2. 创建的文件

| 文件 | 用途 |
|------|------|
| `src/db_manager_postgres.py` | PostgreSQL 数据库管理器（支持连接池） |
| `scripts/init_postgres_abu_db.py` | 数据库表结构初始化脚本 |
| `scripts/migrate_duckdb_to_postgres.py` | 数据迁移工具 |
| `scripts/create_db_interactive.bat` | 交互式数据库创建脚本 |
| `scripts/create_abu_database.sql` | SQL 创建脚本 |
| `.env.postgres` | PostgreSQL 配置示例 |
| `POSTGRES_MIGRATION_STEPS.md` | 详细执行步骤指南 |
| `docs/PostgreSQL_Migration_Plan.md` | 完整迁移方案文档 |

---

## 🚀 现在开始执行迁移

请按照以下步骤操作：

### Step 1: 停止 Abu 系统（必须）

```cmd
Abu停止所有.bat
```

### Step 2: 配置环境变量

打开 `.env` 文件，在末尾添加以下内容（从 `.env.postgres` 复制）：

```
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=qingniao_abu
PG_USER=abu_user
PG_PASSWORD=Abu2026!Secure
PG_POOL_MIN_SIZE=2
PG_POOL_MAX_SIZE=10
```

### Step 3: 创建数据库

**选择一种方式执行**：

**方式1（推荐）**: 运行批处理脚本
```cmd
scripts\create_db_interactive.bat
```
输入 postgres 用户密码后，脚本会自动创建数据库和用户。

**方式2**: 使用 pgAdmin 图形界面
- 打开 pgAdmin
- 创建数据库 `qingniao_abu`
- 创建用户 `abu_user`，密码 `Abu2026!Secure`
- 授予权限

### Step 4: 初始化数据库表

```cmd
python scripts\init_postgres_abu_db.py
```

预期输出：
```
[1/5] 创建 trading_signals 表...
   ✓ trading_signals 表创建成功
...
✅ PostgreSQL 数据库初始化完成！
```

### Step 5: 测试连接

```cmd
python src\db_manager_postgres.py
```

预期输出：
```
测试 PostgreSQL 连接...
[INFO] PostgreSQL 连接池已初始化
✅ 连接成功！
```

### Step 6: 迁移数据（如果有旧数据）

```cmd
python scripts\migrate_duckdb_to_postgres.py
```

### Step 7: 切换到 PostgreSQL

```cmd
REM 备份 DuckDB 管理器
move src\db_manager_trader.py src\db_manager_trader_duckdb.bak

REM 使用 PostgreSQL 管理器
copy src\db_manager_postgres.py src\db_manager_trader.py
```

### Step 8: 测试系统

```cmd
python scripts\auto_signal_generator.py --once --coins 3
```

### Step 9: 重启 Abu 系统

```cmd
Abu全部启动.bat
```

---

## 📖 详细文档

- **详细步骤**: 请查看 `POSTGRES_MIGRATION_STEPS.md`
- **完整方案**: 请查看 `docs/PostgreSQL_Migration_Plan.md`

---

## ⏱️ 预计时间

- Step 1-3: 5分钟（创建数据库）
- Step 4-5: 2分钟（初始化和测试）
- Step 6: 5-30分钟（取决于数据量）
- Step 7-9: 5分钟（切换和测试）

**总计**: 约 20-50 分钟

---

## 🆘 需要帮助？

如遇到问题：

1. 查看 `POSTGRES_MIGRATION_STEPS.md` 的故障排查部分
2. 检查日志文件
3. 使用回滚方案恢复到 DuckDB

---

## ✅ 成功标志

迁移成功后您将看到：

- ✅ 无数据库锁冲突错误
- ✅ 模式匹配 + 视觉匹配可同时运行
- ✅ 信号正常生成和保存
- ✅ 系统稳定运行

---

**准备好了吗？让我们开始吧！** 🚀

首先执行 **Step 1: 停止 Abu 系统**
