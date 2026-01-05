#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
千叶交易系统 - 提取视频信息
从YouTube视频中提取标题、描述等信息
"""

import sys
from pathlib import Path
from typing import Dict, List
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


def extract_video_info(url: str) -> Dict:
    """提取视频信息（不下载）"""
    try:
        import yt_dlp
        
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['zh', 'zh-Hans', 'zh-Hant', 'en'],
            'subtitlesformat': 'vtt'
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            result = {
                'url': url,
                'video_id': info.get('id'),
                'title': info.get('title'),
                'description': info.get('description', ''),
                'duration': info.get('duration', 0),
                'upload_date': info.get('upload_date'),
                'view_count': info.get('view_count', 0),
                'like_count': info.get('like_count', 0),
                'categories': info.get('categories', []),
                'tags': info.get('tags', []),
                'subtitles_available': bool(info.get('subtitles')),
                'automatic_captions_available': bool(info.get('automatic_captions'))
            }
            
            return result
            
    except Exception as e:
        print(f"提取视频信息失败: {e}", file=sys.stderr)
        return {}


def main():
    """主函数"""
    video_urls = [
        "https://www.youtube.com/watch?v=r-1F__Ed-e4",
        "https://www.youtube.com/watch?v=-iW_GEN95IU",
        "https://www.youtube.com/watch?v=efHztTLabcU"
    ]
    
    print("=" * 80)
    print("千叶交易系统 - 提取视频信息")
    print("=" * 80)
    print()
    
    all_info = []
    
    for i, url in enumerate(video_urls, 1):
        print(f"【{i}/{len(video_urls)}】提取视频信息...")
        print(f"链接: {url}")
        
        info = extract_video_info(url)
        
        if info:
            print(f"  标题: {info.get('title', 'N/A')}")
            print(f"  时长: {info.get('duration', 0)} 秒")
            print(f"  描述长度: {len(info.get('description', ''))} 字符")
            print(f"  字幕可用: {'是' if info.get('subtitles_available') else '否'}")
            print(f"  自动字幕可用: {'是' if info.get('automatic_captions_available') else '否'}")
            all_info.append(info)
        else:
            print("  ✗ 提取失败")
        
        print()
    
    # 保存信息
    output_file = Path(__file__).parent.parent.parent / "data" / "chiba_videos" / "video_info.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'extracted_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'videos': all_info
        }, f, indent=2, ensure_ascii=False)
    
    print(f"✓ 视频信息已保存: {output_file}")
    print()
    
    # 打印描述（可能包含交易规则）
    print("=" * 80)
    print("视频描述（可能包含交易规则）")
    print("=" * 80)
    print()
    
    for i, info in enumerate(all_info, 1):
        print(f"视频 {i}: {info.get('title', 'N/A')}")
        print()
        description = info.get('description', '')
        if description:
            # 只显示前500字符
            print(description[:500])
            if len(description) > 500:
                print("...")
        else:
            print("（无描述）")
        print()
        print("-" * 80)
        print()

if __name__ == '__main__':
    main()






