# -*- coding: utf-8 -*-
"""
基于文件的简单日志系统
- 使用JSON Lines格式（.jsonl），每行一个JSON对象
- 按日期分文件，便于管理和清理
- 零外部依赖，只使用Python标准库
- 高效追加写入
"""

import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List
import uuid

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


class FileLogger:
    """基于文件的日志记录器"""
    
    def __init__(self, 
                 log_dir: str = "data/logs",
                 retention_days: int = 90):
        """
        初始化文件日志记录器
        
        Args:
            log_dir: 日志目录，默认'data/logs'
            retention_days: 保留天数，默认90天（3个月）
        """
        self.log_dir = Path(log_dir)
        self.retention_days = retention_days
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.available = True  # 文件系统总是可用的
    
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
        
        # 添加元数据
        log_entry = {
            'id': str(uuid.uuid4()),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'log_type': log_type,
            **data
        }
        
        # 追加写入JSON Lines格式（每行一个JSON对象）
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            return log_entry['id']
        except Exception as e:
            print(f"⚠️ 写入日志失败: {e}", file=sys.stderr)
            return None
    
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
                     raw_data: Optional[Dict] = None) -> Optional[str]:
        """
        记录系统操作日志
        
        Args:
            operation_type: 操作类型（signal_generation, trade_record_add等）
            operation_details: 操作详情
            log_level: 日志级别（info, warning, error）
            timestamp: 时间戳
            btc_price: BTC价格
            raw_data: 原始数据
        
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

