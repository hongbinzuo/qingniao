#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
千叶交易系统 - 处理本地视频文件
处理用户已下载的视频文件，转录并提取交易规则
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
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


class LocalVideoProcessor:
    """本地视频处理器"""
    
    def __init__(self, videos_dir: Path = None):
        if videos_dir is None:
            self.videos_dir = Path(__file__).parent.parent.parent / "data" / "chiba_videos" / "downloads"
        else:
            self.videos_dir = Path(videos_dir)
        
        self.transcripts_dir = self.videos_dir.parent / "transcripts"
        self.transcripts_dir.mkdir(parents=True, exist_ok=True)
        self.rules_dir = self.videos_dir.parent / "rules"
        self.rules_dir.mkdir(parents=True, exist_ok=True)
    
    def find_video_files(self) -> List[Path]:
        """查找视频文件"""
        video_extensions = ['.webm', '.mp4', '.mkv', '.avi', '.mov', '.m4v']
        video_files = []
        
        for ext in video_extensions:
            video_files.extend(self.videos_dir.glob(f"*{ext}"))
        
        # 排除.part文件
        video_files = [f for f in video_files if not f.name.endswith('.part')]
        
        return sorted(video_files)
    
    def transcribe_video(self, video_path: Path) -> Optional[Dict]:
        """转录视频"""
        try:
            import whisper
            
            print(f"正在转录: {video_path.name}")
            print(f"  （这可能需要几分钟，请耐心等待...）")
            
            # 清除缓存后重新下载模型
            try:
                # 使用tiny模型（更快）
                model = whisper.load_model("tiny")
            except RuntimeError as e:
                if "SHA256" in str(e):
                    print("  模型文件损坏，正在重新下载...")
                    import os
                    import shutil
                    cache_dir = os.path.expanduser('~/.cache/whisper')
                    shutil.rmtree(cache_dir, ignore_errors=True)
                    model = whisper.load_model("tiny")
                else:
                    raise
            
            # 转录
            result = model.transcribe(str(video_path), language="zh")
            
            # 保存转录结果
            transcript_file = self.transcripts_dir / f"{video_path.stem}.json"
            with open(transcript_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            # 保存文本
            text_file = self.transcripts_dir / f"{video_path.stem}.txt"
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(result['text'])
            
            print(f"  ✓ 转录完成")
            print(f"    - 文本长度: {len(result['text'])} 字符")
            print(f"    - 段落数: {len(result.get('segments', []))}")
            print(f"    - JSON: {transcript_file.name}")
            print(f"    - 文本: {text_file.name}")
            
            return result
            
        except ImportError:
            print("  ✗ 需要安装 openai-whisper")
            print("    安装命令: pip install openai-whisper")
            return None
        except Exception as e:
            print(f"  ✗ 转录失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def extract_trading_rules(self, transcript: Dict, video_name: str) -> Dict:
        """从转录文本中提取交易规则"""
        text = transcript.get('text', '')
        segments = transcript.get('segments', [])
        
        print(f"  正在提取交易规则...")
        
        rules = {
            'entry_conditions': [],
            'stop_loss_rules': [],
            'take_profit_rules': [],
            'risk_management': [],
            'indicators': [],
            'patterns': [],
            'market_analysis': []
        }
        
        # 交易关键词模式
        patterns = {
            'entry': [
                r'入场|开仓|买入|卖出|做多|做空|entry|buy|sell|long|short',
                r'突破|回调|反弹|支撑|阻力|support|resistance|breakout|pullback'
            ],
            'stop_loss': [
                r'止损|stop\s*loss|sl|止损点|stop',
                r'(\d+(?:\.\d+)?)\s*%?\s*止损',
                r'止损.*?(\d+(?:\.\d+)?)\s*%?'
            ],
            'take_profit': [
                r'止盈|take\s*profit|tp|目标|止盈点|profit',
                r'(\d+(?:\.\d+)?)\s*%?\s*止盈',
                r'止盈.*?(\d+(?:\.\d+)?)\s*%?',
                r'目标.*?(\d+(?:\.\d+)?)\s*%?'
            ],
            'risk': [
                r'风险|仓位|资金管理|risk|position|资金|仓位管理',
                r'(\d+(?:\.\d+)?)\s*%?\s*仓位',
                r'风险.*?(\d+(?:\.\d+)?)\s*%?'
            ],
            'indicator': [
                r'均线|MA|EMA|SMA|MACD|RSI|指标|moving\s*average',
                r'(\d+)\s*日均线|(\d+)\s*日MA',
                r'金叉|死叉|golden\s*cross|death\s*cross'
            ],
            'pattern': [
                r'形态|双顶|双底|头肩|三角形|pattern|突破|回调',
                r'M顶|W底|头肩顶|头肩底',
                r'FVG|order\s*block|OTE'
            ],
            'market': [
                r'BTC|比特币|bitcoin|黄金|gold|白银|silver|XAU|XAG',
                r'看涨|看跌|bullish|bearish|上涨|下跌',
                r'趋势|trend|上升趋势|下降趋势'
            ]
        }
        
        # 从段落中提取
        for segment in segments:
            text_segment = segment.get('text', '').strip()
            if not text_segment or len(text_segment) < 3:
                continue
            
            time_start = segment.get('start', 0)
            time_end = segment.get('end', 0)
            
            # 检查每个规则类型
            for rule_type, pattern_list in patterns.items():
                for pattern in pattern_list:
                    if re.search(pattern, text_segment, re.IGNORECASE):
                        rule_entry = {
                            'text': text_segment,
                            'start_time': time_start,
                            'end_time': time_end,
                            'video_name': video_name,
                            'pattern_matched': pattern
                        }
                        
                        # 提取数字（如果有）
                        numbers = re.findall(r'\d+(?:\.\d+)?', text_segment)
                        if numbers:
                            rule_entry['numbers'] = [float(n) for n in numbers]
                        
                        # 分类到对应的规则类型
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
                        
                        break  # 每个段落只匹配一次
        
        # 去重（基于文本相似度）
        for key in rules:
            seen = set()
            unique_rules = []
            for rule in rules[key]:
                text_key = rule['text'][:50]  # 使用前50字符作为唯一标识
                if text_key not in seen:
                    seen.add(text_key)
                    unique_rules.append(rule)
            rules[key] = unique_rules
        
        print(f"  ✓ 提取规则:")
        print(f"    - 入场条件: {len(rules['entry_conditions'])} 条")
        print(f"    - 止损规则: {len(rules['stop_loss_rules'])} 条")
        print(f"    - 止盈规则: {len(rules['take_profit_rules'])} 条")
        print(f"    - 风险管理: {len(rules['risk_management'])} 条")
        print(f"    - 技术指标: {len(rules['indicators'])} 条")
        print(f"    - 图表形态: {len(rules['patterns'])} 条")
        print(f"    - 市场分析: {len(rules['market_analysis'])} 条")
        
        return rules
    
    def process_all_videos(self):
        """处理所有视频"""
        print("=" * 80)
        print("千叶交易系统 - 处理本地视频文件")
        print("=" * 80)
        print()
        print(f"视频目录: {self.videos_dir}")
        print()
        
        # 查找视频文件
        video_files = self.find_video_files()
        
        if not video_files:
            print("未找到视频文件")
            print()
            print("请将视频文件放在以下目录:")
            print(f"  {self.videos_dir}")
            print()
            print("支持的格式: .webm, .mp4, .mkv, .avi, .mov, .m4v")
            return None
        
        print(f"找到 {len(video_files)} 个视频文件:")
        for vf in video_files:
            print(f"  - {vf.name}")
        print()
        
        all_rules = {
            'entry_conditions': [],
            'stop_loss_rules': [],
            'take_profit_rules': [],
            'risk_management': [],
            'indicators': [],
            'patterns': [],
            'market_analysis': []
        }
        
        all_transcripts = []
        
        for i, video_file in enumerate(video_files, 1):
            print("=" * 80)
            print(f"视频 {i}/{len(video_files)}: {video_file.name}")
            print("=" * 80)
            print()
            
            # 检查是否已转录
            transcript_file = self.transcripts_dir / f"{video_file.stem}.txt"
            if transcript_file.exists():
                print(f"  ✓ 已存在转录文件，跳过转录")
                print(f"    转录文件: {transcript_file.name}")
                print()
                
                # 读取已有转录
                with open(transcript_file, 'r', encoding='utf-8') as f:
                    transcript_text = f.read()
                
                # 尝试读取JSON
                json_file = self.transcripts_dir / f"{video_file.stem}.json"
                if json_file.exists():
                    with open(json_file, 'r', encoding='utf-8') as f:
                        transcript = json.load(f)
                else:
                    # 创建简单的转录结构
                    transcript = {
                        'text': transcript_text,
                        'segments': []
                    }
            else:
                # 转录视频
                transcript = self.transcribe_video(video_file)
                if not transcript:
                    print("  跳过此视频（转录失败）")
                    print()
                    continue
            
            all_transcripts.append({
                'video_file': str(video_file),
                'video_name': video_file.name,
                'transcript': transcript
            })
            
            print()
            
            # 提取规则
            rules = self.extract_trading_rules(transcript, video_file.name)
            
            # 合并规则
            for key in all_rules:
                all_rules[key].extend(rules[key])
            
            print()
        
        # 保存所有结果
        print("=" * 80)
        print("保存分析结果")
        print("=" * 80)
        print()
        
        # 保存规则
        rules_file = self.rules_dir / "chiba_trading_rules.json"
        with open(rules_file, 'w', encoding='utf-8') as f:
            json.dump({
                'extracted_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'source_videos': [t['video_name'] for t in all_transcripts],
                'rules': all_rules,
                'summary': {
                    'total_entry_conditions': len(all_rules['entry_conditions']),
                    'total_stop_loss_rules': len(all_rules['stop_loss_rules']),
                    'total_take_profit_rules': len(all_rules['take_profit_rules']),
                    'total_risk_management': len(all_rules['risk_management']),
                    'total_indicators': len(all_rules['indicators']),
                    'total_patterns': len(all_rules['patterns']),
                    'total_market_analysis': len(all_rules['market_analysis'])
                }
            }, f, indent=2, ensure_ascii=False)
        
        print(f"✓ 规则已保存: {rules_file}")
        print()
        
        # 打印摘要
        print("=" * 80)
        print("分析完成 - 规则摘要")
        print("=" * 80)
        print()
        for key, value in all_rules.items():
            print(f"  {key}: {len(value)} 条")
        print()
        
        return rules_file


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='处理本地视频文件并提取交易规则')
    parser.add_argument('--videos-dir', type=str, help='视频文件目录（可选）')
    args = parser.parse_args()
    
    videos_dir = Path(args.videos_dir) if args.videos_dir else None
    processor = LocalVideoProcessor(videos_dir)
    rules_file = processor.process_all_videos()
    
    if rules_file and rules_file.exists():
        print("=" * 80)
        print("下一步")
        print("=" * 80)
        print()
        print("规则已提取完成！现在可以运行交易系统生成信号：")
        print()
        print("  python src/chiba_trading_system/chiba_trading_system.py")
        print()
    else:
        print("=" * 80)
        print("处理未完成")
        print("=" * 80)
        print()
        print("请检查视频文件是否已放置在正确目录")


if __name__ == '__main__':
    main()



