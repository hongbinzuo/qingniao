#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话日志记录器
自动记录所有用户和AI之间的对话（无论关于什么内容）
同时提取De.观点（如果有）
"""

import uuid
from datetime import datetime, timedelta
from db_config import get_db_manager
from auto_record_de_viewpoints import process_conversation_for_de
# 使用文件日志系统（简单、高效、零依赖）
try:
    from file_logger import get_file_logger
    FILE_LOGGER_AVAILABLE = True
except ImportError:
    FILE_LOGGER_AVAILABLE = False

class ConversationLogger:
    """对话日志记录器"""
    
    def __init__(self, session_id=None):
        self.session_id = session_id or str(uuid.uuid4())
        self.db = get_db_manager()
    
    def log_conversation(self, user_message: str, assistant_message: str = None, 
                        conversation_type: str = 'general', metadata: dict = None):
        """
        记录所有对话（无论关于什么内容）
        
        Args:
            user_message: 用户消息
            assistant_message: AI助手回复
            conversation_type: 对话类型（general/trading/system/strategy等）
            metadata: 额外元数据
        """
        # 提取De.内容（如果有）
        de_contents = process_conversation_for_de(user_message, assistant_message)
        de_content_combined = '\n'.join(de_contents) if de_contents else None
        
        # 记录对话日志（所有对话都记录，不仅仅是De.相关的）
        log_id = self.db.add_conversation_log(
            user_message=user_message,
            assistant_message=assistant_message or '',
            session_id=self.session_id,
            de_content=de_content_combined
        )
        
        # 同时保存到文件日志系统（原始对话记录 - 所有对话都保存）
        if FILE_LOGGER_AVAILABLE:
            try:
                file_logger = get_file_logger()
                if file_logger and file_logger.available:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    # 构建元数据
                    log_metadata = {
                        'log_id': log_id,
                        'conversation_type': conversation_type,
                        'de_content': de_content_combined
                    }
                    if metadata:
                        log_metadata.update(metadata)
                    
                    file_logger.log_conversation(
                        user_message=user_message,
                        assistant_message=assistant_message or '',
                        timestamp=timestamp,
                        session_id=self.session_id,
                        source='user_assistant',
                        conversation_type=conversation_type,
                        metadata=log_metadata
                    )
            except Exception as e:
                # 文件日志记录失败不影响主流程
                pass
        
        # 如果有De.内容，自动记录为观点（可选）
        if de_contents:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            for content in de_contents:
                # 判断类别
                category = None
                if any(kw in content for kw in ['做多', '做空', '多单', '空单', '挂单', '止损', '止盈']):
                    category = 'trading'
                elif any(kw in content for kw in ['分析', '观点', '看法']):
                    category = 'analysis'
                elif any(kw in content for kw in ['指令', '计划', '策略']):
                    category = 'instruction'
                
                self.db.add_de_viewpoint(
                    content=content,
                    timestamp=timestamp,
                    source='conversation',
                    category=category
                )
        
        return log_id, de_contents
    
    def cleanup_old_logs(self, days=90):
        """清理旧日志"""
        return self.db.cleanup_old_logs(days)

# 全局日志记录器实例
_logger = None

def get_logger(session_id=None):
    """获取全局日志记录器"""
    global _logger
    if _logger is None:
        _logger = ConversationLogger(session_id)
    return _logger

def log_conversation(user_message: str, assistant_message: str = None, 
                    session_id: str = None, conversation_type: str = 'general', 
                    metadata: dict = None):
    """
    便捷函数：记录所有对话（无论关于什么内容）
    
    Args:
        user_message: 用户消息
        assistant_message: AI助手回复
        session_id: 会话ID（可选）
        conversation_type: 对话类型（general/trading/system/strategy等）
        metadata: 额外元数据（可选）
    
    Returns:
        (log_id, de_contents)
    """
    logger = get_logger(session_id)
    return logger.log_conversation(user_message, assistant_message, conversation_type, metadata)

