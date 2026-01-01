#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速录入De.对话记录
"""

import sys
from datetime import datetime
from pathlib import Path

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from db_manager_trader import TraderDBManager
from de_strategy_extractor import DeStrategyExtractor
from add_user_evaluation import UserEvaluationExtractor
from price_validator import PriceValidator
from file_logger import get_file_logger
from system_logger import get_system_logger

def add_conversation(timestamp_str, trader_message, user_message=None, source='discord', btc_price=None):
    """添加对话记录，自动提取策略信息和用户评价，验证价格合理性"""
    db = TraderDBManager('de')
    extractor = DeStrategyExtractor()
    eval_extractor = UserEvaluationExtractor()
    price_validator = PriceValidator()
    
    # 提取用户评价（从trader_message或user_message中）
    evaluation_info = None
    cleaned_trader_message = trader_message
    cleaned_user_message = user_message
    
    if trader_message:
        eval_result = eval_extractor.extract_and_clean(trader_message)
        if eval_result['has_evaluation']:
            evaluation_info = eval_result
            # 保留原始消息用于交易记录提取，清理后的用于显示
            cleaned_trader_message = eval_result['cleaned_text']
            # 但存储时使用原始消息（包含完整信息）
            stored_trader_message = trader_message
        else:
            stored_trader_message = trader_message
    else:
        stored_trader_message = None
    
    if user_message:
        eval_result = eval_extractor.extract_and_clean(user_message)
        if eval_result['has_evaluation']:
            if evaluation_info:
                # 合并评价
                evaluation_info['evaluations'].extend(eval_result['evaluations'])
                evaluation_info['evaluation_contents'].extend(eval_result['evaluation_contents'])
                evaluation_info['evaluation_text'] = ' | '.join(evaluation_info['evaluation_contents'])
            else:
                evaluation_info = eval_result
            cleaned_user_message = eval_result['cleaned_text']
    
    # 格式化时间
    try:
        # 如果只有时间，补充日期
        if len(timestamp_str) == 5:  # 22:26
            today = datetime.now().strftime('%Y-%m-%d')
            timestamp_str = f"{today} {timestamp_str}:00"
        elif len(timestamp_str) == 8:  # 22:26:00
            today = datetime.now().strftime('%Y-%m-%d')
            timestamp_str = f"{today} {timestamp_str}"
        
        # 尝试解析时间
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y/%m/%d %H:%M:%S',
        ]
        
        timestamp = None
        for fmt in formats:
            try:
                timestamp = datetime.strptime(timestamp_str, fmt).strftime('%Y-%m-%d %H:%M:%S')
                break
            except:
                continue
        
        if not timestamp:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    except:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 验证价格合理性
    price_warnings = []
    system_logger = get_system_logger()
    if cleaned_trader_message:
        price_validations = price_validator.validate_prices_in_text(cleaned_trader_message, timestamp)
        for price_val, is_valid, error_msg in price_validations:
            # 记录价格验证操作
            system_logger.log_price_validation(
                price=price_val,
                timestamp=timestamp,
                is_valid=is_valid,
                price_range=None,  # 可以从error_msg中提取
                suggestion=price_validator.suggest_correction(price_val, timestamp) if not is_valid else None
            )
            
            if not is_valid:
                price_warnings.append(error_msg)
                # 尝试建议修正
                suggested = price_validator.suggest_correction(price_val, timestamp)
                if suggested:
                    price_warnings.append(f"   建议修正为: ${suggested:,.0f}")
    
    # 如果有价格警告，打印但不阻止录入
    if price_warnings:
        print("\n⚠️ 价格验证警告:")
        for warning in price_warnings:
            print(warning)
        print()
    
    # 提取策略信息（使用清理后的文本）
    strategy_info = extractor.extract_strategy_info(cleaned_trader_message)
    
    # 记录策略提取操作
    if strategy_info.get('category') and strategy_info['category'] != 'conversation':
        system_logger.log_strategy_extraction(
            conversation_id=None,  # 将在录入后更新
            strategy_info=strategy_info,
            success=True
        )
    
    # 构建提取内容
    extracted_parts = []
    if strategy_info.get('prices'):
        extracted_parts.append(f"价格: {', '.join([f'${p:,.0f}' for p in strategy_info['prices']])}")
    if strategy_info.get('actions'):
        extracted_parts.append(f"动作: {', '.join(strategy_info['actions'])}")
    if strategy_info.get('strategy'):
        extracted_parts.append(f"策略: {', '.join(strategy_info['strategy'])}")
    if strategy_info.get('concepts'):
        extracted_parts.append(f"概念: {', '.join(strategy_info['concepts'])}")
    
    extracted_content = ' | '.join(extracted_parts) if extracted_parts else None
    
    # 如果没有BTC价格，尝试从策略信息中获取
    if btc_price is None and strategy_info.get('prices'):
        # 使用第一个价格作为参考
        btc_price = strategy_info['prices'][0]
    
    # 准备评价信息
    user_evaluation = evaluation_info['evaluation_text'] if evaluation_info else None
    evaluation_keywords = None
    if evaluation_info and evaluation_info.get('evaluation_contents'):
        # 提取评价中的关键词（简单实现，可以后续增强）
        keywords = []
        for content in evaluation_info['evaluation_contents']:
            # 提取可能的策略关键词
            if any(kw in content for kw in ['策略', '规则', '方法', '技巧', '建议']):
                keywords.append('策略相关')
            if any(kw in content for kw in ['好', '不错', '有效', '成功']):
                keywords.append('正面评价')
            if any(kw in content for kw in ['不好', '无效', '失败', '问题']):
                keywords.append('负面评价')
        evaluation_keywords = ', '.join(keywords) if keywords else None
    
    # 录入对话（使用原始消息，保留完整信息）
    conv_id = db.add_conversation(
        timestamp=timestamp,
        user_message=user_message,  # 使用原始消息
        trader_message=stored_trader_message if 'stored_trader_message' in locals() else trader_message,  # 使用原始消息
        source=source,
        btc_price=btc_price,
        extracted_content=extracted_content,
        user_evaluation=user_evaluation,
        evaluation_keywords=evaluation_keywords
    )
    
    # 更新策略提取日志中的conversation_id
    if strategy_info.get('category') and strategy_info['category'] != 'conversation':
        system_logger.log_strategy_extraction(
            conversation_id=conv_id,
            strategy_info=strategy_info,
            success=True
        )
    
    # 同时保存到文件日志系统（原始对话记录）
    try:
        file_logger = get_file_logger()
        if file_logger and file_logger.available:
            file_logger.log_de_conversation(
                timestamp=timestamp,
                user_message=user_message,
                trader_message=stored_trader_message if 'stored_trader_message' in locals() else trader_message,
                btc_price=btc_price,
                user_evaluation=user_evaluation,
                evaluation_keywords=evaluation_info.get('evaluation_keywords') if evaluation_info else None,
                metadata={
                    'conversation_id': conv_id,
                    'has_trading_info': bool(extracted_content),
                    'extracted_content': extracted_content
                }
            )
    except Exception as e:
        # 文件日志记录失败不影响主流程
        print(f"⚠️ 文件日志记录失败（不影响数据库保存）: {e}", file=sys.stderr)
    
    # 如果有策略信息，同时录入为观点
    if strategy_info.get('category') and strategy_info['category'] != 'conversation':
        category = strategy_info['category']
        tags = strategy_info.get('tags', [])
        
        # 构建观点内容
        viewpoint_content = trader_message
        if strategy_info.get('prices'):
            viewpoint_content += f"\n[价格: {', '.join([f'${p:,.0f}' for p in strategy_info['prices']])}]"
        
        db.add_viewpoint(
            content=viewpoint_content,
            timestamp=timestamp,
            source=source,
            category=category,
            tags=tags,
            btc_price=btc_price,
            related_conversation_id=conv_id
        )
    
    price_validator.close()
    db.close()
    return conv_id, strategy_info, evaluation_info

def add_conversation_simple(timestamp_str, trader_message, user_message=None, source='discord', btc_price=None):
    """添加对话记录（简化版，只返回ID，保持向后兼容）"""
    conv_id, _, _ = add_conversation(timestamp_str, trader_message, user_message, source, btc_price)
    return conv_id

if __name__ == '__main__':
    # 从命令行参数获取
    if len(sys.argv) >= 3:
        timestamp = sys.argv[1]
        message = sys.argv[2]
        source = sys.argv[3] if len(sys.argv) > 3 else 'discord'
        
        conv_id, strategy_info, evaluation_info = add_conversation(timestamp, message, source=source)
        print(f"✓ 对话记录录入成功！ID: {conv_id}")
        
        # 显示提取的策略信息
        if strategy_info.get('category') != 'conversation':
            print(f"\n提取的策略信息:")
            print(f"  分类: {strategy_info['category']}")
            if strategy_info.get('prices'):
                print(f"  价格: {', '.join([f'${p:,.0f}' for p in strategy_info['prices']])}")
            if strategy_info.get('actions'):
                print(f"  动作: {', '.join(strategy_info['actions'])}")
            if strategy_info.get('strategy'):
                print(f"  策略: {', '.join(strategy_info['strategy'])}")
        
        # 显示提取的用户评价
        if evaluation_info and evaluation_info.get('has_evaluation'):
            print(f"\n提取的用户评价:")
            for i, eval_content in enumerate(evaluation_info['evaluation_contents'], 1):
                print(f"  评价{i}: {eval_content}")
    else:
        # 交互式录入
        print("=" * 80)
        print("De.对话记录录入")
        print("=" * 80)
        print()
        
        timestamp = input("时间 (格式: 22:26 或 2025-12-30 22:26:00): ").strip()
        message = input("De.的消息内容: ").strip()
        source = input("来源 (默认: discord): ").strip() or 'discord'
        
        conv_id, strategy_info = add_conversation(timestamp, message, source=source)
        print()
        print("=" * 80)
        print(f"✓ 对话记录录入成功！ID: {conv_id}")
        
        # 显示提取的策略信息
        if strategy_info.get('category') != 'conversation':
            print(f"\n提取的策略信息:")
            print(f"  分类: {strategy_info['category']}")
            if strategy_info.get('prices'):
                print(f"  价格: {', '.join([f'${p:,.0f}' for p in strategy_info['prices']])}")
            if strategy_info.get('actions'):
                print(f"  动作: {', '.join(strategy_info['actions'])}")
            if strategy_info.get('strategy'):
                print(f"  策略: {', '.join(strategy_info['strategy'])}")
        
        # 显示提取的用户评价
        if evaluation_info and evaluation_info.get('has_evaluation'):
            print(f"\n提取的用户评价:")
            for i, eval_content in enumerate(evaluation_info['evaluation_contents'], 1):
                print(f"  评价{i}: {eval_content}")
            if evaluation_keywords:
                print(f"  评价关键词: {evaluation_keywords}")
        print("=" * 80)


