# 青鸟交易系统使用说明

## 概述

青鸟交易系统整合了两个交易系统：
1. **De.交易系统** - 区间震荡剥头皮交易系统（主要分析BTC）
2. **梦多空策略** - 涨幅榜做空+追多交易系统

## 快速开始

### 基本使用

```bash
# 运行所有系统（推荐）
python src/unified_trading_system.py

# 或者明确指定运行所有系统
python src/unified_trading_system.py --system all
```

### 运行单个系统

```bash
# 只运行De.交易系统（BTC分析）
python src/unified_trading_system.py --system de

# 只运行梦多空策略（涨幅榜扫描）
python src/unified_trading_system.py --system meng
```

### 自定义参数

```bash
# 运行所有系统，自定义参数
python src/unified_trading_system.py --system all \
    --exchange bybit \
    --limit 50

# 只运行梦多空策略，指定交易所和币种数
python src/unified_trading_system.py --system meng \
    --exchange bitget \
    --limit 200
```

## 命令行参数

| 参数 | 说明 | 可选值 | 默认值 |
|------|------|--------|--------|
| `--system` | 选择要运行的系统 | `de`, `meng`, `all` | `all` |
| `--symbol` | De.系统分析的币种 | 币种符号 | `BTC` |
| `--exchange` | 交易所选择 | `auto`, `bitget`, `bybit`, `binance` | `auto` |
| `--limit` | 扫描币种数 | 整数 | `100` |

## 系统说明

### De.交易系统

**特点**：
- 主要分析BTC/USDT
- 适用于5分钟、15分钟、1小时时间框架
- 区间震荡剥头皮交易
- 使用规则引擎分析

**输出文件**：
- `BTC_de_signals_YYYYMMDD_HHMMSS.md`

**主要功能**：
- 多时间框架分析
- FVG、M顶/W底、Vegas通道等技术形态识别
- 支撑阻力位分析
- OTE区间分析

### 梦多空策略

**特点**：
- 扫描涨幅榜（前100个币种）
- 做空：24小时涨幅 > 20%
- 做多：24小时涨幅 8%-12%
- 使用斐波那契扩展计算目标位

**输出文件**：
- `梦多空策略_交易计划_YYYYMMDD_HHMMSS.md`

**主要功能**：
- 涨幅榜扫描
- 做空机会筛选（斐波扩展位计算）
- 做多机会筛选
- 详细的交易计划生成

## 使用场景

### 场景1：每日交易准备

每天早上运行一次，获取所有系统的交易信号：

```bash
python src/unified_trading_system.py --system all
```

### 场景2：专注BTC交易

如果只想看BTC的交易信号：

```bash
python src/unified_trading_system.py --system de
```

### 场景3：寻找涨幅榜机会

如果想寻找涨幅榜的做空/做多机会：

```bash
python src/unified_trading_system.py --system meng --limit 200
```

### 场景4：定时任务

可以设置定时任务，每2小时运行一次：

**Windows任务计划程序**：
```cmd
python C:\Users\zuoho\code\qimeng2\src\unified_trading_system.py --system all
```

**Linux/Mac cron**：
```bash
# 每2小时运行一次
0 */2 * * * cd /path/to/qimeng2 && python src/unified_trading_system.py --system all
```

## 输出文件位置

所有生成的交易计划文件都保存在项目根目录：

- De.系统：`BTC_de_signals_YYYYMMDD_HHMMSS.md`
- 梦多空策略：`梦多空策略_交易计划_YYYYMMDD_HHMMSS.md`

## 系统集成

### Python代码中调用

```python
from src.unified_trading_system import UnifiedTradingSystem  # 青鸟交易系统

# 创建系统实例
system = UnifiedTradingSystem()

# 运行所有系统
files = system.run_all_systems(exchange='auto', limit=100, de_symbol='BTC')

# 只运行De.系统
de_file = system.run_de_system('BTC')

# 只运行梦多空策略
meng_file = system.run_meng_system(exchange='auto', limit=100)
```

## 注意事项

1. **数据源**：两个系统使用不同的数据源
   - De.系统：主要使用Gate.io/Bitget
   - 梦多空策略：主要使用Bybit/Bitget/Binance

2. **运行时间**：
   - De.系统：约1-2分钟
   - 梦多空策略：约2-5分钟（取决于符合条件的币种数量）

3. **API限制**：注意API调用频率，避免过快请求

4. **网络连接**：需要稳定的网络连接访问交易所API

## 故障排除

### 问题1：模块导入失败

**错误**：`ModuleNotFoundError`

**解决**：确保在项目根目录运行，或者使用完整路径

### 问题2：De.系统未生成文件

**可能原因**：
- 网络连接问题
- API调用失败
- BTC数据获取失败

**解决**：检查网络连接，查看错误信息

### 问题3：梦多空策略未生成文件

**可能原因**：
- 交易所API不可用
- 没有符合条件的币种
- K线数据获取失败

**解决**：尝试更换交易所（`--exchange bitget`）

## 更新日志

- **2025-12-28**: 初始版本，整合De.系统和梦多空策略

