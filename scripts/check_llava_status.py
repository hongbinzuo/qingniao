#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查 llava 图片模式识别进程状态
使用统一详细日志系统
"""

import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime

# 添加 src 到路径
SRC = Path(__file__).resolve().parent.parent / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from detailed_logger import get_detailed_logger

def check_process_status(pid: int):
    """检查进程状态"""
    logger = get_detailed_logger('check_llava_status')
    logger.log_startup({'pid': pid})
    
    try:
        # Windows: 使用 tasklist 检查进程
        if os.name == 'nt':
            result = subprocess.run(
                ['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV'],
                capture_output=True,
                text=True,
                timeout=5
            )
            is_running = str(pid) in result.stdout
            
            if is_running:
                # 获取详细进程信息
                wmic_result = subprocess.run(
                    ['wmic', 'process', 'where', f'ProcessId={pid}',
                     'get', 'CommandLine,WorkingSetSize,PageFileUsage,KernelModeTime,UserModeTime'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                logger.info(f"进程 {pid} 正在运行", {
                    'pid': pid,
                    'wmic_output': wmic_result.stdout[:500]  # 限制长度
                })
                
                # 解析输出
                lines = [l.strip() for l in wmic_result.stdout.split('\n') if l.strip()]
                if len(lines) > 1:
                    cmd_line = lines[1] if len(lines) > 1 else ''
                    logger.info(f"命令行: {cmd_line[:200]}", {'command_line': cmd_line})
            else:
                logger.warning(f"进程 {pid} 不存在", {'pid': pid})
                return False
        else:
            # Linux/macOS
            result = subprocess.run(
                ['ps', '-p', str(pid), '-o', 'pid,comm,etime,cpu,rss'],
                capture_output=True,
                text=True,
                timeout=5
            )
            is_running = result.returncode == 0
            
            if is_running:
                logger.info(f"进程 {pid} 正在运行", {
                    'pid': pid,
                    'ps_output': result.stdout
                })
            else:
                logger.warning(f"进程 {pid} 不存在", {'pid': pid})
                return False
        
        return is_running
        
    except subprocess.TimeoutExpired:
        logger.error(f"检查进程超时", {'pid': pid})
        return False
    except Exception as e:
        logger.error(f"检查进程失败", error=e, details={'pid': pid})
        return False

def main():
    """主函数"""
    logger = get_detailed_logger('check_llava_status')
    
    # 从命令行获取 PID，或使用默认值
    pid = 24008  # llava 进程的默认 PID
    if len(sys.argv) > 1:
        try:
            pid = int(sys.argv[1])
        except ValueError:
            logger.error(f"无效的 PID: {sys.argv[1]}")
            sys.exit(1)
    
    logger.log_startup({'pid': pid, 'target': 'llava_classify_patterns'})
    
    logger.start_operation('check_process')
    is_running = check_process_status(pid)
    logger.end_operation('check_process', success=is_running)
    
    if is_running:
        # 检查输出文件
        logger.start_operation('check_output_files')
        output_dirs = [
            Path('outputs'),
            Path('data/abu'),
            Path('data/logs')
        ]
        
        found_files = []
        for output_dir in output_dirs:
            if output_dir.exists():
                # 查找最近修改的文件
                for file_path in output_dir.rglob('*'):
                    if file_path.is_file():
                        try:
                            mtime = file_path.stat().st_mtime
                            # 最近24小时内修改的文件
                            if (datetime.now().timestamp() - mtime) < 86400:
                                found_files.append({
                                    'path': str(file_path),
                                    'size': file_path.stat().st_size,
                                    'modified': datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                                })
                        except Exception:
                            pass
        
        if found_files:
            logger.info(f"找到 {len(found_files)} 个最近修改的文件", {
                'file_count': len(found_files),
                'files': found_files[:10]  # 只显示前10个
            })
        else:
            logger.warning("未找到最近24小时内修改的输出文件")
        
        logger.end_operation('check_output_files', success=True)
    
    logger.log_shutdown(exit_code=0 if is_running else 1)
    
    sys.exit(0 if is_running else 1)

if __name__ == '__main__':
    main()



