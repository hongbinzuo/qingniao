#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
千叶交易系统 - 下载并分析视频
尝试从YouTube链接下载视频并分析
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
import json
from datetime import datetime

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))


class VideoDownloaderAndAnalyzer:
    """视频下载和分析器"""
    
    def __init__(self):
        self.videos_dir = Path(__file__).parent.parent.parent / "data" / "chiba_videos"
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        self.transcripts_dir = self.videos_dir / "transcripts"
        self.transcripts_dir.mkdir(parents=True, exist_ok=True)
        
        # 视频链接
        self.video_urls = [
            "https://www.youtube.com/watch?v=r-1F__Ed-e4",
            "https://www.youtube.com/watch?v=-iW_GEN95IU",
            "https://www.youtube.com/watch?v=efHztTLabcU"
        ]
    
    def check_dependencies(self):
        """检查依赖"""
        print("检查依赖...")
        print()
        
        dependencies = {
            'yt_dlp': False,
            'whisper': False
        }
        
        # 检查yt-dlp
        try:
            import yt_dlp
            dependencies['yt_dlp'] = True
            print("✓ yt-dlp 已安装")
        except ImportError:
            print("✗ yt-dlp 未安装")
            print("  安装命令: pip install yt-dlp")
        
        # 检查whisper
        try:
            import whisper
            dependencies['whisper'] = True
            print("✓ openai-whisper 已安装")
        except ImportError:
            print("✗ openai-whisper 未安装")
            print("  安装命令: pip install openai-whisper")
        
        print()
        return dependencies
    
    def download_video(self, url: str) -> Optional[Path]:
        """下载YouTube视频"""
        try:
            import yt_dlp
            
            print(f"正在下载: {url}")
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': str(self.videos_dir / '%(title)s.%(ext)s'),
                'quiet': False,
                'extract_flat': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                video_path = Path(ydl.prepare_filename(info))
                
                # 如果文件不存在，尝试查找
                if not video_path.exists():
                    # 查找最近创建的文件
                    files = sorted(self.videos_dir.glob('*'), key=lambda p: p.stat().st_mtime, reverse=True)
                    if files:
                        video_path = files[0]
                
                if video_path.exists():
                    print(f"✓ 视频已下载: {video_path.name}")
                    return video_path
                else:
                    print(f"✗ 视频下载失败")
                    return None
                    
        except ImportError:
            print("✗ 需要安装 yt-dlp")
            print("  安装命令: pip install yt-dlp")
            return None
        except Exception as e:
            print(f"✗ 下载失败: {e}")
            return None
    
    def transcribe_video(self, video_path: Path) -> Optional[Dict]:
        """转录视频"""
        try:
            import whisper
            
            print(f"正在转录: {video_path.name}")
            print("  这可能需要几分钟...")
            
            # 加载模型
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
            
            print(f"✓ 转录完成")
            print(f"  - JSON: {transcript_file.name}")
            print(f"  - 文本: {text_file.name}")
            print(f"  - 文本长度: {len(result['text'])} 字符")
            
            return result
            
        except ImportError:
            print("✗ 需要安装 openai-whisper")
            print("  安装命令: pip install openai-whisper")
            return None
        except Exception as e:
            print(f"✗ 转录失败: {e}")
            return None
    
    def extract_trading_rules(self, transcript: Dict) -> Dict:
        """从转录文本中提取交易规则"""
        text = transcript.get('text', '')
        segments = transcript.get('segments', [])
        
        print("正在提取交易规则...")
        
        # 交易关键词
        trading_keywords = {
            'entry': ['入场', '开仓', '买入', '卖出', '做多', '做空', 'entry', 'buy', 'sell'],
            'stop_loss': ['止损', 'stop loss', 'sl', '止损点', 'stop'],
            'take_profit': ['止盈', 'take profit', 'tp', '目标', '止盈点', 'profit'],
            'risk': ['风险', '仓位', '资金管理', 'risk', 'position', '资金'],
            'indicator': ['均线', 'MA', 'EMA', 'MACD', 'RSI', '指标', 'moving average'],
            'pattern': ['形态', '双顶', '双底', '头肩', '三角形', 'pattern', '突破', '回调']
        }
        
        rules = {
            'entry_conditions': [],
            'stop_loss_rules': [],
            'take_profit_rules': [],
            'risk_management': [],
            'indicators': [],
            'patterns': []
        }
        
        # 从段落中提取
        for segment in segments:
            text_segment = segment.get('text', '')
            time_start = segment.get('start', 0)
            
            # 检查是否包含交易关键词
            for rule_type, keywords in trading_keywords.items():
                if any(kw in text_segment for kw in keywords):
                    rule_entry = {
                        'text': text_segment,
                        'start_time': time_start,
                        'end_time': segment.get('end', 0),
                        'keywords': [kw for kw in keywords if kw in text_segment]
                    }
                    
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
        
        print(f"✓ 提取规则:")
        print(f"  - 入场条件: {len(rules['entry_conditions'])} 条")
        print(f"  - 止损规则: {len(rules['stop_loss_rules'])} 条")
        print(f"  - 止盈规则: {len(rules['take_profit_rules'])} 条")
        print(f"  - 风险管理: {len(rules['risk_management'])} 条")
        print(f"  - 技术指标: {len(rules['indicators'])} 条")
        print(f"  - 图表形态: {len(rules['patterns'])} 条")
        
        return rules
    
    def analyze_all_videos(self):
        """分析所有视频"""
        print("=" * 80)
        print("千叶交易系统 - 视频下载和分析")
        print("=" * 80)
        print()
        
        # 检查依赖
        deps = self.check_dependencies()
        
        if not deps['yt_dlp'] or not deps['whisper']:
            print("=" * 80)
            print("需要安装依赖")
            print("=" * 80)
            print()
            print("安装命令:")
            print("  pip install yt-dlp openai-whisper")
            print()
            print("或者，在Claude Code中直接分析视频（推荐）")
            print()
            return
        
        print("=" * 80)
        print(f"开始分析 {len(self.video_urls)} 个视频")
        print("=" * 80)
        print()
        
        all_results = []
        all_rules = {
            'entry_conditions': [],
            'stop_loss_rules': [],
            'take_profit_rules': [],
            'risk_management': [],
            'indicators': [],
            'patterns': []
        }
        
        for i, url in enumerate(self.video_urls, 1):
            print("=" * 80)
            print(f"视频 {i}/{len(self.video_urls)}")
            print("=" * 80)
            print()
            
            # 下载视频
            video_path = self.download_video(url)
            if not video_path:
                print("跳过此视频")
                print()
                continue
            
            print()
            
            # 转录视频
            transcript = self.transcribe_video(video_path)
            if not transcript:
                print("跳过此视频")
                print()
                continue
            
            print()
            
            # 提取规则
            rules = self.extract_trading_rules(transcript)
            
            # 合并规则
            for key in all_rules:
                all_rules[key].extend(rules[key])
            
            result = {
                'url': url,
                'video_path': str(video_path),
                'transcript': transcript,
                'rules': rules
            }
            all_results.append(result)
            
            print()
        
        # 保存所有结果
        output_file = self.videos_dir / "all_analysis_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'analyzed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'videos': all_results,
                'combined_rules': all_rules
            }, f, indent=2, ensure_ascii=False)
        
        print("=" * 80)
        print("分析完成")
        print("=" * 80)
        print()
        print(f"✓ 结果已保存: {output_file}")
        print()
        print("提取的规则统计:")
        for key, value in all_rules.items():
            print(f"  - {key}: {len(value)} 条")
        print()


def main():
    """主函数"""
    analyzer = VideoDownloaderAndAnalyzer()
    analyzer.analyze_all_videos()

if __name__ == '__main__':
    main()






