# Brooks PA概率分类集成方案

**日期**: 2026-01-14  
**目标**: 将Brooks的PA概率分类知识集成到ABU系统，提升信号质量评估和置信度计算

---

## 一、集成目标

### 1.1 核心目标
- **概率知识提取**: 从PDF中提取概率分类信息（如：Bull Flag 70%概率，Bear Flag 60%概率）
- **模式库增强**: 将概率信息关联到现有模式库
- **置信度优化**: 使用概率信息优化信号置信度计算
- **信号过滤**: 基于概率阈值过滤低概率信号

### 1.2 预期效果
- 信号置信度更准确（结合模式匹配和概率分类）
- 自动过滤低概率信号（如 < 50%）
- 高概率信号优先展示（如 > 70%）
- 回测表现提升（更准确的信号质量评估）

---

## 二、技术方案

### 2.1 数据提取层

#### 2.1.1 PDF文本提取
```python
# 使用pdfplumber提取文本
- 提取每页文本内容
- 识别概率关键词（概率、probability、%等）
- 识别模式名称（Bull Flag、Bear Flag等）
- 提取概率数值（60%、70%、80%等）
```

#### 2.1.2 概率规则解析
```python
# 解析规则格式
{
    "page": 12,
    "pattern_name": "Bull Flag",
    "probability": 70,  # 百分比
    "context": "上升趋势中的Bull Flag有70%概率继续上涨",
    "conditions": ["上升趋势", "突破阻力"],
    "source": "Brooks PA概率分类"
}
```

### 2.2 数据存储层

#### 2.2.1 JSON存储
```json
// data/brooks_probability_rules.json
{
    "version": "1.0",
    "extracted_date": "2026-01-14",
    "rules": [
        {
            "pattern_name": "Bull Flag",
            "probability": 70,
            "direction": "long",
            "conditions": ["上升趋势", "突破阻力"],
            "page": 12,
            "text_snippet": "..."
        }
    ]
}
```

#### 2.2.2 数据库集成（可选）
```sql
-- 添加到ebook_knowledge_base表
ALTER TABLE ebook_knowledge_base 
ADD COLUMN probability_score INTEGER;  -- 概率分数（0-100）

-- 或创建新表
CREATE TABLE brooks_probability_rules (
    id INTEGER PRIMARY KEY,
    pattern_name TEXT,
    probability INTEGER,  -- 0-100
    direction TEXT,  -- 'long', 'short', 'neutral'
    conditions TEXT,  -- JSON数组
    page_number INTEGER,
    source TEXT
);
```

### 2.3 模式库集成层

#### 2.3.1 概率信息关联
```python
# 在UnifiedPattern中添加概率字段
@dataclass
class UnifiedPattern:
    pattern_id: str
    pattern_name: str
    pattern_type: str
    source: str
    probability_score: Optional[int] = None  # 新增：概率分数
    probability_source: Optional[str] = None  # 新增：概率来源
    # ... 其他字段
```

#### 2.3.2 模式匹配增强
```python
# 在EnhancedHybridMatcher中集成概率
class EnhancedHybridMatcher:
    def __init__(self):
        self.probability_rules: Dict[str, int] = {}  # {pattern_name: probability}
        self._load_probability_rules()
    
    def _load_probability_rules(self):
        # 从JSON加载概率规则
        # 建立pattern_name -> probability映射
        pass
    
    def match_patterns(self, features):
        # 原有匹配逻辑
        matches = self._find_matches(features)
        
        # 增强：添加概率信息
        for match in matches:
            if match.pattern_name in self.probability_rules:
                match.probability_score = self.probability_rules[match.pattern_name]
                # 调整置信度：结合匹配度和概率
                match.enhanced_confidence = (
                    match.combined_confidence * 0.7 + 
                    (match.probability_score / 100) * 0.3
                )
        
        return matches
```

### 2.4 信号生成层

#### 2.4.1 置信度计算优化
```python
# 在generate_coin_plan中
def calculate_confidence(match, probability_score):
    """
    计算综合置信度
    
    Args:
        match: 模式匹配结果
        probability_score: 概率分数（0-100）
    
    Returns:
        综合置信度（0-1）
    """
    # 算法匹配置信度（0-1）
    algorithm_confidence = match.combined_confidence
    
    # 概率分数（0-1）
    probability_normalized = probability_score / 100.0
    
    # 加权组合
    # 算法匹配权重70%，概率权重30%
    combined = (
        algorithm_confidence * 0.7 + 
        probability_normalized * 0.3
    )
    
    return combined
```

#### 2.4.2 信号过滤
```python
# 在信号生成时过滤低概率信号
MIN_PROBABILITY_THRESHOLD = 50  # 最低概率阈值

if signal.get('probability_score', 100) < MIN_PROBABILITY_THRESHOLD:
    # 标记为低概率信号
    signal['is_low_probability'] = True
    signal['validation_warnings'].append(
        f"低概率信号：概率仅{signal['probability_score']}%，建议谨慎"
    )
```

### 2.5 回测评估层

#### 2.5.1 概率分组分析
```python
# 在PerformanceAnalyzer中
def analyze_by_probability(self):
    """
    按概率分组分析表现
    """
    groups = {
        'high': [],  # >= 70%
        'medium': [],  # 50-69%
        'low': []  # < 50%
    }
    
    for signal in self.signals:
        prob = signal.get('probability_score', 0)
        if prob >= 70:
            groups['high'].append(signal)
        elif prob >= 50:
            groups['medium'].append(signal)
        else:
            groups['low'].append(signal)
    
    return {
        'high_probability': self._calculate_stats(groups['high']),
        'medium_probability': self._calculate_stats(groups['medium']),
        'low_probability': self._calculate_stats(groups['low'])
    }
```

---

## 三、实施步骤

### 步骤1: PDF提取（已完成）
- ✅ 创建`BrooksProbabilityExtractor`
- ✅ 实现PDF文本提取
- ✅ 实现概率规则解析

### 步骤2: 数据提取和验证
```bash
# 运行提取脚本
python scripts/integrate_brooks_probability.py

# 检查提取结果
cat data/brooks_probability_rules.json
```

### 步骤3: 模式库集成
- 修改`UnifiedPattern`添加概率字段
- 修改`UnifiedPatternLibrary`加载概率规则
- 建立pattern_name -> probability映射

### 步骤4: 匹配器增强
- 修改`EnhancedHybridMatcher`集成概率
- 优化置信度计算（结合匹配度和概率）
- 添加概率过滤逻辑

### 步骤5: 信号生成优化
- 修改`generate_coin_plan`使用概率信息
- 添加概率阈值过滤
- 在报告中显示概率信息

### 步骤6: 回测评估增强
- 修改`PerformanceAnalyzer`按概率分组
- 生成概率分析报告
- 验证高概率信号表现更好

### 步骤7: 测试和验证
- 运行完整测试
- 对比集成前后的信号质量
- 验证回测表现提升

---

## 四、数据流

```
PDF文件
  ↓
BrooksProbabilityExtractor
  ↓
JSON文件 (brooks_probability_rules.json)
  ↓
UnifiedPatternLibrary (加载概率规则)
  ↓
EnhancedHybridMatcher (匹配时应用概率)
  ↓
信号生成 (置信度计算 + 概率过滤)
  ↓
回测评估 (按概率分组分析)
```

---

## 五、配置参数

```python
# config/brooks_probability_config.json
{
    "min_probability_threshold": 50,  # 最低概率阈值
    "high_probability_threshold": 70,  # 高概率阈值
    "probability_weight": 0.3,  # 概率在置信度计算中的权重
    "algorithm_weight": 0.7,  # 算法匹配在置信度计算中的权重
    "enable_probability_filter": true  # 是否启用概率过滤
}
```

---

## 六、预期改进

### 6.1 信号质量
- **置信度更准确**: 结合模式匹配和概率分类
- **低概率信号过滤**: 自动过滤 < 50% 概率的信号
- **高概率信号优先**: 优先展示 > 70% 概率的信号

### 6.2 回测表现
- **高概率信号胜率更高**: 预期高概率信号（>=70%）胜率 > 60%
- **低概率信号胜率更低**: 预期低概率信号（<50%）胜率 < 40%
- **整体表现提升**: 通过过滤低概率信号，整体胜率提升

### 6.3 用户体验
- **信号更可靠**: 用户看到的是经过概率验证的信号
- **决策更清晰**: 概率信息帮助用户做出更好的交易决策
- **报告更详细**: 显示概率信息，让用户了解信号的可信度

---

## 七、风险与应对

### 7.1 风险
- **PDF提取不准确**: 可能提取到错误的概率信息
- **模式名称不匹配**: PDF中的模式名称与系统模式名称不一致
- **概率过时**: Brooks的概率分类可能不适用于当前市场

### 7.2 应对
- **人工审核**: 提取后人工审核概率规则
- **模式名称映射**: 建立模式名称映射表
- **动态调整**: 根据回测结果动态调整概率权重

---

## 八、后续优化

### 8.1 机器学习优化
- 使用历史回测数据训练概率模型
- 动态调整概率权重
- 基于实际表现优化概率阈值

### 8.2 多源概率融合
- 结合多个数据源的概率信息
- 加权平均计算综合概率
- 考虑市场环境对概率的影响

---

**状态**: 📋 方案已制定，准备实施  
**下一步**: 运行集成脚本提取概率分类知识
