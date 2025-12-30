# -*- coding: utf-8 -*-
"""
通用对话日志记录器
记录所有用户和AI之间的对话，无论关于什么内容
这是一个装饰器和中间件，可以在任何地方使用
"""

import sys
import functools
from datetime import datetime
from typing import Callable, Optional, Dict, Any

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

try:
    from conversation_logger import log_conversation
    LOGGER_AVAILABLE = True
except ImportError:
    LOGGER_AVAILABLE = False
    print("⚠️ 警告: conversation_logger未找到，对话将不会被记录", file=sys.stderr)


def log_all_conversations(conversation_type: str = 'general', 
                         auto_detect_type: bool = True):
    """
    装饰器：自动记录所有对话
    
    Args:
        conversation_type: 对话类型（general/trading/system/strategy/de等）
        auto_detect_type: 是否自动检测对话类型
    
    Usage:
        @log_all_conversations(conversation_type='system')
        def my_function(user_input: str) -> str:
            response = process(user_input)
            return response
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 尝试从参数中提取用户消息和助手回复
            user_message = None
            assistant_message = None
            
            # 从位置参数提取
            if args:
                user_message = str(args[0]) if len(args) > 0 else None
            
            # 从关键字参数提取
            if 'user_message' in kwargs:
                user_message = kwargs['user_message']
            elif 'user_input' in kwargs:
                user_message = kwargs['user_input']
            elif 'query' in kwargs:
                user_message = kwargs['query']
            elif 'question' in kwargs:
                user_message = kwargs['question']
            
            if 'assistant_message' in kwargs:
                assistant_message = kwargs['assistant_message']
            elif 'response' in kwargs:
                assistant_message = kwargs['response']
            elif 'answer' in kwargs:
                assistant_message = kwargs['answer']
            
            # 自动检测对话类型
            detected_type = conversation_type
            if auto_detect_type and user_message:
                user_msg_lower = user_message.lower()
                if any(kw in user_msg_lower for kw in ['de.', '交易', '策略', '信号']):
                    detected_type = 'trading'
                elif any(kw in user_msg_lower for kw in ['系统', '配置', '设置']):
                    detected_type = 'system'
                elif any(kw in user_msg_lower for kw in ['错误', 'bug', '问题']):
                    detected_type = 'error'
                elif any(kw in user_msg_lower for kw in ['日志', '记录']):
                    detected_type = 'logging'
            
            # 执行原函数
            try:
                result = func(*args, **kwargs)
                
                # 如果结果是字符串，作为助手回复
                if isinstance(result, str) and not assistant_message:
                    assistant_message = result
                
                # 记录对话
                if LOGGER_AVAILABLE and user_message:
                    try:
                        log_conversation(
                            user_message=user_message,
                            assistant_message=assistant_message,
                            conversation_type=detected_type,
                            metadata={
                                'function': func.__name__,
                                'module': func.__module__
                            }
                        )
                    except Exception as e:
                        # 记录失败不影响主流程
                        print(f"⚠️ 对话记录失败: {e}", file=sys.stderr)
                
                return result
            except Exception as e:
                # 如果函数执行出错，也记录错误对话
                if LOGGER_AVAILABLE and user_message:
                    try:
                        log_conversation(
                            user_message=user_message,
                            assistant_message=f"[错误] {str(e)}",
                            conversation_type='error',
                            metadata={
                                'function': func.__name__,
                                'module': func.__module__,
                                'error': str(e)
                            }
                        )
                    except:
                        pass
                raise
        
        return wrapper
    return decorator


class UniversalConversationLogger:
    """通用对话日志记录器（中间件模式）"""
    
    def __init__(self, session_id: str = None):
        self.session_id = session_id
    
    def log(self, user_message: str, assistant_message: str = None,
           conversation_type: str = 'general', metadata: Dict[str, Any] = None):
        """
        记录对话
        
        Args:
            user_message: 用户消息
            assistant_message: AI助手回复
            conversation_type: 对话类型
            metadata: 额外元数据
        """
        if not LOGGER_AVAILABLE:
            return None
        
        try:
            return log_conversation(
                user_message=user_message,
                assistant_message=assistant_message,
                session_id=self.session_id,
                conversation_type=conversation_type,
                metadata=metadata
            )
        except Exception as e:
            print(f"⚠️ 对话记录失败: {e}", file=sys.stderr)
            return None
    
    def log_system_operation(self, operation: str, details: str = None, 
                            success: bool = True):
        """记录系统操作对话"""
        user_msg = f"[系统操作] {operation}"
        assistant_msg = f"{'成功' if success else '失败'}: {details}" if details else None
        
        return self.log(
            user_message=user_msg,
            assistant_message=assistant_msg,
            conversation_type='system',
            metadata={
                'operation': operation,
                'success': success,
                'details': details
            }
        )
    
    def log_error(self, error_type: str, error_message: str, 
                 user_context: str = None):
        """记录错误对话"""
        user_msg = user_context or f"[错误] {error_type}"
        assistant_msg = f"错误: {error_message}"
        
        return self.log(
            user_message=user_msg,
            assistant_message=assistant_msg,
            conversation_type='error',
            metadata={
                'error_type': error_type,
                'error_message': error_message
            }
        )


# 全局实例
_global_logger = None

def get_global_logger(session_id: str = None) -> UniversalConversationLogger:
    """获取全局对话日志记录器"""
    global _global_logger
    if _global_logger is None:
        _global_logger = UniversalConversationLogger(session_id)
    return _global_logger


# 便捷函数
def log_user_assistant_conversation(user_message: str, assistant_message: str,
                                   conversation_type: str = 'general'):
    """
    便捷函数：记录用户和AI的对话
    
    Usage:
        log_user_assistant_conversation(
            "如何生成BTC信号？",
            "使用 generate_btc_de_signals.py 脚本...",
            conversation_type='trading'
        )
    """
    if LOGGER_AVAILABLE:
        return log_conversation(
            user_message=user_message,
            assistant_message=assistant_message,
            conversation_type=conversation_type
        )
    return None


if __name__ == '__main__':
    # 测试
    print("=" * 80)
    print("通用对话日志记录器测试")
    print("=" * 80)
    print()
    
    # 测试记录一般对话
    print("1. 记录一般对话")
    log_user_assistant_conversation(
        "你好，这个系统怎么用？",
        "这是一个交易系统，你可以...",
        conversation_type='general'
    )
    print("✓ 已记录一般对话")
    print()
    
    # 测试记录交易相关对话
    print("2. 记录交易相关对话")
    log_user_assistant_conversation(
        "如何生成BTC交易信号？",
        "使用 generate_btc_de_signals.py 脚本可以生成BTC交易信号...",
        conversation_type='trading'
    )
    print("✓ 已记录交易相关对话")
    print()
    
    # 测试记录系统操作对话
    print("3. 记录系统操作对话")
    logger = get_global_logger()
    logger.log_system_operation(
        "价格数据同步",
        "成功同步了100条记录",
        success=True
    )
    print("✓ 已记录系统操作对话")
    print()
    
    # 测试记录错误对话
    print("4. 记录错误对话")
    logger.log_error(
        "API错误",
        "无法连接到交易所API",
        "尝试获取BTC价格时出错"
    )
    print("✓ 已记录错误对话")
    print()
    
    print("=" * 80)
    print("所有测试完成！")
    print("=" * 80)

