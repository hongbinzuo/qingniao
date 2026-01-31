# PostgreSQL 迁移执行步骤

## ✅ 准备工作（已完成）

- [x] PostgreSQL 18.1 已安装
- [x] Python 依赖已安装 (psycopg2-binary, python-dotenv)
- [x] 迁移脚本已创建

---

## 📝 执行步骤

### Step 1: 停止 Abu 系统

```cmd
scripts/abu/Abu停止所有.bat
```

等待所有进程停止（重要！避免数据库锁定）

---

### Step 2: 配置环境变量

将 `.env.postgres` 文件的内容追加到 `.env` 文件：

```bash
# 使用记事本打开 .env 文件
notepad .env

# 在文件末尾添加以下内容（来自 .env.postgres）:
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=qingniao_abu
PG_USER=abu_user
PG_PASSWORD=Abu2026!Secure
PG_POOL_MIN_SIZE=2
PG_POOL_MAX_SIZE=10
```

保存并关闭文件。

---

### Step 3: 创建 PostgreSQL 数据库和用户

**方式1: 使用批处理脚本（推荐）**

```cmd
scripts\create_db_interactive.bat
```

系统会提示输入 postgres 用户的密码。

**方式2: 使用 pgAdmin 图形界面**

1. 打开 pgAdmin
2. 连接到 localhost
3. 创建数据库 `qingniao_abu`
4. 创建用户 `abu_user`，密码 `Abu2026!Secure`
5. 授予 `abu_user` 对 `qingniao_abu` 的所有权限

**方式3: 手动执行 SQL（如果您熟悉命令行）**

```cmd
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres
```

然后执行以下 SQL：

```sql
CREATE DATABASE qingniao_abu ENCODING 'UTF8';
CREATE USER abu_user WITH PASSWORD 'Abu2026!Secure';
GRANT ALL PRIVILEGES ON DATABASE qingniao_abu TO abu_user;
\c qingniao_abu
GRANT ALL ON SCHEMA public TO abu_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO abu_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO abu_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO abu_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO abu_user;
\q
```

---

### Step 4: 初始化数据库表结构

```cmd
python scripts\abu\init_postgres_abu_db.py
```

应该看到：
```
[1/5] 创建 trading_signals 表...
   ✓ trading_signals 表创建成功
[2/5] 创建 signal_evaluations 表...
   ✓ signal_evaluations 表创建成功
...
✅ PostgreSQL 数据库初始化完成！
```

---

### Step 5: 测试 PostgreSQL 连接

```cmd
python src\db_manager_postgres.py
```

应该看到：
```
测试 PostgreSQL 连接...
[INFO] PostgreSQL 连接池已初始化
✅ 连接成功！
```

如果连接失败，请检查：
- PostgreSQL 服务是否运行
- .env 文件配置是否正确
- 数据库和用户是否创建成功

---

### Step 6: 迁移 DuckDB 数据（可选）

**如果有旧数据需要迁移**：

```cmd
python scripts\migrate_duckdb_to_postgres.py
```

**如果是新安装或不需要迁移**：

跳过此步骤。

---

### Step 7: 备份 DuckDB 文件

```cmd
move src\data\qingniao_abu.duckdb src\data\qingniao_abu.duckdb.bak
```

---

### Step 8: 修改代码使用 PostgreSQL

**方式1: 重命名文件（推荐）**

```cmd
REM 备份原 DuckDB 管理器
move src\db_manager_trader.py src\db_manager_trader_duckdb.bak

REM 使用 PostgreSQL 管理器
copy src\db_manager_postgres.py src\db_manager_trader.py
```

**方式2: 修改导入（如果需要同时支持两种数据库）**

在需要使用数据库的文件中，修改导入：

```python
# 原来:
from db_manager_trader import TraderDBManager

# 改为:
try:
    from db_manager_postgres import PostgresDBManager as TraderDBManager
    print("[INFO] 使用 PostgreSQL 数据库")
except ImportError:
    from db_manager_trader import TraderDBManager
    print("[INFO] 使用 DuckDB 数据库")
```

---

### Step 9: 测试系统

**测试信号生成**:

```cmd
python scripts\auto_signal_generator.py --once --coins 3
```

**检查数据库**:

```cmd
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U abu_user -d qingniao_abu

-- 查看信号数量
SELECT COUNT(*) FROM trading_signals;

-- 查看最新信号
SELECT * FROM trading_signals ORDER BY created_at DESC LIMIT 5;

-- 退出
\q
```

---

### Step 10: 重新启动 Abu 系统

```cmd
scripts/abu/Abu全部启动.bat
```

观察日志，确认：
- ✅ 无数据库锁冲突错误
- ✅ 信号正常生成
- ✅ 数据正确写入

---

## 🔧 故障排查

### 问题1: 连接失败 "psycopg2.OperationalError"

**可能原因**:
- PostgreSQL 服务未启动
- 密码错误
- 数据库不存在

**解决方案**:
```cmd
REM 检查服务状态
sc query postgresql-x64-18

REM 启动服务
net start postgresql-x64-18

REM 检查数据库是否存在
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -l
```

### 问题2: 权限错误 "permission denied"

**解决方案**:
```sql
-- 重新授权
\c qingniao_abu
GRANT ALL ON SCHEMA public TO abu_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO abu_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO abu_user;
```

### 问题3: 迁移时 DuckDB 锁定

**解决方案**:
确保所有 Abu 进程已停止：
```cmd
tasklist | findstr python
REM 如果有进程，强制停止
taskkill /F /IM python.exe
```

---

## 🔄 回滚方案

如果迁移失败或出现问题：

```cmd
REM 1. 停止系统
scripts/abu/Abu停止所有.bat

REM 2. 恢复 DuckDB 管理器
del src\db_manager_trader.py
move src\db_manager_trader_duckdb.bak src\db_manager_trader.py

REM 3. 恢复数据库文件
del src\data\qingniao_abu.duckdb
move src\data\qingniao_abu.duckdb.bak src\data\qingniao_abu.duckdb

REM 4. 重启系统
scripts/abu/Abu全部启动.bat
```

---

## ✅ 验收标准

迁移成功的标志：

- [ ] PostgreSQL 连接测试通过
- [ ] 数据库表结构创建成功
- [ ] 旧数据（如果有）迁移成功
- [ ] 信号生成测试通过
- [ ] 模式匹配 + 视觉匹配可同时运行
- [ ] 无数据库锁冲突错误
- [ ] 数据正确写入和读取

---

## 📊 预期效果

| 指标 | 迁移前 (DuckDB) | 迁移后 (PostgreSQL) |
|------|----------------|---------------------|
| 并发写入 | ❌ 单进程 | ✅ 多进程 |
| 锁冲突 | 频繁 | 极少 |
| 连接管理 | 手动 | 连接池自动管理 |
| 可扩展性 | 低 | 高 |
| 事务支持 | 基础 | 完整 ACID |

---

**准备好开始迁移了吗？**

请按照上述步骤逐步执行，有任何问题随时告知。
