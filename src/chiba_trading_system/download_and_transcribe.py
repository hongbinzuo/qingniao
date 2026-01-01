#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载YouTube视频并转录
下载包含音频的完整视频，然后使用Whisper转录
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


def download_video_with_audio(url: str):
    """下载包含音频的完整视频"""
    try:
        import yt_dlp
        
        output_dir = Path(__file__).parent.parent.parent / "data" / "chiba_videos" / "downloads"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print("=" * 80)
        print("下载YouTube视频（包含音频）")
        print("=" * 80)
        print()
        print(f"视频URL: {url}")
        print()
        
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',  # 最佳视频+最佳音频
            'outtmpl': str(output_dir / '%(id)s.%(ext)s'),
            'quiet': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 获取信息
            info = ydl.extract_info(url, download=False)
            video_id = info.get('id')
            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            
            print(f"视频标题: {title}")
            print(f"视频ID: {video_id}")
            print(f"时长: {duration} 秒 ({duration//60} 分钟)")
            print()
            
            # 检查是否已下载
            existing_files = list(output_dir.glob(f"{video_id}.*"))
            if existing_files:
                video_file = existing_files[0]
                print(f"✓ 视频已存在: {video_file.name}")
                return video_file
            
            # 下载
            print("正在下载视频（包含音频）...")
            print("  这可能需要几分钟...")
            ydl.download([url])
            
            # 查找下载的文件
            downloaded_files = list(output_dir.glob(f"{video_id}.*"))
            if downloaded_files:
                video_file = downloaded_files[0]
                print(f"✓ 下载完成: {video_file.name}")
                return video_file
            else:
                print("✗ 未找到下载的文件")
                return None
                
    except Exception as e:
        print(f"✗ 下载失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def transcribe_video(video_path: Path):
    """使用Whisper转录视频"""
    try:
        import whisper
        import os
        
        print()
        print("=" * 80)
        print("使用Whisper转录视频")
        print("=" * 80)
        print()
        print(f"视频文件: {video_path.name}")
        print(f"文件大小: {video_path.stat().st_size / 1024 / 1024:.2f} MB")
        print()
        print("正在转录（这可能需要几分钟，请耐心等待）...")
        print()
        
        output_dir = Path(__file__).parent.parent.parent / "data" / "chiba_videos" / "transcripts"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 检查是否已转录
        transcript_file = output_dir / f"{video_path.stem}.txt"
        if transcript_file.exists():
            print(f"✓ 已存在转录文件: {transcript_file.name}")
            with open(transcript_file, 'r', encoding='utf-8') as f:
                text = f.read()
            return text
        
        # 加载模型
        try:
            model = whisper.load_model("tiny")
        except RuntimeError as e:
            if "SHA256" in str(e):
                import shutil
                cache_dir = os.path.expanduser('~/.cache/whisper')
                shutil.rmtree(cache_dir, ignore_errors=True)
                print("  清除损坏的模型缓存，重新下载...")
                model = whisper.load_model("tiny")
            else:
                raise
        
        # 转录
        result = model.transcribe(
            str(video_path),
            language="zh",
            fp16=False
        )
        
        text = result.get('text', '')
        
        # 保存转录结果
        with open(transcript_file, 'w', encoding='utf-8') as f:
            f.write(text)
        
        json_file = output_dir / f"{video_path.stem}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                'video_file': str(video_path),
                'text': text,
                'segments': result.get('segments', []),
                'language': result.get('language', 'zh'),
                'transcribed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }, f, indent=2, ensure_ascii=False)
        
        print()
        print("=" * 80)
        print("✓ 转录完成")
        print("=" * 80)
        print()
        print(f"文本文件: {transcript_file.name}")
        print(f"JSON文件: {json_file.name}")
        print(f"文本长度: {len(text)} 字符")
        print()
        print("前500字符预览:")
        print("-" * 80)
        print(text[:500])
        if len(text) > 500:
            print("...")
        print("-" * 80)
        
        return text
        
    except ImportError:
        print("✗ 需要安装 openai-whisper")
        print("  安装命令: pip install openai-whisper")
        return None
    except Exception as e:
        print(f"✗ 转录失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """主函数"""
    urls = [
        "https://www.youtube.com/watch?v=r-1F__Ed-e4",
        "https://www.youtube.com/watch?v=-iW_GEN95IU",
        "https://www.youtube.com/watch?v=efHztTLabcU"
    ]
    
    print("=" * 80)
    print("千叶交易系统 - 下载并转录视频")
    print("=" * 80)
    print()
    print(f"将处理 {len(urls)} 个视频")
    print()
    
    all_transcripts = []
    
    for i, url in enumerate(urls, 1):
        print("=" * 80)
        print(f"视频 {i}/{len(urls)}")
        print("=" * 80)
        print()
        
        # 下载视频
        video_file = download_video_with_audio(url)
        if not video_file:
            print("跳过此视频")
            print()
            continue
        
        print()
        
        # 转录视频
        transcript_text = transcribe_video(video_file)
        if transcript_text:
            all_transcripts.append({
                'url': url,
                'video_file': str(video_file),
                'text': transcript_text
            })
        
        print()
    
    if all_transcripts:
        print("=" * 80)
        print("✓ 所有视频处理完成")
        print("=" * 80)
        print()
        print(f"成功转录 {len(all_transcripts)} 个视频")
        print()
        print("下一步: 提取交易规则")
        print("  python src/chiba_trading_system/extract_rules_from_text.py")
    else:
        print("=" * 80)
        print("处理未完成")
        print("=" * 80)


if __name__ == '__main__':
    main()



