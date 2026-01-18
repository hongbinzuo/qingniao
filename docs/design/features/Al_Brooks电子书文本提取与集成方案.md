# Al Brooks 电子书文本提取与ABU系统集成方案

## 📋 概述

将Al Brooks的三本英文电子书（PDF格式）的文本内容提取、分析和集成到ABU系统中，作为模式识别和交易信号生成的知识补充。

**核心原则**：
- **主要关注文字内容**：电子书中的图片仅作为参考，不作为主要模式识别源
- **不使用Gemini**：文本提取和分析使用本地NLP技术，避免API成本
- **与现有系统无缝集成**：补充`pattern_library`表，增强模式匹配能力

---

## 🎯 目标与价值

### 1. 知识补充
- **理论支撑**：电子书提供Al Brooks价格行为理论的详细文字说明
- **模式解释**：文字描述帮助理解模式的形成原因、适用场景、交易逻辑
- **参数指导**：从文字中提取交易参数设置规则（止损、止盈、入场时机等）

### 2. 系统增强
- **模式库扩展**：将文字描述的模式与现有图片模式库关联
- **匹配精度提升**：文字描述提供更多上下文，提高模式匹配准确性
- **信号质量改善**：结合文字理论，优化交易信号的生成逻辑

### 3. 成本控制
- **零API成本**：文本提取和分析完全本地化
- **高效处理**：PDF文本提取速度快，无需等待API响应

---

## 📚 电子书处理流程

### 阶段1: PDF文本提取

#### 1.1 技术选型
- **PyMuPDF (fitz)**：已有依赖，支持PDF文本提取
- **pdfplumber**：备选方案，对表格和复杂布局支持更好
- **OCR（可选）**：如果PDF是扫描版，使用Tesseract OCR

#### 1.2 提取策略
```python
# 提取层次结构
{
    "book_title": "Al Brooks Trading Course - Volume 1",
    "chapters": [
        {
            "chapter_number": 1,
            "chapter_title": "Introduction to Price Action",
            "sections": [
                {
                    "section_title": "Understanding Trends",
                    "paragraphs": [
                        "Price action trading is based on...",
                        "Trends can be identified by..."
                    ],
                    "key_concepts": ["trend", "support", "resistance"],
                    "patterns_mentioned": ["uptrend", "downtrend"],
                    "trading_rules": [
                        {
                            "rule": "Enter long on pullback to support",
                            "stop_loss": "below recent low",
                            "take_profit": "previous high"
                        }
                    ]
                }
            ],
            "images": [
                {
                    "page_number": 15,
                    "image_path": "book1_page15_fig1.png",
                    "caption": "Example of uptrend with pullback",
                    "related_text": "As shown in Figure 1..."
                }
            ]
        }
    ]
}
```

#### 1.3 实现脚本
**文件**: `scripts/abu_extract_ebook_text.py`

**功能**：
- 批量处理PDF文件
- 提取文本、章节结构、图表说明
- 识别关键概念、模式名称、交易规则
- 输出结构化JSON

---

### 阶段2: 文本分析与知识提取

#### 2.1 NLP分析任务

**A. 模式识别与提取**
- 识别模式名称（Wedge, Triangle, Head and Shoulders等）
- 提取模式描述和特征
- 识别模式组合（"Wedge followed by Triangle"）

**B. 交易规则提取**
- 入场规则（Entry rules）
- 止损规则（Stop loss rules）
- 止盈规则（Take profit rules）
- 风险管理规则（Risk management）

**C. 概念与术语提取**
- 价格行为术语（Price action terms）
- 市场结构概念（Market structure concepts）
- 交易心理要点（Trading psychology）

#### 2.2 技术实现

**使用本地NLP库**：
- **spaCy**：命名实体识别、词性标注、依存分析
- **NLTK**：文本预处理、关键词提取
- **正则表达式**：模式匹配（模式名称、价格、百分比等）
- **规则引擎**：基于规则的交易参数提取

**实现脚本**: `scripts/abu_analyze_ebook_text.py`

---

### 阶段3: 知识库构建

#### 3.1 数据库设计

**新增表**: `ebook_knowledge_base`

```sql
CREATE TABLE IF NOT EXISTS ebook_knowledge_base (
    id INTEGER PRIMARY KEY,
    book_title TEXT NOT NULL,
    chapter_number INTEGER,
    chapter_title TEXT,
    section_title TEXT,
    content_type TEXT,  -- 'pattern_description', 'trading_rule', 'concept', 'example'
    content_text TEXT NOT NULL,
    extracted_patterns TEXT,  -- JSON数组: ["Wedge", "Triangle"]
    trading_rules_json TEXT,  -- JSON: {entry: "...", stop_loss: "...", take_profit: "..."}
    key_concepts TEXT,  -- JSON数组: ["support", "resistance", "breakout"]
    related_image_path TEXT,  -- 关联的图片路径（如果有）
    page_number INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_ebook_patterns ON ebook_knowledge_base(extracted_patterns);
CREATE INDEX IF NOT EXISTS idx_ebook_content_type ON ebook_knowledge_base(content_type);
```

**扩展`pattern_library`表**：

```sql
-- 添加字段关联电子书知识
ALTER TABLE pattern_library ADD COLUMN IF NOT EXISTS ebook_references TEXT;  
-- JSON数组: [{"book": "Volume 1", "chapter": 3, "section": "Wedge Patterns", "page": 45}]

ALTER TABLE pattern_library ADD COLUMN IF NOT EXISTS text_description TEXT;
-- 从电子书提取的文字描述
```

#### 3.2 知识关联策略

**模式匹配算法**：
1. **名称匹配**：模式名称直接匹配（"Wedge" → "Wedge"）
2. **特征匹配**：基于模式特征描述匹配
3. **上下文匹配**：基于交易场景和上下文匹配

**实现脚本**: `scripts/abu_link_ebook_to_patterns.py`

---

### 阶段4: 与ABU系统集成

#### 4.1 模式匹配增强

**修改**: `src/abu/gemini_pattern_matcher.py` 或 `src/abu/gemini_pattern_matcher_enhanced.py`

**增强点**：
```python
class EnhancedGeminiPatternMatcher:
    def __init__(self):
        self.pattern_library: List[Dict] = []
        self.ebook_knowledge: List[Dict] = []  # 新增：电子书知识库
        self._load_pattern_library()
        self._load_ebook_knowledge()  # 新增方法
    
    def _load_ebook_knowledge(self):
        """加载电子书知识库"""
        # 从ebook_knowledge_base表加载
        # 构建模式名称到知识的索引
    
    def match_pattern(self, realtime_features: Dict) -> List[Dict]:
        """增强的模式匹配"""
        # 1. 传统Gemini模式匹配
        gemini_matches = self._match_gemini_patterns(realtime_features)
        
        # 2. 电子书知识验证（新增）
        for match in gemini_matches:
            pattern_name = match['pattern_name']
            # 查找电子书中关于该模式的描述
            ebook_info = self._find_ebook_knowledge(pattern_name)
            if ebook_info:
                # 使用电子书知识验证和增强匹配
                match['ebook_validation'] = self._validate_with_ebook(match, ebook_info)
                match['ebook_rules'] = ebook_info.get('trading_rules', {})
        
        return gemini_matches
```

#### 4.2 交易信号生成增强

**修改**: `scripts/abu_gemini_signal_scanner_enhanced.py`

**增强点**：
- 从电子书知识库提取交易规则
- 结合Gemini识别的模式和电子书规则生成信号
- 使用电子书中的参数设置指导（止损、止盈距离等）

#### 4.3 知识检索接口

**新增**: `src/abu/ebook_knowledge_retriever.py`

**功能**：
- 根据模式名称检索相关电子书内容
- 根据交易场景检索相关规则
- 提供知识摘要和关键点提取

---

## 🔧 实现细节

### 1. PDF文本提取脚本

**文件**: `scripts/abu_extract_ebook_text.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提取Al Brooks电子书文本内容
"""
import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Optional

try:
    import fitz  # PyMuPDF
except ImportError:
    print("请安装PyMuPDF: pip install pymupdf")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / 'data' / 'abu' / 'ebooks' / 'extracted'

def extract_text_from_pdf(pdf_path: Path) -> Dict:
    """从PDF提取文本和结构"""
    doc = fitz.open(str(pdf_path))
    
    book_data = {
        "book_title": pdf_path.stem,
        "total_pages": len(doc),
        "chapters": [],
        "all_text": []
    }
    
    current_chapter = None
    current_section = None
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        
        # 识别章节标题（通常是大字体、居中、特定格式）
        chapter_match = re.search(r'^Chapter\s+(\d+)[:.\s]+(.+)$', text, re.MULTILINE | re.IGNORECASE)
        if chapter_match:
            # 保存上一章
            if current_chapter:
                book_data["chapters"].append(current_chapter)
            
            # 开始新章
            current_chapter = {
                "chapter_number": int(chapter_match.group(1)),
                "chapter_title": chapter_match.group(2).strip(),
                "sections": [],
                "page_range": [page_num + 1]
            }
        
        # 识别节标题
        section_match = re.search(r'^(\d+\.\d+)\s+(.+)$', text, re.MULTILINE)
        if section_match:
            if current_chapter:
                if current_section:
                    current_chapter["sections"].append(current_section)
                
                current_section = {
                    "section_number": section_match.group(1),
                    "section_title": section_match.group(2).strip(),
                    "paragraphs": [],
                    "page_number": page_num + 1
                }
        
        # 提取段落
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if current_section:
            current_section["paragraphs"].extend(paragraphs)
        elif current_chapter:
            # 如果没有节，直接添加到章节
            if "paragraphs" not in current_chapter:
                current_chapter["paragraphs"] = []
            current_chapter["paragraphs"].extend(paragraphs)
        
        book_data["all_text"].append({
            "page": page_num + 1,
            "text": text
        })
    
    # 保存最后一章
    if current_chapter:
        if current_section:
            current_chapter["sections"].append(current_section)
        book_data["chapters"].append(current_chapter)
    
    doc.close()
    return book_data

def extract_images_with_captions(pdf_path: Path) -> List[Dict]:
    """提取PDF中的图片和说明文字"""
    doc = fitz.open(str(pdf_path))
    images = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        image_list = page.get_images()
        
        for img_index, img in enumerate(image_list):
            # 提取图片
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            
            # 保存图片
            image_dir = OUTPUT_DIR / "images" / pdf_path.stem
            image_dir.mkdir(parents=True, exist_ok=True)
            image_path = image_dir / f"page_{page_num+1}_img_{img_index+1}.png"
            with open(image_path, "wb") as img_file:
                img_file.write(image_bytes)
            
            # 尝试提取图片说明（通常在图片下方或上方）
            text = page.get_text()
            # 查找"Figure", "Chart", "Example"等关键词附近的文字
            
            images.append({
                "page_number": page_num + 1,
                "image_index": img_index + 1,
                "image_path": str(image_path.relative_to(ROOT)),
                "caption": ""  # 需要进一步处理
            })
    
    doc.close()
    return images

def main():
    """主函数"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 查找PDF文件
    ebook_dir = ROOT / 'data' / 'abu' / 'ebooks'
    pdf_files = list(ebook_dir.glob('*.pdf'))
    
    if not pdf_files:
        print(f"❌ 未找到PDF文件，请将电子书放在: {ebook_dir}")
        return
    
    print(f"找到 {len(pdf_files)} 个PDF文件")
    
    for pdf_path in pdf_files:
        print(f"\n处理: {pdf_path.name}")
        
        # 提取文本
        book_data = extract_text_from_pdf(pdf_path)
        
        # 提取图片
        images = extract_images_with_captions(pdf_path)
        book_data["images"] = images
        
        # 保存结果
        output_file = OUTPUT_DIR / f"{pdf_path.stem}_extracted.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(book_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 已保存: {output_file}")
        print(f"   章节数: {len(book_data['chapters'])}")
        print(f"   总页数: {book_data['total_pages']}")
        print(f"   图片数: {len(images)}")

if __name__ == '__main__':
    main()
```

### 2. 文本分析与知识提取脚本

**文件**: `scripts/abu_analyze_ebook_text.py`

**核心功能**：
- 使用spaCy进行命名实体识别
- 提取模式名称、交易规则、关键概念
- 结构化输出到数据库

### 3. 知识关联脚本

**文件**: `scripts/abu_link_ebook_to_patterns.py`

**功能**：
- 将电子书中的模式描述与`pattern_library`表中的模式关联
- 更新`pattern_library.ebook_references`和`pattern_library.text_description`字段

---

## 📊 数据流图

```
Al Brooks电子书 (PDF)
    ↓
[PDF文本提取]
    ├─ 章节结构
    ├─ 段落文本
    └─ 图片（仅参考）
    ↓
[文本分析]
    ├─ 模式名称提取
    ├─ 交易规则提取
    ├─ 关键概念提取
    └─ 结构化知识
    ↓
[知识库构建]
    └─ ebook_knowledge_base表
    ↓
[知识关联]
    └─ 与pattern_library关联
    ↓
[系统集成]
    ├─ 模式匹配增强
    ├─ 信号生成增强
    └─ 知识检索接口
    ↓
[ABU交易信号系统]
```

---

## 🎯 使用场景

### 场景1: 模式匹配时检索理论支撑
```python
# 当匹配到"Wedge"模式时
pattern_match = matcher.match_pattern(realtime_features)
if pattern_match['pattern_name'] == 'Wedge':
    # 检索电子书中关于Wedge的描述
    ebook_info = ebook_retriever.get_pattern_info('Wedge')
    # 使用电子书理论验证匹配
    validation = validate_match_with_ebook(pattern_match, ebook_info)
```

### 场景2: 生成交易信号时应用规则
```python
# 生成信号时
signal = generate_signal(pattern_match)
# 从电子书获取该模式的交易规则
rules = ebook_retriever.get_trading_rules('Wedge')
# 应用规则调整信号参数
signal = apply_ebook_rules(signal, rules)
```

### 场景3: 知识查询接口
```python
# 用户查询某个模式的理论
info = ebook_retriever.get_pattern_description('Triangle')
# 返回：模式定义、形成原因、交易逻辑、参数设置等
```

---

## 📝 实施步骤

### 步骤1: 准备环境
```bash
# 安装依赖
pip install pymupdf spacy nltk

# 下载spaCy英文模型
python -m spacy download en_core_web_sm
```

### 步骤2: 提取文本
```bash
# 将电子书PDF放在 data/abu/ebooks/ 目录
python scripts/abu_extract_ebook_text.py
```

### 步骤3: 分析文本
```bash
python scripts/abu_analyze_ebook_text.py
```

### 步骤4: 关联知识
```bash
python scripts/abu_link_ebook_to_patterns.py
```

### 步骤5: 集成测试
```bash
# 测试知识检索
python scripts/test_ebook_integration.py

# 测试模式匹配增强
python scripts/test_enhanced_pattern_matching.py
```

---

## 🔍 技术细节

### 1. 模式名称识别

**策略**：
- 使用预定义的模式名称列表（从现有`pattern_library`提取）
- 使用正则表达式匹配（"Wedge", "Triangle", "Head and Shoulders"等）
- 使用NLP实体识别（识别技术分析术语）

### 2. 交易规则提取

**规则模板**：
- Entry: "Enter long when...", "Buy at...", "Go long if..."
- Stop Loss: "Stop loss below...", "Place stop at..."
- Take Profit: "Target...", "Take profit at...", "Exit at..."

### 3. 知识关联算法

**相似度计算**：
- 模式名称完全匹配：相似度 = 1.0
- 模式名称部分匹配：相似度 = 0.7
- 特征描述相似：使用TF-IDF + 余弦相似度

---

## ✅ 优势

1. **零API成本**：完全本地处理
2. **理论支撑**：电子书提供详细的理论说明
3. **可扩展性**：易于添加更多电子书
4. **无缝集成**：与现有系统完美结合
5. **知识检索**：支持快速查询和学习

---

## 📌 注意事项

1. **PDF质量**：确保PDF是文本版而非扫描版
2. **语言处理**：针对英文文本优化，如需支持中文需调整
3. **知识更新**：电子书内容相对固定，但可以定期更新关联关系
4. **性能考虑**：大量文本处理可能需要优化，考虑分批处理

---

## 🚀 未来扩展

1. **视频字幕提取**：如果Al Brooks有视频课程，可以提取字幕文本
2. **多语言支持**：支持中文翻译版电子书
3. **知识图谱**：构建模式、规则、概念之间的知识图谱
4. **智能问答**：基于电子书内容构建问答系统



