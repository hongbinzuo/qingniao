# -*- coding: utf-8 -*-
"""
统一详细日志初始化模块
所有程序应从此模块导入详细日志功能
自动从 config/logging_config.json 读取配置
"""

import sys
import time
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

try:
    from file_logger import get_file_logger
    from system_logger import get_system_logger
    LOGGING_AVAILABLE = True
except ImportError:
    LOGGING_AVAILABLE = False
    print("⚠️ 日志模块导入失败，将使用基础 print 输出", file=sys.stderr)


class DetailedLogger:
    """详细日志记录器 - 统一接口"""
    
    def __init__(self, script_name: str = None):
        """
        初始化详细日志记录器
        
        Args:
            script_name: 脚本名称（自动从 sys.argv[0] 获取）
        """
        self.script_name = script_name or Path(sys.argv[0]).stem if sys.argv else 'unknown'
        self.file_logger = get_file_logger() if LOGGING_AVAILABLE else None
        self.system_logger = get_system_logger() if LOGGING_AVAILABLE else None
        self.start_time = datetime.now()
        self._operation_start_times = {}
    
    def log_startup(self, args: Dict = None):
        """记录程序启动"""
        cmd_line = ' '.join(sys.argv)
        self.info(f"程序启动: {self.script_name}", {
            'command_line': cmd_line,
            'arguments': args or {},
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S')
        })
        if self.system_logger:
            self.system_logger.log_custom_operation(
                operation_type='system_startup',
                operation_details={
                    'script': self.script_name,
                    'command_line': cmd_line,
                    'arguments': args or {}
                },
                log_level='info'
            )
    
    def log_shutdown(self, exit_code: int = 0):
        """记录程序结束"""
        duration = (datetime.now() - self.start_time).total_seconds()
        self.info(f"程序结束: {self.script_name} (退出码: {exit_code}, 耗时: {duration:.2f}秒)", {
            'exit_code': exit_code,
            'duration_seconds': duration
        })
        if self.system_logger:
            self.system_logger.log_custom_operation(
                operation_type='system_shutdown',
                operation_details={
                    'script': self.script_name,
                    'exit_code': exit_code,
                    'duration_seconds': duration
                },
                log_level='info'
            )
    
    def info(self, message: str, details: Dict = None):
        """记录信息日志"""
        self._log('info', message, details)
    
    def debug(self, message: str, details: Dict = None):
        """记录调试日志"""
        self._log('debug', message, details)
    
    def warning(self, message: str, details: Dict = None):
        """记录警告日志"""
        self._log('warning', message, details)
    
    def error(self, message: str, error: Exception = None, details: Dict = None):
        """记录错误日志"""
        error_details = details or {}
        if error:
            error_details['error_type'] = type(error).__name__
            error_details['error_message'] = str(error)
            import traceback
            error_details['traceback'] = traceback.format_exc()
        
        self._log('error', message, error_details)
        
        if self.system_logger:
            self.system_logger.log_error(
                error_type=error_details.get('error_type', 'Unknown'),
                error_message=message,
                error_details=error_details,
                traceback=error_details.get('traceback')
            )
    
    def progress(self, operation: str, current: int, total: int, message: str = None):
        """记录进度"""
        if self.file_logger and self.file_logger.enable_detailed:
            self.file_logger.log_progress(
                operation_type=operation,
                current=current,
                total=total,
                message=message
            )
        # 同时输出到控制台
        percent = (current / total * 100) if total > 0 else 0
        msg = message or f"{operation}: {current}/{total} ({percent:.1f}%)"
        print(f"[进度] {msg}", flush=True)
    
    def start_operation(self, operation: str):
        """开始计时操作"""
        self._operation_start_times[operation] = datetime.now()
        self.debug(f"开始操作: {operation}")
    
    def end_operation(self, operation: str, success: bool = True, details: Dict = None):
        """结束计时操作"""
        if operation not in self._operation_start_times:
            return
        
        start_time = self._operation_start_times.pop(operation)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if self.file_logger and self.file_logger.enable_timing:
            self.file_logger.log_timing(
                operation_type=operation,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                message=f"{operation} 完成 (耗时: {duration:.3f}秒, 状态: {'成功' if success else '失败'})",
                details=details
            )
        
        status = "✓" if success else "✗"
        print(f"[{status}] {operation}: {duration:.3f}秒", flush=True)
    
    def _log(self, level: str, message: str, details: Dict = None):
        """内部日志方法"""
        if self.file_logger:
            self.file_logger.log_operation(
                operation_type=f"{self.script_name}_{level}",
                operation_details={
                    'message': message,
                    **(details or {})
                },
                log_level=level
            )
        
        # 控制台输出
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        level_marker = {
            'info': 'ℹ',
            'debug': '🔍',
            'warning': '⚠',
            'error': '❌'
        }.get(level, '•')
        print(f"[{timestamp}] [{level_marker}] {message}", flush=True)
        if details:
            print(f"  详情: {details}", flush=True)


# 全局实例
_logger_instance = None

def get_detailed_logger(script_name: str = None) -> DetailedLogger:
    """获取全局详细日志记录器实例"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = DetailedLogger(script_name)
    return _logger_instance


# 便捷函数
def log_info(message: str, details: Dict = None):
    """便捷：记录信息日志"""
    get_detailed_logger().info(message, details)

def log_progress(operation: str, current: int, total: int, message: str = None):
    """便捷：记录进度"""
    get_detailed_logger().progress(operation, current, total, message)

def log_start_operation(operation: str):
    """便捷：开始计时操作"""
    get_detailed_logger().start_operation(operation)

def log_end_operation(operation: str, success: bool = True, details: Dict = None):
    """便捷：结束计时操作"""
    get_detailed_logger().end_operation(operation, success, details)

