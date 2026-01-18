# ABU模式类型分类说明

## 📊 当前问题

**所有1004个模式都是"other"类型**，原因：

1. **没有Gemini标注**: 模式入库时没有使用Gemini API进行标注
2. **模式名称不包含类型信息**: 名称都是 `"Pattern from page X"`，无法识别类型
3. **推断逻辑无法匹配**: 代码尝试从名称中推断类型，但找不到关键词

## 🔍 模式类型推断逻辑

当前代码 (`abu_ingest_patterns.py`) 的推断逻辑：

```python
# 如果没有从 Gemini 获取 pattern_type，根据 pattern_name 推断
if not pattern_type:
    pattern_lower = pattern_name.lower()
    if any(x in pattern_lower for x in ['engulfing', 'pin', 'inside', 'key level']):
        pattern_type = 'price_action'  # 价格行为模式
    elif any(x in pattern_lower for x in ['head', 'shoulder', 'triangle', 'flag', 'wedge']):
        pattern_type = 'chart_pattern'  # 图表形态
    else:
        pattern_type = 'other'  # 其他（默认）
```

## 💡 解决方案

### 方案1: 使用Gemini API标注（推荐）

使用Gemini Vision API分析图片，自动识别模式类型：

```bash
# 运行Gemini标注
py -3 scripts\abu_gemini_annotate.py --api-key YOUR_KEY --images-dir data\abu\images

# 重新入库（带Gemini标注）
py -3 scripts\abu_ingest_patterns.py --from-jsonl data\abu\raw_pages.jsonl --from-gemini outputs\abu_gemini_annotations.jsonl
```

**优点**: 
- 自动识别模式类型、方向、时间框架
- 准确度高
- 可以提取更多特征

**缺点**: 
- 需要Gemini API Key
- 需要API费用

### 方案2: 从上下文文本提取模式类型

改进推断逻辑，从PDF页面的上下文文本中提取模式类型：

```python
def infer_pattern_type_from_context(context_text: str, pattern_name: str) -> str:
    """从上下文文本推断模式类型"""
    text_lower = context_text.lower()
    
    # 价格行为模式关键词
    price_action_keywords = {
        'inside bar': 'InsideBar',
        'engulfing': 'Engulfing',
        'pin bar': 'PinBar',
        'key level': 'KeyLevel',
        'support': 'KeyLevel',
        'resistance': 'KeyLevel',
    }
    
    # 图表形态关键词
    chart_pattern_keywords = {
        'head and shoulder': 'HeadShoulder',
        'triangle': 'Triangle',
        'flag': 'Flag',
        'wedge': 'Wedge',
        'double top': 'DoubleTop',
        'double bottom': 'DoubleBottom',
    }
    
    # 检查关键词
    for keyword, pattern_type in price_action_keywords.items():
        if keyword in text_lower:
            return 'price_action'
    
    for keyword, pattern_type in chart_pattern_keywords.items():
        if keyword in text_lower:
            return 'chart_pattern'
    
    return 'other'
```

### 方案3: 手动分类（小规模）

如果模式数量不多，可以手动分类：

```sql
-- 更新特定模式的类型
UPDATE pattern_library 
SET pattern_type = 'price_action' 
WHERE id IN (1, 2, 3, ...);

UPDATE pattern_library 
SET pattern_type = 'chart_pattern' 
WHERE id IN (10, 11, 12, ...);
```

### 方案4: 基于模式匹配结果自动分类

根据模式匹配的结果，自动推断类型：

- 如果匹配到 `InsideBar` 检测器 → `price_action`
- 如果匹配到 `Engulfing` 检测器 → `price_action`
- 如果匹配到 `PinBar` 检测器 → `price_action`
- 如果匹配到 `KeyLevel` 检测器 → `price_action`
- 其他 → `chart_pattern` 或 `other`

## 🎯 推荐做法

1. **短期**: 使用方案2（从上下文文本提取），快速改善分类
2. **长期**: 使用方案1（Gemini标注），获得最准确的分类

## 📝 模式类型说明

### price_action（价格行为模式）
- **InsideBar**: 内包线
- **Engulfing**: 吞没
- **PinBar**: Pin Bar
- **KeyLevel**: 关键位（支撑/阻力）

### chart_pattern（图表形态）
- **HeadShoulder**: 头肩形态
- **Triangle**: 三角形
- **Flag**: 旗形
- **Wedge**: 楔形
- **DoubleTop/Bottom**: 双顶/双底

### other（其他）
- 无法明确分类的模式
- 需要进一步分析

## 🔧 实施步骤

### 步骤1: 改进推断逻辑

修改 `scripts/abu_ingest_patterns.py`，添加从上下文文本提取模式类型的逻辑。

### 步骤2: 重新分类现有模式

运行更新脚本，重新分类所有模式：

```python
# 重新分类所有模式
for pattern in patterns:
    new_type = infer_pattern_type_from_context(pattern.context_text, pattern.pattern_name)
    update_pattern_type(pattern.id, new_type)
```

### 步骤3: 验证分类结果

检查分类结果：

```bash
py -3 scripts\abu_check_patterns.py
```

## ⚠️ 注意事项

1. **模式类型影响权重**: 不同类型的模式在评分时权重不同
2. **模式匹配**: 模式类型用于匹配算法，影响匹配准确度
3. **统计分析**: 需要正确的类型才能进行统计分析

---

**下一步**: 我可以帮您实施方案2（从上下文文本提取），快速改善模式分类！

