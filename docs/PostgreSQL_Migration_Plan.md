# Abu 系统 PostgreSQL 迁移方案

## 一、迁移目标

解决 DuckDB 单进程锁竞争问题，支持多脚本并发运行。

---

## 二、PostgreSQL 环境准备

### 1. 确认 PostgreSQL 安装

```cmd
# 检查版本
psql --version

# 检查服务状态
sc query postgresql-x64-16  # 或您安装的版本号
```

### 2. 创建数据库和用户

```sql
-- 以管理员身份连接
psql -U postgres

-- 创建数据库
CREATE DATABASE qingniao_abu ENCODING 'UTF8';

-- 创建用户
CREATE USER abu_user WITH PASSWORD 'your_secure_password_here';

-- 授权
GRANT ALL PRIVILEGES ON DATABASE qingniao_abu TO abu_user;

-- 切换到新数据库
\c qingniao_abu

-- 授权模式
GRANT ALL ON SCHEMA public TO abu_user;
```

### 3. 配置连接信息

创建 `.env` 文件（项目根目录）：

```env
# PostgreSQL 配置
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=qingniao_abu
PG_USER=abu_user
PG_PASSWORD=your_secure_password_here

# 连接池配置
PG_POOL_MIN_SIZE=2
PG_POOL_MAX_SIZE=10
```

---

## 三、安装依赖

```bash
pip install psycopg2-binary python-dotenv
# 或者使用 psycopg3（异步支持更好）
pip install psycopg[binary,pool] python-dotenv
```

---

## 四、代码实现

### 4.1 创建 PostgreSQL 数据库管理器

**文件：`src/db_manager_postgres.py`**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostgreSQL 数据库管理器
用于 Abu 系统，支持多进程并发
"""

import os
import sys
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class PostgresDBManager:
    """PostgreSQL 数据库管理器"""
    
    # 连接池（类级别共享）
    _connection_pool = None
    
    def __init__(self, trader_id='abu'):
        self.trader_id = trader_id
        self._init_connection_pool()
    
    @classmethod
    def _init_connection_pool(cls):
        """初始化连接池（只初始化一次）"""
        if cls._connection_pool is None:
            try:
                cls._connection_pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=int(os.getenv('PG_POOL_MIN_SIZE', 2)),
                    maxconn=int(os.getenv('PG_POOL_MAX_SIZE', 10)),
                    host=os.getenv('PG_HOST', 'localhost'),
                    port=int(os.getenv('PG_PORT', 5432)),
                    database=os.getenv('PG_DATABASE', 'qingniao_abu'),
                    user=os.getenv('PG_USER', 'abu_user'),
                    password=os.getenv('PG_PASSWORD', ''),
                    cursor_factory=RealDictCursor
                )
                print(f"[INFO] PostgreSQL 连接池已初始化", file=sys.stderr)
            except Exception as e:
                print(f"[ERROR] 无法初始化 PostgreSQL 连接池: {e}", file=sys.stderr)
                raise
    
    def get_connection(self):
        """从连接池获取连接"""
        if self._connection_pool is None:
            raise RuntimeError("连接池未初始化")
        return self._connection_pool.getconn()
    
    def return_connection(self, conn):
        """归还连接到连接池"""
        if self._connection_pool:
            self._connection_pool.putconn(conn)
    
    def close_all_connections(self):
        """关闭所有连接"""
        if self._connection_pool:
            self._connection_pool.closeall()
            PostgresDBManager._connection_pool = None
    
    # ========== 交易信号操作 ==========
    
    def add_trading_signal(self, signal_data: Dict) -> int:
        """添加交易信号"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO trading_signals (
                    signal_time, timeframe, symbol, signal_type, entry_price,
                    stop_loss, take_profit_1, take_profit_2, entry_model,
                    strength, risk_reward_ratio, volatility_level, system_name,
                    score, notes, status, created_at
                ) VALUES (
                    %(signal_time)s, %(timeframe)s, %(symbol)s, %(signal_type)s, %(entry_price)s,
                    %(stop_loss)s, %(take_profit_1)s, %(take_profit_2)s, %(entry_model)s,
                    %(strength)s, %(risk_reward_ratio)s, %(volatility_level)s, %(system_name)s,
                    %(score)s, %(notes)s, %(status)s, %(created_at)s
                ) RETURNING id
            ''', signal_data)
            
            signal_id = cursor.fetchone()['id']
            conn.commit()
            return signal_id
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"[ERROR] 添加交易信号失败: {e}", file=sys.stderr)
            raise
        finally:
            if conn:
                self.return_connection(conn)
    
    def update_signal_status(self, signal_id: int, status: str, **kwargs):
        """更新信号状态"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 构建更新语句
            update_fields = ['status = %s', 'updated_at = %s']
            values = [status, datetime.now().isoformat()]
            
            # 动态添加其他字段
            field_mapping = {
                'entry_time': 'entry_time',
                'exit_time': 'exit_time',
                'exit_price': 'exit_price',
                'exit_reason': 'exit_reason',
                'pnl_pct': 'pnl_pct',
                'breakeven_stop_set': 'breakeven_stop_set',
                'quick_tp_reached': 'quick_tp_reached',
                'last_check_time': 'last_check_time',
                'check_count': 'check_count',
                'entry_price_actual': 'entry_price_actual'
            }
            
            for key, db_field in field_mapping.items():
                if key in kwargs and kwargs[key] is not None:
                    update_fields.append(f'{db_field} = %s')
                    values.append(kwargs[key])
            
            values.append(signal_id)
            
            query = f'''
                UPDATE trading_signals 
                SET {', '.join(update_fields)}
                WHERE id = %s
            '''
            
            cursor.execute(query, values)
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"[ERROR] 更新信号状态失败: {e}", file=sys.stderr)
            raise
        finally:
            if conn:
                self.return_connection(conn)
    
    def get_active_signals(self, hours: int = 24) -> List[Dict]:
        """获取活跃信号"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            cursor.execute('''
                SELECT *
                FROM trading_signals
                WHERE status IN ('pending', 'active', 'partial_tp')
                AND created_at >= %s
                ORDER BY created_at DESC
            ''', (cutoff_time,))
            
            return cursor.fetchall()
        except Exception as e:
            print(f"[ERROR] 获取活跃信号失败: {e}", file=sys.stderr)
            return []
        finally:
            if conn:
                self.return_connection(conn)
    
    def get_trading_signals(self, 
                           timeframe: Optional[str] = None,
                           symbol: Optional[str] = None,
                           status: Optional[str] = None,
                           limit: int = 100,
                           days: int = 7) -> List[Dict]:
        """查询交易信号"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            conditions = []
            values = []
            
            cutoff_time = (datetime.now() - timedelta(days=days)).isoformat()
            conditions.append('created_at >= %s')
            values.append(cutoff_time)
            
            if timeframe:
                conditions.append('timeframe = %s')
                values.append(timeframe)
            
            if symbol:
                conditions.append('symbol = %s')
                values.append(symbol)
            
            if status:
                conditions.append('status = %s')
                values.append(status)
            
            where_clause = ' AND '.join(conditions) if conditions else '1=1'
            values.append(limit)
            
            query = f'''
                SELECT *
                FROM trading_signals
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT %s
            '''
            
            cursor.execute(query, values)
            return cursor.fetchall()
        except Exception as e:
            print(f"[ERROR] 查询交易信号失败: {e}", file=sys.stderr)
            return []
        finally:
            if conn:
                self.return_connection(conn)

# 向后兼容：创建别名
TraderDBManager = PostgresDBManager
```

### 4.2 创建数据库表结构

**文件：`scripts/init_postgres_abu_db.py`**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始化 PostgreSQL Abu 数据库
"""

import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

def init_database():
    """创建 Abu 系统所需的表结构"""
    
    conn = psycopg2.connect(
        host=os.getenv('PG_HOST', 'localhost'),
        port=int(os.getenv('PG_PORT', 5432)),
        database=os.getenv('PG_DATABASE', 'qingniao_abu'),
        user=os.getenv('PG_USER', 'abu_user'),
        password=os.getenv('PG_PASSWORD', '')
    )
    
    cursor = conn.cursor()
    
    print("[1/5] 创建 trading_signals 表...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trading_signals (
            id SERIAL PRIMARY KEY,
            signal_time TIMESTAMP NOT NULL,
            timeframe VARCHAR(10),
            symbol VARCHAR(20),
            signal_type VARCHAR(10),
            entry_price NUMERIC(20, 8),
            stop_loss NUMERIC(20, 8),
            take_profit_1 NUMERIC(20, 8),
            take_profit_2 NUMERIC(20, 8),
            entry_model TEXT,
            strength VARCHAR(20),
            risk_reward_ratio NUMERIC(10, 2),
            volatility_level VARCHAR(20),
            system_name VARCHAR(50),
            score NUMERIC(10, 2),
            notes TEXT,
            status VARCHAR(20) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            
            -- 信号反馈相关字段
            entry_time TIMESTAMP,
            exit_time TIMESTAMP,
            exit_price NUMERIC(20, 8),
            exit_reason TEXT,
            pnl_pct NUMERIC(10, 4),
            breakeven_stop_set BOOLEAN DEFAULT FALSE,
            quick_tp_reached BOOLEAN DEFAULT FALSE,
            last_check_time TIMESTAMP,
            check_count INTEGER DEFAULT 0,
            entry_price_actual NUMERIC(20, 8)
        )
    ''')
    
    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_symbol ON trading_signals(symbol)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_status ON trading_signals(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_created_at ON trading_signals(created_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_timeframe ON trading_signals(timeframe)')
    
    print("[2/5] 创建 signal_evaluations 表...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS signal_evaluations (
            id SERIAL PRIMARY KEY,
            signal_id INTEGER NOT NULL,
            evaluation_time TIMESTAMP NOT NULL,
            result VARCHAR(20),
            actual_entry_price NUMERIC(20, 8),
            actual_exit_price NUMERIC(20, 8),
            actual_profit_pct NUMERIC(10, 4),
            actual_profit_usdt NUMERIC(20, 8),
            stop_loss_hit BOOLEAN DEFAULT FALSE,
            take_profit_1_hit BOOLEAN DEFAULT FALSE,
            take_profit_2_hit BOOLEAN DEFAULT FALSE,
            missed BOOLEAN DEFAULT FALSE,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (signal_id) REFERENCES trading_signals(id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_evaluations_signal_id ON signal_evaluations(signal_id)')
    
    print("[3/5] 创建 pattern_library 表...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pattern_library (
            id SERIAL PRIMARY KEY,
            pattern_name VARCHAR(100),
            pattern_type VARCHAR(50),
            confidence NUMERIC(5, 2),
            chart_path TEXT,
            gemini_annotation_json TEXT,
            chart_features_json TEXT,
            ebook_references TEXT,
            text_description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    print("[4/5] 创建 ml_optimization_results 表...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ml_optimization_results (
            id SERIAL PRIMARY KEY,
            model_type VARCHAR(50),
            parameters_json TEXT,
            metrics_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    print("[5/5] 创建 system_configs 表...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_configs (
            id SERIAL PRIMARY KEY,
            config_key VARCHAR(100) UNIQUE NOT NULL,
            config_value TEXT,
            description TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("\n✅ PostgreSQL 数据库初始化完成！")

if __name__ == '__main__':
    init_database()
```

### 4.3 数据迁移脚本

**文件：`scripts/migrate_duckdb_to_postgres.py`**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 DuckDB 数据迁移到 PostgreSQL
"""

import duckdb
import psycopg2
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

DB_DIR = Path(__file__).parent.parent / "src" / "data"
DUCKDB_FILE = DB_DIR / "qingniao_abu.duckdb"

def migrate_table(duck_conn, pg_conn, table_name, columns):
    """迁移单个表"""
    print(f"\n迁移表: {table_name}")
    
    # 读取 DuckDB 数据
    try:
        rows = duck_conn.execute(f"SELECT * FROM {table_name}").fetchall()
        print(f"  从 DuckDB 读取 {len(rows)} 条记录")
    except Exception as e:
        print(f"  ⚠️ 表不存在或读取失败: {e}")
        return
    
    if not rows:
        print("  ℹ️ 表为空，跳过")
        return
    
    # 写入 PostgreSQL
    pg_cursor = pg_conn.cursor()
    placeholders = ', '.join(['%s'] * len(columns))
    insert_query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
    
    success_count = 0
    error_count = 0
    
    for row in rows:
        try:
            # DuckDB 返回的是 tuple，需要转换
            values = [row[i] for i in range(len(columns))]
            pg_cursor.execute(insert_query, values)
            success_count += 1
        except Exception as e:
            error_count += 1
            print(f"  ❌ 插入失败: {e}")
            continue
    
    pg_conn.commit()
    print(f"  ✅ 成功迁移 {success_count} 条记录，失败 {error_count} 条")

def main():
    """主迁移流程"""
    
    if not DUCKDB_FILE.exists():
        print(f"❌ DuckDB 文件不存在: {DUCKDB_FILE}")
        return
    
    print("=" * 60)
    print("DuckDB → PostgreSQL 数据迁移工具")
    print("=" * 60)
    
    # 连接 DuckDB
    print("\n[1] 连接 DuckDB...")
    duck_conn = duckdb.connect(str(DUCKDB_FILE), read_only=True)
    print("  ✅ DuckDB 连接成功")
    
    # 连接 PostgreSQL
    print("\n[2] 连接 PostgreSQL...")
    pg_conn = psycopg2.connect(
        host=os.getenv('PG_HOST', 'localhost'),
        port=int(os.getenv('PG_PORT', 5432)),
        database=os.getenv('PG_DATABASE', 'qingniao_abu'),
        user=os.getenv('PG_USER', 'abu_user'),
        password=os.getenv('PG_PASSWORD', '')
    )
    print("  ✅ PostgreSQL 连接成功")
    
    # 迁移 trading_signals 表
    print("\n[3] 迁移数据...")
    migrate_table(
        duck_conn, pg_conn, 'trading_signals',
        [
            'signal_time', 'timeframe', 'symbol', 'signal_type', 'entry_price',
            'stop_loss', 'take_profit_1', 'take_profit_2', 'entry_model',
            'strength', 'risk_reward_ratio', 'volatility_level', 'system_name',
            'score', 'notes', 'status', 'created_at',
            'entry_time', 'exit_time', 'exit_price', 'exit_reason', 'pnl_pct',
            'breakeven_stop_set', 'quick_tp_reached', 'last_check_time',
            'check_count', 'entry_price_actual'
        ]
    )
    
    # 迁移 signal_evaluations 表
    migrate_table(
        duck_conn, pg_conn, 'signal_evaluations',
        [
            'signal_id', 'evaluation_time', 'result', 'actual_entry_price',
            'actual_exit_price', 'actual_profit_pct', 'actual_profit_usdt',
            'stop_loss_hit', 'take_profit_1_hit', 'take_profit_2_hit',
            'missed', 'notes', 'created_at'
        ]
    )
    
    # 迁移 pattern_library 表（如果存在）
    migrate_table(
        duck_conn, pg_conn, 'pattern_library',
        [
            'pattern_name', 'pattern_type', 'confidence', 'chart_path',
            'gemini_annotation_json', 'chart_features_json',
            'ebook_references', 'text_description', 'created_at'
        ]
    )
    
    duck_conn.close()
    pg_conn.close()
    
    print("\n" + "=" * 60)
    print("✅ 迁移完成！")
    print("=" * 60)

if __name__ == '__main__':
    main()
```

---

## 五、修改现有代码

### 5.1 修改 `signal_result_feedback.py`

在文件开头添加：

```python
# 尝试导入 PostgreSQL 管理器
try:
    from db_manager_postgres import PostgresDBManager as TraderDBManager
    DB_BACKEND = 'postgres'
except ImportError:
    from db_manager_trader import TraderDBManager
    DB_BACKEND = 'duckdb'
```

### 5.2 修改 `auto_signal_generator.py`

同样在开头添加数据库选择逻辑。

---

## 六、迁移步骤

### Step 1: 环境准备（5分钟）

```bash
# 安装依赖
pip install psycopg2-binary python-dotenv

# 创建 .env 文件
cat > .env << EOF
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=qingniao_abu
PG_USER=abu_user
PG_PASSWORD=your_password_here
PG_POOL_MIN_SIZE=2
PG_POOL_MAX_SIZE=10
EOF
```

### Step 2: 初始化数据库（2分钟）

```bash
# 连接 PostgreSQL 创建数据库和用户
psql -U postgres -f scripts/create_abu_database.sql

# 初始化表结构
python scripts/init_postgres_abu_db.py
```

### Step 3: 数据迁移（10-30分钟，取决于数据量）

```bash
# 停止所有 Abu 进程
Abu停止所有.bat

# 执行迁移
python scripts/migrate_duckdb_to_postgres.py

# 验证数据
psql -U abu_user -d qingniao_abu -c "SELECT COUNT(*) FROM trading_signals;"
```

### Step 4: 切换数据库后端（5分钟）

```bash
# 重命名文件（启用 PostgreSQL 管理器）
move src\db_manager_trader.py src\db_manager_trader_duckdb.py.bak
copy src\db_manager_postgres.py src\db_manager_trader.py
```

### Step 5: 测试（10分钟）

```bash
# 测试信号生成
python scripts/auto_signal_generator.py --once --coins 3

# 测试信号跟踪
python src/check_signal_status.py

# 检查数据库
psql -U abu_user -d qingniao_abu -c "SELECT * FROM trading_signals ORDER BY created_at DESC LIMIT 5;"
```

### Step 6: 重新启动系统

```bash
Abu全部启动.bat
```

---

## 七、回滚方案

如果迁移失败或出现问题：

```bash
# 停止系统
Abu停止所有.bat

# 恢复 DuckDB 管理器
move src\db_manager_trader.py src\db_manager_trader_postgres.py.bak
move src\db_manager_trader_duckdb.py.bak src\db_manager_trader.py

# 重启系统
Abu全部启动.bat
```

---

## 八、性能优化建议

### 1. 连接池配置

根据并发需求调整：
- 低并发（2-3个脚本）：`PG_POOL_MAX_SIZE=5`
- 中并发（5-10个脚本）：`PG_POOL_MAX_SIZE=15`
- 高并发（>10个脚本）：`PG_POOL_MAX_SIZE=20`

### 2. 查询优化

- 已创建必要索引
- 定期运行 `VACUUM ANALYZE` 优化表

### 3. 监控

```sql
-- 查看活跃连接
SELECT * FROM pg_stat_activity WHERE datname = 'qingniao_abu';

-- 查看表大小
SELECT pg_size_pretty(pg_total_relation_size('trading_signals'));
```

---

## 九、预期收益

| 指标 | DuckDB | PostgreSQL |
|------|--------|------------|
| 并发写入 | ❌ 单进程 | ✅ 多进程 |
| 连接管理 | 手动 | 连接池 |
| 锁冲突 | 频繁 | 极少 |
| 可扩展性 | 低 | 高 |
| 事务支持 | 基础 | 完整 ACID |

---

## 十、注意事项

1. **.env 文件安全**：不要提交到 Git
2. **备份 DuckDB 文件**：迁移前备份
3. **测试充分**：先在测试环境验证
4. **逐步迁移**：可以先只迁移 Abu 系统
5. **监控性能**：迁移后观察系统表现

---

## 总结

完成以上步骤后，Abu 系统将能够：
- ✅ **多脚本并行运行**（模式匹配 + 视觉匹配同时运行）
- ✅ **无数据库锁冲突**
- ✅ **更好的并发性能**
- ✅ **更强的数据一致性**

**预计迁移时间**：1-2小时（含测试）
