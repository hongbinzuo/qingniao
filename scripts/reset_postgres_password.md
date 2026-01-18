# 重置 PostgreSQL postgres 用户密码

## 方法1: 使用 Windows 身份验证（推荐）

PostgreSQL 在 Windows 上默认允许本地管理员使用 Windows 身份验证。

### Step 1: 以管理员身份打开命令提示符

右键点击"命令提示符" → "以管理员身份运行"

### Step 2: 使用 Windows 身份验证连接

```cmd
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres
```

**不需要密码**，应该能直接进入。

### Step 3: 重置密码

在 psql 提示符下，执行：

```sql
ALTER USER postgres WITH PASSWORD 'woQunide008!';
```

看到 `ALTER ROLE` 表示成功。

### Step 4: 退出

```sql
\q
```

---

## 方法2: 修改 pg_hba.conf（如果方法1不行）

### Step 1: 找到配置文件

```cmd
notepad "C:\Program Files\PostgreSQL\18\data\pg_hba.conf"
```

### Step 2: 修改认证方式

找到这一行：
```
# IPv4 local connections:
host    all             all             127.0.0.1/32            scram-sha-256
```

临时改为：
```
# IPv4 local connections:
host    all             all             127.0.0.1/32            trust
```

**注意**: `scram-sha-256` 改为 `trust`

同样修改 IPv6 的行：
```
host    all             all             ::1/128                 trust
```

保存文件。

### Step 3: 重启 PostgreSQL 服务

以管理员身份运行：

```cmd
net stop postgresql-x64-18
net start postgresql-x64-18
```

### Step 4: 无需密码连接并重置

```cmd
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h 127.0.0.1
```

在 psql 中执行：

```sql
ALTER USER postgres WITH PASSWORD 'woQunide008!';
\q
```

### Step 5: 恢复 pg_hba.conf

再次编辑 pg_hba.conf，把 `trust` 改回 `scram-sha-256`：

```
host    all             all             127.0.0.1/32            scram-sha-256
host    all             all             ::1/128                 scram-sha-256
```

保存。

### Step 6: 再次重启服务

```cmd
net stop postgresql-x64-18
net start postgresql-x64-18
```

---

## 方法3: 使用 pgAdmin 重置

1. 打开 pgAdmin
2. 如果能连接（可能记住了旧密码）：
   - 右键点击 "postgres" 用户
   - Properties → Definition
   - 设置新密码：`woQunide008!`
   - Save

---

## 验证密码

重置后，测试连接：

```cmd
set PGPASSWORD=woQunide008!
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h 127.0.0.1 -c "SELECT version();"
```

应该能看到 PostgreSQL 版本信息。

---

## 之后继续迁移

密码重置成功后，运行：

```cmd
python scripts\create_db_python.py
```

这将自动创建数据库、用户和授权。
