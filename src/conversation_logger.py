#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话日志记录器
自动记录所有对话，并提取De.观点
"""

import uuid
from datetime import datetime, timedelta
from db_config import get_db_manager
from auto_record_de_viewpoints import process_conversation_for_de

class ConversationLogger:
    """对话日志记录器"""
    
    def __init__(self, session_id=None):
        self.session_id = session_id or str(uuid.uuid4())
        self.db = get_db_manager()
    
    def log_conversation(self, user_message: str, assistant_message: str = None):
        """记录对话"""
        # 提取De.内容
        de_contents = process_conversation_for_de(user_message, assistant_message)
        de_content_combined = '\n'.join(de_contents) if de_contents else None
        
        # 记录对话日志
        log_id = self.db.add_conversation_log(
            user_message=user_message,
            assistant_message=assistant_message or '',
            session_id=self.session_id,
            de_content=de_content_combined
        )
        
        # 如果有De.内容，自动记录为观点
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

def log_conversation(user_message: str, assistant_message: str = None, session_id: str = None):
    """便捷函数：记录对话"""
    logger = get_logger(session_id)
    return logger.log_conversation(user_message, assistant_message)

