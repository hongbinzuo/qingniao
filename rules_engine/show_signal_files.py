"""
显示所有信号文件的位置和信息
"""

import os
import sys
import io
import glob
from datetime import datetime

# 设置UTF-8编码输出
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def show_signal_files():
    """显示所有信号文件"""
    print("=" * 70)
    print("BTC交易信号文件位置")
    print("=" * 70)
    
    # 获取当前目录
    current_dir = os.getcwd()
    print(f"\n当前工作目录: {current_dir}")
    
    # 查找所有信号文件
    signal_files = glob.glob("BTC_signals_*.md")
    signal_files.sort(key=os.path.getmtime, reverse=True)  # 按修改时间排序
    
    if not signal_files:
        print("\n❌ 未找到信号文件")
        return
    
    print(f"\n找到 {len(signal_files)} 个信号文件:\n")
    
    # 显示最新的5个文件
    for i, filename in enumerate(signal_files[:5], 1):
        filepath = os.path.join(current_dir, filename)
        mtime = os.path.getmtime(filepath)
        size = os.path.getsize(filepath)
        time_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"{i}. {filename}")
        print(f"   路径: {filepath}")
        print(f"   生成时间: {time_str}")
        print(f"   文件大小: {size:,} 字节")
        
        # 读取文件前几行
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()[:5]
                if len(lines) >= 2:
                    print(f"   当前价格: {lines[1].strip() if '价格' in lines[1] else 'N/A'}")
        except:
            pass
        print()
    
    # 显示最新文件
    latest_file = signal_files[0]
    latest_path = os.path.join(current_dir, latest_file)
    print("=" * 70)
    print(f"最新信号文件: {latest_file}")
    print(f"完整路径: {latest_path}")
    print("=" * 70)
    
    # 显示最新文件内容预览
    try:
        with open(latest_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            
            print("\n文件内容预览:")
            print("-" * 70)
            for i, line in enumerate(lines[:30], 1):
                if line.strip():
                    print(f"{i:3d} | {line}")
            
            # 统计信号数量
            signal_count = content.count('**做多**') + content.count('**做空**')
            print(f"\n信号统计: 发现 {signal_count} 个交易信号")
            
    except Exception as e:
        print(f"读取文件失败: {e}")
    
    print("\n" + "=" * 70)
    print("提示: 使用以下命令查看最新文件")
    print(f"  cat {latest_file}")
    print(f"  或直接打开: {latest_path}")
    print("=" * 70)


if __name__ == "__main__":
    show_signal_files()

