# 千叶交易系统 - 使用指南

## 📋 概述

千叶交易系统是从千叶交易员的公开YouTube视频和行情分析图片中提取交易规则，并建立完整的交易系统。

---

## 🚀 快速开始

### 1. 分析YouTube视频

```bash
# 提供YouTube视频链接
python src/chiba_trading_system/video_analyzer.py --url <youtube_url>

# 或使用本地视频文件
python src/chiba_trading_system/video_analyzer.py --video <video_path>
```

**功能**:
- 自动下载YouTube视频
- 自动转录视频为文字
- 自动提取交易规则
- 保存分析结果

**输出**:
- 视频文件: `data/chiba_videos/`
- 转录文本: `data/chiba_videos/transcripts/`
- 分析结果: `data/chiba_videos/analysis_result.json`

### 2. 分析行情图片

```bash
# 提供行情分析图片
python src/chiba_trading_system/image_analyzer.py --image <image_path>
```

**功能**:
- OCR提取图片文字
- 识别图表元素（K线、趋势线等）
- 提取交易标注（入场、止损、止盈）
- 保存分析结果

**输出**:
- 分析结果: `data/chiba_images/analysis/`

---

## 📦 依赖安装

### 视频分析依赖

```bash
# YouTube下载
pip install yt-dlp

# 视频转录
pip install openai-whisper
```

### 图片分析依赖

```bash
# OCR
pip install pytesseract pillow

# 图像处理
pip install opencv-python

# Tesseract OCR (需要单独安装)
# Windows: https://github.com/UB-Mannheim/tesseract/wiki
# macOS: brew install tesseract
# Linux: sudo apt-get install tesseract-ocr
```

---

## 📝 使用示例

### 示例1: 分析YouTube视频

```bash
python src/chiba_trading_system/video_analyzer.py --url "https://www.youtube.com/watch?v=xxxxx"
```

### 示例2: 分析本地视频

```bash
python src/chiba_trading_system/video_analyzer.py --video "data/chiba_videos/千叶交易教学.mp4"
```

### 示例3: 分析行情图片

```bash
python src/chiba_trading_system/image_analyzer.py --image "data/chiba_images/行情分析1.png"
```

---

## 🔧 系统架构

### 模块说明

1. **video_analyzer.py** - 视频分析模块
   - 下载YouTube视频
   - 转录视频为文字
   - 提取交易规则

2. **image_analyzer.py** - 图片分析模块
   - OCR提取文字
   - 识别图表元素
   - 提取交易标注

3. **rule_extractor.py** - 规则提取模块（待实现）
   - 结构化交易规则
   - 验证规则完整性
   - 生成规则配置

4. **chiba_rules.py** - 规则引擎（待实现）
   - 执行交易规则
   - 生成交易信号
   - 评估信号质量

---

## 📊 数据流程

```
YouTube视频 / 行情图片
    ↓
视频分析 / 图片分析
    ↓
提取交易规则
    ↓
规则结构化
    ↓
规则编码
    ↓
集成到交易系统
    ↓
生成交易信号
```

---

## 🎯 下一步

1. **提供视频链接**: 请提供千叶交易员的YouTube视频链接
2. **提供分析图片**: 请提供行情分析图片
3. **确认规则**: 确认提取的交易规则
4. **系统实现**: 实现完整的交易系统

---

## 📞 支持

如有问题，请查看：
- 设计文档: `docs/design/features/千叶交易系统设计方案.md`
- 系统代码: `src/chiba_trading_system/`

---

**创建时间**: 2025-12-30  
**状态**: ✅ 视频和图片分析模块已就绪，等待输入




