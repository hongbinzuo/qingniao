#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
随机选择50张图片用于对比试验
"""
import sys
import json
import random
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    
    # 图片目录
    images_dir = ROOT / 'data' / 'abu' / 'images'
    
    # 获取所有图片
    image_files = sorted(list(images_dir.glob('page_*_img_*_clip.png')))
    
    if len(image_files) < 50:
        print(f"❌ 图片数量不足50张，只有 {len(image_files)} 张")
        return
    
    # 随机选择50张
    random.seed(42)  # 固定种子，确保可重复
    selected_images = random.sample(image_files, 50)
    selected_images.sort(key=lambda x: x.name)  # 按名称排序
    
    # 保存选择结果
    output_dir = ROOT / 'data' / 'abu' / 'comparison_test'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存图片列表
    selected_list = [{
        'index': idx + 1,
        'image_name': img.name,
        'image_path': str(img.relative_to(ROOT)),
        'full_path': str(img)
    } for idx, img in enumerate(selected_images)]
    
    list_file = output_dir / 'selected_50_images.json'
    with open(list_file, 'w', encoding='utf-8') as f:
        json.dump(selected_list, f, ensure_ascii=False, indent=2)
    
    # 创建对比目录结构
    cursor_results_dir = output_dir / 'cursor_results'
    cursor_results_dir.mkdir(exist_ok=True)
    
    # 生成说明文件
    readme_file = output_dir / 'README_对比试验说明.md'
    readme_content = f"""# Cursor vs Gemini 对比试验说明

## 试验设计

- **随机选择**: 50张图片（从1000张中随机选择）
- **提示词**: "啥意思"（简单提示，测试模型的自然理解能力）
- **对比模型**: Cursor自动模型 vs Gemini 2.5 Flash

## 选择结果

共选择了 {len(selected_images)} 张图片。

### 图片列表

"""
    
    for item in selected_list:
        readme_content += f"{item['index']}. `{item['image_name']}`\n"
    
    readme_content += f"""

## 使用说明

### 步骤1: 使用Cursor识别这50张图片

1. 打开Cursor编辑器
2. 对于每张图片：
   - 在Cursor中打开图片（拖拽到Cursor或使用文件打开）
   - 使用Cursor的AI功能，提示词："啥意思"
   - 将识别结果保存到 `cursor_results/{'{'}{'{'}image_name{'}'}{'}'}.txt`

或者批量处理：
- 可以使用Cursor的批量处理功能（如果有）
- 或手动逐张处理

### 步骤2: 保存Cursor识别结果

将每张图片的识别结果保存为文本文件：
- 文件命名格式：`{{image_name}}.txt`
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

{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print("=" * 80)
    print("随机选择50张图片用于对比试验")
    print("=" * 80)
    print(f"\n✅ 已选择 {len(selected_images)} 张图片")
    print(f"✅ 图片列表已保存: {list_file}")
    print(f"✅ 说明文件已生成: {readme_file}")
    print(f"\n图片列表（前10张）:")
    for item in selected_list[:10]:
        print(f"  {item['index']}. {item['image_name']}")
    print(f"  ... (共{len(selected_list)}张)")
    print(f"\n下一步:")
    print(f"  1. 查看说明文件: {readme_file}")
    print(f"  2. 使用Cursor识别这50张图片")
    print(f"  3. 将结果保存到: {output_dir / 'cursor_results'}")
    print(f"  4. 运行对比脚本: python scripts/compare_cursor_vs_gemini.py")
    print("=" * 80)

if __name__ == '__main__':
    main()

