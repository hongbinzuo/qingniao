# -*- coding: utf-8 -*-
"""
ABU 批量图片处理脚本 (601-1000)
使用 Kimi CLI 的 Task 工具并行处理图片

使用方法:
1. 确保在 Kimi CLI 环境中运行
2. 执行: python scripts/run_abu_batch_601_1000.py

作者: AI Assistant
创建时间: 2026-01-28
"""

import json
import time
import os
import sys
from datetime import datetime
from pathlib import Path

# 配置参数
START_PAGE = 601
END_PAGE = 1000
BATCH_SIZE = 5  # 每个Sub Agent处理5张
CONCURRENT_AGENTS = 3  # 每轮3个并发
IMAGES_DIR = r"C:\Users\zuoho\code\qingniao\data\abu\images"
OUTPUTS_DIR = r"C:\Users\zuoho\code\qingniao\outputs"

# 进度和结果文件
PROGRESS_FILE = os.path.join(OUTPUTS_DIR, f"abu_progress_{START_PAGE}_{END_PAGE}.json")
RESULTS_FILE = os.path.join(OUTPUTS_DIR, f"abu_results_{START_PAGE}_{END_PAGE}.jsonl")


def load_progress():
    """加载进度"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "completed_images": [],
        "failed_images": [],
        "current_round": 0,
        "start_time": datetime.now().isoformat(),
        "last_update": datetime.now().isoformat()
    }


def save_progress(progress):
    """保存进度"""
    progress["last_update"] = datetime.now().isoformat()
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


def save_result(result):
    """追加保存单个结果 (JSON Lines)"""
    with open(RESULTS_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(result, ensure_ascii=False) + '\n')


def get_image_path(page_num):
    """获取图片完整路径"""
    return os.path.join(IMAGES_DIR, f"page_{page_num:04d}_img_01_clip.png")


def get_all_batches():
    """获取所有批次"""
    all_pages = list(range(START_PAGE, END_PAGE + 1))
    
    # 每批5张
    batches = []
    for i in range(0, len(all_pages), BATCH_SIZE):
        batch_pages = all_pages[i:i+BATCH_SIZE]
        batch_images = [get_image_path(p) for p in batch_pages]
        batches.append({
            "batch_num": i // BATCH_SIZE + 1,
            "pages": batch_pages,
            "images": batch_images,
            "start_page": batch_pages[0],
            "end_page": batch_pages[-1]
        })
    
    return batches


def build_subagent_prompt(batch):
    """构建 Sub Agent 的提示词"""
    image_list = "\n".join([f"- {img}" for img in batch["images"]])
    
    return f"""你是一个专业的 Al Brooks 价格行为交易分析师。

请分析以下 {len(batch['images'])} 张图表图片：

图片列表：
{image_list}

## 分析要求

### 1. 完整图表描述 (必须)
- 描述整张图表的完整画面 - 从开始到结束展示了什么
- 完整价格旅程: 从左到右逐步描述价格走势
- 图表结构: 整体结构是什么? (如"左侧强势上涨，中间回调，右侧延续")
- 视觉布局: 各模式之间的相对位置? 空间关系?
- 所有视觉元素: 描述所有线条、箭头、标签、注释、颜色、形状
- 价格范围: 提取可见的最高和最低价格
- 时间框架: 什么时间周期和时间段? (如可见)

### 2. 交易信号 (最重要)
- 查找文本注释如 "20-Gap bar buy", "75% chance", "test of high of day"
- 提取入场条件、入场价格、止损水平、止盈水平
- 提取概率百分比 (如 "75%", "80% chance")
- 提取方向 (long/short)、时间框架提示 (如 "15m", "5m")

### 3. 模式识别
- 常见模式: 头肩顶/底、双顶/底、三重顶/底、楔形、三角形、旗形、三角旗
- 价格行为模式: Small Pullback (PB)、Measured Move (MM)、Bear Trap、Bull Trap
- 趋势模式: Higher Highs/Higher Lows、Lower Highs/Lower Lows、Trend Channels

### 4. K线特征
- 吞没形态 (看涨/看跌) - 出现在哪里
- Pin bars / Rejection bars - 位置和重要性
- Inside bars - 数量、位置
- Gap bars - 大小、位置、方向

### 5. 市场状况
- 市场背景描述 (如 "Small PB bull trend", "Bear trend from the open")
- 基于时间的背景: 早盘? 午盘? 盘前? 日内演变?
- 趋势强度: 强、中等、弱 - 以及如何变化
- 波动性: 高、低、中等 - 以及何时变化

## 输出格式 (严格的 JSON)

```json
{{
  "batch_info": {{
    "start_page": {batch['start_page']},
    "end_page": {batch['end_page']},
    "image_count": {len(batch['images'])}
  }},
  "results": [
    {{
      "image": "page_XXXX_img_01_clip.png",
      "page_number": XXXX,
      "success": true,
      "chart_overview": {{
        "timeframe": "5m E-mini",
        "time_period": "morning session",
        "price_range": {{"high": 4990, "low": 4930}},
        "chart_structure": "描述图表整体结构"
      }},
      "complete_price_path": {{
        "start_price": 4930,
        "end_price": 4985,
        "price_journey": "详细步骤描述",
        "major_swings": [
          {{"type": "up", "from": 4930, "to": 4970, "location": "left third"}}
        ]
      }},
      "patterns": [
        {{
          "name": "Small Pullback Bull Trend",
          "type": "continuation",
          "location": "left to middle third",
          "confidence": 0.95
        }}
      ],
      "trading_signals": [
        {{
          "direction": "long",
          "entry_price": 4975,
          "stop_loss": 4960,
          "take_profit": 5000,
          "probability": 0.75,
          "timeframe": "5m",
          "setup": "20-Gap bar buy"
        }}
      ],
      "kline_features": {{
        "engulfing_patterns": [],
        "pin_bars": [],
        "inside_bars": [],
        "gap_bars": []
      }},
      "market_conditions": {{
        "trend": "bullish",
        "trend_strength": "strong",
        "volatility": "moderate",
        "session": "morning"
      }}
    }}
  ],
  "failed_images": [],
  "processing_time_seconds": 120,
  "errors": []
}}
```

## 重要规则

1. **必须分析所有图片**: 即使某张图片有问题，也要记录原因并继续
2. **图片读取**: 使用 ReadMediaFile 工具读取每张图片
3. **失败处理**: 如果某张图片无法分析，在 failed_images 中记录原因
4. **JSON 格式**: 返回必须是有效的 JSON，不要有任何其他文本

请现在开始分析这些图片。记住：详细、全面、准确是关键。
"""


def print_progress_banner(progress, total_images):
    """打印进度横幅"""
    completed = len(progress["completed_images"])
    failed = len(progress["failed_images"])
    percentage = (completed / total_images) * 100 if total_images > 0 else 0
    
    print("\n" + "="*60)
    print(" ABU 批量图片处理进度")
    print("="*60)
    print(f" 总图片数: {total_images}")
    print(f" 已完成:   {completed} ({percentage:.1f}%)")
    print(f" 失败:     {failed}")
    print(f" 剩余:     {total_images - completed - failed}")
    print(f" 开始时间: {progress.get('start_time', 'N/A')}")
    print(f" 最后更新: {progress.get('last_update', 'N/A')}")
    print("="*60 + "\n")


def simulate_task_call(batch, progress):
    """
    模拟 Task 工具调用
    实际使用时，这里会被替换为真正的 Task 工具调用
    """
    print(f"\n[批次 {batch['batch_num']}] 处理图片 {batch['start_page']}-{batch['end_page']}")
    print(f"  图片列表:")
    for img in batch["images"]:
        exists = "✓" if os.path.exists(img) else "✗"
        print(f"    {exists} {os.path.basename(img)}")
    
    # 实际使用时，这里调用 Task 工具
    # result = Task(
    #     description=f"分析图表{batch['start_page']}-{batch['end_page']}",
    #     subagent_name="abu_image_analyzer",
    #     prompt=build_subagent_prompt(batch)
    # )
    
    # 模拟返回结果
    return {
        "batch_num": batch["batch_num"],
        "success": True,
        "results": [
            {
                "image": os.path.basename(img),
                "page": batch["pages"][i],
                "success": True
            }
            for i, img in enumerate(batch["images"])
        ],
        "failed": []
    }


def main():
    """主函数"""
    print("\n" + "="*60)
    print(" ABU 批量图片处理脚本")
    print(f" 范围: {START_PAGE}-{END_PAGE} (共{END_PAGE-START_PAGE+1}张)")
    print("="*60 + "\n")
    
    # 确保输出目录存在
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    
    # 加载进度
    progress = load_progress()
    
    # 获取所有批次
    all_batches = get_all_batches()
    total_batches = len(all_batches)
    total_images = (END_PAGE - START_PAGE + 1)
    
    print(f"总批次数: {total_batches}")
    print(f"每批图片: {BATCH_SIZE}张")
    print(f"并发数: {CONCURRENT_AGENTS}个Sub Agent")
    print(f"每轮处理: {BATCH_SIZE * CONCURRENT_AGENTS}张")
    print(f"预计轮数: {(total_batches + CONCURRENT_AGENTS - 1) // CONCURRENT_AGENTS}轮")
    print()
    
    # 显示当前进度
    print_progress_banner(progress, total_images)
    
    # 过滤已完成的批次
    completed_set = set(progress["completed_images"])
    remaining_batches = [
        b for b in all_batches 
        if not all(os.path.basename(img) in completed_set for img in b["images"])
    ]
    
    if not remaining_batches:
        print("✓ 所有图片已处理完成！")
        return
    
    print(f"剩余批次: {len(remaining_batches)}/{total_batches}\n")
    
    # 按轮次处理
    round_num = 0
    for i in range(0, len(remaining_batches), CONCURRENT_AGENTS):
        round_num += 1
        current_round_batches = remaining_batches[i:i+CONCURRENT_AGENTS]
        
        print(f"\n{'='*60}")
        print(f" 第 {round_num} 轮处理 ({len(current_round_batches)} 个批次)")
        print(f"{'='*60}")
        
        for batch in current_round_batches:
            print(f"\n→ 批次 {batch['batch_num']}: 图片 {batch['start_page']}-{batch['end_page']}")
            
            try:
                # 调用 Sub Agent 处理
                result = simulate_task_call(batch, progress)
                
                if result["success"]:
                    # 更新进度
                    for r in result.get("results", []):
                        if r.get("success"):
                            progress["completed_images"].append(r["image"])
                            save_result(r)
                    
                    # 记录失败的
                    for f in result.get("failed", []):
                        progress["failed_images"].append(f)
                    
                    save_progress(progress)
                    print(f"  ✓ 完成")
                else:
                    print(f"  ✗ 处理失败")
                    
            except Exception as e:
                print(f"  ✗ 错误: {e}")
                continue
        
        # 每5轮暂停
        if round_num % 5 == 0 and i + CONCURRENT_AGENTS < len(remaining_batches):
            print(f"\n⏸ 已处理5轮，暂停10秒...")
            time.sleep(10)
        
        # 显示进度
        print_progress_banner(progress, total_images)
    
    # 最终报告
    print("\n" + "="*60)
    print(" 处理完成！")
    print("="*60)
    print(f" 完成图片: {len(progress['completed_images'])}/{total_images}")
    print(f" 失败图片: {len(progress['failed_images'])}")
    print(f" 进度文件: {PROGRESS_FILE}")
    print(f" 结果文件: {RESULTS_FILE}")
    print("="*60)


if __name__ == "__main__":
    main()
