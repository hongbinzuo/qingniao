# 使用Cursor识别50张图片的详细指南

## 快速开始

### 方法1: 在Cursor中逐张处理（推荐）

1. **打开Cursor编辑器**

2. **对于每张图片**：
   - 将图片拖拽到Cursor编辑器中（或在Cursor中打开图片文件）
   - 在Cursor的AI聊天窗口中输入提示词：`啥意思`
   - 复制AI的回复
   - 保存为文本文件：`cursor_results/{图片名称}.txt`

3. **批量保存**：
   - 在 `data/abu/comparison_test/cursor_results/` 目录下创建文本文件
   - 文件名格式：`page_0007_img_01_clip.png.txt`（注意：是 `.png.txt`）

### 方法2: 使用Cursor的批量功能（如果支持）

如果Cursor支持批量处理，可以：
- 一次性选择所有50张图片
- 使用相同的提示词："啥意思"
- 批量获取结果

## 详细步骤

### 步骤1: 准备图片路径

图片位置：`data/abu/images/`

选中的50张图片列表：
- 查看 `selected_50_images.json` 获取完整列表
- 或查看 `README_对比试验说明.md` 中的列表

### 步骤2: 在Cursor中识别

**示例操作**：
1. 在Cursor中打开 `data/abu/images/page_0007_img_01_clip.png`
2. 在AI聊天窗口输入：`啥意思`
3. 等待AI回复
4. 复制回复内容
5. 保存到：`data/abu/comparison_test/cursor_results/page_0007_img_01_clip.png.txt`

**提示词**（统一使用）：
```
啥意思
```

**注意事项**：
- 保持提示词一致
- 保存原始回复（不要修改）
- 如果AI没有回复或出错，保存错误信息

### 步骤3: 检查结果

处理完成后，检查 `cursor_results/` 目录：
- 应该有50个 `.txt` 文件
- 文件名格式：`{image_name}.txt`

### 步骤4: 运行对比分析

```bash
python scripts/compare_cursor_vs_gemini.py
```

## 文件结构

```
data/abu/comparison_test/
├── selected_50_images.json          # 选中的50张图片列表
├── README_对比试验说明.md            # 说明文档
├── 使用Cursor识别指南.md            # 本文件
└── cursor_results/                  # Cursor识别结果（需要创建）
    ├── page_0007_img_01_clip.png.txt
    ├── page_0026_img_01_clip.png.txt
    ├── page_0028_img_01_clip.png.txt
    └── ... (共50个文件)
```

## 快捷脚本（可选）

如果你熟悉Python，可以创建一个简单的脚本来自动化部分流程，但核心的Cursor AI调用仍需要手动完成。

## 常见问题

**Q: 可以在Cursor中批量处理吗？**
A: 这取决于Cursor的功能。如果支持批量处理，可以使用；否则需要逐张处理。

**Q: 如果某张图片Cursor无法识别怎么办？**
A: 保存错误信息或"无法识别"到对应的文本文件中。

**Q: 需要处理多长时间？**
A: 如果逐张处理，每张图片大约需要10-30秒（包括打开图片、输入提示、等待回复、保存结果），50张大约需要10-25分钟。

**Q: 结果文件格式有要求吗？**
A: 纯文本格式即可，保存Cursor的原始回复，不要修改。

## 提示

- 可以一次性在Cursor中打开多张图片（如果支持）
- 可以使用快捷键加快操作速度
- 建议按顺序处理，避免遗漏
- 处理过程中可以休息，不需要一次性完成

