# Gate.io扩展K线数据获取实施总结

## 需求

1. **15分钟时间框架至少需要10天数据**（推荐90天）
2. **优先使用Gate.io**（限制较少）
3. **支持动态扩展**（不局限于单次限制）
4. **专注于15分钟**，其他时间周期先不做

## 实施内容

### 1. 新增扩展函数

**文件**: `src/get_extended_gateio_klines.py`

**函数**: `get_kline_gateio_extended(symbol, timeframe, days)`

**功能**:
- 支持超过单次限制的数据获取
- 使用Gate.io的from/to参数获取历史数据
- 自动合并多次请求的结果
- 去重并排序

### 2. 修改获取逻辑

**文件**: `scripts/abu_gemini_signal_scanner_enhanced.py`

**修改**:
- `get_klines()`: 添加`days`参数，支持扩展API
- `scan_timeframe()`: 15分钟时间框架使用扩展API
- 默认交易所改为`gate`（优先Gate.io）

### 3. 配置调整

**15分钟时间框架**:
- 从2天改为90天
- 使用扩展API获取数据
- 对应Page 269日线图的匹配需求

## 数据量计算

### 15分钟K线数量

- **1天**: 96根（24小时 × 4）
- **10天**: 960根
- **30天**: 2,880根
- **90天**: 8,640根
- **180天**: 17,280根

### Page 269对应需求

**Page 269**: 日线图（1996-2023，27年）

**15分钟对应**:
- 最小需求：30-90天（对应日线1-3个月）
- 推荐需求：90-180天（对应日线3-6个月）
- 理想需求：180-365天（对应日线6-12个月）

## API限制

### Gate.io API

- **单次请求最大limit**: 1,000根K线
- **支持from/to参数**: 可以获取历史数据
- **无总数据量限制**: 可通过多次请求获取

### 实现策略

1. **第一次请求**: 获取最新的1,000根K线（或所需数量）
2. **后续请求**: 使用from/to参数获取更早的数据
   - `from`: 最旧时间戳 - 1
   - `to`: 最旧时间戳
   - `limit`: 剩余需要的数量（最多1,000）
3. **合并数据**: 
   - 按时间戳去重
   - 按时间从早到晚排序
   - 只返回需要的数量（最新的N根）

## 代码改动

### 1. 新增文件

- `src/get_extended_gateio_klines.py`: 扩展API实现

### 2. 修改文件

- `scripts/abu_gemini_signal_scanner_enhanced.py`:
  - 导入扩展API模块
  - 修改`get_klines()`函数
  - 修改`scan_timeframe()`函数
  - 15分钟时间框架配置改为90天

## 使用方式

### 15分钟时间框架

```python
# 自动使用扩展API，获取90天数据
signals_15m = scan_timeframe(
    matcher, '15m', coins=200, days=90, top_n=200,
    exchange='gate', min_similarity=0.5,
    max_matches_per_symbol=5, write_db=True
)
```

### 其他时间框架

```python
# 使用标准API
signals_5m = scan_timeframe(
    matcher, '5m', coins=300, days=1, top_n=300,
    exchange='gate', min_similarity=0.5,
    max_matches_per_symbol=5, write_db=True
)
```

## 优势

1. ✅ **数据量充足**: 可以获取90天甚至更多数据
2. ✅ **优先Gate.io**: 限制较少，更适合扩展
3. ✅ **自动扩展**: 不需要手动计算limit
4. ✅ **向后兼容**: 仍支持标准API（limit参数）
5. ✅ **时区处理**: 统一使用UTC时间戳

## 下一步

1. **测试验证**: 测试扩展API功能
2. **性能优化**: 优化多次请求的性能
3. **错误处理**: 增强错误处理和重试机制
4. **文档更新**: 更新使用文档



