# -*- coding: utf-8 -*-
"""
系统操作日志记录器
统一记录所有关键系统操作到Elasticsearch
"""

import sys
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 使用文件日志系统（简单、高效、零依赖）
try:
    from file_logger import get_file_logger
    FILE_LOGGER_AVAILABLE = True
except ImportError:
    FILE_LOGGER_AVAILABLE = False

# 操作类型定义
OPERATION_TYPES = {
    # 信号相关
    'SIGNAL_GENERATION': 'signal_generation',
    'SIGNAL_EVALUATION': 'signal_evaluation',
    'SIGNAL_TRACKING': 'signal_tracking',
    
    # 交易记录相关
    'TRADE_RECORD_ADD': 'trade_record_add',
    'TRADE_RECORD_EXTRACT': 'trade_record_extract',
    'TRADE_RECORD_UPDATE': 'trade_record_update',
    
    # 数据同步相关
    'PRICE_SYNC': 'price_sync',
    'DATA_SYNC': 'data_sync',
    'DATA_BACKUP': 'data_backup',
    
    # 策略相关
    'STRATEGY_EXTRACTION': 'strategy_extraction',
    'STRATEGY_ANALYSIS': 'strategy_analysis',
    'STRATEGY_QA': 'strategy_qa',
    
    # 价格验证
    'PRICE_VALIDATION': 'price_validation',
    'PRICE_WARNING': 'price_warning',
    
    # 系统配置
    'CONFIG_CHANGE': 'config_change',
    'SYSTEM_STARTUP': 'system_startup',
    'SYSTEM_SHUTDOWN': 'system_shutdown',
    
    # 错误和异常
    'ERROR': 'error',
    'WARNING': 'warning',
    'CRITICAL': 'critical',
    
    # 性能监控
    'PERFORMANCE_METRIC': 'performance_metric',
}


class SystemLogger:
    """系统操作日志记录器"""
    
    def __init__(self):
        self.file_logger = get_file_logger() if FILE_LOGGER_AVAILABLE else None
    
    def log_signal_generation(self,
                              signals_count: int,
                              timeframe: str,
                              system_name: str = 'de',
                              current_price: float = None,
                              details: Dict = None):
        """记录信号生成操作"""
        operation_details = {
            "signals_count": signals_count,
            "timeframe": timeframe,
            "system_name": system_name,
            "current_price": current_price,
            "details": details or {}
        }
        
        if self.file_logger and self.file_logger.available:
            self.file_logger.log_operation(
                operation_type=OPERATION_TYPES['SIGNAL_GENERATION'],
                operation_details=operation_details,
                log_level='info',
                btc_price=current_price
            )
    
    def log_trade_record(self,
                        action: str,  # add, extract, update
                        trade_id: int = None,
                        conversation_id: int = None,
                        details: Dict = None):
        """记录交易记录操作"""
        operation_type_map = {
            'add': OPERATION_TYPES['TRADE_RECORD_ADD'],
            'extract': OPERATION_TYPES['TRADE_RECORD_EXTRACT'],
            'update': OPERATION_TYPES['TRADE_RECORD_UPDATE']
        }
        
        operation_details = {
            "action": action,
            "trade_id": trade_id,
            "conversation_id": conversation_id,
            "details": details or {}
        }
        
        if self.file_logger and self.file_logger.available:
            self.file_logger.log_operation(
                operation_type=operation_type_map.get(action, OPERATION_TYPES['TRADE_RECORD_ADD']),
                operation_details=operation_details,
                log_level='info'
            )
    
    def log_price_sync(self,
                       timeframe: str,
                       records_synced: int,
                       start_time: str = None,
                       end_time: str = None,
                       success: bool = True,
                       error: str = None):
        """记录价格同步操作"""
        operation_details = {
            "timeframe": timeframe,
            "records_synced": records_synced,
            "start_time": start_time,
            "end_time": end_time,
            "success": success,
            "error": error
        }
        
        log_level = 'error' if not success else 'info'
        
        if self.file_logger and self.file_logger.available:
            self.file_logger.log_operation(
                operation_type=OPERATION_TYPES['PRICE_SYNC'],
                operation_details=operation_details,
                log_level=log_level
            )
    
    def log_strategy_extraction(self,
                                conversation_id: int,
                                strategy_info: Dict,
                                success: bool = True):
        """记录策略提取操作"""
        operation_details = {
            "conversation_id": conversation_id,
            "strategy_info": strategy_info,
            "success": success
        }
        
        if self.file_logger and self.file_logger.available:
            self.file_logger.log_operation(
                operation_type=OPERATION_TYPES['STRATEGY_EXTRACTION'],
                operation_details=operation_details,
                log_level='info'
            )
    
    def log_price_validation(self,
                             price: float,
                             timestamp: str,
                             is_valid: bool,
                             price_range: str = None,
                             suggestion: float = None):
        """记录价格验证操作"""
        operation_details = {
            "price": price,
            "timestamp": timestamp,
            "is_valid": is_valid,
            "price_range": price_range,
            "suggestion": suggestion
        }
        
        log_level = 'warning' if not is_valid else 'info'
        operation_type = OPERATION_TYPES['PRICE_WARNING'] if not is_valid else OPERATION_TYPES['PRICE_VALIDATION']
        
        if self.file_logger and self.file_logger.available:
            self.file_logger.log_operation(
                operation_type=operation_type,
                operation_details=operation_details,
                log_level=log_level
            )
    
    def log_error(self,
                  error_type: str,
                  error_message: str,
                  error_details: Dict = None,
                  traceback: str = None):
        """记录错误"""
        operation_details = {
            "error_type": error_type,
            "error_message": error_message,
            "error_details": error_details or {},
            "traceback": traceback
        }
        
        if self.file_logger and self.file_logger.available:
            self.file_logger.log_operation(
                operation_type=OPERATION_TYPES['ERROR'],
                operation_details=operation_details,
                log_level='error'
            )
    
    def log_warning(self,
                   warning_type: str,
                   warning_message: str,
                   warning_details: Dict = None):
        """记录警告"""
        operation_details = {
            "warning_type": warning_type,
            "warning_message": warning_message,
            "warning_details": warning_details or {}
        }
        
        if self.file_logger and self.file_logger.available:
            self.file_logger.log_operation(
                operation_type=OPERATION_TYPES['WARNING'],
                operation_details=operation_details,
                log_level='warning'
            )
    
    def log_performance_metric(self,
                              metric_name: str,
                              metric_value: float,
                              unit: str = None,
                              details: Dict = None):
        """记录性能指标"""
        operation_details = {
            "metric_name": metric_name,
            "metric_value": metric_value,
            "unit": unit,
            "details": details or {}
        }
        
        if self.file_logger and self.file_logger.available:
            self.file_logger.log_operation(
                operation_type=OPERATION_TYPES['PERFORMANCE_METRIC'],
                operation_details=operation_details,
                log_level='info'
            )
    
    def log_custom_operation(self,
                            operation_type: str,
                            operation_details: Dict,
                            log_level: str = 'info',
                            btc_price: float = None):
        """记录自定义操作"""
        if self.file_logger and self.file_logger.available:
            self.file_logger.log_operation(
                operation_type=operation_type,
                operation_details=operation_details,
                log_level=log_level,
                btc_price=btc_price
            )


# 全局实例
_system_logger = None

def get_system_logger() -> SystemLogger:
    """获取全局系统日志记录器实例"""
    global _system_logger
    if _system_logger is None:
        _system_logger = SystemLogger()
    return _system_logger


# 便捷函数
def log_signal_generation(signals_count: int, timeframe: str, **kwargs):
    """记录信号生成"""
    get_system_logger().log_signal_generation(signals_count, timeframe, **kwargs)

def log_trade_record(action: str, **kwargs):
    """记录交易记录操作"""
    get_system_logger().log_trade_record(action, **kwargs)

def log_price_sync(timeframe: str, records_synced: int, **kwargs):
    """记录价格同步"""
    get_system_logger().log_price_sync(timeframe, records_synced, **kwargs)

def log_price_validation(price: float, timestamp: str, is_valid: bool, **kwargs):
    """记录价格验证"""
    get_system_logger().log_price_validation(price, timestamp, is_valid, **kwargs)

def log_error(error_type: str, error_message: str, **kwargs):
    """记录错误"""
    get_system_logger().log_error(error_type, error_message, **kwargs)

def log_warning(warning_type: str, warning_message: str, **kwargs):
    """记录警告"""
    get_system_logger().log_warning(warning_type, warning_message, **kwargs)


if __name__ == '__main__':
    # 测试
    logger = get_system_logger()
    
    print("测试系统操作日志记录...")
    
    # 测试信号生成
    logger.log_signal_generation(
        signals_count=5,
        timeframe='15m',
        system_name='de',
        current_price=88710.0
    )
    print("✓ 信号生成日志已记录")
    
    # 测试交易记录
    logger.log_trade_record(
        action='add',
        trade_id=123,
        details={'entry_price': 88710.0}
    )
    print("✓ 交易记录日志已记录")
    
    # 测试价格同步
    logger.log_price_sync(
        timeframe='5m',
        records_synced=100,
        success=True
    )
    print("✓ 价格同步日志已记录")
    
    # 测试价格验证
    logger.log_price_validation(
        price=81800.0,
        timestamp='2025-12-31 00:23:00',
        is_valid=False,
        price_range='$88,000 - $89,000',
        suggestion=88100.0
    )
    print("✓ 价格验证日志已记录")
    
    print("\n所有测试完成！")

