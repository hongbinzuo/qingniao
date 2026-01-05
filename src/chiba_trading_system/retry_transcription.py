#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
千叶交易系统 - 重试转录
对已下载的视频进行转录
"""

import sys
from pathlib import Path
import json
from datetime import datetime

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))


def transcribe_video(video_path: Path, output_dir: Path):
    """转录视频"""
    try:
        import whisper
        
        print(f"正在转录: {video_path.name}")
        print(f"  （这可能需要几分钟...）")
        
        # 使用tiny模型（更快，适合测试）
        model = whisper.load_model("tiny")
        
        # 转录
        result = model.transcribe(str(video_path), language="zh")
        
        # 保存转录结果
        transcript_file = output_dir / f"{video_path.stem}.json"
        with open(transcript_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        # 保存文本
        text_file = output_dir / f"{video_path.stem}.txt"
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(result['text'])
        
        print(f"✓ 转录完成")
        print(f"  - 文本长度: {len(result['text'])} 字符")
        print(f"  - 段落数: {len(result.get('segments', []))}")
        
        return result
        
    except Exception as e:
        print(f"✗ 转录失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """主函数"""
    downloads_dir = Path(__file__).parent.parent.parent / "data" / "chiba_videos" / "downloads"
    transcripts_dir = Path(__file__).parent.parent.parent / "data" / "chiba_videos" / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("千叶交易系统 - 重试转录")
    print("=" * 80)
    print()
    
    # 查找已下载的视频文件
    video_files = list(downloads_dir.glob("*.webm")) + list(downloads_dir.glob("*.mp4"))
    
    if not video_files:
        print("未找到已下载的视频文件")
        return
    
    print(f"找到 {len(video_files)} 个视频文件")
    print()
    
    for video_file in video_files:
        print("=" * 80)
        print(f"处理: {video_file.name}")
        print("=" * 80)
        print()
        
        # 检查是否已转录
        transcript_file = transcripts_dir / f"{video_file.stem}.txt"
        if transcript_file.exists():
            print(f"✓ 已存在转录文件: {transcript_file.name}")
            print()
            continue
        
        # 转录
        result = transcribe_video(video_file, transcripts_dir)
        
        if result:
            print(f"✓ 转录成功")
        else:
            print(f"✗ 转录失败")
        
        print()


if __name__ == '__main__':
    main()




