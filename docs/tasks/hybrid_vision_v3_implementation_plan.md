# 混合视觉匹配系统 v3.0 实施计划

**创建时间**: 2025-01-XX  
**状态**: 待执行  
**版本**: v3.0

---

## 📋 实施步骤

### ✅ 已完成

1. **代码实现**
   - [x] `src/abu/chart_renderer.py` - K线图表渲染器
   - [x] `src/abu/ai_vision_matcher.py` - AI视觉匹配器
   - [x] `src/abu/hybrid_vision_pattern_matcher.py` - 混合匹配器（v3.0）
   - [x] `scripts/hybrid_vision_scanner.py` - 扫描脚本

2. **功能特性**
   - [x] 支持全部候选视觉匹配（v3.0默认）
   - [x] 支持Gemini 3.0模型（代码中已准备）
   - [x] 缓存机制
   - [x] 错误处理

---

### ⏳ 待执行（按顺序）

#### 步骤1: 等待图片识别完成
- [ ] **等待300张图片识别完成**
  - 当前状态：识别中...
  - 依赖：Cursor AI识别流程
  - 预计：等待中

#### 步骤2: 代码Review
- [ ] **整体代码Review**
  - 检查代码质量和规范
  - 优化性能和错误处理
  - 确保与现有系统集成良好
  - 验证依赖和配置

#### 步骤3: 机器学习训练
- [ ] **执行机器学习训练**
  - 使用识别完成的图片数据
  - 训练模式匹配模型
  - 优化匹配精度

#### 步骤4: 系统运行
- [ ] **运行混合视觉匹配系统**
  - 配置API密钥
  - 测试运行
  - 生产部署

---

## 📊 预期效果

### 功能
- **全部候选视觉匹配**：对所有算法筛选的候选进行AI视觉验证
- **高精度匹配**：结合算法和AI视觉，提供更准确的匹配结果
- **成本可控**：通过缓存和优化，控制API调用成本

### 成本估算（v3.0 - 全部候选）
- **10个币种，每小时扫描**
- **每月API调用**：约144,000次
- **预计成本**：$28.8/月

---

## 🔧 配置说明

### 默认配置（v3.0）
```python
use_all_candidates=True  # 全部候选视觉匹配
vision_model="google/gemini-2.5-flash-image"  # 或 gemini-3-flash-preview
max_candidates=20  # 算法筛选候选数
```

### 运行命令
```bash
# 单次扫描（测试）
python scripts/hybrid_vision_scanner.py --once --symbols 10

# 循环扫描（每小时）
python scripts/hybrid_vision_scanner.py --interval 3600 --symbols 10
```

---

## 📝 注意事项

1. **API密钥**：需要配置 `OPENROUTER_API_KEY` 环境变量
2. **依赖安装**：需要安装 `matplotlib` 和 `requests`
3. **模型选择**：Gemini 3.0模型可能还未在OpenRouter上可用，需验证
4. **成本控制**：v3.0使用全部候选，成本较高，适合充分试验阶段

---

## 📌 待办事项追踪

- [ ] 步骤1：等待300张图片识别完成
- [ ] 步骤2：代码Review
- [ ] 步骤3：机器学习训练
- [ ] 步骤4：系统运行

**当前状态**: 等待图片识别完成

