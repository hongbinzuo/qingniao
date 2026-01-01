#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
千叶交易系统 - 视频分析模块
从YouTube视频中提取交易规则
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
import json

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))


class VideoAnalyzer:
    """视频分析器"""
    
    def __init__(self):
        self.videos_dir = Path(__file__).parent.parent.parent / "data" / "chiba_videos"
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        self.transcripts_dir = self.videos_dir / "transcripts"
        self.transcripts_dir.mkdir(parents=True, exist_ok=True)
    
    def download_youtube_video(self, url: str) -> Optional[Path]:
        """下载YouTube视频"""
        try:
            import yt_dlp
            
            print(f"正在下载视频: {url}")
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': str(self.videos_dir / '%(title)s.%(ext)s'),
                'quiet': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                video_path = Path(ydl.prepare_filename(info))
                print(f"✓ 视频已下载: {video_path}")
                return video_path
                
        except ImportError:
            print("错误: 需要安装 yt-dlp")
            print("安装命令: pip install yt-dlp")
            return None
        except Exception as e:
            print(f"下载失败: {e}")
            return None
    
    def transcribe_video(self, video_path: Path) -> Optional[Dict]:
        """转录视频为文字"""
        try:
            import whisper
            
            print(f"正在转录视频: {video_path.name}")
            
            # 加载Whisper模型
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
            
            print(f"✓ 转录完成: {transcript_file}")
            print(f"✓ 文本保存: {text_file}")
            
            return result
            
        except ImportError:
            print("错误: 需要安装 openai-whisper")
            print("安装命令: pip install openai-whisper")
            return None
        except Exception as e:
            print(f"转录失败: {e}")
            return None
    
    def extract_trading_rules(self, transcript: Dict) -> List[Dict]:
        """从转录文本中提取交易规则"""
        text = transcript.get('text', '')
        segments = transcript.get('segments', [])
        
        print("正在提取交易规则...")
        
        # 关键词列表
        trading_keywords = [
            '入场', '开仓', '买入', '卖出', '做多', '做空',
            '止损', '止盈', '平仓', '出场',
            '支撑', '阻力', '突破', '回调',
            '均线', 'MA', 'EMA', 'MACD', 'RSI',
            '形态', '双顶', '双底', '头肩', '三角形',
            '风险', '仓位', '资金管理'
        ]
        
        rules = []
        
        # 查找包含交易关键词的段落
        for segment in segments:
            text_segment = segment.get('text', '')
            time_start = segment.get('start', 0)
            
            # 检查是否包含交易关键词
            if any(keyword in text_segment for keyword in trading_keywords):
                rule = {
                    'text': text_segment,
                    'start_time': time_start,
                    'end_time': segment.get('end', 0),
                    'keywords': [kw for kw in trading_keywords if kw in text_segment]
                }
                rules.append(rule)
        
        print(f"✓ 提取了 {len(rules)} 条潜在规则")
        
        return rules
    
    def analyze_video(self, url: str) -> Dict:
        """分析视频（下载+转录+提取规则）"""
        print("=" * 80)
        print("千叶交易系统 - 视频分析")
        print("=" * 80)
        print()
        
        # 1. 下载视频
        video_path = self.download_youtube_video(url)
        if not video_path:
            return {}
        
        print()
        
        # 2. 转录视频
        transcript = self.transcribe_video(video_path)
        if not transcript:
            return {}
        
        print()
        
        # 3. 提取交易规则
        rules = self.extract_trading_rules(transcript)
        
        print()
        print("=" * 80)
        print("分析完成")
        print("=" * 80)
        print(f"视频: {video_path.name}")
        print(f"转录文本长度: {len(transcript.get('text', ''))} 字符")
        print(f"提取规则数: {len(rules)}")
        print()
        
        return {
            'video_path': str(video_path),
            'transcript': transcript,
            'rules': rules
        }


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='千叶交易系统 - 视频分析')
    parser.add_argument('--url', type=str, help='YouTube视频链接')
    parser.add_argument('--video', type=str, help='本地视频文件路径')
    
    args = parser.parse_args()
    
    analyzer = VideoAnalyzer()
    
    if args.url:
        result = analyzer.analyze_video(args.url)
    elif args.video:
        video_path = Path(args.video)
        if video_path.exists():
            transcript = analyzer.transcribe_video(video_path)
            if transcript:
                rules = analyzer.extract_trading_rules(transcript)
                result = {
                    'video_path': str(video_path),
                    'transcript': transcript,
                    'rules': rules
                }
            else:
                result = {}
        else:
            print(f"错误: 视频文件不存在: {args.video}")
            result = {}
    else:
        print("请提供YouTube视频链接 (--url) 或本地视频文件 (--video)")
        result = {}
    
    # 保存结果
    if result:
        output_file = Path(__file__).parent.parent.parent / "data" / "chiba_videos" / "analysis_result.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"✓ 分析结果已保存: {output_file}")

if __name__ == '__main__':
    main()





