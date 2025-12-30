#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提取视频字幕
支持多种方式：
1. YouTube视频 - 使用yt-dlp提取字幕
2. 本地视频 - 使用ffmpeg提取内置字幕
3. 如果都没有，使用Whisper转录
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


class SubtitleExtractor:
    """字幕提取器"""
    
    def __init__(self):
        self.output_dir = Path(__file__).parent.parent.parent / "data" / "chiba_videos" / "transcripts"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_from_youtube_url(self, url: str) -> dict:
        """从YouTube URL提取字幕"""
        try:
            import yt_dlp
            
            print(f"从YouTube提取字幕: {url}")
            
            ydl_opts = {
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['zh', 'zh-Hans', 'zh-Hant', 'zh-CN', 'zh-TW', 'en'],
                'subtitlesformat': 'vtt',
                'skip_download': True,
                'quiet': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                video_id = info.get('id')
                title = info.get('title', 'Unknown')
                
                # 下载字幕
                ydl_opts_download = {
                    'writesubtitles': True,
                    'writeautomaticsub': True,
                    'subtitleslangs': ['zh', 'zh-Hans', 'zh-Hant', 'zh-CN', 'zh-TW', 'en'],
                    'subtitlesformat': 'vtt',
                    'skip_download': True,
                    'outtmpl': str(self.output_dir / f'{video_id}.%(ext)s'),
                }
                
                with yt_dlp.YoutubeDL(ydl_opts_download) as ydl2:
                    ydl2.extract_info(url, download=True)
                
                # 查找下载的字幕文件
                subtitle_files = list(self.output_dir.glob(f"{video_id}*.vtt"))
                
                if subtitle_files:
                    subtitle_file = subtitle_files[0]
                    print(f"✓ 找到字幕文件: {subtitle_file.name}")
                    
                    # 解析VTT字幕
                    subtitle_text = self.parse_vtt(subtitle_file)
                    
                    return {
                        'source': 'youtube',
                        'video_id': video_id,
                        'title': title,
                        'subtitle_file': str(subtitle_file),
                        'text': subtitle_text,
                        'success': True
                    }
                else:
                    print("⚠️ 未找到字幕文件")
                    return {'success': False, 'error': 'No subtitle file found'}
                    
        except Exception as e:
            print(f"✗ 提取失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def extract_from_video_file(self, video_path: Path) -> dict:
        """从视频文件提取字幕"""
        video_path = Path(video_path)
        
        if not video_path.exists():
            return {'success': False, 'error': f'Video file not found: {video_path}'}
        
        print(f"从视频文件提取字幕: {video_path.name}")
        
        # 方法1: 使用ffmpeg提取内置字幕
        subtitle_text = self.extract_with_ffmpeg(video_path)
        if subtitle_text:
            return {
                'source': 'video_file',
                'video_file': str(video_path),
                'text': subtitle_text,
                'success': True
            }
        
        # 方法2: 使用Whisper转录
        print("尝试使用Whisper转录...")
        subtitle_text = self.transcribe_with_whisper(video_path)
        if subtitle_text:
            return {
                'source': 'whisper_transcription',
                'video_file': str(video_path),
                'text': subtitle_text,
                'success': True
            }
        
        # 方法3: 如果视频是YouTube下载的，尝试从文件名提取video_id
        video_id = self.extract_video_id_from_filename(video_path.name)
        if video_id and len(video_id) == 11:  # YouTube video ID通常是11个字符
            # 尝试从YouTube获取字幕
            url = f"https://www.youtube.com/watch?v={video_id}"
            result = self.extract_from_youtube_url(url)
            if result.get('success'):
                return result
        
        return {'success': False, 'error': 'Could not extract subtitles'}
    
    def extract_with_ffmpeg(self, video_path: Path) -> str:
        """使用ffmpeg提取内置字幕"""
        try:
            import subprocess
            
            # 检查是否有字幕轨道
            cmd = [
                'ffmpeg', '-i', str(video_path),
                '-map', '0:s:0', '-f', 'srt', '-'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout:
                print("✓ 使用ffmpeg提取到内置字幕")
                return self.parse_srt(result.stdout)
            else:
                # 尝试其他字幕轨道
                for i in range(1, 5):
                    cmd = [
                        'ffmpeg', '-i', str(video_path),
                        '-map', f'0:s:{i}', '-f', 'srt', '-'
                    ]
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    if result.returncode == 0 and result.stdout:
                        print(f"✓ 使用ffmpeg提取到字幕轨道 {i}")
                        return self.parse_srt(result.stdout)
                
                return None
                
        except FileNotFoundError:
            print("⚠️ ffmpeg未安装，跳过内置字幕提取")
            return None
        except Exception as e:
            print(f"⚠️ ffmpeg提取失败: {e}")
            return None
    
    def extract_video_id_from_filename(self, filename: str) -> str:
        """从文件名提取YouTube video ID"""
        # 常见的YouTube文件名格式
        import re
        
        # 格式: videoplayback?expire=...&id=VIDEO_ID&...
        match = re.search(r'[?&]id=([a-zA-Z0-9_-]{11})', filename)
        if match:
            return match.group(1)
        
        # 格式: VIDEO_ID.webm
        match = re.search(r'([a-zA-Z0-9_-]{11})\.(webm|mp4)', filename)
        if match:
            return match.group(1)
        
        return None
    
    def transcribe_with_whisper(self, video_path: Path) -> str:
        """使用Whisper转录"""
        try:
            import whisper
            import os
            
            print("  正在使用Whisper转录（这可能需要几分钟）...")
            
            # 清除损坏的缓存
            try:
                model = whisper.load_model("tiny")
            except RuntimeError as e:
                if "SHA256" in str(e):
                    import shutil
                    cache_dir = os.path.expanduser('~/.cache/whisper')
                    shutil.rmtree(cache_dir, ignore_errors=True)
                    print("  已清除损坏的模型缓存，重新下载...")
                    model = whisper.load_model("tiny")
                else:
                    raise
            
            # 使用fp32避免CPU上的FP16问题
            result = model.transcribe(
                str(video_path), 
                language="zh",
                fp16=False  # CPU上使用FP32
            )
            
            text = result.get('text', '')
            if text:
                print(f"  ✓ 转录完成，文本长度: {len(text)} 字符")
            
            return text
            
        except ImportError:
            print("  ✗ Whisper未安装")
            print("    安装命令: pip install openai-whisper")
            return None
        except Exception as e:
            print(f"  ✗ Whisper转录失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def parse_vtt(self, vtt_file: Path) -> str:
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
                        import re
                        line = re.sub(r'<[^>]+>', '', line)
                        if line:
                            text_lines.append(line)
            return ' '.join(text_lines)
        except Exception as e:
            print(f"解析VTT失败: {e}")
            return ""
    
    def parse_srt(self, srt_content: str) -> str:
        """解析SRT字幕内容"""
        try:
            text_lines = []
            lines = srt_content.split('\n')
            for line in lines:
                line = line.strip()
                # 跳过序号和时间戳
                if line and not line.isdigit() and '-->' not in line:
                    text_lines.append(line)
            return ' '.join(text_lines)
        except Exception as e:
            print(f"解析SRT失败: {e}")
            return ""
    
    def save_subtitle(self, result: dict, output_name: str = None) -> Path:
        """保存字幕"""
        if not result.get('success'):
            return None
        
        if output_name is None:
            if 'video_id' in result:
                output_name = result['video_id']
            elif 'video_file' in result:
                output_name = Path(result['video_file']).stem
            else:
                output_name = f"subtitle_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 保存文本
        text_file = self.output_dir / f"{output_name}.txt"
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(result['text'])
        
        # 保存JSON
        json_file = self.output_dir / f"{output_name}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"✓ 字幕已保存:")
        print(f"  - 文本: {text_file.name}")
        print(f"  - JSON: {json_file.name}")
        print(f"  - 文本长度: {len(result['text'])} 字符")
        
        return text_file


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='提取视频字幕')
    parser.add_argument('--video', type=str, help='视频文件路径')
    parser.add_argument('--url', type=str, help='YouTube视频URL')
    parser.add_argument('--output', type=str, help='输出文件名（不含扩展名）')
    args = parser.parse_args()
    
    extractor = SubtitleExtractor()
    
    print("=" * 80)
    print("视频字幕提取器")
    print("=" * 80)
    print()
    
    result = None
    
    if args.url:
        # 从YouTube URL提取
        result = extractor.extract_from_youtube_url(args.url)
    elif args.video:
        # 从视频文件提取
        result = extractor.extract_from_video_file(Path(args.video))
    else:
        # 尝试从Downloads目录查找videoplayback文件
        downloads = Path('C:/Users/zuoho/Downloads')
        video_files = []
        
        for ext in ['.webm', '.mp4', '.mkv', '.avi', '.mov', '.m4v']:
            # 查找videoplayback文件
            files = list(downloads.glob(f'*videoplayback*{ext}'))
            video_files.extend(files)
            
            # 如果没有，查找所有视频文件
            if not video_files:
                files = [f for f in downloads.iterdir() if f.suffix.lower() == ext and f.is_file()]
                video_files.extend(files)
        
        if video_files:
            print(f"找到 {len(video_files)} 个视频文件")
            video_file = video_files[0]
            print(f"处理: {video_file.name}")
            print()
            result = extractor.extract_from_video_file(video_file)
        else:
            print("未找到视频文件")
            print("使用方法:")
            print("  python extract_subtitles.py --video <视频文件路径>")
            print("  python extract_subtitles.py --url <YouTube URL>")
            return
    
    if result and result.get('success'):
        extractor.save_subtitle(result, args.output)
        print()
        print("=" * 80)
        print("✓ 提取完成")
        print("=" * 80)
    else:
        error = result.get('error', 'Unknown error') if result else 'No result'
        print(f"✗ 提取失败: {error}")


if __name__ == '__main__':
    main()

