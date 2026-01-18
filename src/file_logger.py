# -*- coding: utf-8 -*-
"""
基于文件的简单日志系统
- 使用JSON Lines格式（.jsonl），每行一个JSON对象
- 按日期分文件，便于管理和清理
- 零外部依赖，只使用Python标准库
- 高效追加写入
- 支持详细日志配置（从 config/logging_config.json 读取）
"""

import sys
import json
import os
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List
import uuid

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 读取日志配置
_logging_config = None

def _load_logging_config() -> Dict:
    """加载日志配置文件"""
    global _logging_config
    if _logging_config is not None:
        return _logging_config
    
    config_file = Path(__file__).parent.parent / "config" / "logging_config.json"
    default_config = {
        "log_level": "DEBUG",
        "log_dir": "data/logs",
        "retention_days": 90,
        "enable_file_logging": True,
        "enable_console_logging": True,
        "enable_detailed_progress": True,
        "enable_timing": True,
        "enable_performance_metrics": True,
        "console_format": "detailed",
        "file_format": "jsonl",
        "log_process_info": True,
        "log_command_line": True,
        "log_environment": False,
        "log_stderr": True,
    }
    
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                _logging_config = json.load(f)
                # 合并默认配置，确保所有字段都存在
                for key, value in default_config.items():
                    if key not in _logging_config:
                        _logging_config[key] = value
        except Exception as e:
            print(f"⚠️ 读取日志配置失败: {e}，使用默认配置", file=sys.stderr)
            _logging_config = default_config
    else:
        _logging_config = default_config
    
    return _logging_config

def _get_logging_config() -> Dict:
    """获取日志配置"""
    return _load_logging_config()


class FileLogger:
    """基于文件的日志记录器"""
    
    def __init__(self, 
                 log_dir: str = None,
                 retention_days: int = None):
        """
        初始化文件日志记录器
        
        Args:
            log_dir: 日志目录，默认从配置文件读取
            retention_days: 保留天数，默认从配置文件读取
        """
        config = _get_logging_config()
        self.log_dir = Path(log_dir or config.get('log_dir', 'data/logs'))
        self.retention_days = retention_days or config.get('retention_days', 90)
        self.config = config
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.available = True  # 文件系统总是可用的
        self.enable_detailed = config.get('enable_detailed_progress', True)
        self.enable_timing = config.get('enable_timing', True)
        self.enable_performance = config.get('enable_performance_metrics', True)
        self.log_process_info = config.get('log_process_info', True)
        self.log_command_line = config.get('log_command_line', True)
    
    def _get_log_file_path(self, date: datetime = None) -> Path:
        """获取指定日期的日志文件路径"""
        if date is None:
            date = datetime.now()
        date_str = date.strftime('%Y%m%d')
        return self.log_dir / f"logs_{date_str}.jsonl"
    
    def _write_log(self, log_type: str, data: Dict) -> Optional[str]:
        """
        写入日志到文件
        
        Args:
            log_type: 日志类型（conversation, operation, etc.）
            data: 日志数据字典
        
        Returns:
            日志ID（UUID字符串）
        """
        log_file = self._get_log_file_path()
        now = datetime.now()
        
        # 添加元数据
        log_entry = {
            'id': str(uuid.uuid4()),
            'timestamp': now.strftime('%Y-%m-%d %H:%M:%S'),
            'log_type': log_type,
            **data
        }
        
        # 如果启用详细日志，添加进程信息
        if self.log_process_info:
            try:
                import psutil
                process = psutil.Process()
                log_entry['process_info'] = {
                    'pid': process.pid,
                    'cpu_percent': process.cpu_percent(interval=0.1),
                    'memory_mb': process.memory_info().rss / 1024 / 1024,
                }
            except (ImportError, Exception):
                pass  # psutil 不可用时跳过
        
        # 如果启用命令行记录
        if self.log_command_line:
            try:
                import sys
                log_entry['command_line'] = ' '.join(sys.argv)
            except Exception:
                pass
        
        # 追加写入JSON Lines格式（每行一个JSON对象）
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            
            # 同时输出到控制台（如果启用）
            if self.config.get('enable_console_logging', True):
                self._console_log(log_entry)
            
            return log_entry['id']
        except Exception as e:
            print(f"⚠️ 写入日志失败: {e}", file=sys.stderr)
            return None
    
    def _console_log(self, log_entry: Dict):
        """输出到控制台（格式化输出）"""
        if not self.config.get('enable_console_logging', True):
            return
        
        format_type = self.config.get('console_format', 'simple')
        timestamp = log_entry.get('timestamp', '')
        log_type = log_entry.get('log_type', '')
        
        if format_type == 'detailed':
            level = log_entry.get('log_level', 'INFO').upper()
            operation_type = log_entry.get('operation_type', '')
            message = log_entry.get('operation_details', {}).get('message', '')
            if not message:
                message = json.dumps(log_entry.get('operation_details', {}), ensure_ascii=False)
            print(f"[{timestamp}] [{level}] [{log_type}] {operation_type}: {message}", flush=True)
        else:
            # 简单格式
            operation_type = log_entry.get('operation_type', '')
            message = log_entry.get('operation_details', {}).get('message', '')
            print(f"[{timestamp}] [{log_type}] {operation_type}: {message}", flush=True)
    
    def log_conversation(self,
                        user_message: str,
                        assistant_message: str,
                        timestamp: str = None,
                        session_id: Optional[str] = None,
                        source: str = 'user_assistant',
                        conversation_type: str = 'general',
                        metadata: Optional[Dict] = None) -> Optional[str]:
        """
        记录对话日志
        
        Args:
            user_message: 用户消息
            assistant_message: 助手回复
            timestamp: 时间戳（格式：YYYY-MM-DD HH:MM:SS），默认当前时间
            session_id: 会话ID
            source: 来源，默认'user_assistant'
            conversation_type: 对话类型（general, trading, system等）
            metadata: 额外元数据
        
        Returns:
            日志ID
        """
        data = {
            'user_message': user_message,
            'assistant_message': assistant_message,
            'source': source,
            'conversation_type': conversation_type,
        }
        
        if session_id:
            data['session_id'] = session_id
        if timestamp:
            data['timestamp'] = timestamp
        if metadata:
            data['metadata'] = metadata
        
        return self._write_log('conversation', data)
    
    def log_de_conversation(self,
                           timestamp: str,
                           user_message: str,
                           trader_message: str,
                           btc_price: Optional[float] = None,
                           user_evaluation: Optional[str] = None,
                           evaluation_keywords: Optional[str] = None,
                           metadata: Optional[Dict] = None) -> Optional[str]:
        """
        记录De.交易员的对话
        
        Args:
            timestamp: 时间戳
            user_message: 用户消息
            trader_message: 交易员消息
            btc_price: BTC价格
            user_evaluation: 用户评价
            evaluation_keywords: 评价关键词
            metadata: 额外元数据
        
        Returns:
            日志ID
        """
        data = {
            'user_message': user_message,
            'trader_message': trader_message,
            'source': 'de_trader',
            'conversation_type': 'trading',
            'btc_price': btc_price,
        }
        
        if user_evaluation:
            data['user_evaluation'] = user_evaluation
        if evaluation_keywords:
            data['evaluation_keywords'] = evaluation_keywords
        if metadata:
            data['metadata'] = metadata
        
        return self._write_log('de_conversation', data)
    
    def log_operation(self,
                     operation_type: str,
                     operation_details: Dict,
                     log_level: str = 'info',
                     timestamp: str = None,
                     btc_price: Optional[float] = None,
                     raw_data: Optional[Dict] = None,
                     timing: Optional[Dict] = None,
                     progress: Optional[Dict] = None) -> Optional[str]:
        """
        记录系统操作日志
        
        Args:
            operation_type: 操作类型（signal_generation, trade_record_add等）
            operation_details: 操作详情
            log_level: 日志级别（info, warning, error）
            timestamp: 时间戳
            btc_price: BTC价格
            raw_data: 原始数据
            timing: 时间统计 {'start_time': ..., 'end_time': ..., 'duration': ...}
            progress: 进度信息 {'current': ..., 'total': ..., 'percent': ...}
        
        Returns:
            日志ID
        """
        data = {
            'operation_type': operation_type,
            'operation_details': operation_details,
            'log_level': log_level,
            'btc_price': btc_price,
        }
        
        if timestamp:
            data['timestamp'] = timestamp
        if raw_data:
            data['raw_data'] = raw_data
        
        # 添加时间统计
        if self.enable_timing and timing:
            data['timing'] = timing
        
        # 添加进度信息
        if self.enable_detailed and progress:
            data['progress'] = progress
        
        return self._write_log('operation', data)
    
    def search(self, 
               query: str = None,
               log_type: str = None,
               start_date: datetime = None,
               end_date: datetime = None,
               limit: int = 100) -> List[Dict]:
        """
        搜索日志
        
        Args:
            query: 搜索关键词（在消息内容中搜索）
            log_type: 日志类型过滤
            start_date: 开始日期
            end_date: 结束日期
            limit: 返回结果数量限制
        
        Returns:
            日志条目列表
        """
        results = []
        
        # 确定要搜索的日期范围
        if start_date is None:
            start_date = datetime.now() - timedelta(days=self.retention_days)
        if end_date is None:
            end_date = datetime.now()
        
        # 遍历日期范围内的所有日志文件
        current_date = start_date
        while current_date <= end_date:
            log_file = self._get_log_file_path(current_date)
            compressed_file = log_file.with_suffix('.jsonl.gz')
            
            # 优先查找压缩文件，如果没有则查找原始文件
            file_to_read = None
            is_compressed = False
            temp_file = None
            
            if compressed_file.exists():
                file_to_read = compressed_file
                is_compressed = True
            elif log_file.exists():
                file_to_read = log_file
                is_compressed = False
            
            if file_to_read:
                try:
                    if is_compressed:
                        # 解压到临时文件
                        temp_file = self._decompress_log_file(file_to_read)
                        if not temp_file:
                            current_date += timedelta(days=1)
                            continue
                        read_file = temp_file
                    else:
                        read_file = file_to_read
                    
                    with open(read_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            
                            try:
                                entry = json.loads(line)
                                
                                # 类型过滤
                                if log_type and entry.get('log_type') != log_type:
                                    continue
                                
                                # 关键词搜索
                                if query:
                                    query_lower = query.lower()
                                    found = False
                                    
                                    # 搜索各个文本字段
                                    for field in ['user_message', 'assistant_message', 'trader_message', 
                                                 'operation_type', 'operation_details']:
                                        if field in entry:
                                            value = str(entry[field])
                                            if query_lower in value.lower():
                                                found = True
                                                break
                                    
                                    if not found:
                                        continue
                                
                                results.append(entry)
                                
                                if len(results) >= limit:
                                    # 清理临时文件
                                    if temp_file and temp_file.exists():
                                        temp_file.unlink()
                                    return results[:limit]
                                    
                            except json.JSONDecodeError:
                                continue  # 跳过无效行
                    
                    # 清理临时文件
                    if temp_file and temp_file.exists():
                        temp_file.unlink()
                                
                except Exception as e:
                    print(f"⚠️ 读取日志文件失败 {file_to_read}: {e}", file=sys.stderr)
                    # 确保清理临时文件
                    if temp_file and temp_file.exists():
                        temp_file.unlink()
            
            current_date += timedelta(days=1)
        
        return results[:limit]
    
    def _get_date_from_filename(self, filename: str) -> Optional[datetime]:
        """从文件名提取日期"""
        try:
            # 处理 logs_20250101.jsonl 或 logs_20250101.jsonl.gz
            base_name = filename.replace('.gz', '').replace('.jsonl', '')
            date_str = base_name.split('_')[1]  # logs_20250101 -> 20250101
            return datetime.strptime(date_str, '%Y%m%d')
        except (ValueError, IndexError):
            return None
    
    def _compress_log_file(self, log_file: Path) -> bool:
        """
        压缩日志文件
        
        Args:
            log_file: 日志文件路径
        
        Returns:
            是否成功压缩
        """
        compressed_file = log_file.with_suffix('.jsonl.gz')
        try:
            with open(log_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            log_file.unlink()  # 删除原文件
            return True
        except Exception as e:
            print(f"⚠️ 压缩日志文件失败 {log_file}: {e}", file=sys.stderr)
            return False
    
    def _decompress_log_file(self, compressed_file: Path) -> Optional[Path]:
        """
        解压日志文件（临时解压，用于读取）
        
        Args:
            compressed_file: 压缩文件路径
        
        Returns:
            临时解压文件路径，或None
        """
        temp_file = compressed_file.with_suffix('.jsonl.tmp')
        try:
            with gzip.open(compressed_file, 'rb') as f_in:
                with open(temp_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            return temp_file
        except Exception as e:
            print(f"⚠️ 解压日志文件失败 {compressed_file}: {e}", file=sys.stderr)
            return None
    
    def compress_old_logs(self) -> int:
        """
        压缩1个月之前的日志文件
        
        Returns:
            压缩的文件数量
        """
        one_month_ago = datetime.now() - timedelta(days=30)
        compressed_count = 0
        
        for log_file in self.log_dir.glob('logs_*.jsonl'):
            # 跳过已压缩的文件和临时文件
            if log_file.name.endswith('.gz') or log_file.name.endswith('.tmp'):
                continue
            
            file_date = self._get_date_from_filename(log_file.name)
            if file_date and file_date < one_month_ago:
                if self._compress_log_file(log_file):
                    compressed_count += 1
        
        return compressed_count
    
    def cleanup_old_logs(self, days: int = None) -> int:
        """
        清理超过保留期限的日志文件（包括压缩文件）
        
        Args:
            days: 保留天数，默认使用retention_days（3个月）
        
        Returns:
            删除的文件数量
        """
        if days is None:
            days = self.retention_days
        
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_count = 0
        
        # 删除超过期限的原始文件和压缩文件
        for log_file in self.log_dir.glob('logs_*'):
            # 跳过临时文件
            if log_file.name.endswith('.tmp'):
                continue
            
            file_date = self._get_date_from_filename(log_file.name)
            if file_date and file_date < cutoff_date:
                try:
                    log_file.unlink()
                    deleted_count += 1
                except Exception as e:
                    print(f"⚠️ 删除日志文件失败 {log_file}: {e}", file=sys.stderr)
        
        return deleted_count
    
    def maintain_logs(self) -> Dict[str, int]:
        """
        维护日志：压缩旧日志，清理过期日志
        
        Returns:
            维护统计信息
        """
        compressed = self.compress_old_logs()
        deleted = self.cleanup_old_logs()
        
        return {
            'compressed': compressed,
            'deleted': deleted
        }
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        stats = {
            'available': True,
            'log_dir': str(self.log_dir),
            'retention_days': self.retention_days,
            'total_files': 0,
            'total_entries': 0,
            'oldest_date': None,
            'newest_date': None,
        }
        
        # 统计所有日志文件（包括压缩文件）
        log_files = list(self.log_dir.glob('logs_*'))
        # 过滤掉临时文件
        log_files = [f for f in log_files if not f.name.endswith('.tmp')]
        stats['total_files'] = len(log_files)
        
        if log_files:
            dates = []
            for log_file in log_files:
                file_date = self._get_date_from_filename(log_file.name)
                if file_date:
                    dates.append(file_date)
                    
                    # 统计文件中的行数
                    try:
                        if log_file.name.endswith('.gz'):
                            # 压缩文件
                            with gzip.open(log_file, 'rt', encoding='utf-8') as f:
                                stats['total_entries'] += sum(1 for line in f if line.strip())
                        else:
                            # 原始文件
                            with open(log_file, 'r', encoding='utf-8') as f:
                                stats['total_entries'] += sum(1 for line in f if line.strip())
                    except Exception:
                        pass
            
            if dates:
                stats['oldest_date'] = min(dates).strftime('%Y-%m-%d')
                stats['newest_date'] = max(dates).strftime('%Y-%m-%d')
        
        return stats
    
    def log_progress(self,
                    operation_type: str,
                    current: int,
                    total: int,
                    message: str = None,
                    details: Dict = None) -> Optional[str]:
        """
        记录进度信息（详细日志）
        
        Args:
            operation_type: 操作类型
            current: 当前进度
            total: 总数
            message: 进度消息
            details: 额外详情
        
        Returns:
            日志ID
        """
        percent = (current / total * 100) if total > 0 else 0
        progress_info = {
            'current': current,
            'total': total,
            'percent': round(percent, 2),
        }
        if message:
            progress_info['message'] = message
        
        operation_details = {
            'message': message or f"进度: {current}/{total} ({percent:.1f}%)",
            **(details or {})
        }
        
        return self.log_operation(
            operation_type=operation_type,
            operation_details=operation_details,
            log_level='info',
            progress=progress_info
        )
    
    def log_timing(self,
                  operation_type: str,
                  start_time: datetime,
                  end_time: datetime = None,
                  duration_seconds: float = None,
                  message: str = None,
                  details: Dict = None) -> Optional[str]:
        """
        记录时间统计（详细日志）
        
        Args:
            operation_type: 操作类型
            start_time: 开始时间
            end_time: 结束时间（可选）
            duration_seconds: 持续时间（秒，可选）
            message: 消息
            details: 额外详情
        
        Returns:
            日志ID
        """
        if end_time is None:
            end_time = datetime.now()
        if duration_seconds is None:
            duration_seconds = (end_time - start_time).total_seconds()
        
        timing_info = {
            'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
            'end_time': end_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
            'duration_seconds': round(duration_seconds, 3),
        }
        
        operation_details = {
            'message': message or f"耗时: {duration_seconds:.3f}秒",
            **(details or {})
        }
        
        return self.log_operation(
            operation_type=operation_type,
            operation_details=operation_details,
            log_level='info',
            timing=timing_info
        )


# 全局实例
_file_logger = None

def get_file_logger() -> FileLogger:
    """获取全局文件日志记录器实例"""
    global _file_logger
    if _file_logger is None:
        _file_logger = FileLogger()
    return _file_logger


if __name__ == '__main__':
    # 测试
    logger = get_file_logger()
    
    print("=" * 60)
    print("文件日志系统测试")
    print("=" * 60)
    print()
    
    # 测试记录对话
    print("1. 测试记录对话...")
    doc_id = logger.log_conversation(
        user_message="测试消息",
        assistant_message="测试回复",
        conversation_type='test'
    )
    print(f"   ✓ 记录成功，日志ID: {doc_id}")
    
    # 测试记录操作
    print("\n2. 测试记录操作...")
    op_id = logger.log_operation(
        operation_type='test_operation',
        operation_details={'test': 'data'},
        log_level='info'
    )
    print(f"   ✓ 记录成功，日志ID: {op_id}")
    
    # 测试搜索
    print("\n3. 测试搜索...")
    results = logger.search(query='测试', limit=5)
    print(f"   ✓ 找到 {len(results)} 条记录")
    
    # 统计信息
    print("\n4. 统计信息:")
    stats = logger.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

