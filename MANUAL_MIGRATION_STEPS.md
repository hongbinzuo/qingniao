# PostgreSQL 手动迁移步骤

由于自动化过程遇到一些环境问题，请按照以下步骤手动完成迁移。

---

## ✅ 已完成的准备工作

1. ✅ Abu 系统已停止
2. ✅ Python 依赖已安装 (`psycopg2-binary`, `python-dotenv`)
3. ✅ 所有脚本文件已创建
4. ✅ PostgreSQL 18.1 服务正在运行

---

## 🚀 继续执行迁移

### Step 1: 打开 pgAdmin（推荐）

1. 打开开始菜单，搜索 "pgAdmin"
2. 启动 pgAdmin 4
3. 连接到 localhost (使用密码: `woQunide008!`)

### Step 2: 创建数据库

在 pgAdmin 中：

1. 右键点击 "Databases" → "Create" → "Database..."
2. 填写信息：
   - Database: `qingniao_abu`
   - Encoding: `UTF8`
   - Owner: `postgres`
3. 点击 "Save"

### Step 3: 创建用户

在 pgAdmin 中：

1. 右键点击 "Login/Group Roles" → "Create" → "Login/Group Role..."
2. "General" 标签：
   - Name: `abu_user`
3. "Definition" 标签：
   - Password: `Abu2026!Secure`
4. "Privileges" 标签：
   - Can login?: Yes
5. 点击 "Save"

### Step 4: 授予权限

在 pgAdmin 中，打开 SQL 工具（Tools → Query Tool），执行以下 SQL：

```sql
-- 授予数据库权限
GRANT ALL PRIVILEGES ON DATABASE qingniao_abu TO abu_user;

-- 连接到 qingniao_abu 数据库后，执行：
GRANT ALL ON SCHEMA public TO abu_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO abu_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO abu_user;

-- 设置默认权限
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO abu_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO abu_user;
```

### Step 5: 更新 .env 文件

打开 `.env` 文件，在末尾添加：

```
# PostgreSQL 配置
PG_HOST=127.0.0.1
PG_PORT=5432
PG_DATABASE=qingniao_abu
PG_USER=abu_user
PG_PASSWORD=Abu2026!Secure
PG_POOL_MIN_SIZE=2
PG_POOL_MAX_SIZE=10
```

保存文件。

### Step 6: 初始化数据库表

在命令行执行：

```cmd
python scripts\init_postgres_abu_db.py
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

### Step 7: 测试连接

```cmd
python src\db_manager_postgres.py
```

预期输出：

```
测试 PostgreSQL 连接...
[INFO] PostgreSQL 连接池已初始化
✅ 连接成功！
```

**如果连接成功，继续下一步。如果失败，检查：**
- PostgreSQL 服务是否运行
- .env 文件配置是否正确
- 用户和密码是否创建成功

### Step 8: 迁移数据（可选）

如果有旧数据需要迁移：

```cmd
python scripts\migrate_duckdb_to_postgres.py
```

如果是新安装或不需要迁移，跳过此步骤。

### Step 9: 切换到 PostgreSQL

备份原数据库管理器：

```cmd
move src\db_manager_trader.py src\db_manager_trader_duckdb.bak
```

使用 PostgreSQL 管理器：

```cmd
copy src\db_manager_postgres.py src\db_manager_trader.py
```

### Step 10: 测试信号生成

```cmd
python scripts\auto_signal_generator.py --once --coins 3
```

观察是否有错误。

### Step 11: 验证数据

在 pgAdmin 中，打开 SQL 工具，执行：

```sql
-- 查看信号数量
SELECT COUNT(*) FROM trading_signals;

-- 查看最新信号
SELECT * FROM trading_signals ORDER BY created_at DESC LIMIT 5;
```

### Step 12: 重启 Abu 系统

```cmd
Abu全部启动.bat
```

观察两个窗口的日志，确认：
- ✅ 无数据库锁冲突错误
- ✅ 信号正常生成
- ✅ 数据正确写入

---

## 🎯 验收标准

迁移成功的标志：

- [ ] pgAdmin 可以连接到 qingniao_abu 数据库
- [ ] Python 测试连接成功
- [ ] 数据库表结构创建成功（5个表）
- [ ] 信号生成测试通过
- [ ] 模式匹配 + 视觉匹配可同时运行
- [ ] 无数据库锁冲突错误

---

## 🔄 如果遇到问题

### 问题1: pgAdmin 连接失败

**解决方案**:
1. 确认 PostgreSQL 服务正在运行：
   ```cmd
   sc query postgresql-x64-18
   ```
2. 如果服务停止，启动它：
   ```cmd
   net start postgresql-x64-18
   ```

### 问题2: 用户权限不足

**解决方案**:
在 pgAdmin 中重新执行 Step 4 的 SQL 语句。

### 问题3: Python 连接失败

**解决方案**:
1. 检查 .env 文件配置
2. 确认密码正确：`Abu2026!Secure`
3. 尝试使用 localhost 代替 127.0.0.1

### 问题4: 需要回滚

如果迁移失败，恢复到 DuckDB：

```cmd
REM 停止系统
Abu停止所有.bat

REM 恢复 DuckDB 管理器
del src\db_manager_trader.py
move src\db_manager_trader_duckdb.bak src\db_manager_trader.py

REM 重启系统
Abu全部启动.bat
```

---

## 📞 完成后

迁移成功后，请告诉我，我可以帮您：
1. 验证系统运行状况
2. 测试并发运行
3. 继续执行其他优化任务

---

**预计时间**: 15-30 分钟

**Good Luck!** 🚀
