# Cursor vs Gemini 对比试验说明

## 试验设计

- **随机选择**: 50张图片（从1000张中随机选择）
- **提示词**: "啥意思"（简单提示，测试模型的自然理解能力）
- **对比模型**: Cursor自动模型 vs Gemini 2.5 Flash

## 选择结果

共选择了 50 张图片。

### 图片列表

1. `page_0007_img_01_clip.png`
2. `page_0026_img_01_clip.png`
3. `page_0028_img_01_clip.png`
4. `page_0031_img_01_clip.png`
5. `page_0033_img_01_clip.png`
6. `page_0090_img_01_clip.png`
7. `page_0095_img_01_clip.png`
8. `page_0096_img_01_clip.png`
9. `page_0105_img_01_clip.png`
10. `page_0115_img_01_clip.png`
11. `page_0143_img_01_clip.png`
12. `page_0160_img_01_clip.png`
13. `page_0164_img_01_clip.png`
14. `page_0204_img_01_clip.png`
15. `page_0221_img_01_clip.png`
16. `page_0224_img_01_clip.png`
17. `page_0226_img_01_clip.png`
18. `page_0229_img_01_clip.png`
19. `page_0239_img_01_clip.png`
20. `page_0251_img_01_clip.png`
21. `page_0282_img_01_clip.png`
22. `page_0285_img_01_clip.png`
23. `page_0345_img_01_clip.png`
24. `page_0349_img_01_clip.png`
25. `page_0390_img_01_clip.png`
26. `page_0430_img_01_clip.png`
27. `page_0433_img_01_clip.png`
28. `page_0460_img_01_clip.png`
29. `page_0518_img_01_clip.png`
30. `page_0559_img_01_clip.png`
31. `page_0575_img_01_clip.png`
32. `page_0604_img_01_clip.png`
33. `page_0605_img_01_clip.png`
34. `page_0617_img_01_clip.png`
35. `page_0655_img_01_clip.png`
36. `page_0666_img_01_clip.png`
37. `page_0693_img_01_clip.png`
38. `page_0715_img_01_clip.png`
39. `page_0719_img_01_clip.png`
40. `page_0734_img_01_clip.png`
41. `page_0755_img_01_clip.png`
42. `page_0759_img_01_clip.png`
43. `page_0760_img_01_clip.png`
44. `page_0778_img_01_clip.png`
45. `page_0782_img_01_clip.png`
46. `page_0826_img_01_clip.png`
47. `page_0829_img_01_clip.png`
48. `page_0891_img_01_clip.png`
49. `page_0914_img_01_clip.png`
50. `page_0981_img_01_clip.png`


## 使用说明

### 步骤1: 使用Cursor识别这50张图片

1. 打开Cursor编辑器
2. 对于每张图片：
   - 在Cursor中打开图片（拖拽到Cursor或使用文件打开）
   - 使用Cursor的AI功能，提示词："啥意思"
   - 将识别结果保存到 `cursor_results/{{image_name}}.txt`

或者批量处理：
- 可以使用Cursor的批量处理功能（如果有）
- 或手动逐张处理

### 步骤2: 保存Cursor识别结果

将每张图片的识别结果保存为文本文件：
- 文件命名格式：`{image_name}.txt`
- 保存位置：`data/abu/comparison_test/cursor_results/`

### 步骤3: 运行对比分析

```bash
python scripts/compare_cursor_vs_gemini.py
```

## 注意事项

- 提示词统一使用："啥意思"
- 保持结果原始格式（不要额外加工）
- 如果某张图片无法识别，保存错误信息
- 记录识别时间（可选）

## 生成时间

2026-01-11 22:23:44
