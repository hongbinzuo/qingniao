#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从转录文本中提取交易规则并总结精华
"""

import sys
from pathlib import Path
import json
from datetime import datetime
import re

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))


class RuleExtractor:
    """规则提取器"""
    
    def __init__(self):
        self.transcripts_dir = Path(__file__).parent.parent.parent / "data" / "chiba_videos" / "transcripts"
        self.rules_dir = Path(__file__).parent.parent.parent / "data" / "chiba_videos" / "rules"
        self.rules_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_rules_from_text(self, text: str, video_name: str = "") -> dict:
        """从文本中提取交易规则"""
        rules = {
            'entry_conditions': [],
            'stop_loss_rules': [],
            'take_profit_rules': [],
            'risk_management': [],
            'indicators': [],
            'patterns': [],
            'market_analysis': [],
            'key_points': []
        }
        
        # 交易关键词模式
        patterns = {
            'entry': [
                r'入场|开仓|买入|卖出|做多|做空|entry|buy|sell|long|short',
                r'突破|回调|反弹|支撑|阻力|support|resistance|breakout|pullback',
                r'进场|建仓|开多|开空'
            ],
            'stop_loss': [
                r'止损|stop\s*loss|sl|止损点|stop',
                r'(\d+(?:\.\d+)?)\s*%?\s*止损',
                r'止损.*?(\d+(?:\.\d+)?)\s*%?',
                r'亏损.*?(\d+(?:\.\d+)?)\s*%?'
            ],
            'take_profit': [
                r'止盈|take\s*profit|tp|目标|止盈点|profit',
                r'(\d+(?:\.\d+)?)\s*%?\s*止盈',
                r'止盈.*?(\d+(?:\.\d+)?)\s*%?',
                r'目标.*?(\d+(?:\.\d+)?)\s*%?',
                r'盈利.*?(\d+(?:\.\d+)?)\s*%?'
            ],
            'risk': [
                r'风险|仓位|资金管理|risk|position|资金|仓位管理',
                r'(\d+(?:\.\d+)?)\s*%?\s*仓位',
                r'风险.*?(\d+(?:\.\d+)?)\s*%?',
                r'仓位.*?(\d+(?:\.\d+)?)\s*%?'
            ],
            'indicator': [
                r'均线|MA|EMA|SMA|MACD|RSI|指标|moving\s*average',
                r'(\d+)\s*日均线|(\d+)\s*日MA',
                r'金叉|死叉|golden\s*cross|death\s*cross',
                r'布林|bollinger|KDJ|BOLL'
            ],
            'pattern': [
                r'形态|双顶|双底|头肩|三角形|pattern|突破|回调',
                r'M顶|W底|头肩顶|头肩底',
                r'FVG|order\s*block|OTE',
                r'缺口|跳空'
            ],
            'market': [
                r'BTC|比特币|bitcoin|黄金|gold|白银|silver|XAU|XAG',
                r'看涨|看跌|bullish|bearish|上涨|下跌',
                r'趋势|trend|上升趋势|下降趋势|牛市|熊市'
            ]
        }
        
        # 按句子分割文本
        sentences = re.split(r'[。！？\n]', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 5:  # 太短的句子跳过
                continue
            
            # 检查每个规则类型
            for rule_type, pattern_list in patterns.items():
                for pattern in pattern_list:
                    if re.search(pattern, sentence, re.IGNORECASE):
                        rule_entry = {
                            'text': sentence,
                            'pattern_matched': pattern
                        }
                        
                        # 提取数字
                        numbers = re.findall(r'\d+(?:\.\d+)?', sentence)
                        if numbers:
                            rule_entry['numbers'] = [float(n) for n in numbers]
                        
                        # 分类
                        if rule_type == 'entry':
                            rules['entry_conditions'].append(rule_entry)
                        elif rule_type == 'stop_loss':
                            rules['stop_loss_rules'].append(rule_entry)
                        elif rule_type == 'take_profit':
                            rules['take_profit_rules'].append(rule_entry)
                        elif rule_type == 'risk':
                            rules['risk_management'].append(rule_entry)
                        elif rule_type == 'indicator':
                            rules['indicators'].append(rule_entry)
                        elif rule_type == 'pattern':
                            rules['patterns'].append(rule_entry)
                        elif rule_type == 'market':
                            rules['market_analysis'].append(rule_entry)
                        
                        break
        
        # 去重
        for key in rules:
            seen = set()
            unique_rules = []
            for rule in rules[key]:
                text_key = rule['text'][:50]
                if text_key not in seen:
                    seen.add(text_key)
                    unique_rules.append(rule)
            rules[key] = unique_rules
        
        return rules
    
    def summarize_key_points(self, text: str) -> list:
        """总结关键要点"""
        key_points = []
        
        # 查找重要关键词
        important_keywords = [
            r'重要|关键|注意|提醒|建议|推荐',
            r'必须|一定|务必|切记',
            r'不要|不能|避免|禁止',
            r'策略|方法|技巧|原则'
        ]
        
        sentences = re.split(r'[。！？\n]', text)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
            
            for keyword in important_keywords:
                if re.search(keyword, sentence, re.IGNORECASE):
                    key_points.append(sentence)
                    break
        
        # 限制数量
        return key_points[:20]
    
    def process_all_transcripts(self):
        """处理所有转录文件"""
        print("=" * 80)
        print("提取交易规则")
        print("=" * 80)
        print()
        
        # 查找所有转录文本文件
        transcript_files = list(self.transcripts_dir.glob("*.txt"))
        
        if not transcript_files:
            print("未找到转录文件")
            print(f"请确保转录文件在: {self.transcripts_dir}")
            return None
        
        print(f"找到 {len(transcript_files)} 个转录文件")
        print()
        
        all_rules = {
            'entry_conditions': [],
            'stop_loss_rules': [],
            'take_profit_rules': [],
            'risk_management': [],
            'indicators': [],
            'patterns': [],
            'market_analysis': [],
            'key_points': []
        }
        
        all_summaries = []
        
        for i, transcript_file in enumerate(transcript_files, 1):
            print(f"处理 {i}/{len(transcript_files)}: {transcript_file.name}")
            
            # 读取文本
            with open(transcript_file, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # 提取规则
            rules = self.extract_rules_from_text(text, transcript_file.stem)
            
            # 总结要点
            key_points = self.summarize_key_points(text)
            rules['key_points'] = key_points
            
            # 合并规则
            for key in all_rules:
                all_rules[key].extend(rules[key])
            
            # 保存单个视频的规则
            video_rules_file = self.rules_dir / f"{transcript_file.stem}_rules.json"
            with open(video_rules_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'video': transcript_file.stem,
                    'text_length': len(text),
                    'rules': rules,
                    'summary': {
                        'total_rules': sum(len(rules[k]) for k in rules if k != 'key_points'),
                        'key_points_count': len(key_points)
                    }
                }, f, indent=2, ensure_ascii=False)
            
            all_summaries.append({
                'video': transcript_file.stem,
                'text_length': len(text),
                'rules_count': sum(len(rules[k]) for k in rules if k != 'key_points'),
                'key_points': key_points[:5]  # 前5个要点
            })
            
            print(f"  ✓ 提取 {sum(len(rules[k]) for k in rules if k != 'key_points')} 条规则")
            print(f"  ✓ 总结 {len(key_points)} 个关键要点")
            print()
        
        # 保存所有规则
        rules_file = self.rules_dir / "chiba_trading_rules.json"
        with open(rules_file, 'w', encoding='utf-8') as f:
            json.dump({
                'extracted_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'source_videos': [f.stem for f in transcript_files],
                'rules': all_rules,
                'summary': {
                    'total_entry_conditions': len(all_rules['entry_conditions']),
                    'total_stop_loss_rules': len(all_rules['stop_loss_rules']),
                    'total_take_profit_rules': len(all_rules['take_profit_rules']),
                    'total_risk_management': len(all_rules['risk_management']),
                    'total_indicators': len(all_rules['indicators']),
                    'total_patterns': len(all_rules['patterns']),
                    'total_market_analysis': len(all_rules['market_analysis']),
                    'total_key_points': len(all_rules['key_points'])
                }
            }, f, indent=2, ensure_ascii=False)
        
        print("=" * 80)
        print("✓ 规则提取完成")
        print("=" * 80)
        print()
        print(f"规则文件: {rules_file}")
        print()
        print("规则统计:")
        for key, value in all_rules.items():
            if key != 'key_points' or len(value) > 0:
                print(f"  {key}: {len(value)} 条")
        print()
        
        # 生成精华总结
        self.generate_summary(all_rules, all_summaries)
        
        return rules_file
    
    def generate_summary(self, all_rules: dict, summaries: list):
        """生成精华总结"""
        summary_file = self.rules_dir / "chiba_trading_summary.md"
        
        lines = []
        lines.append("# 千叶交易系统 - 精华总结")
        lines.append("")
        lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # 关键要点
        lines.append("## 关键要点")
        lines.append("")
        for i, point in enumerate(all_rules['key_points'][:10], 1):
            lines.append(f"{i}. {point}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # 入场条件
        if all_rules['entry_conditions']:
            lines.append("## 入场条件")
            lines.append("")
            for i, rule in enumerate(all_rules['entry_conditions'][:10], 1):
                lines.append(f"{i}. {rule['text']}")
            lines.append("")
            lines.append("---")
            lines.append("")
        
        # 止损规则
        if all_rules['stop_loss_rules']:
            lines.append("## 止损规则")
            lines.append("")
            for i, rule in enumerate(all_rules['stop_loss_rules'][:10], 1):
                lines.append(f"{i}. {rule['text']}")
                if 'numbers' in rule:
                    lines.append(f"   数值: {rule['numbers']}")
            lines.append("")
            lines.append("---")
            lines.append("")
        
        # 止盈规则
        if all_rules['take_profit_rules']:
            lines.append("## 止盈规则")
            lines.append("")
            for i, rule in enumerate(all_rules['take_profit_rules'][:10], 1):
                lines.append(f"{i}. {rule['text']}")
                if 'numbers' in rule:
                    lines.append(f"   数值: {rule['numbers']}")
            lines.append("")
            lines.append("---")
            lines.append("")
        
        # 风险管理
        if all_rules['risk_management']:
            lines.append("## 风险管理")
            lines.append("")
            for i, rule in enumerate(all_rules['risk_management'][:10], 1):
                lines.append(f"{i}. {rule['text']}")
            lines.append("")
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print(f"✓ 精华总结已保存: {summary_file}")


def main():
    """主函数"""
    extractor = RuleExtractor()
    rules_file = extractor.process_all_transcripts()
    
    if rules_file:
        print()
        print("下一步: 生成交易信号")
        print("  python src/chiba_trading_system/chiba_trading_system.py")


if __name__ == '__main__':
    main()



