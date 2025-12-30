# De.交易员交易记录录入说明

## 功能说明

这个工具用于录入De.交易员的交易记录到数据库，支持两种录入方式：
1. **交互式录入**：单条记录，逐步填写信息
2. **批量录入**：从文本批量导入多条记录

## 使用方法

### 方法1：使用批处理文件（推荐）

双击运行 `add_trade_record.bat`

### 方法2：直接运行Python脚本

```bash
python src/add_de_trade_record.py
```

## 录入方式

### 1. 交互式录入

运行脚本后选择 `1`，然后按提示填写：

- **交易时间**：格式支持多种，如 `2025-12-30 10:00:00` 或 `2025/12/30 10:00`
- **交易对**：默认 `BTC/USDT`，可修改为其他交易对
- **方向**：输入 `long`/`l`/`多` 表示做多，`short`/`s`/`空` 表示做空
- **杠杆倍数**：数字，如 `10` 表示10倍杠杆
- **开仓价格**：必填，USD价格
- **平仓价格**：可选，未平仓可留空
- **收益率**：可选，百分比
- **盈利金额**：可选，USDT金额
- **策略名称**：可选
- **截图路径**：可选
- **备注信息**：可选

### 2. 批量录入

运行脚本后选择 `2`，然后按格式输入：

**格式**：`时间|交易对|方向|杠杆|开仓价|平仓价|收益率|盈利`

**示例**：
```
2025-12-30 10:00:00|BTC/USDT|long|10|87000|87500|5.75|575
2025-12-30 11:00:00|ETH/USDT|short|5|3000|2950|1.67|50
```

输入 `done` 或 `完成` 结束录入。

## 数据存储

所有交易记录存储在：
```
data/qingniao_de.duckdb
```

表名：`trade_records`

## 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键，自动生成 |
| timestamp | TEXT | 交易时间 |
| symbol | TEXT | 交易对，如 BTC/USDT |
| direction | TEXT | 方向：long/short |
| leverage | INTEGER | 杠杆倍数 |
| entry_price | REAL | 开仓价格 |
| exit_price | REAL | 平仓价格（可选） |
| profit_pct | REAL | 收益率（%） |
| profit_usdt | REAL | 盈利金额（USDT） |
| strategy | TEXT | 策略名称（可选） |
| screenshot_path | TEXT | 截图路径（可选） |
| text_content | TEXT | 备注信息（可选） |
| source | TEXT | 数据来源，默认 'manual' |
| created_at | TEXT | 创建时间 |

## 查询交易记录

### 使用Python查询

```python
from db_manager_trader import TraderDBManager

db = TraderDBManager('de')
conn = db._get_connection()

# 查询最近的10条记录
result = conn.execute('''
    SELECT * FROM trade_records 
    ORDER BY timestamp DESC 
    LIMIT 10
''').fetchall()

for row in result:
    print(row)

db.close()
```

### 使用DuckDB直接查询

```bash
# 安装DuckDB CLI后
duckdb data/qingniao_de.duckdb

# 在DuckDB命令行中
SELECT * FROM trade_records ORDER BY timestamp DESC LIMIT 10;
```

## 注意事项

1. **时间格式**：支持多种时间格式，系统会自动转换
2. **必填字段**：交易时间和开仓价格是必填的
3. **数据验证**：系统会验证数据格式，错误的数据会被跳过
4. **数据库连接**：确保数据库文件存在且可写

## 常见问题

### Q: 录入失败怎么办？
A: 检查数据库文件是否存在，路径是否正确。确保有写入权限。

### Q: 可以修改已录入的记录吗？
A: 目前不支持修改，如需修改请直接操作数据库或删除后重新录入。

### Q: 支持哪些交易对？
A: 支持任意交易对，如 BTC/USDT、ETH/USDT 等。

### Q: 如何导出交易记录？
A: 可以使用DuckDB的导出功能，或编写Python脚本查询后导出为CSV。

## 更新日志

- **2025-12-30**: 初始版本，支持交互式和批量录入


