#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
千叶交易系统 - 完整视频分析
下载视频、转录、提取规则、生成信号
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


class CompleteVideoAnalysis:
    """完整视频分析器"""
    
    def __init__(self):
        self.videos_dir = Path(__file__).parent.parent.parent / "data" / "chiba_videos"
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        self.downloads_dir = self.videos_dir / "downloads"
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        self.transcripts_dir = self.videos_dir / "transcripts"
        self.transcripts_dir.mkdir(parents=True, exist_ok=True)
        self.rules_dir = self.videos_dir / "rules"
        self.rules_dir.mkdir(parents=True, exist_ok=True)
        
        self.video_urls = [
            "https://www.youtube.com/watch?v=r-1F__Ed-e4",
            "https://www.youtube.com/watch?v=-iW_GEN95IU",
            "https://www.youtube.com/watch?v=efHztTLabcU"
        ]
    
    def download_video(self, url: str) -> Optional[Path]:
        """下载视频（仅音频）"""
        try:
            import yt_dlp
            
            print(f"  正在下载: {url}")
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': str(self.downloads_dir / '%(id)s.%(ext)s'),
                'quiet': False,
                'extract_flat': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                video_id = info.get('id')
                
                # 查找下载的文件
                downloaded_files = list(self.downloads_dir.glob(f"{video_id}.*"))
                if downloaded_files:
                    print(f"  ✓ 下载完成: {downloaded_files[0].name}")
                    return downloaded_files[0]
                else:
                    print(f"  ✗ 未找到下载文件")
                    return None
                    
        except Exception as e:
            print(f"  ✗ 下载失败: {e}")
            return None
    
    def transcribe_video(self, video_path: Path) -> Optional[Dict]:
        """转录视频"""
        try:
            import whisper
            
            print(f"  正在转录: {video_path.name}")
            print(f"    （这可能需要几分钟，请耐心等待...）")
            
            # 使用base模型（速度较快）
            model = whisper.load_model("base")
            
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
            
            return result
            
        except Exception as e:
            print(f"  ✗ 转录失败: {e}")
            return None
    
    def extract_trading_rules(self, transcript: Dict, video_id: str) -> Dict:
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
                            'video_id': video_id,
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
    
    def analyze_all_videos(self):
        """分析所有视频"""
        print("=" * 80)
        print("千叶交易系统 - 完整视频分析")
        print("=" * 80)
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
        
        for i, url in enumerate(self.video_urls, 1):
            print("=" * 80)
            print(f"视频 {i}/{len(self.video_urls)}")
            print("=" * 80)
            print()
            
            video_id = url.split('v=')[-1]
            
            # 1. 下载视频
            video_path = self.download_video(url)
            if not video_path:
                print("  跳过此视频（下载失败）")
                print()
                continue
            
            print()
            
            # 2. 转录视频
            transcript = self.transcribe_video(video_path)
            if not transcript:
                print("  跳过此视频（转录失败）")
                print()
                continue
            
            all_transcripts.append({
                'url': url,
                'video_id': video_id,
                'transcript': transcript
            })
            
            print()
            
            # 3. 提取规则
            rules = self.extract_trading_rules(transcript, video_id)
            
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
                'source_videos': [url.split('v=')[-1] for url in self.video_urls],
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
        
        # 保存完整分析结果
        analysis_file = self.videos_dir / "complete_analysis.json"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump({
                'analyzed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'videos': all_transcripts,
                'rules': all_rules
            }, f, indent=2, ensure_ascii=False)
        
        print(f"✓ 完整分析已保存: {analysis_file}")
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
    analyzer = CompleteVideoAnalysis()
    rules_file = analyzer.analyze_all_videos()
    
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
        print("分析未完成")
        print("=" * 80)
        print()
        print("请检查错误信息并重试")


if __name__ == '__main__':
    main()









