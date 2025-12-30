#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从YouTube URL提取字幕
这是最简单可靠的方法
"""

import sys
from pathlib import Path
import json
from datetime import datetime
import re

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))


def extract_youtube_subtitle(url: str):
    """从YouTube URL提取字幕"""
    try:
        import yt_dlp
        
        print("=" * 80)
        print("从YouTube提取字幕")
        print("=" * 80)
        print()
        print(f"视频URL: {url}")
        print()
        
        output_dir = Path(__file__).parent.parent.parent / "data" / "chiba_videos" / "transcripts"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        ydl_opts = {
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['zh', 'zh-Hans', 'zh-Hant', 'zh-CN', 'zh-TW', 'en'],
            'subtitlesformat': 'vtt',
            'skip_download': True,
            'outtmpl': str(output_dir / '%(id)s.%(ext)s'),
            'quiet': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 先获取信息
            info = ydl.extract_info(url, download=False)
            video_id = info.get('id')
            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            
            print(f"视频标题: {title}")
            print(f"视频ID: {video_id}")
            print(f"时长: {duration} 秒 ({duration//60} 分钟)")
            print()
            
            # 检查是否有字幕
            subtitles = info.get('subtitles', {})
            auto_captions = info.get('automatic_captions', {})
            
            print("字幕检查:")
            if subtitles:
                print("  手动字幕:", ', '.join(subtitles.keys()))
            if auto_captions:
                print("  自动字幕:", ', '.join(auto_captions.keys()))
            
            if not subtitles and not auto_captions:
                print("⚠️ 未检测到字幕，但将尝试强制下载自动字幕...")
            print()
            
            # 强制下载字幕（即使检测不到也尝试）
            print("正在下载字幕...")
            try:
                ydl.download([url])
            except Exception as e:
                print(f"下载字幕时出错: {e}")
                # 继续尝试，可能已经下载了
            
            # 查找下载的字幕文件
            subtitle_files = list(output_dir.glob(f"{video_id}*.vtt"))
            
            if not subtitle_files:
                print("✗ 未找到字幕文件")
                print()
                print("可能的原因:")
                print("  1. 视频确实没有字幕（包括自动字幕）")
                print("  2. 需要使用Whisper进行语音转录")
                print()
                print("建议: 使用Whisper转录视频音频")
                return None
            
            # 解析字幕
            best_subtitle = None
            best_lang = None
            
            # 优先选择中文
            for lang in ['zh', 'zh-Hans', 'zh-Hant', 'zh-CN', 'zh-TW']:
                for sub_file in subtitle_files:
                    if lang in sub_file.name:
                        best_subtitle = sub_file
                        best_lang = lang
                        break
                if best_subtitle:
                    break
            
            # 如果没有中文，使用第一个
            if not best_subtitle:
                best_subtitle = subtitle_files[0]
            
            print(f"✓ 使用字幕文件: {best_subtitle.name}")
            print()
            
            # 解析VTT字幕
            subtitle_text = parse_vtt(best_subtitle)
            
            # 保存结果
            text_file = output_dir / f"{video_id}.txt"
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(subtitle_text)
            
            json_file = output_dir / f"{video_id}.json"
            result = {
                'source': 'youtube',
                'url': url,
                'video_id': video_id,
                'title': title,
                'duration': duration,
                'subtitle_file': str(best_subtitle),
                'text': subtitle_text,
                'text_length': len(subtitle_text),
                'extracted_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print("=" * 80)
            print("✓ 字幕提取完成")
            print("=" * 80)
            print()
            print(f"文本文件: {text_file.name}")
            print(f"JSON文件: {json_file.name}")
            print(f"文本长度: {len(subtitle_text)} 字符")
            print()
            print("前500字符预览:")
            print("-" * 80)
            print(subtitle_text[:500])
            if len(subtitle_text) > 500:
                print("...")
            print("-" * 80)
            print()
            
            return result
            
    except ImportError:
        print("✗ 需要安装 yt-dlp")
        print("  安装命令: pip install yt-dlp")
        return None
    except Exception as e:
        print(f"✗ 提取失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def parse_vtt(vtt_file: Path) -> str:
    """解析VTT字幕文件"""
    try:
        text_lines = []
        with open(vtt_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                line = line.strip()
                # 跳过时间戳、标记和空行
                if line and not line.startswith('<') and '-->' not in line and not line.startswith('WEBVTT'):
                    # 移除HTML标签
                    line = re.sub(r'<[^>]+>', '', line)
                    if line:
                        text_lines.append(line)
        return ' '.join(text_lines)
    except Exception as e:
        print(f"解析VTT失败: {e}")
        return ""


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='从YouTube URL提取字幕')
    parser.add_argument('url', nargs='?', help='YouTube视频URL')
    args = parser.parse_args()
    
    if args.url:
        url = args.url
    else:
        # 提示用户输入
        print("=" * 80)
        print("YouTube字幕提取器")
        print("=" * 80)
        print()
        print("请提供YouTube视频URL")
        print("例如: https://www.youtube.com/watch?v=r-1F__Ed-e4")
        print()
        url = input("请输入URL: ").strip()
        
        if not url:
            print("未提供URL，退出")
            return
    
    result = extract_youtube_subtitle(url)
    
    if result:
        print()
        print("下一步: 提取交易规则")
        print("  python src/chiba_trading_system/extract_rules_from_text.py")
    else:
        print()
        print("提取失败，请检查:")
        print("  1. URL是否正确")
        print("  2. 视频是否有字幕")
        print("  3. 网络连接是否正常")


if __name__ == '__main__':
    main()

