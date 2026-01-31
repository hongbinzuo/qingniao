# Abu 系统修复执行计划

## 当前状态总结

根据扫描和您的要求，现在需要处理以下事项：

---

## ✅ 1. PostgreSQL 迁移方案

**状态**: 已完成  
**文档**: `docs/PostgreSQL_Migration_Plan.md`

**包含内容**:
- 完整的迁移步骤（环境准备 → 数据库初始化 → 数据迁移 → 代码切换 → 测试）
- `src/db_manager_postgres.py` - PostgreSQL 数据库管理器（支持连接池）
- `scripts/abu/init_postgres_abu_db.py` - 数据库表结构初始化
- `scripts/migrate_duckdb_to_postgres.py` - 数据迁移工具
- 回滚方案和性能优化建议

**预计效果**:
- ✅ 解决数据库锁竞争问题
- ✅ 支持多脚本并发运行
- ✅ 更好的数据一致性

---

## ✅ 2. 信号生成逻辑调整

**需求**: 每4小时生成一批，Top 10 币种

### 修改内容

#### A. 修改 `scripts/abu/Abu全部启动.bat`

```批处理
REM 原来: --interval 1.0 --coins 30
REM 修改为: --interval 4.0 --coins 10

start "ABU模式匹配" cmd /k "python scripts\auto_signal_generator.py --interval 4.0 --coins 10"
```

#### B. 修改默认参数 (`auto_signal_generator.py:72,85`)

```python
def __init__(
    self,
    interval_hours: float = 4.0,    # 从 1.0 改为 4.0
    top_n_coins: int = 10,           # 从 30 改为 10
    timeframes: List[str] = None
):
```

#### C. 修改文档说明

更新 `README_Abu跑批使用说明.md`:
- 每4小时自动生成一次（原：每小时）
- Top 10币种（原：Top 30）
- 每4小时约20个信号（原：每小时60个）

---

## ✅ 3. 每分钟信号跟踪状态

**状态**: 已实现，完成度 75%

### 分析报告（来自 Task Agent）

**已实现功能** ✅:
- 每1分钟检查活跃信号
- 入场条件检查（±1%误差）
- 快速止盈（0.5%）
- 保本止损逻辑
- TP1/TP2 止盈检查
- 数据库状态实时更新
- 双存储机制（数据库 + JSON）

**存在问题** ⚠️:
1. **价格数据源单一**（仅 Gate.io，无备用）
2. **入场误差过大**（1%，建议 5m→0.3%, 15m→0.5%）
3. **无 API 限流保护**（可能被封禁）
4. **无重试机制**（价格获取失败直接返回 None）
5. **无实时通知**（止损/止盈无告警）
6. **频率控制不严格**（50秒防护窗口可能漏检）

### 改进建议（按优先级）

#### P0（高优先级）
- 添加多数据源支持（Binance, OKX 备用）
- 优化入场误差判断（5m: 0.3%, 15m: 0.5%）
- 添加 API 限流保护

#### P1（中优先级）
- 添加实时通知（Telegram/Discord）
- 实现重试机制
- 添加性能监控

---

## 📊 4. 信号评估功能测试

**需求**: 验证信号评估功能是否正常工作

### 测试计划

#### A. 单元测试

创建 `scripts/test_signal_evaluation.py`:

```python
#!/usr/bin/env python3
"""测试信号评估功能"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / 'src'))

from abu.auto_evaluator import AutoEvaluator
from abu.auto_backtest_integration import AutoBacktestIntegration

def test_评估单个信号():
    """测试评估单个信号"""
    evaluator = AutoEvaluator()
    
    test_signal = {
        'symbol': 'BTC',
        'timeframe': '5m',
        'signal_type': 'long',
        'entry_price': 100000,
        'stop_loss': 99000,
        'take_profit_1': 100500,
        'take_profit_2': 101000,
        'signal_time': '2026-01-15 12:00:00'
    }
    
    result = evaluator.evaluate_signal(test_signal)
    print(f"评估结果: {result}")
    assert 'score' in result, "评估结果应包含 score 字段"
    assert 0 <= result['score'] <= 100, "评分应在 0-100 之间"

def test_回测集成():
    """测试回测集成"""
    integration = AutoBacktestIntegration()
    
    signals = [
        {'symbol': 'BTC', 'timeframe': '5m', 'entry_price': 100000},
        {'symbol': 'ETH', 'timeframe': '15m', 'entry_price': 3000}
    ]
    
    results = integration.run_batch_backtest(signals)
    print(f"回测结果: {results}")
    assert 'total_signals' in results
    assert results['total_signals'] == 2

if __name__ == '__main__':
    print("=" * 60)
    print("信号评估功能测试")
    print("=" * 60)
    
    print("\n[测试1] 评估单个信号...")
    test_评估单个信号()
    print("✅ 通过")
    
    print("\n[测试2] 回测集成...")
    test_回测集成()
    print("✅ 通过")
    
    print("\n" + "=" * 60)
    print("所有测试通过！")
    print("=" * 60)
```

#### B. 集成测试

```bash
# 生成少量信号并评估
python scripts/auto_signal_generator.py --once --coins 3

# 检查评估统计
python scripts/show_auto_signal_status.py

# 查看评估详情
python src/check_signal_status.py
```

### 验收标准

- [ ] 评估分数在合理范围内（50-80分）
- [ ] 评估统计显示非0个信号被评估
- [ ] 回测结果包含胜率、盈亏比等指标
- [ ] 历史记录正确保存

---

## 🔧 5. 修复数据库并发锁问题

**方案**: 迁移到 PostgreSQL（已准备好方案）

**执行步骤**:
1. 按照 `docs/PostgreSQL_Migration_Plan.md` 执行迁移
2. 测试多脚本并发运行
3. 验证数据一致性

**验收标准**:
- [ ] 模式匹配 + 视觉匹配可同时运行
- [ ] 无数据库锁冲突错误
- [ ] 数据正确写入和读取

---

## 🔁 6. 添加 API 重试机制

### A. Gemini API 重试

修改 `src/abu/gemini_vision_analyzer.py`:

```python
import time
from typing import Callable, Any

class APIRetryHandler:
    """API 重试处理器"""
    
    def __init__(self, max_retries=3, base_delay=2):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    def call_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """带指数退避的重试"""
        for attempt in range(self.max_retries):
            try:
                result = func(*args, **kwargs)
                
                # 检查是否是可重试错误
                if isinstance(result, dict) and 'error' in result:
                    error_msg = result['error'].lower()
                    if any(x in error_msg for x in ['429', 'rate', 'quota', 'timeout']):
                        if attempt < self.max_retries - 1:
                            delay = self.base_delay * (2 ** attempt)  # 指数退避
                            print(f"[RETRY] API 限流或超时，{delay}秒后重试...")
                            time.sleep(delay)
                            continue
                
                return result
            except Exception as e:
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)
                    print(f"[RETRY] 请求失败，{delay}秒后重试: {e}")
                    time.sleep(delay)
                    continue
                return {"error": f"重试{self.max_retries}次后仍失败: {e}"}
        
        return {"error": "达到最大重试次数"}
```

### B. 价格 API 重试

修改 `src/abu/signal_result_feedback.py`:

```python
def get_current_price_with_retry(self, symbol: str, max_retries=3) -> Optional[float]:
    """带重试的价格获取"""
    for attempt in range(max_retries):
        price = self.get_current_price(symbol)
        if price and price > 0:
            return price
        
        if attempt < max_retries - 1:
            time.sleep(1)  # 重试前等待
    
    return None
```

---

## 🧹 7. 修复代码质量问题

### A. 消除重复代码 (`auto_signal_generator.py:498-602`)

```python
def _format_signal_markdown(self, signals: List[Dict], timeframe: str) -> str:
    """统一的信号格式化函数"""
    if not signals:
        return f"#### {timeframe} 信号\n\n无信号\n\n"
    
    md = f"#### {timeframe} 信号\n\n"
    
    for i, sig in enumerate(signals, 1):
        md += f"**信号 {i}**: {sig['type']}\n"
        md += f"- 入场: {sig['entry_price']:.2f}\n"
        md += f"- 止损: {sig['stop_loss']:.2f}\n"
        md += f"- 止盈1: {sig['take_profit_1']:.2f}\n"
        md += f"- 止盈2: {sig['take_profit_2']:.2f}\n"
        
        if 'brooks_probability' in sig:
            md += f"- Brooks概率: {sig['brooks_probability']}\n"
        if 'risk_reward' in sig:
            md += f"- 风险回报比: {sig['risk_reward']:.2f}\n"
        
        md += "\n"
    
    return md

# 使用
md_content += self._format_signal_markdown(signals_5m, "5分钟")
md_content += self._format_signal_markdown(signals_15m, "15分钟")
```

### B. 缓存模块引用 (`auto_signal_generator.py:384-390`)

```python
class AutoSignalGenerator:
    def __init__(self, ...):
        # 缓存模块引用
        self._test_module = None
        self._test_func = None
    
    def _get_cached_generator_func(self):
        """获取缓存的生成函数"""
        if self._test_func is None:
            import importlib.util
            scripts_dir = Path(__file__).parent
            spec = importlib.util.spec_from_file_location(
                "test_top10_pattern_only",
                scripts_dir / "test_top10_pattern_only.py"
            )
            self._test_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self._test_module)
            self._test_func = self._test_module.generate_top10_pattern_only_plan
        
        return self._test_func
```

---

## 💭 8. 关于 Gemini vs 模式匹配融合的建议

**您的问题**: 先通过3天运行数据回测，是否需要融合？

### 我的建议：**不建议立即融合，先分别评估**

#### 理由：

1. **数据驱动决策**
   - 3天数据可以提供初步胜率对比
   - 分别运行更容易归因（知道哪个系统表现好）
   - 融合前需要知道各自的优劣势

2. **系统特性不同**
   - **模式匹配**: 基于规则，可解释性强，响应快
   - **Gemini 视觉**: AI驱动，可能发现新模式，但成本高（$0.0088/张）

3. **融合的复杂性**
   - 需要设计融合策略（投票？加权？）
   - 信号冲突如何处理？
   - 可能引入新的bug

### 建议的评估维度：

| 指标 | 模式匹配 | Gemini 视觉 |
|------|---------|------------|
| 胜率 | ? | ? |
| 平均盈亏比 | ? | ? |
| 最大回撤 | ? | ? |
| 信号频率 | 高（每4小时20个） | 低（每4小时10个） |
| 响应速度 | 快（秒级） | 慢（需API调用） |
| 成本 | 低（本地计算） | 高（$0.088/次） |
| 可解释性 | 强 | 弱 |

### 融合时机：

**满足以下条件后再考虑融合**:
1. ✅ 两个系统都稳定运行超过1周
2. ✅ 都有正胜率（>55%）
3. ✅ 特征互补明显（如 Gemini 擅长某些模式）
4. ✅ 有明确的融合策略和冲突解决方案

### 可能的融合方案（未来）:

```python
class HybridSignalGenerator:
    """混合信号生成器"""
    
    def generate(self, symbol, timeframe):
        # 1. 两个系统都运行
        pattern_signals = self.pattern_matcher.match(symbol, timeframe)
        gemini_signals = self.gemini_matcher.match(symbol, timeframe)
        
        # 2. 融合策略
        if pattern_signals and gemini_signals:
            # 两者都有信号 → 高置信度
            return self._merge_signals(pattern_signals, gemini_signals, confidence='high')
        elif pattern_signals:
            # 仅模式匹配 → 中置信度
            return pattern_signals, confidence='medium'
        elif gemini_signals:
            # 仅 Gemini → 根据历史表现决定
            return gemini_signals, confidence='medium'
        else:
            return None
```

---

## 📅 执行时间表

### 立即执行（今天）
- [x] PostgreSQL 迁移方案准备
- [ ] 修改信号生成参数（4小时/10币种）
- [ ] 测试信号评估功能

### 明天
- [ ] 执行 PostgreSQL 迁移
- [ ] 添加 API 重试机制
- [ ] 修复代码质量问题

### 本周内
- [ ] 优化入场误差判断
- [ ] 添加多数据源支持
- [ ] 添加 API 限流保护

### 下周
- [ ] 收集3天回测数据
- [ ] 分析 Gemini vs 模式匹配表现
- [ ] 决定是否融合

---

## 🎯 总结

1. **PostgreSQL 迁移**: ✅ 方案已准备，预计1-2小时完成迁移
2. **信号生成调整**: 简单修改，5分钟完成
3. **信号跟踪**: 已实现核心功能，需要优化数据源和误差判断
4. **信号评估**: 需要测试验证
5. **Gemini 融合**: **建议先不融合**，用3天数据评估后再决定

**下一步**: 我可以立即开始修改信号生成逻辑和创建测试脚本，您希望我继续吗？
