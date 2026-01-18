#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速处理视频文件 - 简化版
直接处理指定目录的视频
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

def find_video_file():
    """查找视频文件"""
    downloads = Path('C:/Users/zuoho/Downloads')
    video_exts = ['.webm', '.mp4', '.mkv', '.avi', '.mov', '.m4v']
    
    # 查找videoplayback相关文件
    for ext in video_exts:
        # 精确匹配
        files = list(downloads.glob(f'videoplayback{ext}'))
        if files:
            return files[0]
        
        # 包含videoplayback的文件
        files = list(downloads.glob(f'*videoplayback*{ext}'))
        if files:
            return files[0]
        
        # 所有视频文件
        files = [f for f in downloads.iterdir() if f.suffix.lower() == ext and f.is_file()]
        if files:
            return files[0]
    
    return None

def main():
    """主函数"""
    print("=" * 80)
    print("快速处理视频文件")
    print("=" * 80)
    print()
    
    # 查找视频文件
    video_file = find_video_file()
    
    if not video_file:
        print("未找到视频文件")
        print("请确认视频文件在 C:/Users/zuoho/Downloads 目录")
        return
    
    print(f"找到视频文件: {video_file.name}")
    print(f"文件大小: {video_file.stat().st_size / 1024 / 1024:.2f} MB")
    print()
    
    # 导入处理模块
    try:
        from chiba_trading_system.process_local_videos import LocalVideoProcessor
        
        # 使用视频文件所在目录
        processor = LocalVideoProcessor(video_file.parent)
        
        print("开始处理...")
        print()
        
        # 处理视频
        rules_file = processor.process_all_videos()
        
        if rules_file and rules_file.exists():
            print()
            print("=" * 80)
            print("✓ 处理完成！")
            print("=" * 80)
            print()
            print(f"规则文件: {rules_file}")
            print()
            print("下一步: 运行交易系统生成信号")
            print("  python src/chiba_trading_system/chiba_trading_system.py")
        else:
            print("处理未完成")
            
    except Exception as e:
        print(f"处理出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()








