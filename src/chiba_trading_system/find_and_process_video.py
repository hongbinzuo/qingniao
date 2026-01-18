#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查找并处理视频文件
"""

import sys
from pathlib import Path

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from chiba_trading_system.process_local_videos import LocalVideoProcessor

def main():
    """主函数"""
    # 查找可能的视频文件位置
    search_paths = [
        Path('C:/Users/zuoho/Downloads'),
        Path('C:/Users/zuoho/Downloads/videoplayback'),
    ]
    
    video_extensions = ['.webm', '.mp4', '.mkv', '.avi', '.mov', '.m4v']
    
    print("=" * 80)
    print("查找视频文件")
    print("=" * 80)
    print()
    
    video_files = []
    
    for search_path in search_paths:
        if not search_path.exists():
            print(f"目录不存在: {search_path}")
            continue
        
        print(f"搜索目录: {search_path}")
        
        # 查找所有视频文件
        for ext in video_extensions:
            files = list(search_path.glob(f"*{ext}"))
            video_files.extend(files)
            
            # 也查找videoplayback相关的
            files2 = list(search_path.glob(f"*videoplayback*{ext}"))
            video_files.extend(files2)
        
        # 递归查找
        for ext in video_extensions:
            files = list(search_path.rglob(f"*{ext}"))
            video_files.extend(files)
    
    # 去重
    video_files = list(set(video_files))
    
    # 排除.part文件
    video_files = [f for f in video_files if not f.name.endswith('.part')]
    
    print()
    print(f"找到 {len(video_files)} 个视频文件:")
    for vf in video_files[:10]:
        print(f"  - {vf}")
    
    if len(video_files) > 10:
        print(f"  ... 还有 {len(video_files) - 10} 个文件")
    
    print()
    
    if not video_files:
        print("未找到视频文件")
        return
    
    # 使用第一个找到的视频文件所在的目录
    video_dir = video_files[0].parent
    print(f"使用视频目录: {video_dir}")
    print()
    
    # 处理视频
    processor = LocalVideoProcessor(video_dir)
    rules_file = processor.process_all_videos()
    
    if rules_file and rules_file.exists():
        print("=" * 80)
        print("处理完成！")
        print("=" * 80)
        print()
        print(f"规则文件: {rules_file}")
        print()
        print("下一步: 运行交易系统生成信号")
        print("  python src/chiba_trading_system/chiba_trading_system.py")
    else:
        print("处理未完成")

if __name__ == '__main__':
    main()








