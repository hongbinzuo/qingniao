#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
千叶交易系统 - 快速分析
下载视频并提取字幕（如果有）
"""

import sys
from pathlib import Path
import json

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))


def download_with_subtitles(url: str, output_dir: Path):
    """下载视频并提取字幕"""
    try:
        import yt_dlp
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': str(output_dir / '%(title)s.%(ext)s'),
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['zh', 'zh-Hans', 'zh-Hant', 'en', 'zh.*'],
            'subtitlesformat': 'vtt',
            'skip_download': False,
            'quiet': False,
        }
        
        print(f"正在处理: {url}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # 查找字幕文件
            video_id = info.get('id')
            subtitle_files = list(output_dir.glob(f"*{video_id}*.vtt"))
            
            if subtitle_files:
                print(f"✓ 找到字幕文件: {subtitle_files[0].name}")
                return subtitle_files[0]
            else:
                print("⚠️ 未找到字幕文件，需要转录")
                return None
                
    except Exception as e:
        print(f"✗ 处理失败: {e}")
        return None


def parse_vtt_subtitle(vtt_file: Path) -> str:
    """解析VTT字幕文件"""
    try:
        text_lines = []
        with open(vtt_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                line = line.strip()
                # 跳过时间戳和标记
                if line and not line.startswith('<') and not '-->' in line and not line.startswith('WEBVTT'):
                    text_lines.append(line)
        return ' '.join(text_lines)
    except Exception as e:
        print(f"解析字幕失败: {e}")
        return ""


def main():
    """主函数"""
    video_urls = [
        "https://www.youtube.com/watch?v=r-1F__Ed-e4",
        "https://www.youtube.com/watch?v=-iW_GEN95IU",
        "https://www.youtube.com/watch?v=efHztTLabcU"
    ]
    
    output_dir = Path(__file__).parent.parent.parent / "data" / "chiba_videos" / "downloads"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("千叶交易系统 - 快速分析")
    print("=" * 80)
    print()
    
    all_transcripts = []
    
    for i, url in enumerate(video_urls, 1):
        print(f"【{i}/{len(video_urls)}】处理视频...")
        
        # 尝试下载并提取字幕
        vtt_file = download_with_subtitles(url, output_dir)
        
        if vtt_file:
            transcript = parse_vtt_subtitle(vtt_file)
            if transcript:
                all_transcripts.append({
                    'url': url,
                    'video_id': url.split('v=')[-1],
                    'transcript': transcript,
                    'transcript_length': len(transcript)
                })
                print(f"✓ 提取字幕: {len(transcript)} 字符")
            else:
                print("⚠️ 字幕文件为空")
        else:
            print("⚠️ 需要手动转录")
        
        print()
    
    # 保存转录文本
    if all_transcripts:
        output_file = output_dir.parent / "transcripts.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'extracted_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'transcripts': all_transcripts
            }, f, indent=2, ensure_ascii=False)
        
        print(f"✓ 转录文本已保存: {output_file}")
        print()
        
        # 打印转录文本摘要
        print("=" * 80)
        print("转录文本摘要")
        print("=" * 80)
        print()
        
        for i, t in enumerate(all_transcripts, 1):
            print(f"视频 {i}: {t['video_id']}")
            print(f"文本长度: {t['transcript_length']} 字符")
            print(f"前200字符: {t['transcript'][:200]}...")
            print()
    
    print("=" * 80)
    print("提示: 如果无法自动提取字幕，需要安装whisper进行转录")
    print("安装命令: pip install openai-whisper")
    print("=" * 80)


if __name__ == '__main__':
    from datetime import datetime
    main()





