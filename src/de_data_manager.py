#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
De.数据管理统一入口
整合对话录入、交易记录录入、策略分析、策略问答等功能
"""

import sys
import argparse
from pathlib import Path

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from add_de_conversation import add_conversation
from de_strategy_analyzer import DeStrategyAnalyzer
from de_strategy_qa import DeStrategyQA, interactive_qa
from de_enhanced_qa import EnhancedDeStrategyQA, interactive_qa as enhanced_interactive_qa
from de_strategy_knowledge_base import DeStrategyKnowledgeBase

# 导入交易记录录入函数
try:
    from add_de_trade_record import add_trade_record_interactive, batch_add_from_text
except ImportError:
    # 如果函数不存在，使用备用方案
    def add_trade_record_interactive():
        print("请使用 python src/add_de_trade_record.py 录入交易记录")
    
    def batch_add_from_text():
        print("请使用 python src/add_de_trade_record.py 批量录入交易记录")

def cmd_add_conversation(args):
    """录入对话命令"""
    if args.message:
        conv_id, strategy_info = add_conversation(
            args.timestamp,
            args.message,
            user_message=args.user_message,
            source=args.source
        )
        print(f"✓ 对话记录录入成功！ID: {conv_id}")
        
        # 显示策略信息
        if strategy_info.get('category') != 'conversation':
            print(f"\n提取的策略信息:")
            print(f"  分类: {strategy_info['category']}")
            if strategy_info.get('prices'):
                print(f"  价格: {', '.join([f'${p:,.0f}' for p in strategy_info['prices']])}")
            if strategy_info.get('actions'):
                print(f"  动作: {', '.join(strategy_info['actions'])}")
            if strategy_info.get('strategy'):
                print(f"  策略: {', '.join(strategy_info['strategy'])}")
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
        if strategy_info.get('category') != 'conversation':
            print(f"\n提取的策略信息:")
            print(f"  分类: {strategy_info['category']}")
            if strategy_info.get('prices'):
                print(f"  价格: {', '.join([f'${p:,.0f}' for p in strategy_info['prices']])}")
            if strategy_info.get('actions'):
                print(f"  动作: {', '.join(strategy_info['actions'])}")
            if strategy_info.get('strategy'):
                print(f"  策略: {', '.join(strategy_info['strategy'])}")
        print("=" * 80)

def cmd_add_trade(args):
    """录入交易记录命令"""
    if args.batch:
        batch_add_from_text()
    else:
        add_trade_record_interactive()

def cmd_analyze_strategy(args):
    """分析策略命令"""
    analyzer = DeStrategyAnalyzer()
    report = analyzer.generate_report(days=args.days, output_file=args.output)
    
    if not args.output:
        print(report)

def cmd_ask_strategy(args):
    """策略问答命令"""
    if args.interactive:
        if args.enhanced:
            enhanced_interactive_qa()
        else:
            interactive_qa()
    elif args.question:
        if args.enhanced:
            qa = EnhancedDeStrategyQA()
            if args.comprehensive:
                import json
                result = qa.get_comprehensive_answer(args.question, days=args.days)
                print("=" * 80)
                print("综合答案（整合规则引擎和ML/DL）")
                print("=" * 80)
                print()
                print(result['base_answer'])
                if result.get('strategy_rules'):
                    print("\n策略规则信息:")
                    print(f"规则: {', '.join(result['strategy_rules'].get('rules', []))}")
                    print(f"概念: {', '.join(result['strategy_rules'].get('concepts', []))}")
            else:
                answer = qa.answer_question(args.question, days=args.days)
                print(answer)
        else:
            qa = DeStrategyQA()
            answer = qa.answer_question(args.question, days=args.days)
            print(answer)
    else:
        print("请提供问题或使用 --interactive 进入交互模式")
        print("示例: python src/de_data_manager.py ask-strategy \"De.最近用了什么策略？\"")
        print("增强版: python src/de_data_manager.py ask-strategy \"FVG策略的规则是什么？\" --enhanced")

def cmd_generate_report(args):
    """生成报告命令"""
    analyzer = DeStrategyAnalyzer()
    output_file = args.output or f"De策略分析报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    report = analyzer.generate_report(days=args.days, output_file=output_file)
    
    if args.output:
        print(f"报告已保存到: {output_file}")
    else:
        print(report)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='De.数据管理统一入口',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例用法:
  # 录入对话
  python src/de_data_manager.py add-conversation "22:26" "摸吧 我挂保本"
  
  # 录入交易记录
  python src/de_data_manager.py add-trade
  
  # 分析策略（最近7天）
  python src/de_data_manager.py analyze-strategy --days 7
  
  # 策略问答
  python src/de_data_manager.py ask-strategy "De.最近用了什么策略？"
  
  # 生成报告
  python src/de_data_manager.py generate-report --days 7 --output report.md
        '''
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # add-conversation 命令
    parser_add_conv = subparsers.add_parser('add-conversation', help='录入对话记录')
    parser_add_conv.add_argument('timestamp', nargs='?', help='时间')
    parser_add_conv.add_argument('message', nargs='?', help='消息内容')
    parser_add_conv.add_argument('--user-message', help='用户消息（可选）')
    parser_add_conv.add_argument('--source', default='discord', help='数据来源（默认: discord）')
    
    # add-trade 命令
    parser_add_trade = subparsers.add_parser('add-trade', help='录入交易记录')
    parser_add_trade.add_argument('--batch', action='store_true', help='批量录入模式')
    
    # analyze-strategy 命令
    parser_analyze = subparsers.add_parser('analyze-strategy', help='分析策略')
    parser_analyze.add_argument('--days', type=int, default=7, help='分析天数（默认7天）')
    parser_analyze.add_argument('--output', help='输出文件路径（可选）')
    
    # ask-strategy 命令
    parser_ask = subparsers.add_parser('ask-strategy', help='策略问答')
    parser_ask.add_argument('question', nargs='?', help='问题文本')
    parser_ask.add_argument('--days', type=int, default=30, help='查询最近N天的数据（默认30天）')
    parser_ask.add_argument('--interactive', action='store_true', help='交互式模式')
    parser_ask.add_argument('--enhanced', action='store_true', help='使用增强版（整合规则引擎和ML/DL）')
    parser_ask.add_argument('--comprehensive', action='store_true', help='显示综合答案（包含规则引擎和ML/DL信息）')
    
    # generate-report 命令
    parser_report = subparsers.add_parser('generate-report', help='生成策略分析报告')
    parser_report.add_argument('--days', type=int, default=7, help='分析天数（默认7天）')
    parser_report.add_argument('--output', help='输出文件路径（可选）')
    
    # build-knowledge-graph 命令
    parser_kg = subparsers.add_parser('build-knowledge-graph', help='构建策略知识图谱')
    parser_kg.add_argument('--output', help='输出文件路径（可选）')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 执行对应命令
    if args.command == 'add-conversation':
        cmd_add_conversation(args)
    elif args.command == 'add-trade':
        cmd_add_trade(args)
    elif args.command == 'analyze-strategy':
        cmd_analyze_strategy(args)
    elif args.command == 'ask-strategy':
        cmd_ask_strategy(args)
    elif args.command == 'generate-report':
        cmd_generate_report(args)
    elif args.command == 'build-knowledge-graph':
        kb = DeStrategyKnowledgeBase()
        output_path = kb.save_knowledge_graph(args.output)
        print(f"✓ 知识图谱已保存到: {output_path}")
    else:
        parser.print_help()

if __name__ == '__main__':
    from datetime import datetime
    main()

