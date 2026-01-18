#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查视频文件信息
"""

import sys
from pathlib import Path
import subprocess
import json

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def check_video(video_path: Path):
    """检查视频文件信息"""
    video_path = Path(video_path)
    
    if not video_path.exists():
        print(f"文件不存在: {video_path}")
        return
    
    print("=" * 80)
    print(f"检查视频文件: {video_path.name}")
    print("=" * 80)
    print()
    
    # 使用ffprobe检查
    try:
        cmd = [
            'ffprobe', '-v', 'error', '-show_streams', 
            '-show_format', '-of', 'json', str(video_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            info = json.loads(result.stdout)
            
            print("视频信息:")
            print(f"  格式: {info.get('format', {}).get('format_name', 'Unknown')}")
            print(f"  时长: {info.get('format', {}).get('duration', 'Unknown')} 秒")
            print()
            
            print("流信息:")
            has_video = False
            has_audio = False
            has_subtitle = False
            
            for stream in info.get('streams', []):
                codec_type = stream.get('codec_type', '')
                codec_name = stream.get('codec_name', '')
                
                if codec_type == 'video':
                    has_video = True
                    width = stream.get('width', '?')
                    height = stream.get('height', '?')
                    print(f"  ✓ 视频流: {codec_name} ({width}x{height})")
                elif codec_type == 'audio':
                    has_audio = True
                    sample_rate = stream.get('sample_rate', '?')
                    print(f"  ✓ 音频流: {codec_name} ({sample_rate} Hz)")
                elif codec_type == 'subtitle':
                    has_subtitle = True
                    language = stream.get('tags', {}).get('language', 'unknown')
                    print(f"  ✓ 字幕流: {codec_name} ({language})")
            
            print()
            
            if not has_video:
                print("⚠️ 警告: 未找到视频流")
            if not has_audio:
                print("⚠️ 警告: 未找到音频流（无法使用Whisper转录）")
            if not has_subtitle:
                print("⚠️ 警告: 未找到内置字幕流")
            
            print()
            
            if has_subtitle:
                print("✓ 可以提取内置字幕")
            elif has_audio:
                print("✓ 可以使用Whisper转录")
            else:
                print("✗ 无法提取字幕（无音频流）")
                print()
                print("建议:")
                print("  1. 如果这是YouTube视频，请提供原始视频URL")
                print("  2. 或者下载包含音频的完整视频文件")
                print("  3. 或者手动提供字幕文件")
                
        else:
            print(f"ffprobe错误: {result.stderr}")
            
    except FileNotFoundError:
        print("ffprobe未安装，无法检查视频信息")
    except Exception as e:
        print(f"检查失败: {e}")

if __name__ == '__main__':
    video_file = Path('C:/Users/zuoho/Downloads/videoplayback.webm')
    check_video(video_file)








