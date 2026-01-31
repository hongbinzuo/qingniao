# Gemini Vision 图形识别模块使用说明

## 🎯 模块定位

**独立模块**：只用于图形识别，不做其他用途  
**成本控制**：强制使用 `gemini-1.5-flash`，禁止Pro模型  
**成本估算**：1000张图片约 $0.125 USD

## 📁 文件结构

```
src/abu/gemini_vision_analyzer.py  # 核心分析模块（独立）
scripts/abu/abu_parse_gemini_output.py  # 解析输出
scripts/abu/abu_update_pattern_library_from_gemini.py  # 更新数据库
scripts/abu/abu_verify_gemini_analysis.py  # 验证结果
```

## 🚀 快速开始

### 1. 设置API Key

```bash
export GEMINI_API_KEY="your_api_key"
```

### 2. 执行分析（自动断点续传）

```bash
# 完整分析1000张图片
python -m src.abu.gemini_vision_analyzer \
    --api-key $GEMINI_API_KEY \
    --model gemini-1.5-flash \
    --sleep-ms 1000 \
    --resume  # 默认开启，支持断点续传
```

### 3. 查看状态

```bash
# 查看处理进度（不执行分析）
python -m src.abu.gemini_vision_analyzer --status
```

### 4. 解析并更新数据库

```bash
# 解析Gemini输出
python scripts/abu/abu_parse_gemini_output.py \
    --input outputs/abu_gemini_annotations_enhanced.jsonl

# 更新模式库（先预览）
python scripts/abu/abu_update_pattern_library_from_gemini.py \
    --input outputs/abu_gemini_parsed.jsonl \
    --dry-run

# 实际更新
python scripts/abu/abu_update_pattern_library_from_gemini.py \
    --input outputs/abu_gemini_parsed.jsonl
```

## 🔒 成本控制机制

1. **模型强制**：自动检测并禁止使用Pro模型
2. **去重机制**：SHA1检查、输出文件检查、缓存检查
3. **成本估算**：实时显示每次调用成本和总成本
4. **API限流**：默认1秒间隔（可配置）

## 📊 输出文件

- `outputs/abu_gemini_annotations_enhanced.jsonl` - Gemini分析结果
- `outputs/abu_gemini_analysis_state.json` - 处理状态（断点续传）
- `outputs/.cache/abu_gemini/{sha1}.json` - 单图缓存
- `outputs/abu_gemini/gemini_analysis.log` - 详细日志

## ⚠️ 注意事项

1. **不要重复分析**：模块会自动跳过已处理的图片
2. **支持中断**：可以随时中断，下次运行自动继续
3. **查看日志**：如有问题，查看 `gemini_analysis.log`
4. **成本监控**：每次运行显示总成本和剩余成本

